import asyncio
import websockets
import json
import logging
import time
from threading import Thread

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
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 2  # 初始重连延迟(秒)
        self.reconnect_task = None
        self.heartbeat_task = None
        self.running = False
        
    async def start(self):
        """启动WebSocket客户端"""
        self.running = True
        self.reconnect_attempts = 0
        await self.connect()
        return self.connected
    
    async def stop(self):
        """停止WebSocket客户端"""
        self.running = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None
            
        if self.reconnect_task:
            self.reconnect_task.cancel()
            self.reconnect_task = None
            
        await self.disconnect()
    
    async def connect(self):
        """建立WebSocket连接"""
        if not self.running:
            return False
            
        ws_url = f"{self.server_url}/ws/terminal/{self.terminal_id}/"
        logger.info(f"尝试连接到WebSocket服务器: {ws_url}")
        
        try:
            self.ws = await websockets.connect(ws_url, ping_interval=30)
            self.connected = True
            self.reconnect_attempts = 0
            logger.info(f"WebSocket连接已建立: {ws_url}")
            
            # 开始心跳任务
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())
            
            # 开始消息接收循环
            await self.message_loop()
            
            return True
        except Exception as e:
            logger.error(f"WebSocket连接失败: {str(e)}")
            self.connected = False
            self.ws = None
            
            # 安排重连
            await self.schedule_reconnect()
            return False
    
    async def disconnect(self):
        """断开WebSocket连接"""
        if self.ws:
            try:
                await self.ws.close()
                logger.info("WebSocket连接已关闭")
            except Exception as e:
                logger.error(f"关闭WebSocket连接时出错: {str(e)}")
            finally:
                self.ws = None
                self.connected = False
    
    async def message_loop(self):
        """消息接收循环"""
        if not self.ws:
            return
            
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except json.JSONDecodeError:
                    logger.error(f"接收到无效的JSON数据: {message}")
                except Exception as e:
                    logger.error(f"处理消息时出错: {str(e)}")
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"WebSocket连接已关闭: {str(e)}")
            self.connected = False
            
            # 安排重连
            if self.running:
                await self.schedule_reconnect()
        except Exception as e:
            logger.error(f"WebSocket消息循环异常: {str(e)}")
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
            
        else:
            # 其他消息类型
            logger.info(f"收到消息: {data}")
    
    async def send_message(self, data):
        """发送消息到服务器"""
        if not self.connected or not self.ws:
            logger.warning("尝试在未连接状态下发送消息")
            return False
            
        try:
            message = json.dumps(data)
            await self.ws.send(message)
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            self.connected = False
            
            # 安排重连
            if self.running:
                await self.schedule_reconnect()
            return False
    
    async def send_nodes_data(self, nodes_data):
        """发送节点数据到服务器"""
        if not nodes_data:
            return False
            
        message = {
            'type': 'nodes_data',
            'nodes': nodes_data,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
        
        return await self.send_message(message)
    
    async def send_system_status(self, status_data):
        """发送系统状态到服务器"""
        message = {
            'type': 'system_status',
            'status': status_data,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
        
        return await self.send_message(message)
    
    async def send_log(self, level, message, source=None):
        """发送日志消息到服务器"""
        log_data = {
            'type': 'log',
            'level': level,
            'message': message,
            'source': source or 'system',
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
        
        return await self.send_message(log_data)
    
    async def heartbeat_loop(self):
        """心跳循环，定期发送心跳消息"""
        while self.connected and self.running:
            try:
                heartbeat = {
                    'type': 'heartbeat',
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                }
                
                await self.send_message(heartbeat)
                await asyncio.sleep(30)  # 30秒发送一次心跳
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳发送失败: {str(e)}")
                break
    
    async def schedule_reconnect(self):
        """安排重连任务"""
        if not self.running or self.reconnect_task:
            return
            
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.error(f"超过最大重连尝试次数({self.max_reconnect_attempts})，停止重连")
            return
        
        # 计算延迟时间（指数退避）
        delay = min(60, self.reconnect_delay * (1.5 ** (self.reconnect_attempts - 1)))
        logger.info(f"将在 {delay:.1f} 秒后尝试重连 (尝试 {self.reconnect_attempts}/{self.max_reconnect_attempts})")
        
        try:
            self.reconnect_task = asyncio.create_task(self._reconnect_after_delay(delay))
        except Exception as e:
            logger.error(f"创建重连任务失败: {str(e)}")
    
    async def _reconnect_after_delay(self, delay):
        """在延迟后重连"""
        try:
            await asyncio.sleep(delay)
            await self.connect()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"重连过程中出错: {str(e)}")
        finally:
            self.reconnect_task = None
