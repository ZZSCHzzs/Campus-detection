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
        
        # 检查终端是否存在
        terminal_exists = await self.check_terminal_exists(self.terminal_id)
        if not terminal_exists:
            # 终端不存在，拒绝连接
            await self.close(code=4004)
            return
            
        # 将连接添加到组
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # 更新终端的连接状态
        await self.update_terminal_status(self.terminal_id, True)
        
        # 接受WebSocket连接
        await self.accept()
        
        # 发送连接确认消息
        await self.send(text_data=json.dumps({
            'type': 'connection_status',
            'status': 'connected',
            'terminal_id': self.terminal_id,
            'timestamp': timezone.now().isoformat()
        }))
        
        logger.info(f"终端 {self.terminal_id} WebSocket连接已建立")
    
    async def disconnect(self, close_code):
        """处理WebSocket断开连接"""
        # 将连接从组中移除
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        # 更新终端的连接状态
        await self.update_terminal_status(self.terminal_id, False)
        
        logger.info(f"终端 {self.terminal_id} WebSocket连接已断开: {close_code}")
    
    async def receive(self, text_data):
        """处理从客户端接收的消息"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            # 处理不同类型的消息
            if message_type == 'system_status':
                await self.handle_system_status(data)
            elif message_type == 'log':
                await self.handle_log_message(data)
            elif message_type == 'heartbeat':
                await self.handle_heartbeat(data)
            elif message_type == 'nodes_data':
                await self.handle_nodes_data(data)
            else:
                # 转发未知类型消息到组
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'broadcast_message',
                        'message': data
                    }
                )
        except json.JSONDecodeError:
            logger.error(f"收到无效的JSON数据: {text_data[:100]}...")
        except Exception as e:
            logger.error(f"处理WebSocket消息时出错: {str(e)}")
    
    async def handle_system_status(self, data):
        """处理系统状态更新消息"""
        status_data = data.get('status', {})
        if not status_data:
            return
            
        # 更新数据库中的终端状态
        await self.update_terminal_system_status(self.terminal_id, status_data)
        
        # 更新Redis缓存
        cache_key = f"terminal:{self.terminal_id}:status"
        cache.set(cache_key, status_data, timeout=60)  # 1分钟过期
        
        # 广播状态消息给所有连接的客户端
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'broadcast_message',
                'message': {
                    'type': 'status',
                    'data': status_data,
                    'timestamp': timezone.now().isoformat()
                }
            }
        )
    
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
    
    async def broadcast_message(self, event):
        """广播消息到WebSocket客户端"""
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
        except ProcessTerminal.DoesNotExist:
            self.send_json({
                'type': 'error',
                'message': f'终端 {self.terminal_id} 不存在',
                'timestamp': timezone.now().isoformat()
            })
        except Exception as e:
            self.send_json({
                'type': 'error',
                'message': f'处理状态更新失败: {str(e)}',
                'timestamp': timezone.now().isoformat()
            })
