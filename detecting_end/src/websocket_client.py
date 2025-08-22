import asyncio
import websockets
import json
import logging
import time
import re
import traceback
from threading import Lock
from urllib.parse import urlparse
import ssl

logger = logging.getLogger('websocket_client')

class TerminalWebSocketClient:
    """WebSocket客户端，用于与Django后端通信"""
    
    def __init__(self, server_url, terminal_id, on_command=None):
        self.server_url = server_url
        self.terminal_id = terminal_id
        self.ws = None
        self.connected = False
        self.on_command = on_command
        self.reconnect_attempts = 0
        # max_reconnect_attempts=None 表示无限重连
        self.max_reconnect_attempts = None
        self.reconnect_delay = 2  # 初始重连延迟(秒)
        self.reconnect_task = None
        self.heartbeat_task = None
        self.running = False
        
        # 添加SSL上下文配置
        self.ssl_context = None
        if server_url and server_url.startswith('wss://'):
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # 添加任务跟踪
        self.tasks = set()
        self.tasks_lock = Lock()
        self.loop = None
    
    def is_connected(self):
        """返回当前WebSocket连接状态"""
        return self.connected and self.ws is not None
    
    async def start(self):
        """启动WebSocket客户端"""
        self.running = True
        self.reconnect_attempts = 0
        # 仅绑定当前线程正在运行的事件循环
        self.loop = asyncio.get_running_loop()
        await self.connect()
        # 首次连接失败则启动重连循环
        if not self.connected and self.running:
            await self.schedule_reconnect()
        return self.connected
    
    async def stop(self):
        """停止WebSocket客户端"""
        logger.info("正在停止WebSocket客户端...")
        self.running = False
        
        # 取消所有跟踪任务
        with self.tasks_lock:
            for task in list(self.tasks):
                if not task.done():
                    try:
                        task.cancel()
                    except Exception as e:
                        logger.error(f"取消任务时出错: {str(e)}")
            self.tasks.clear()
            
        # 断开连接
        await self.disconnect()
        logger.info("WebSocket客户端已停止")
    
    def _create_task(self, coro):
        """安全地创建任务并跟踪它"""
        # 使用已绑定在 start() 中的 loop，避免跨线程误建新的loop
        if not self.loop or self.loop.is_closed():
            logger.warning("事件循环不可用，忽略任务创建")
            return asyncio.get_running_loop().create_task(asyncio.sleep(0))  # 占位，避免返回None
        task = self.loop.create_task(coro)
        
        with self.tasks_lock:
            self.tasks.add(task)
            
        # 添加任务完成回调以移除跟踪
        task.add_done_callback(self._remove_task)
        return task
    
    def _remove_task(self, task):
        """从任务集合中移除已完成的任务"""
        with self.tasks_lock:
            if task in self.tasks:
                self.tasks.remove(task)
    
    def normalize_ws_url(self, url, terminal_id=None):
        """标准化WebSocket URL，确保格式正确"""
        # 使用传入的terminal_id，如果没有则使用实例的terminal_id
        if terminal_id is None:
            terminal_id = self.terminal_id
            
        # 解析URL
        parsed_url = urlparse(url)
        
        # 检查协议
        if parsed_url.scheme not in ('ws', 'wss'):
            # 如果URL没有websocket协议，尝试判断是否是HTTP(S) URL
            if parsed_url.scheme in ('http', 'https'):
                # 将http -> ws, https -> wss
                new_scheme = 'ws' if parsed_url.scheme == 'http' else 'wss'
            else:
                # 默认使用ws协议
                new_scheme = 'ws'
                # 如果提供的是完整域名但没有协议，则解析可能不正确，需要重新构建
                if not parsed_url.netloc and parsed_url.path:
                    # 假设第一段是域名
                    parts = parsed_url.path.split('/', 1)
                    parsed_url = urlparse(f"{new_scheme}://{parts[0]}")
                    if len(parts) > 1:
                        path = f"/{parts[1]}"
                    else:
                        path = ""
                else:
                    path = parsed_url.path
        else:
            new_scheme = parsed_url.scheme
            path = parsed_url.path
            
        # 确保路径包含terminal ID
        if path.endswith('/'):
            path = path[:-1]  # 去除尾部斜杠以便正确检查
            
        # 检查路径是否已包含终端ID
        terminal_pattern = re.compile(r'\/ws\/terminal\/\d+\/?$')
        if not terminal_pattern.search(path):
            # 路径不包含终端ID格式，构建正确的路径
            if '/ws/terminal/' in path:
                # 有ws/terminal前缀但没有ID，直接添加ID
                path = f"{path}/{terminal_id}/"
            else:
                # 完全没有ws/terminal路径，构建完整路径
                if path and not path.endswith('/'):
                    path += '/'
                path = f"{path}ws/terminal/{terminal_id}/"
        elif not path.endswith('/'):
            # 包含终端ID但没有尾部斜杠，添加斜杠
            path += '/'
            
        # 重新组合URL
        netloc = parsed_url.netloc or parsed_url.path.split('/')[0]
        
        # 根据是否有netloc决定最终的URL格式
        if netloc:
            final_url = f"{new_scheme}://{netloc}{path}"
        else:
            # 如果没有提取到netloc，可能是没有协议的URL
            final_url = f"{new_scheme}://{url}"
            # 尝试再次提取正确的终端ID路径
            final_url = self.normalize_ws_url(final_url, terminal_id)

        return final_url
    
    def get_ws_url(self):
        """获取WebSocket URL"""
        try:
            # 标准化URL
            return self.normalize_ws_url(self.server_url)
        except Exception as e:
            logger.error(f"构建WebSocket URL失败: {str(e)}")
            # 返回一个保守的默认值
            return f"ws://localhost/ws/terminal/{self.terminal_id}/"
    
    async def connect(self):
        """建立WebSocket连接"""
        if not self.running:
            return False
        # 已连接则跳过
        if self.is_connected():
            logger.debug("已连接，跳过重复连接")
            return True
            
        ws_url = self.get_ws_url()
        logger.info(f"尝试连接到WebSocket服务器: {ws_url}")
        
        try:
            self.ws = await asyncio.wait_for(
                websockets.connect(
                    ws_url, 
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5,
                    ssl=self.ssl_context if ws_url.startswith('wss://') else None,
                    max_size=10_000_000,
                    max_queue=32
                ),
                timeout=15
            )
            self.connected = True
            # 重连成功后清零计数
            self.reconnect_attempts = 0
            logger.info(f"WebSocket连接已建立: {ws_url}")
            
            # 成功后启动心跳，并进入消息循环（直到关闭）
            self.heartbeat_task = self._create_task(self.heartbeat_loop())
            await self.message_loop()
            return True
        except asyncio.TimeoutError:
            logger.error("WebSocket连接超时")
            self.connected = False
            self.ws = None
            # 注意：不在此处调度重连，统一由重连循环管理
            return False
        except ConnectionResetError:
            logger.warning("WebSocket连接被重置，连接失败")
            self.connected = False
            self.ws = None
            return False
        except Exception as e:
            logger.error(f"WebSocket连接失败: {str(e)}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            self.connected = False
            self.ws = None
            return False
    
    async def disconnect(self):
        """断开WebSocket连接"""
        if self.ws:
            try:
                await asyncio.wait_for(self.ws.close(), timeout=5)
                logger.info("WebSocket连接已关闭")
            except asyncio.TimeoutError:
                logger.warning("关闭WebSocket连接超时")
            except Exception as e:
                logger.error(f"关闭WebSocket连接时出错: {str(e)}")
            finally:
                self.ws = None
                self.connected = False
        # 断开时确保心跳任务被取消
        if self.heartbeat_task and not self.heartbeat_task.done():
            try:
                self.heartbeat_task.cancel()
            except Exception:
                pass
            finally:
                self.heartbeat_task = None
    
    async def message_loop(self):
        """消息接收循环"""
        if not self.ws:
            return
            
        try:
            async for message in self.ws:
                if not self.running:
                    logger.info("客户端已停止，中断消息循环")
                    break
                    
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except json.JSONDecodeError:
                    logger.error(f"接收到无效的JSON数据: {message}")
                except Exception as e:
                    logger.error(f"处理消息时出错: {str(e)}")
                    logger.error(f"异常堆栈: {traceback.format_exc()}")
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"WebSocket连接已关闭: {str(e)}")
            self.connected = False
            
            # 安排重连
            if self.running:
                await self.schedule_reconnect()
        except Exception as e:
            logger.error(f"WebSocket消息循环异常: {str(e)}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            self.connected = False
            
            # 安排重连
            if self.running:
                await self.schedule_reconnect()
    
    async def handle_message(self, data):
        """处理接收到的消息"""
        message_type = data.get('type')
        
        if message_type == 'heartbeat_response':
            # 心跳响应，无需特殊处理
            logger.debug("收到心跳响应")
            
        elif message_type == 'send_command':
            # 命令消息
            command = data.get('command')
            params = data.get('params', {})
            logger.info(f"收到命令: {command}, 参数: {params}")
            
            # 调用命令处理回调
            if self.on_command:
                try:
                    await self.on_command({
                        'command': command,
                        'params': params
                    })
                except Exception as e:
                    logger.error(f"执行命令回调时出错: {str(e)}")
                    # 添加异常堆栈信息以便调试
                    import traceback
                    logger.error(f"异常堆栈: {traceback.format_exc()}")
        elif message_type == 'status' or message_type == 'new_log' or message_type == 'logs_batch':
            logger.debug(f"收到服务端状态/日志反馈: {message_type}")
        elif message_type == 'command_response':
            # 根据布尔值显示“成功/失败”
            success = data.get('success')
            if success is None:
                success = (data.get('result') is True)
            status_text = '成功' if success else '失败'
            logger.info(f"命令响应（{data.get('command')}): {status_text}")
        elif message_type == 'connection_status':
            status = data.get('status')
            id = data.get('terminal_id')
            logger.info(f"连接状态: {status}, ID: {id}")
        else:
            # 其他消息类型
            logger.info(f"收到消息: {data}")
    
    async def send_message(self, data):
        """发送消息到服务器"""
        if not self.connected or not self.ws:
            logger.warning("尝试在未连接状态下发送消息")
            return False
        
        try:
            # 确保数据可以序列化为JSON
            safe_data = self._ensure_serializable(data)
            message = json.dumps(safe_data)
            
            # 使用超时确保发送不会阻塞过长时间
            await asyncio.wait_for(self.ws.send(message), timeout=5)
            return True
        except asyncio.TimeoutError:
            logger.error("发送消息超时")
            self.connected = False
            if self.running:
                await self.schedule_reconnect()
            return False
        except websockets.exceptions.ConnectionClosed:
            logger.error("发送消息时连接已关闭")
            self.connected = False
            if self.running:
                await self.schedule_reconnect()
            return False
        except json.JSONDecodeError:
            logger.error("消息无法序列化为JSON")
            return False
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            self.connected = False
            if self.running:
                await self.schedule_reconnect()
            return False

    def _ensure_serializable(self, data):
        """确保数据可序列化为JSON"""
        if isinstance(data, dict):
            return {k: self._ensure_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._ensure_serializable(item) for item in data]
        elif isinstance(data, tuple):
            # 修复：遍历元组本身，而不是类型
            return [self._ensure_serializable(item) for item in data]
        elif isinstance(data, (int, float, str, bool)) or data is None:
            return data
        else:
            return str(data)

    async def send_command_response(self, command, result, success=True):
        """发送命令执行结果响应"""
        try:
            safe_result = self._ensure_serializable(result)
            message = {
                'type': 'command_response',
                'command': command,
                'result': safe_result,
                'success': success,
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
            return await self.send_message(message)
        except Exception as e:
            logger.error(f"发送命令响应失败: {str(e)}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            return False

    async def send_nodes_data(self, nodes_data):
        """发送节点数据到服务器（主动推送节点配置）"""
        if not nodes_data:
            return False
        message = {
            'type': 'nodes_data',
            'nodes': nodes_data,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
        return await self.send_message(message)

    async def send_log(self, level, message, source=None):
        """发送日志消息到服务器（主动推送日志）"""
        try:
            log_data = {
                'type': 'log',
                'level': level,
                'message': message,
                'source': source or 'system',
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
            return await self.send_message(log_data)
        except Exception as e:
            logger.error(f"发送日志消息失败: {str(e)}")
            return False

    async def heartbeat_loop(self):
        """心跳循环，定期发送心跳消息"""
        while self.connected and self.running:
            try:
                heartbeat = {
                    'type': 'heartbeat',
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                }
                
                success = await self.send_message(heartbeat)
                if not success and self.running:
                    logger.warning("心跳发送失败，尝试重连")
                    await self.schedule_reconnect()
                    break
                    
                await asyncio.sleep(30)  # 30秒发送一次心跳
            except asyncio.CancelledError:
                logger.info("心跳任务已取消")
                break
            except Exception as e:
                logger.error(f"心跳发送失败: {str(e)}")
                logger.error(f"异常堆栈: {traceback.format_exc()}")
                
                # 只有在客户端仍在运行时才尝试重连
                if self.running:
                    await self.schedule_reconnect()
                break
    
    async def schedule_reconnect(self):
        """确保重连循环在运行（无限重连）"""
        if not self.running:
            logger.info("客户端已停止，不再尝试重连")
            return
        if self.reconnect_task and not self.reconnect_task.done():
            logger.debug("重连循环已在运行，跳过")
            return
        logger.info("启动重连循环")
        try:
            self.reconnect_task = self._create_task(self._reconnect_loop())
        except Exception as e:
            logger.error(f"创建重连循环失败: {str(e)}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
    
    async def _reconnect_loop(self):
        """持续重连循环，直到连接成功或停止运行"""
        try:
            while self.running and not self.is_connected():
                self.reconnect_attempts += 1
                # None 表示无限重连
                if self.max_reconnect_attempts is not None and self.reconnect_attempts > self.max_reconnect_attempts:
                    logger.error(f"超过最大重连尝试次数({self.max_reconnect_attempts})，停止重连")
                    break
                delay = min(60, self.reconnect_delay * (1.5 ** (self.reconnect_attempts - 1)))
                logger.info(f"将在 {delay:.1f} 秒后尝试重连 (尝试 {self.reconnect_attempts}/{self.max_reconnect_attempts or '∞'})")
                try:
                    await asyncio.sleep(delay)
                    if not self.running:
                        break
                    await self.connect()
                    if self.is_connected():
                        logger.info("重连成功")
                        self.reconnect_attempts = 0
                        break
                except asyncio.CancelledError:
                    logger.info("重连循环已取消")
                    break
                except Exception as e:
                    logger.error(f"重连过程中出错: {str(e)}")
                    logger.error(f"异常堆栈: {traceback.format_exc()}")
                    # 继续下一轮
        finally:
            self.reconnect_task = None

    async def send_system_status(self, status_data):
        """发送系统状态到服务器（用于系统监控主动推送）"""
        # 确保有终端ID
        if 'terminal_id' not in status_data and self.terminal_id:
            status_data['terminal_id'] = self.terminal_id
        message = {
            'type': 'system_status',
            'status': status_data,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
        if not self.is_connected():
            logger.warning("WebSocket未连接，无法发送系统状态")
            return False
        return await self.send_message(message)
       
    async def send_status(self, status_data):
        return await self.send_system_status(status_data)