import os
import time
import psutil
import logging
import threading
import json
from datetime import datetime
from typing import Dict, Any, Optional

# 导入CO2传感器模块
from sgp30_reader import SGP30Reader

logger = logging.getLogger('system_monitor')

class SystemMonitor:
    """
    系统监控模块
    独立于检测服务运行，持续监控系统资源和摄像头状态
    """
    
    def __init__(self, config_manager=None, node_manager=None, 
                 detection_manager=None, log_manager=None, 
                 ws_client=None):
        self.config_manager = config_manager
        self.node_manager = node_manager
        self.detection_manager = detection_manager
        self.log_manager = log_manager
        self.ws_client = ws_client
        
        # 状态数据
        self.status = {
            "cpu_usage": 0,
            "memory_usage": 0,
            "disk_usage": 0,
            "disk_free": 0,
            "disk_total": 0,
            "memory_available": 0,
            "memory_total": 0,
            "system_uptime": 0,
            "nodes": {},
            "frame_rate": 0,
            "total_frames": 0,
            "model_loaded": False,
            "push_running": False,
            "pull_running": False,
            "mode": "both",  # 默认模式
            "terminal_id": 1,  # 默认终端ID
            "co2_level": -1,  # CO2浓度(ppm)，-1表示无效或未检测到
            "co2_status": "未连接",  # CO2传感器状态：正常、异常、未连接
            # 新增：完整节点详情映射，供前端悬浮展示
            "node_details": {},
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
        
        # 添加配置监控相关属性
        self.last_config = {}
        self.last_config_hash = 0
        
        # 初始化CO2传感器
        self.co2_reader = None
        self.co2_enabled = config_manager.get('co2_enabled', True) if config_manager else True
        self.co2_last_read_time = 0
        self.co2_read_interval = config_manager.get('co2_read_interval', 30) if config_manager else 30  # CO2读取间隔（秒）
        
        if self.co2_enabled:
            try:
                self.co2_reader = SGP30Reader()
                self.status["co2_status"] = "正常"
                logger.info("CO2传感器初始化成功")
                if self.log_manager:
                    self.log_manager.info("CO2传感器初始化成功", source="monitor")
            except Exception as e:
                logger.error(f"CO2传感器初始化失败: {str(e)}")
                self.status["co2_status"] = "异常"
                self.co2_enabled = False
                if self.log_manager:
                    self.log_manager.error(f"CO2传感器初始化失败: {str(e)}", source="monitor")
        
        if config_manager:
            self.last_config = config_manager.get_all()
            self.last_config_hash = self._get_config_hash()

        # 新增：节点状态主动轮询控制
        self.node_ping_interval = (self.config_manager.get('node_ping_interval', 10)
                                   if self.config_manager else 10)  # 每个节点轮询间隔(秒)
        self.node_ping_batch = (self.config_manager.get('node_ping_batch', 3)
                                if self.config_manager else 3)      # 每周期最多轮询的节点数
        self._node_last_ping: Dict[Any, float] = {}

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
                self._update_node_status()
                
                # 更新帧率
                self._update_frame_rate()
                
                # 更新CO2数据
                self._update_co2_data()
                
                # 计算系统运行时间
                uptime = int(time.time() - psutil.boot_time())
                self.status["system_uptime"] = uptime
                
                # 通过WebSocket定期发送状态更新到服务端
                # 无论检测模式是否运行，都要发送状态
                current_time = time.time()
                if (current_time - self.last_ws_update) >= self.ws_update_interval:
                    self._send_ws_status_update()
                    self.last_ws_update = current_time
                
                # 检查配置是否变更
                if self.config_manager:
                    current_hash = self._get_config_hash()
                    if current_hash != self.last_config_hash:
                        # 配置已变更
                        try:
                            new_config = self.config_manager.get_all()
                            self.on_config_changed(self.last_config, new_config)
                            # 更新配置哈希和备份
                            self.last_config = new_config
                            self.last_config_hash = current_hash
                        except Exception as config_error:
                            # 如果配置变更处理失败，记录错误但继续运行
                            logger.error(f"处理配置变更失败: {str(config_error)}")
                            # 使用安全的日志记录
                            self._safe_log('error', f"处理配置变更失败: {str(config_error)}")
                
                # 延时
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"系统监控循环出错: {str(e)}")
                # 使用安全的日志记录方式
                self._safe_log('error', f"系统监控出错: {str(e)}")
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
    
    def _update_node_status(self):
        """更新摄像头状态（主动轮询 + 读取缓存）"""
        if not self.node_manager:
            return
        try:
            nodes_status: Dict[Any, str] = {}

            # 汇总所有节点ID（数据节点 + 控制节点）
            node_ids = set()
            if hasattr(self.node_manager, 'get_data_nodes'):
                node_ids.update(self.node_manager.get_data_nodes().keys())
            if hasattr(self.node_manager, 'get_control_nodes'):
                node_ids.update(self.node_manager.get_control_nodes().keys())

            # 新增：主动轮询到期节点，限制每周期的请求数量
            now = time.time()
            polled = 0
            for node_id in sorted(list(node_ids)):
                last = self._node_last_ping.get(node_id, 0)
                if (now - last) >= self.node_ping_interval and polled < self.node_ping_batch:
                    try:
                        # 触发 /status 请求与 NodeManager 缓存更新
                        self.node_manager.check_node_connection(node_id)
                    except Exception as e:
                        logger.debug(f"主动轮询节点 {node_id} 失败: {e}")
                    self._node_last_ping[node_id] = now
                    polled += 1

            # 读取 NodeManager 的状态缓存并汇总
            status_map = self.node_manager.get_node_status() if hasattr(self.node_manager, 'get_node_status') else {}
            if not node_ids and status_map:
                node_ids.update(status_map.keys())

            for node_id in node_ids:
                info = status_map.get(node_id, {})
                status_text = info.get('status', '未知') if isinstance(info, dict) else (str(info) if info else '未知')
                nodes_status[node_id] = status_text

            self.status["nodes"] = nodes_status
            # 新增：暴露完整节点详情映射
            self.status["node_details"] = status_map or {}
        except Exception as e:
            logger.error(f"更新摄像头状态失败: {str(e)}")
            # 记录更详细的错误信息以便调试
            if self.node_manager and hasattr(self.node_manager, 'nodes'):
                for node_id, node in self.node_manager.nodes.items():
                    logger.debug(f"摄像头 {node_id} 的类型: {type(node)}")
    
    def _update_co2_data(self):
        """更新CO2数据"""
        if not self.co2_enabled or not self.co2_reader:
            return

        current_time = time.time()

        # 检查是否到了读取CO2数据的时间
        if current_time - self.co2_last_read_time < self.co2_read_interval:
            return

        try:
            # 读取CO2数据
            prev_level = self.status.get("co2_level", -1)
            co2_ppm = self.co2_reader.get_co2()

            if co2_ppm >= 0:  # 有效读数
                self.status["co2_level"] = co2_ppm
                self.status["co2_status"] = "正常"
                logger.debug(f"CO2读数: {co2_ppm} ppm")

                # 记录显著变化（对比更新前的上次读数）
                if prev_level >= 0 and abs(co2_ppm - prev_level) > 100:
                    if self.log_manager:
                        self.log_manager.info(f"CO2浓度变化: {co2_ppm} ppm", source="monitor")

            else:  # 读取失败
                logger.warning("CO2传感器读取失败，尝试重新初始化")
                self.status["co2_status"] = "异常"

                # 尝试重新初始化传感器
                try:
                    self.co2_reader = SGP30Reader()
                    self.status["co2_status"] = "正常"
                    logger.info("CO2传感器重新初始化成功")
                except Exception as reinit_error:
                    logger.error(f"CO2传感器重新初始化失败: {str(reinit_error)}")
                    self.co2_enabled = False

            self.co2_last_read_time = current_time

        except Exception as e:
            logger.error(f"更新CO2数据失败: {str(e)}")
            self.status["co2_status"] = "异常"

            # 如果连续失败，暂时禁用CO2传感器
            if current_time - self.co2_last_read_time > self.co2_read_interval * 3:
                logger.warning("CO2传感器连续失败，暂时禁用")
                self.co2_enabled = False
                self.status["co2_status"] = "未连接"
    
    def _update_frame_rate(self):
        """更新帧率计算"""
        current_time = time.time()
        time_diff = current_time - self.last_frame_time
        
        if time_diff >= 1.0:  # 每秒计算一次帧率
            self.status["frame_rate"] = round(self.frame_count / time_diff, 2)
            self.last_frame_time = current_time
            self.frame_count = 0
    
    # 添加一个安全的日志记录方法
    def _safe_log(self, level, message, source="monitor"):
        """安全地记录日志，避免事件循环关闭错误"""
        try:
            if self.log_manager:
                # 使用标准日志方法记录到文件和内存
                if level == 'info':
                    self.log_manager.info_sync(message, source)
                elif level == 'error':
                    self.log_manager.error_sync(message, source)
                elif level == 'warning':
                    self.log_manager.warning_sync(message, source)
                elif level == 'debug':
                    self.log_manager.debug_sync(message, source)
            
            # 同时使用系统日志记录
            if level == 'info':
                logger.info(message)
            elif level == 'error':
                logger.error(message)
            elif level == 'warning':
                logger.warning(message)
            elif level == 'debug':
                logger.debug(message)
        except Exception as e:
            # 如果连记录日志都失败了，至少在系统日志中记录这个错误
            logger.error(f"记录日志失败: {str(e)}, 原始消息: {message}")
    
    
    def _send_ws_status_update(self):
        """通过WebSocket发送状态更新到服务端"""
        if not self.ws_client:
            return

        # 兼容不同的连接状态属性/方法
        try:
            is_connected = False
            if hasattr(self.ws_client, 'is_connected') and callable(getattr(self.ws_client, 'is_connected')):
                is_connected = self.ws_client.is_connected()
            elif hasattr(self.ws_client, 'connected'):
                is_connected = bool(getattr(self.ws_client, 'connected'))
            if not is_connected:
                return
        except Exception:
            return

        try:
            status_data = self.get_status()

            # 兼容不同的发送方法
            send_coro = None
            if hasattr(self.ws_client, 'send_system_status'):
                send_coro = self.ws_client.send_system_status(status_data)
            elif hasattr(self.ws_client, 'send_status'):
                send_coro = self.ws_client.send_status(status_data)
            else:
                logger.warning("WebSocket客户端不支持发送系统状态的方法")
                return

            # 使用线程安全的方式发送WebSocket消息
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(send_coro)
                loop.close()
                logger.debug("通过WebSocket发送状态更新成功")
            except RuntimeError as async_error:
                if "Event loop is closed" in str(async_error):
                    logger.warning("检测到事件循环已关闭，尝试使用新的事件循环")
                    import asyncio
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        new_loop.run_until_complete(send_coro)
                    finally:
                        new_loop.close()
                else:
                    raise

        except Exception as e:
            logger.error(f"通过WebSocket发送状态更新失败: {str(e)}")
    
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
    
    def on_config_changed(self, old_config: Dict[str, Any], new_config: Dict[str, Any]):
        """处理配置变更"""
        # 记录配置变更
        logger.info("配置已更改，正在应用变更...")
        # 使用安全的日志记录
        self._safe_log('info', "配置已更改，正在应用变更...")
        
        # 1. 通知检测管理器配置已更改
        try:
            if self.detection_manager and hasattr(self.detection_manager, 'on_config_changed'):
                self.detection_manager.on_config_changed(old_config, new_config)
        except Exception as e:
            logger.error(f"通知检测管理器配置变更失败: {str(e)}")
            self._safe_log('error', f"通知检测管理器配置变更失败: {str(e)}")
        
        # 2. 更新摄像头配置
        if 'nodes' in new_config and new_config['nodes'] != old_config.get('nodes', {}):
            self._safe_log('info', "摄像头配置已更改，重新加载摄像头")
            try:
                if self.node_manager and hasattr(self.node_manager, '_load_nodes'):
                    self.node_manager._load_nodes()
            except Exception as e:
                logger.error(f"重新加载摄像头失败: {str(e)}")
                self._safe_log('error', f"重新加载摄像头失败: {str(e)}")
        
        # 3. 更新监控间隔
        if 'monitor_interval' in new_config and new_config['monitor_interval'] != old_config.get('monitor_interval', 3):
            self._safe_log('info', f"监控间隔已更改: {old_config.get('monitor_interval', 3)} -> {new_config['monitor_interval']}")
            self.update_interval = new_config['monitor_interval']
            self.ws_update_interval = max(5, self.update_interval * 2)
        
        # 4. 更新检测模式
        if 'mode' in new_config and new_config['mode'] != old_config.get('mode', 'both'):
            self._safe_log('info', f"检测模式已更改: {old_config.get('mode', 'both')} -> {new_config['mode']}")
            # 检测管理器的on_config_changed方法会处理模式变更
        
        # 5. 更新拉取间隔
        if 'interval' in new_config and new_config['interval'] != old_config.get('interval', 5):
            self._safe_log('info', f"拉取间隔已更改: {old_config.get('interval', 5)} -> {new_config['interval']}")
            # 如果检测管理器正在运行拉取模式，重启拉取服务使新间隔生效
            try:
                if self.detection_manager and hasattr(self.detection_manager, 'pull_running') and self.detection_manager.pull_running:
                    self._safe_log('info', "重启拉取服务以应用新间隔")
                    self.detection_manager.stop_pull()
                    self.detection_manager.start_pull()
            except Exception as e:
                logger.error(f"重启拉取服务失败: {str(e)}")
                self._safe_log('error', f"重启拉取服务失败: {str(e)}")
        
        # 6. 更新预加载模型设置
        if 'preload_model' in new_config and new_config['preload_model'] != old_config.get('preload_model', True):
            self._safe_log('info', f"预加载模型设置已更改: {old_config.get('preload_model', True)} -> {new_config['preload_model']}")
            try:
                if new_config['preload_model'] and self.detection_manager and hasattr(self.detection_manager, 'model_loaded') and \
                   hasattr(self.detection_manager, 'model_loading') and hasattr(self.detection_manager, 'load_model_async'):
                    if not self.detection_manager.model_loaded and not self.detection_manager.model_loading:
                        self._safe_log('info', "启动模型加载")
                        self.detection_manager.load_model_async()
            except Exception as e:
                logger.error(f"应用预加载模型设置失败: {str(e)}")
                self._safe_log('error', f"应用预加载模型设置失败: {str(e)}")
        
        # 7. 更新保存图像设置
        if 'save_image' in new_config and new_config['save_image'] != old_config.get('save_image', True):
            self._safe_log('info', f"保存图像设置已更改: {old_config.get('save_image', True)} -> {new_config['save_image']}")
        
       
        logger.info("配置更改已应用")
        self._safe_log('info', "配置更改已应用")
    
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
    
    def update_ws_client(self, ws_client):
        """更新WebSocket客户端引用"""
        self.ws_client = ws_client
    
    def _get_config_hash(self):
        """获取配置的哈希值，用于检测配置更改"""
        if not self.config_manager:
            return 0
            
        try:
            config_str = json.dumps(self.config_manager.get_all(), sort_keys=True)
            return hash(config_str)
        except Exception as e:
            logger.error(f"计算配置哈希失败: {str(e)}")
            return 0
