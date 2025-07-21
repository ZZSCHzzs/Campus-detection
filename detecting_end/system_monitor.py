import os
import time
import psutil
import logging
import threading
import json
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger('system_monitor')

class SystemMonitor:
    """
    系统监控模块
    独立于检测服务运行，持续监控系统资源和摄像头状态
    """
    
    def __init__(self, config_manager=None, camera_manager=None, 
                 detection_manager=None, log_manager=None, 
                 socketio=None, ws_client=None):
        self.config_manager = config_manager
        self.camera_manager = camera_manager
        self.detection_manager = detection_manager
        self.log_manager = log_manager
        self.socketio = socketio
        self.ws_client = ws_client
        
        # 状态数据
        self.status = {
            "cpu_usage": 0,
            "memory_usage": 0,
            "cameras": {},
            "started_at": datetime.now().isoformat(),
            "frame_rate": 0,
            "total_frames": 0,
            "system_uptime": 0
        }
        
        # 帧率计算
        self.frame_count = 0
        self.last_frame_time = time.time()
        
        # 监控线程
        self.monitor_thread = None
        self.is_running = False
        self.update_interval = 3  # 状态更新间隔（秒）
        self.ws_update_interval = 10  # WebSocket更新间隔（秒）
        self.last_ws_update = 0
    
    def start(self):
        """启动监控线程"""
        if self.is_running:
            logger.info("系统监控已在运行中")
            return
            
        self.is_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="SystemMonitorThread"
        )
        self.monitor_thread.start()
        logger.info("系统监控已启动")
        
        if self.log_manager:
            self.log_manager.info("系统监控已启动", source="monitor")
    
    def stop(self):
        """停止监控线程"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
            
        logger.info("系统监控已停止")
        if self.log_manager:
            self.log_manager.info("系统监控已停止", source="monitor")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                # 更新系统资源使用情况
                self._update_system_resources()
                
                # 更新摄像头状态
                self._update_camera_status()
                
                # 更新帧率
                self._update_frame_rate()
                
                # 计算系统运行时间
                uptime = int(time.time() - psutil.boot_time())
                self.status["system_uptime"] = uptime
                
                # 通过Socket.IO发送状态更新
                self._emit_status_update()
                
                # 通过WebSocket定期发送状态更新到服务端
                # 无论检测模式是否运行，都要发送状态
                current_time = time.time()
                if (current_time - self.last_ws_update) >= self.ws_update_interval:
                    self._send_ws_status_update()
                    self.last_ws_update = current_time
                
                # 延时
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"系统监控循环出错: {str(e)}")
                if self.log_manager:
                    self.log_manager.error(f"系统监控出错: {str(e)}", source="monitor")
                time.sleep(5)  # 出错后等待一段时间再继续
    
    def _update_system_resources(self):
        """更新系统资源使用情况"""
        try:
            # CPU使用率
            self.status["cpu_usage"] = psutil.cpu_percent(interval=0.5)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            self.status["memory_usage"] = memory.percent
            
            # 额外系统信息
            self.status["memory_available"] = memory.available
            self.status["memory_total"] = memory.total
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            self.status["disk_usage"] = disk.percent
            self.status["disk_free"] = disk.free
            self.status["disk_total"] = disk.total
        except Exception as e:
            logger.error(f"更新系统资源信息失败: {str(e)}")
    
    def _update_camera_status(self):
        """更新摄像头状态"""
        if not self.camera_manager:
            return
            
        try:
            # 获取摄像头状态
            cameras_status = {}
            for cam_id, camera in self.camera_manager.cameras.items():
                cameras_status[cam_id] = "在线" if camera.is_available() else "离线"
            
            self.status["cameras"] = cameras_status
        except Exception as e:
            logger.error(f"更新摄像头状态失败: {str(e)}")
    
    def _update_frame_rate(self):
        """更新帧率计算"""
        current_time = time.time()
        time_diff = current_time - self.last_frame_time
        
        if time_diff >= 1.0:  # 每秒计算一次帧率
            self.status["frame_rate"] = round(self.frame_count / time_diff, 2)
            self.last_frame_time = current_time
            self.frame_count = 0
    
    def _emit_status_update(self):
        """通过Socket.IO发送状态更新"""
        if not self.socketio:
            return
            
        try:
            # 合并检测状态（如果可用）
            status_data = self.get_status()
            
            # 发送状态更新
            self.socketio.emit('system_resources', status_data)
        except Exception as e:
            logger.error(f"通过Socket.IO发送状态更新失败: {str(e)}")
    
    def _send_ws_status_update(self):
        """通过WebSocket发送状态更新到服务端"""
        if not self.ws_client or not self.ws_client.is_connected():
            return
            
        try:
            # 获取完整状态
            status_data = self.get_status()
            
            # 通过WebSocket客户端发送状态
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.ws_client.send_system_status(status_data))
            loop.close()
            
            logger.debug("通过WebSocket发送状态更新成功")
        except Exception as e:
            logger.error(f"通过WebSocket发送状态更新失败: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前系统状态"""
        status_data = dict(self.status)
        
        # 如果检测管理器可用，合并检测状态
        if self.detection_manager:
            detection_status = self.detection_manager.get_system_status()
            status_data.update({
                'model_loaded': detection_status.get('model_loaded', False),
                'push_running': detection_status.get('push_running', False),
                'pull_running': detection_status.get('pull_running', False),
                'mode': detection_status.get('mode', 'both')
            })
        
        # 获取终端ID（如果可用）
        if self.config_manager:
            status_data['terminal_id'] = self.config_manager.get('terminal_id')
        
        return status_data
    
    def add_frame_processed(self):
        """记录一帧已处理，用于帧率计算"""
        self.frame_count += 1
        self.status["total_frames"] += 1
    
    def set_update_interval(self, interval: float):
        """设置状态更新间隔"""
        if interval > 0:
            self.update_interval = interval
            logger.info(f"系统监控更新间隔已设置为 {interval} 秒")
    
    def set_ws_update_interval(self, interval: float):
        """设置WebSocket状态更新间隔"""
        if interval > 0:
            self.ws_update_interval = interval
            logger.info(f"WebSocket状态更新间隔已设置为 {interval} 秒")
        if hasattr(self.detection_manager, 'on_config_changed'):
            self.detection_manager.on_config_changed(old_config, new_config)
        
        # 2. 更新摄像头配置
        if 'cameras' in new_config and new_config['cameras'] != old_config.get('cameras', {}):
            self.log_manager.info("摄像头配置已更改，重新加载摄像头")
            self.camera_manager._load_cameras()
        
        # 3. 更新监控间隔
        if 'monitor_interval' in new_config and new_config['monitor_interval'] != old_config.get('monitor_interval', 3):
            self.log_manager.info(f"监控间隔已更改: {old_config.get('monitor_interval', 3)} -> {new_config['monitor_interval']}")
            self.monitor_interval = new_config['monitor_interval']
            self.server_update_interval = max(5, self.monitor_interval * 2)
        
        # 4. 更新检测模式
        if 'mode' in new_config and new_config['mode'] != old_config.get('mode', 'both'):
            self.log_manager.info(f"检测模式已更改: {old_config.get('mode', 'both')} -> {new_config['mode']}")
            # 检测管理器的on_config_changed方法会处理模式变更
        
        # 5. 更新拉取间隔
        if 'interval' in new_config and new_config['interval'] != old_config.get('interval', 5):
            self.log_manager.info(f"拉取间隔已更改: {old_config.get('interval', 5)} -> {new_config['interval']}")
            # 如果检测管理器正在运行拉取模式，重启拉取服务使新间隔生效
            if self.detection_manager.pull_running:
                self.log_manager.info("重启拉取服务以应用新间隔")
                self.detection_manager.stop_pull()
                self.detection_manager.start_pull()
        
        # 6. 更新预加载模型设置
        if 'preload_model' in new_config and new_config['preload_model'] != old_config.get('preload_model', True):
            self.log_manager.info(f"预加载模型设置已更改: {old_config.get('preload_model', True)} -> {new_config['preload_model']}")
            if new_config['preload_model'] and not self.detection_manager.model_loaded and not self.detection_manager.model_loading:
                self.log_manager.info("启动模型加载")
                self.detection_manager.load_model_async()
        
        # 7. 更新保存图像设置
        if 'save_image' in new_config and new_config['save_image'] != old_config.get('save_image', True):
            self.log_manager.info(f"保存图像设置已更改: {old_config.get('save_image', True)} -> {new_config['save_image']}")
            # 此设置在检测管理器运行时会自动生效
        
        # 8. 通知用户界面配置已更改
        if self.socketio:
            self.socketio.emit('system_message', {'message': '配置已更新并应用'})
            self.socketio.emit('system_update', {
                'config_updated': True,
                'config': new_config
            })
        
        # 更新配置哈希
        self.last_config = new_config
        self.last_config_hash = self._get_config_hash()
        
        self.log_manager.info("配置更改已应用")

    def _get_config_hash(self):
        """获取配置的哈希值，用于检测配置更改"""
        config_str = json.dumps(self.config_manager.get_all(), sort_keys=True)
        # 保存当前配置的副本用于比较
        self.last_config = self.config_manager.get_all()
        return hash(config_str)
    
    def _get_system_resources(self, last_cpu_times):
        """获取系统资源使用情况"""
        # 当前CPU时间
        current_cpu_times = psutil.cpu_times()
        
        # 计算所有CPU时间差值
        user_diff = current_cpu_times.user - last_cpu_times.user
        system_diff = current_cpu_times.system - last_cpu_times.system
        idle_diff = current_cpu_times.idle - last_cpu_times.idle
        
        # 计算总时间差
        total_diff = user_diff + system_diff + idle_diff
        
        # 计算CPU使用率
        if total_diff > 0:
            cpu_usage = 100.0 * (1.0 - (idle_diff / total_diff))
        else:
            # 如果差值为0（极少发生），则获取即时值
            cpu_usage = psutil.cpu_percent(interval=0.1)
        
        # 获取内存使用情况
        memory = psutil.virtual_memory()
        
        # 获取主要进程的资源使用
        process = psutil.Process()
        
        return {
            'cpu_usage': round(cpu_usage, 1),
            'memory_usage': round(memory.percent, 1),
            'memory_used_mb': round(memory.used / (1024 * 1024), 1),
            'memory_total_mb': round(memory.total / (1024 * 1024), 1),
            'process_cpu_percent': round(process.cpu_percent(interval=0.1) / psutil.cpu_count(), 1),
            'process_memory_percent': round(process.memory_percent(), 1),
            'cpu_times': current_cpu_times  # 保存当前CPU时间点，用于下次计算
        }
    
    def get_status(self):
        """获取当前系统状态"""
        return self.system_status.copy()
    
    def add_frame_processed(self):
        """增加处理帧计数，用于计算帧率"""
        self.frame_count += 1
    
    def update_ws_client(self, ws_client):
        """更新WebSocket客户端引用"""
        self.ws_client = ws_client
    
    def update_socketio(self, socketio):
        """更新SocketIO引用"""
        self.socketio = socketio
