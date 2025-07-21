import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.utils import timezone
from .models import ProcessTerminal

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
    
    async def disconnect(self, close_code):
        """处理WebSocket断开连接"""
        # 将连接从组中移除
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        # 如果是检测端断开，更新终端状态为离线
        if self.is_detector:
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
            detector_message_types = ['system_status', 'heartbeat', 'nodes_data', 'log']
            if message_type in detector_message_types and not self.is_detector:
                # 如果收到检测端特有消息类型，标记当前连接为检测端
                self.is_detector = True
                # 更新终端的在线状态
                await self.update_terminal_status(self.terminal_id, True)
                logger.info(f"检测到检测端 {self.terminal_id} 的WebSocket连接")
            
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
    
    # 改进系统状态处理
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
        if len(logs) > 100:
            logs = logs[:100]
        
        # 更新缓存
        cache.set(cache_key, logs, timeout=300)  # 5分钟过期
        
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
        
        # 回复心跳
        await self.send(text_data=json.dumps({
            'type': 'heartbeat_response',
            'timestamp': timezone.now().isoformat()
        }))
    
    async def handle_nodes_data(self, data):
        """处理节点数据更新"""
        nodes_data = data.get('nodes', [])
        if not nodes_data:
            return
            
        # 处理节点数据 - 可能需要更新数据库
        # 这里仅转发消息
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
            terminal.status = connected
            terminal.last_active = timezone.now()
            terminal.save(update_fields=['status', 'last_active'])
            
            # 更新缓存中的状态
            if not connected:
                # 如果断开连接，更新状态缓存为离线
                cache_key = f"terminal:{terminal_id}:status"
                cached_status = cache.get(cache_key)
                if cached_status:
                    cached_status.update({"terminal_online": False})
                    cache.set(cache_key, cached_status, timeout=60)
            
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
            if 'push_running' in status_data:
                terminal.push_running = status_data['push_running']
            if 'pull_running' in status_data:
                terminal.pull_running = status_data['pull_running']
            if 'model_loaded' in status_data:
                terminal.model_loaded = status_data['model_loaded']
            if 'cameras' in status_data:
                terminal.cameras = status_data['cameras']
                
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
