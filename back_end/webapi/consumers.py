import json
import logging
import asyncio
import traceback
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from .models import ProcessTerminal, HardwareNode, Area, HistoricalData

logger = logging.getLogger('django')

class TerminalConsumer(AsyncWebsocketConsumer):
    """终端WebSocket消费者，处理终端连接和消息"""
    
    async def connect(self):
        """处理WebSocket连接"""
        # 获取终端ID - 从URL路由参数
        self.terminal_id = self.scope['url_route']['kwargs']['terminal_id']
        self.group_name = f"terminal_{self.terminal_id}"
        self.is_detector = False  # 标记是否为检测端连接
        self.client_info = self.scope.get('client', ['Unknown', 0])
        
        # 增加连接日志，包含客户端信息
        logger.info(f"WebSocket连接请求 - 终端ID: {self.terminal_id}, 客户端: {self.client_info[0]}:{self.client_info[1]}")
        
        # 检查终端是否存在
        terminal_exists = await self.check_terminal_exists(self.terminal_id)
        if not terminal_exists:
            # 终端不存在，拒绝连接
            logger.warning(f"拒绝连接 - 终端ID {self.terminal_id} 不存在")
            await self.close(code=4004)
            return
            
        # 将连接添加到组
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # 接受WebSocket连接
        await self.accept()
        
        # 发送连接确认消息
        await self.send(text_data=json.dumps({
            'type': 'connection_status',
            'status': 'connected',
            'terminal_id': self.terminal_id,
            'timestamp': timezone.now().isoformat()
        }))
        
        logger.info(f"客户端已连接到终端 {self.terminal_id} 的WebSocket - {self.client_info[0]}:{self.client_info[1]}")
        
        # 添加: 启动连接心跳检查任务 
        self.heartbeat_check_task = asyncio.create_task(self.heartbeat_check_loop())
        
        # 如果不是检测端连接，主动发送最新日志
        if not self.is_detector:
            # 从缓存获取最新日志并发送
            cache_key = f"terminal:{self.terminal_id}:logs"
            cached_logs = cache.get(cache_key)
            if cached_logs:
                await self.send(text_data=json.dumps({
                    'type': 'logs_batch',
                    'logs': cached_logs[:100],  # 最多发送100条日志
                    'timestamp': timezone.now().isoformat()
                }))
        
        # 如果是新的检测端连接，主动请求状态更新
        # 延迟2秒发送，确保检测端准备好接收命令
        await asyncio.sleep(2)
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'send_command',
                'command': 'get_status',
                'params': {},
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # 同时请求配置信息
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'send_command',
                'command': 'get_config',
                'params': {},
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # 同时请求日志信息
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'send_command',
                'command': 'get_logs',
                'params': {'count': 100},  # 请求最近100条日志
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def disconnect(self, close_code):
        """处理WebSocket断开连接"""
        # 取消心跳检查任务
        if hasattr(self, 'heartbeat_check_task') and not self.heartbeat_check_task.done():
            self.heartbeat_check_task.cancel()
            
        # 将连接从组中移除
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        # 如果是检测端断开，更新终端状态为离线
        if self.is_detector:
            # 添加: 设置状态缓存，加快响应速度
            cache_key = f"terminal:{self.terminal_id}:connected"
            cache.set(cache_key, False, timeout=300)  # 5分钟过期
            
            await self.update_terminal_status(self.terminal_id, False)
            logger.info(f"检测端 {self.terminal_id} 的WebSocket连接已断开: {close_code}")
        else:
            logger.info(f"客户端与终端 {self.terminal_id} 的WebSocket连接已断开: {close_code}")
    
    async def receive(self, text_data):
        """处理从客户端接收的消息"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            # 增加消息接收日志
            logger.debug(f"从终端 {self.terminal_id} 接收到消息类型: {message_type}")
            
            # 检查是否为检测端特有的消息类型
            detector_message_types = ['system_status', 'heartbeat', 'nodes_data', 'log', 'command_response']
            if message_type in detector_message_types and not self.is_detector:
                # 如果收到检测端特有消息类型，标记当前连接为检测端
                self.is_detector = True
                # 更新终端的在线状态
                await self.update_terminal_status(self.terminal_id, True)
                logger.info(f"检测到检测端 {self.terminal_id} 的WebSocket连接")
                
                # 检测到新的检测端连接，发送状态请求命令
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'send_command',
                        'command': 'get_status',
                        'params': {},
                        'timestamp': timezone.now().isoformat()
                    }
                )
                
                # 同时发送配置请求命令
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'send_command',
                        'command': 'get_config',
                        'params': {},
                        'timestamp': timezone.now().isoformat()
                    }
                )
                
                # 同时发送日志请求命令
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'send_command',
                        'command': 'get_logs',
                        'params': {'count': 100},  # 请求最近100条日志
                        'timestamp': timezone.now().isoformat()
                    }
                )
            
            # 处理不同类型的消息
            if message_type == 'system_status':
                await self.handle_system_status(data)
            elif message_type == 'log':
                await self.handle_log_message(data)
            elif message_type == 'heartbeat':
                await self.handle_heartbeat(data)
            elif message_type == 'nodes_data':
                await self.handle_nodes_data(data)
            elif message_type == 'command_response':
                # 添加命令响应处理
                await self.handle_command_response(data)
            else:
                # 对于其他类型的消息，只记录不转发
                logger.debug(f"收到未知类型消息: {message_type}")
        except json.JSONDecodeError:
            logger.error(f"收到无效的JSON数据: {text_data[:100]}...")
        except Exception as e:
            logger.error(f"处理WebSocket消息时出错: {str(e)}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
    
    async def handle_nodes_data(self, data):
        """处理节点数据更新"""
        nodes_data = data.get('nodes', [])
        if not nodes_data:
            return
            
        # 更新节点数据到数据库
        updated_nodes = await self.update_nodes_data(nodes_data)
        
        # 转发消息
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'broadcast_message',
                'message': {
                    'type': 'nodes_data',
                    'data': nodes_data,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )
    
    async def handle_system_status(self, data):
        """处理系统状态更新消息"""
        status_data = data.get('status', {})
        if not status_data:
            return
            
        # 确保状态数据有时间戳
        if 'timestamp' not in status_data:
            status_data['timestamp'] = timezone.now().isoformat()
            
        # 更新数据库中的终端状态
        await self.update_terminal_system_status(self.terminal_id, status_data)
        
        # 更新Redis缓存 - 保留60秒
        cache_key = f"terminal:{self.terminal_id}:status"
        cache.set(cache_key, status_data, timeout=60)
        
        # 广播状态消息给所有连接的客户端 - 不包括发送者
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'broadcast_message',
                'message': {
                    'type': 'status',
                    'data': status_data,
                    'timestamp': timezone.now().isoformat()
                },
                'exclude': self.channel_name  # 排除发送者
            }
        )
        
        # 每次收到状态更新时，检查模式是否变化
        if 'mode' in status_data and hasattr(self, 'last_mode') and self.last_mode != status_data['mode']:
            logger.info(f"终端 {self.terminal_id} 的模式已变更: {self.last_mode} -> {status_data['mode']}")
            self.last_mode = status_data['mode']
            
            # 更新数据库中的模式
            await self.update_terminal_mode(self.terminal_id, status_data['mode'])
    
    async def handle_log_message(self, data):
        """处理日志消息"""
        # 添加到日志缓存
        cache_key = f"terminal:{self.terminal_id}:logs"
        
        # 获取现有日志
        logs = cache.get(cache_key) or []
        
        # 添加新日志
        log_entry = {
            'timestamp': data.get('timestamp', timezone.now().isoformat()),
            'level': data.get('level', 'info'),
            'message': data.get('message', ''),
            'source': data.get('source', 'system')
        }
        
        # 将新日志添加到列表开头
        logs.insert(0, log_entry)
        
        # 限制日志数量
        if len(logs) > 500:
            logs = logs[:500]
        
        # 更新缓存，延长过期时间
        try:
            cache.set(cache_key, logs, timeout=1800)  # 30分钟过期
            logger.debug(f"更新终端 {self.terminal_id} 日志缓存，当前日志数量: {len(logs)}")
        except Exception as e:
            logger.error(f"缓存日志时出错: {str(e)}")
        
        # 广播日志消息
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'broadcast_message',
                'message': {
                    'type': 'new_log',
                    'data': log_entry,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )
    
    async def handle_heartbeat(self, data):
        """处理心跳消息"""
        # 更新终端的最后活动时间
        await self.update_terminal_last_active(self.terminal_id)
        
        # 如果是从检测端发送的心跳，确保我们记录它是在线的
        if self.is_detector:
            # 设置连接状态缓存
            cache_key = f"terminal:{self.terminal_id}:connected"
            cache.set(cache_key, True, timeout=90)  # 90秒过期
            
            # 更新数据库状态
            await self.update_terminal_status(self.terminal_id, True)
        
        # 回复心跳
        await self.send(text_data=json.dumps({
            'type': 'heartbeat_response',
            'timestamp': timezone.now().isoformat()
        }))
    
    async def send_command(self, event):
        """发送命令到终端"""
        # 只有当连接是检测端时才发送命令
        if not self.is_detector and event.get('command') != 'get_status':
            # 如果不是面向检测端的命令，或者不是状态请求，则不发送
            return
            
        command = event.get('command')
        params = event.get('params', {})
        timestamp = event.get('timestamp', timezone.now().isoformat())
        
        # 发送命令消息
        await self.send(text_data=json.dumps({
            'type': 'send_command',
            'command': command,
            'params': params,
            'timestamp': timestamp
        }))
        
        logger.info(f"命令 '{command}' 已发送到终端 {self.terminal_id}")
    
    async def handle_command_response(self, data):
        """处理从检测端返回的命令响应"""
        command = data.get('command')
        result = data.get('result', {})
        success = data.get('success', False)
        
        logger.info(f"收到终端 {self.terminal_id} 的命令响应: {command}, 结果: {'成功' if success else '失败'}")
        
        # 特殊处理get_config命令的响应 - 将配置数据保存到缓存
        if command == 'get_config' and success and result:
            try:
                cache_key = f"terminal:{self.terminal_id}:config"
                # 保存配置数据到缓存，5分钟过期
                cache.set(cache_key, result, timeout=300)
                logger.info(f"已将终端 {self.terminal_id} 的配置数据保存到缓存")
                
                # 同时更新数据库中的配置数据
                await self.update_terminal_config_from_response(self.terminal_id, result)
            except Exception as e:
                logger.error(f"保存终端 {self.terminal_id} 配置到缓存失败: {str(e)}")
        
        # 特殊处理get_logs命令的响应 - 将日志数据保存到缓存
        elif command == 'get_logs' and success and result:
            try:
                cache_key = f"terminal:{self.terminal_id}:logs"
                # 保存日志数据到缓存，30分钟过期
                cache.set(cache_key, result, timeout=1800)
                logger.info(f"已将终端 {self.terminal_id} 的 {len(result)} 条日志保存到缓存")
            except Exception as e:
                logger.error(f"保存终端 {self.terminal_id} 日志到缓存失败: {str(e)}")
        
        # 广播命令响应到组内所有连接
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'broadcast_message',
                'message': {
                    'type': 'command_response',
                    'command': command,
                    'result': result,
                    'success': success,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )
    
    async def broadcast_message(self, event):
        """广播消息到WebSocket客户端"""
        # 检查是否应该排除当前连接
        exclude_channel = event.get('exclude', None)
        if exclude_channel and exclude_channel == self.channel_name:
            # 如果需要排除当前连接，则不发送
            return
            
        message = event.get('message', {})
        
        # 发送消息
        await self.send(text_data=json.dumps(message))
    
    @database_sync_to_async
    def check_terminal_exists(self, terminal_id):
        """检查终端是否存在"""
        try:
            return ProcessTerminal.objects.filter(id=terminal_id).exists()
        except Exception:
            return False
    
    @database_sync_to_async
    def update_terminal_status(self, terminal_id, connected):
        """更新终端的连接状态"""
        try:
            terminal = ProcessTerminal.objects.get(id=terminal_id)
            # 只有状态变化时才更新和记录日志
            if terminal.status != connected:
                terminal.status = connected
                terminal.last_active = timezone.now()
                terminal.save(update_fields=['status', 'last_active'])
                logger.info(f"终端 {terminal_id} 状态已更新为: {'在线' if connected else '离线'}")
            else:
                # 仅更新最后活动时间
                terminal.last_active = timezone.now()
                terminal.save(update_fields=['last_active'])
                
            # 更新缓存中的状态
            cache_key = f"terminal:{terminal_id}:status"
            cached_status = cache.get(cache_key)
            if cached_status:
                cached_status.update({"terminal_online": connected})
                cache.set(cache_key, cached_status, timeout=60)
            
            # 设置连接状态缓存
            cache_key = f"terminal:{terminal_id}:connected"
            cache.set(cache_key, connected, timeout=300)  # 5分钟过期
            
            return True
        except ProcessTerminal.DoesNotExist:
            logger.error(f"终端 {terminal_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"更新终端 {terminal_id} 状态失败: {str(e)}")
            return False
    
    @database_sync_to_async
    def update_terminal_system_status(self, terminal_id, status_data):
        """更新终端的系统状态"""
        try:
            terminal = ProcessTerminal.objects.get(id=terminal_id)
            
            # 更新状态字段
            if 'cpu_usage' in status_data:
                terminal.cpu_usage = status_data['cpu_usage']
            if 'memory_usage' in status_data:
                terminal.memory_usage = status_data['memory_usage']
            if 'disk_usage' in status_data:
                terminal.disk_usage = status_data['disk_usage']
            if 'disk_free' in status_data:
                terminal.disk_free = status_data['disk_free']
            if 'disk_total' in status_data:
                terminal.disk_total = status_data['disk_total']
            if 'memory_available' in status_data:
                terminal.memory_available = status_data['memory_available']
            if 'memory_total' in status_data:
                terminal.memory_total = status_data['memory_total']
            if 'push_running' in status_data:
                terminal.push_running = status_data['push_running']
            if 'pull_running' in status_data:
                terminal.pull_running = status_data['pull_running']
            if 'model_loaded' in status_data:
                terminal.model_loaded = status_data['model_loaded']
            if 'nodes' in status_data:
                terminal.nodes = status_data['nodes']
            if 'co2_level' in status_data:
                terminal.co2_level = status_data['co2_level']
            if 'system_uptime' in status_data:
                terminal.system_uptime = status_data['system_uptime']
            if 'frame_rate' in status_data:
                terminal.frame_rate = status_data['frame_rate']
            if 'total_frames' in status_data:
                terminal.total_frames = status_data['total_frames']
            if 'terminal_id' in status_data:
                terminal.terminal_id = status_data['terminal_id']
            if 'mode' in status_data:
                terminal.mode = status_data['mode']
            if 'last_detection' in status_data:
                terminal.last_detection = status_data['last_detection']
                
            terminal.last_active = timezone.now()
            terminal.save()
            
            # 添加在线状态到缓存数据
            status_data["terminal_online"] = True
            
            return True
        except ProcessTerminal.DoesNotExist:
            logger.error(f"终端 {terminal_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"更新终端 {terminal_id} 系统状态失败: {str(e)}")
            return False
    
    @database_sync_to_async
    def update_nodes_data(self, nodes_data):
        """更新节点数据"""
        updated_nodes = []
        try:
            for node_data in nodes_data:
                node_id = node_data.get('id')
                if not node_id:
                    continue
                    
                try:
                    node = HardwareNode.objects.get(id=node_id)
                    
                    # 更新基本字段
                    if 'detected_count' in node_data:
                        node.detected_count = node_data['detected_count']
                    
                    # 更新环境数据字段
                    if 'temperature' in node_data:
                        node.temperature = node_data['temperature']
                    if 'humidity' in node_data:
                        node.humidity = node_data['humidity']
                    
                    node.updated_at = timezone.now()
                    node.save()
                    updated_nodes.append(node_id)
                    
                    # 如果有区域绑定，保存历史数据
                    try:
                        area = Area.objects.get(bound_node=node)
                        if 'detected_count' in node_data:
                            HistoricalData.objects.create(
                                area=area,
                                detected_count=node_data['detected_count'],
                                timestamp=timezone.now()
                            )
                    except Area.DoesNotExist:
                        pass
                        
                except HardwareNode.DoesNotExist:
                    logger.warning(f"节点 {node_id} 不存在，无法更新数据")
                    
            return updated_nodes
        except Exception as e:
            logger.error(f"更新节点数据失败: {str(e)}")
            return []
    
    @database_sync_to_async
    def update_terminal_last_active(self, terminal_id):
        """更新终端的最后活动时间"""
        try:
            terminal = ProcessTerminal.objects.get(id=terminal_id)
            terminal.last_active = timezone.now()
            terminal.save(update_fields=['last_active'])
            return True
        except Exception as e:
            logger.error(f"更新终端 {terminal_id} 最后活动时间失败: {str(e)}")
            return False

    # 添加模式更新方法
    @database_sync_to_async
    def update_terminal_mode(self, terminal_id, mode):
        """更新终端的运行模式"""
        try:
            terminal = ProcessTerminal.objects.get(id=terminal_id)
            terminal.mode = mode
            terminal.save(update_fields=['mode'])
            return True
        except ProcessTerminal.DoesNotExist:
            logger.error(f"终端 {terminal_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"更新终端 {terminal_id} 模式失败: {str(e)}")
            return False

    async def heartbeat_check_loop(self):
        """心跳检查循环 - 检查是否需要断开连接"""
        try:
            while True:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                if self.is_detector:
                    # 获取终端最后活动时间
                    last_active = await self.get_terminal_last_active(self.terminal_id)
                    
                    if last_active:
                        # 检查最后活动时间是否超过2分钟
                        time_diff = timezone.now() - last_active
                        if time_diff > timedelta(minutes=2):
                            logger.warning(f"终端 {self.terminal_id} 超过2分钟未活动，将断开连接")
                            # 更新终端状态为离线
                            await self.update_terminal_status(self.terminal_id, False)
                            # 断开WebSocket连接
                            await self.close(code=1000)
                            break
        except asyncio.CancelledError:
            # 任务被取消，正常退出
            pass
        except Exception as e:
            logger.error(f"心跳检查循环异常: {str(e)}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
    
    @database_sync_to_async
    def get_terminal_last_active(self, terminal_id):
        """获取终端最后活动时间"""
        try:
            terminal = ProcessTerminal.objects.get(id=terminal_id)
            return terminal.last_active
        except Exception as e:
            logger.error(f"获取终端 {terminal_id} 最后活动时间失败: {str(e)}")
            return None

    @database_sync_to_async
    def update_terminal_config_from_response(self, terminal_id, config_data):
        """从命令响应更新终端配置到数据库"""
        try:
            terminal = ProcessTerminal.objects.get(id=terminal_id)
            
            # 更新配置字段
            if 'mode' in config_data:
                terminal.mode = config_data['mode']
            if 'interval' in config_data:
                terminal.interval = config_data['interval']
            if 'nodes' in config_data:
                terminal.node_config = config_data['nodes']
            if 'save_image' in config_data:
                terminal.save_image = config_data['save_image']
            if 'preload_model' in config_data:
                terminal.preload_model = config_data['preload_model']
            if 'co2_enabled' in config_data:
                terminal.co2_enabled = config_data['co2_enabled']
            if 'co2_read_interval' in config_data:
                terminal.co2_read_interval = config_data['co2_read_interval']
                
            terminal.save()
            logger.debug(f"已更新终端 {terminal_id} 的数据库配置")
            return True
        except ProcessTerminal.DoesNotExist:
            logger.error(f"终端 {terminal_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"更新终端 {terminal_id} 数据库配置失败: {str(e)}")
            return False

# 添加一个系统广播消费者，用于向所有连接的客户端广播系统消息

class SystemBroadcastConsumer(AsyncWebsocketConsumer):
    """系统广播WebSocket消费者，用于广播系统级消息"""
    
    async def connect(self):
        """处理WebSocket连接"""
        # 将连接添加到系统广播组
        await self.channel_layer.group_add(
            "system_broadcast",
            self.channel_name
        )
        
        # 接受WebSocket连接
        await self.accept()
        
        # 发送连接确认消息
        await self.send(text_data=json.dumps({
            'type': 'connection_status',
            'status': 'connected',
            'message': '已连接到系统广播通道',
            'timestamp': timezone.now().isoformat()
        }))
    
    async def disconnect(self, close_code):
        """处理WebSocket断开连接"""
        # 将连接从组中移除
        await self.channel_layer.group_discard(
            "system_broadcast",
            self.channel_name
        )
    
    async def receive(self, text_data):
        """接收消息 - 系统广播通道不处理客户端发送的消息"""
        pass
    
    async def broadcast_message(self, event):
        """向客户端广播消息"""
        message = event.get('message', {})
        await self.send(text_data=json.dumps(message))
