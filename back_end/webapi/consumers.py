import json
from channels.generic.websocket import WebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from asgiref.sync import async_to_sync
from .models import ProcessTerminal, HardwareNode, HistoricalData, Area
import logging

# 配置日志
logger = logging.getLogger('terminal_ws')

class TerminalConsumer(WebsocketConsumer):
    def connect(self):
        # 从URL路径中获取terminal_id
        self.terminal_id = self.scope['url_route']['kwargs']['terminal_id']
        
        # 验证终端是否存在
        terminal = self.get_terminal()
        if not terminal:
            logger.warning(f"终端 {self.terminal_id} 不存在，拒绝连接")
            self.close()
            return
        
        # 将连接添加到组
        self.group_name = f"terminal_{self.terminal_id}"
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        
        # 更新终端状态为在线
        self.update_terminal_status(True)
        
        # 接受WebSocket连接
        self.accept()
        
        logger.info(f"终端 {self.terminal_id} 已连接")
        
    def disconnect(self, close_code):
        # 终端断开连接，更新状态为离线
        self.update_terminal_status(False)
        
        # 从组中移除
        try:
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name,
                self.channel_name
            )
        except Exception as e:
            logger.error(f"从组移除通道时出错: {str(e)}")
            
        logger.info(f"终端 {self.terminal_id} 已断开连接，代码: {close_code}")
        
    def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            # 处理心跳消息
            if message_type == 'heartbeat':
                self.handle_heartbeat()
                return
                
            # 处理节点数据
            if message_type == 'nodes_data' and 'nodes' in data:
                self.process_nodes_data(data['nodes'])
                return
                
            # 处理系统状态
            if message_type == 'system_status' and 'status' in data:
                self.process_system_status(data['status'])
                return
                
            # 处理日志消息
            if message_type == 'log':
                self.process_log(data)
                return
                
            # 处理认证消息
            if message_type == 'authenticate':
                # 已在connect中处理认证，这里无需额外处理
                return
                
            # 其他未知消息类型
            logger.warning(f"收到未知类型消息: {text_data}")
                
        except json.JSONDecodeError:
            logger.error(f"收到无效JSON数据: {text_data}")
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
    
    def handle_heartbeat(self):
        """处理心跳消息"""
        # 发送心跳响应
        self.send(text_data=json.dumps({
            'type': 'heartbeat_response',
            'timestamp': timezone.now().isoformat()
        }))
        
        # 顺便更新终端状态
        self.update_terminal_status(True)
    
    def send_command(self, event):
        """处理发送命令事件（由组消息触发）"""
        command = event.get('command')
        params = event.get('params', {})
        timestamp = event.get('timestamp', timezone.now().isoformat())
        
        # 构建命令消息
        command_data = {
            'type': 'send_command',
            'command': command,
            'params': params,
            'timestamp': timestamp
        }
        
        # 发送命令到终端
        self.send(text_data=json.dumps(command_data))
        logger.info(f"向终端 {self.terminal_id} 发送命令: {command}")
    
    @database_sync_to_async
    def get_terminal(self):
        """获取终端对象"""
        try:
            return ProcessTerminal.objects.get(id=self.terminal_id)
        except ProcessTerminal.DoesNotExist:
            logger.warning(f"终端ID {self.terminal_id} 不存在")
            return None
    
    @database_sync_to_async
    def update_terminal_status(self, is_online):
        """更新终端在线状态"""
        try:
            terminal = ProcessTerminal.objects.get(id=self.terminal_id)
            terminal.status = is_online
            terminal.save()
            return True
        except ProcessTerminal.DoesNotExist:
            logger.warning(f"尝试更新不存在的终端状态: {self.terminal_id}")
            return False
    
    @database_sync_to_async
    def process_nodes_data(self, nodes_data):
        """处理节点数据，更新节点状态并保存历史记录"""
        current_time = timezone.now()
        
        try:
            for node_data in nodes_data:
                node_id = node_data.get('node_id')
                detected_count = node_data.get('count', 0)
                
                if not node_id:
                    logger.warning("节点数据缺少node_id字段")
                    continue
                
                try:
                    # 更新节点数据
                    node = HardwareNode.objects.get(id=node_id)
                    node.detected_count = detected_count
                    node.status = True  # 节点在线
                    node.updated_at = current_time
                    node.save()
                    
                    # 保存历史数据
                    try:
                        area = Area.objects.get(bound_node=node)
                        HistoricalData.objects.create(
                            area=area,
                            detected_count=detected_count,
                            timestamp=current_time
                        )
                    except Area.DoesNotExist:
                        logger.warning(f"节点 {node_id} 未绑定区域，无法保存历史数据")
                        
                except HardwareNode.DoesNotExist:
                    logger.warning(f"节点ID {node_id} 不存在")
                    
            return True
        except Exception as e:
            logger.error(f"处理节点数据时出错: {str(e)}")
            return False
    
    @database_sync_to_async
    def process_system_status(self, status_data):
        """处理系统状态更新"""
        try:
            terminal = ProcessTerminal.objects.get(id=self.terminal_id)
            
            # 更新终端状态（可根据需要保存更多字段）
            if 'cpu_usage' in status_data:
                terminal.cpu_usage = status_data['cpu_usage']
            if 'memory_usage' in status_data:
                terminal.memory_usage = status_data['memory_usage']
                
            terminal.save()
            return True
        except ProcessTerminal.DoesNotExist:
            logger.warning(f"尝试更新不存在的终端状态: {self.terminal_id}")
            return False
        except Exception as e:
            logger.error(f"处理系统状态时出错: {str(e)}")
            return False
    
    @database_sync_to_async
    def process_log(self, log_data):
        """处理日志消息"""
        try:
            level = log_data.get('level', 'info')
            message = log_data.get('message', '')
            source = log_data.get('source', 'system')
            
            # 可以选择将日志保存到数据库或仅记录到服务器日志
            logger.info(f"终端 {self.terminal_id} 日志 [{level}] {source}: {message}")
            
            return True
        except Exception as e:
            logger.error(f"处理日志消息时出错: {str(e)}")
            return False
