import time
import os
import datetime
import threading
import asyncio
import cv2
import logging
import requests
import json
from threading import Thread, Event, Lock
import psutil
import importlib

logger = logging.getLogger('detection_manager')

class DetectionManager:
    """
    检测管理器，负责管理检测线程和任务
    支持两种模式：被动接收(push)和主动拉取(pull)
    """
    
    def __init__(self, config_manager, camera_manager, log_manager, socketio=None, ws_client=None):
        """初始化检测管理器"""
        self.config_manager = config_manager
        self.camera_manager = camera_manager
        self.log_manager = log_manager
        self.socketio = socketio
        self.ws_client = ws_client
        
        # 线程控制
        self.pull_thread = None
        self.stop_pull_event = Event()
        self.pull_running = False
        self.push_running = False
        self.error_count = 0
        self.max_errors = 5
        
        # 检测模型
        self.model = None
        self.model_loading = False
        self.model_loaded = False
        self.model_lock = Lock()
        
        # 检测统计
        self.stats_lock = Lock()
        self.detection_stats = {
            'today_count': 0,
            'total_count': 0,
            'max_count': 0,
            'avg_count': 0,
            'detection_sum': 0,
            'last_day_reset': datetime.datetime.now().strftime("%Y-%m-%d")
        }
        
        # 系统状态
        self.system_status = {
            'cpu_usage': 0,
            'memory_usage': 0,
            'model_loaded': False,
            'mode': self.config_manager.get('mode', 'push'),
            'push_running': False,
            'pull_running': False,
            'started_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.status_lock = Lock()
    
    def initialize(self):
        """初始化检测管理器"""
        # 如果配置为预加载模型，则启动模型加载线程
        if self.config_manager.get('preload_model', True):
            self.load_model_async()
        
        # 根据配置的模式启动相应的检测服务
        mode = self.config_manager.get('mode', 'push')
        if mode == 'push' or mode == 'both':
            self.start_push()
        
        if mode == 'pull' or mode == 'both':
            self.start_pull()
        
        return True
    
    def load_model_async(self):
        """异步加载模型"""
        if self.model_loading or self.model_loaded:
            return False
        
        self.model_loading = True
        self.log_manager.info("开始异步加载YOLO模型")
        
        # 创建模型加载线程
        model_thread = Thread(target=self._load_model)
        model_thread.daemon = True
        model_thread.start()
        
        return True
    
    def _load_model(self):
        """加载YOLO模型的线程函数"""
        try:
            self.log_manager.info("正在加载YOLO模型...")
            
            # 动态导入detect模块，避免循环导入
            detect_module = importlib.import_module('detect.run')
            
            with self.model_lock:
                self.model = detect_module.load_model()
                self.model_loaded = True
                self.model_loading = False
            
            with self.status_lock:
                self.system_status['model_loaded'] = True
            
            self.log_manager.info("YOLO模型加载完成")
            
            # 通知前端模型已加载
            if self.socketio:
                self.socketio.emit('system_update', {'model_loaded': True})
            
            return True
        except Exception as e:
            error_msg = f"加载模型失败: {str(e)}"
            self.log_manager.error(error_msg)
            
            self.model_loading = False
            with self.model_lock:
                self.model_loaded = False
            
            with self.status_lock:
                self.system_status['model_loaded'] = False
            
            # 通知前端模型加载失败
            if self.socketio:
                self.socketio.emit('system_error', {'message': error_msg})
            
            return False
    
    def start_push(self):
        """启动被动接收模式"""
        if self.push_running:
            return False
        
        self.push_running = True
        
        with self.status_lock:
            self.system_status["push_running"] = True
        
        self.log_manager.info("已启动被动接收模式")
        
        if self.socketio:
            self.socketio.emit('system_message', {'message': '已启动被动接收模式'})
            self.socketio.emit('system_update', {'push_running': True})
        
        return True
    
    def stop_push(self):
        """停止被动接收模式"""
        if not self.push_running:
            return False
        
        self.push_running = False
        
        with self.status_lock:
            self.system_status["push_running"] = False
        
        self.log_manager.info("已停止被动接收模式")
        
        if self.socketio:
            self.socketio.emit('system_message', {'message': '已停止被动接收模式'})
            self.socketio.emit('system_update', {'push_running': False})
        
        return True
    
    def start_pull(self):
        """启动主动拉取模式"""
        if self.pull_running:
            return False
        
        self.stop_pull_event.clear()
        self.error_count = 0
        
        self.pull_thread = Thread(target=self._pull_mode_handler)
        self.pull_thread.daemon = True
        self.pull_thread.start()
        
        self.pull_running = True
        
        with self.status_lock:
            self.system_status["pull_running"] = True
        
        self.log_manager.info("已启动主动拉取模式")
        
        if self.socketio:
            self.socketio.emit('system_message', {'message': '已启动主动拉取模式'})
            self.socketio.emit('system_update', {'pull_running': True})
        
        return True
    
    def stop_pull(self):
        """停止主动拉取模式"""
        if not self.pull_running:
            return False
        
        self.log_manager.info("正在停止主动拉取模式...")
        self.stop_pull_event.set()
        
        if self.pull_thread and self.pull_thread.is_alive():
            self.pull_thread.join(timeout=3.0)
        
        self.pull_running = False
        
        with self.status_lock:
            self.system_status["pull_running"] = False
        
        self.log_manager.info("已停止主动拉取模式")
        
        if self.socketio:
            self.socketio.emit('system_message', {'message': '已停止主动拉取模式'})
            self.socketio.emit('system_update', {'pull_running': False})
        
        return True
    
    def change_mode(self, new_mode):
        """根据模式启动或停止相应服务"""
        current_mode = self.config_manager.get('mode')
        if new_mode == current_mode:
            return False
        
        self.log_manager.info(f"切换模式: {current_mode} -> {new_mode}")
        self.config_manager.set('mode', new_mode)
        self.config_manager.save_config()
        
        # 根据新模式决定是否启动或停止服务
        if new_mode == "push":
            # 如果切换到被动模式，确保被动模式开启，停止主动拉取
            self.start_push()
            self.stop_pull()
        elif new_mode == "pull":
            # 如果切换到主动模式，确保主动模式开启，停止被动接收
            self.stop_push()
            self.start_pull()
        elif new_mode == "both":
            # 如果是双模式，确保两种模式都开启
            self.start_push()
            self.start_pull()
        
        # 更新系统状态
        with self.status_lock:
            self.system_status["mode"] = new_mode
        
        # 如果有socketio，通知前端模式变更
        if self.socketio:
            self.socketio.emit('system_update', {
                'mode': new_mode,
                'push_running': self.push_running,
                'pull_running': self.pull_running
            })
        
        return True
    
    def update_interval(self, new_interval):
        """更新拉取间隔"""
        current_interval = self.config_manager.get('interval')
        if new_interval == current_interval:
            return False
        
        self.config_manager.set('interval', new_interval)
        self.config_manager.save_config()
        
        self.log_manager.info(f"拉取间隔已更新为{new_interval}秒")
        
        # 如果当前正在进行主动拉取，重启主动拉取使新间隔生效
        if self.pull_running:
            self.stop_pull()
            self.start_pull()
            self.log_manager.info("已重启拉取服务以应用新间隔")
        
        if self.socketio:
            self.socketio.emit('system_message', {'message': f'拉取间隔已更新为{new_interval}秒'})
        
        return True
    
    def _pull_mode_handler(self):
        """主动拉取模式处理函数"""
        self.log_manager.info("运行在主动拉取模式...")
        
        try:
            while not self.stop_pull_event.is_set():
                try:
                    images_to_process = []
                    
                    # 更新系统资源使用情况
                    cpu_usage = psutil.cpu_percent()
                    memory_usage = psutil.virtual_memory().percent
                    
                    with self.status_lock:
                        self.system_status["cpu_usage"] = cpu_usage
                        self.system_status["memory_usage"] = memory_usage
                    
                    if self.socketio:
                        self.socketio.emit('system_resources', {
                            'cpu': cpu_usage, 
                            'memory': memory_usage
                        })
                    
                    # 收集多个摄像头的图像
                    cameras = self.camera_manager.get_cameras()
                    for camera_id in cameras:
                        try:
                            # 捕获图像
                            image = self.camera_manager.capture_image(camera_id)
                            
                            if image is not None:
                                self.camera_manager.update_camera_status(camera_id, '在线')
                                
                                if self.socketio:
                                    self.socketio.emit('camera_status', {'id': camera_id, 'status': '在线'})
                                
                                # 如果配置为保存图像，则保存图像
                                if self.config_manager.get('save_image', True):
                                    self.camera_manager.save_image(image, camera_id)
                                
                                images_to_process.append((image, camera_id))
                            else:
                                self.camera_manager.update_camera_status(camera_id, '离线', "捕获图像失败")
                                
                                if self.socketio:
                                    self.socketio.emit('camera_status', {'id': camera_id, 'status': '离线', 'error': "捕获图像失败"})
                        except Exception as e:
                            error_msg = f"摄像头 {camera_id} 捕获失败: {str(e)}"
                            self.log_manager.error(error_msg)
                            
                            self.camera_manager.update_camera_status(camera_id, '离线', str(e))
                            
                            if self.socketio:
                                self.socketio.emit('camera_status', {'id': camera_id, 'status': '离线', 'error': str(e)})
                    
                    if images_to_process:
                        try:
                            # 批量分析图像
                            results = self.analyze_images(images_to_process)
                            
                            # 上传结果
                            for camera_id, detected_count in results.items():
                                self.log_manager.detection(f"检测到人数: {detected_count}", f"摄像头 {camera_id}")
                                self.upload_result(camera_id, detected_count)
                        except Exception as e:
                            error_msg = f"批量处理失败: {str(e)}"
                            self.log_manager.error(error_msg)
                            
                            if self.socketio:
                                self.socketio.emit('system_error', {'message': error_msg})
                
                except Exception as e:
                    self.error_count += 1
                    error_msg = f"拉取模式循环异常 ({self.error_count}/{self.max_errors}): {str(e)}"
                    self.log_manager.error(error_msg)
                    
                    if self.socketio:
                        self.socketio.emit('system_error', {'message': f'拉取模式异常: {str(e)}'})
                    
                    # 如果错误次数过多，退出循环
                    if self.error_count >= self.max_errors:
                        self.log_manager.error("错误次数过多，停止检测线程")
                        break
                    
                    # 短暂延迟后继续尝试
                    time.sleep(2)
                
                # 使用事件对象的wait方法，允许提前中断
                interval = self.config_manager.get('interval', 1)
                if self.stop_pull_event.wait(interval):
                    break
        
        except Exception as e:
            error_msg = f"严重错误，拉取模式线程退出: {str(e)}"
            self.log_manager.error(error_msg)
        
        finally:
            # 确保线程退出时更新状态
            if self.pull_running:
                self.log_manager.warning("拉取模式线程异常退出，更新状态")
                self.pull_running = False
                
                with self.status_lock:
                    self.system_status["pull_running"] = False
                
                if self.socketio:
                    self.socketio.emit('system_update', {'pull_running': False})
                    self.socketio.emit('system_error', {'message': '拉取模式异常退出，请检查日志'})
            
            self.log_manager.info("主动拉取模式已停止")
    
    def analyze_image(self, image, camera_id):
        """分析单个图像"""
        # 确保模型已加载
        if not self.model_loaded:
            if not self.model_loading:
                self.load_model_async()
                # 等待模型加载完成
                timeout = 30  # 最多等待30秒
                start_time = time.time()
                while self.model_loading and time.time() - start_time < timeout:
                    time.sleep(0.5)
                
                if not self.model_loaded:
                    raise Exception("模型加载失败或超时")
            else:
                raise Exception("模型正在加载中，请稍后再试")
        
        # 保存图像到临时文件
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        temp_dir = os.path.join("temp", f"camera_{camera_id}")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"{timestamp}.jpg")
        
        cv2.imwrite(temp_path, image)
        
        # 导入检测模块
        detect_module = importlib.import_module('detect.run')
        
        # 使用模型进行检测
        with self.model_lock:
            count = detect_module.detect(temp_path, model=self.model)
        
        return count
    
    def analyze_images(self, images_data):
        """批量处理多个图像"""
        # 确保模型已加载
        if not self.model_loaded:
            if not self.model_loading:
                self.load_model_async()
                # 等待模型加载完成
                timeout = 30  # 最多等待30秒
                start_time = time.time()
                while self.model_loading and time.time() - start_time < timeout:
                    time.sleep(0.5)
                
                if not self.model_loaded:
                    raise Exception("模型加载失败或超时")
            else:
                raise Exception("模型正在加载中，请稍后再试")
        
        temp_paths = []
        path_to_camera = {}
        
        # 保存所有图像到文件
        for image, camera_id in images_data:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            temp_dir = os.path.join("temp", f"camera_{camera_id}")
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, f"{timestamp}.jpg")
            
            cv2.imwrite(temp_path, image)
            temp_paths.append(temp_path)
            path_to_camera[temp_path] = camera_id
        
        # 导入检测模块
        detect_module = importlib.import_module('detect.run')
        
        # 批量处理图像
        with self.model_lock:
            results = detect_module.detect_series(temp_paths, model=self.model)
        
        # 整理结果
        camera_results = {}
        for path, count in results.items():
            camera_id = path_to_camera[path]
            camera_results[camera_id] = count
        
        # 准备节点数据用于WebSocket发送
        nodes_data = []
        for camera_id, count in camera_results.items():
            nodes_data.append({
                "node_id": camera_id,
                "count": count
            })
        
        # 使用WebSocket发送数据（如果可用）
        if self.ws_client and self.ws_client.connected:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            asyncio.run_coroutine_threadsafe(
                self.ws_client.send_nodes_data(nodes_data),
                loop
            )
        
        return camera_results
    
    def upload_result(self, camera_id, detected_count):
        """上传检测结果到服务器"""
        api_url = self.config_manager.get('api_url')
        
        data = {
            "id": camera_id,
            "detected_count": detected_count,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
        try:
            response = requests.post(api_url, json=data, timeout=5)
            if response.status_code != 201:
                error_msg = f"上传警告: 状态码 {response.status_code}, 响应: {response.text}"
                self.log_manager.warning(error_msg, f"摄像头 {camera_id}")
                
                self.camera_manager.update_camera_status(camera_id, '错误', response.text)
                
                if self.socketio:
                    self.socketio.emit('camera_status', {'id': camera_id, 'status': '错误', 'error': response.text})
            else:
                self.camera_manager.update_camera_status(camera_id, '在线')
                self.camera_manager.update_detection_count(camera_id, detected_count)
                
                # 记录检测事件
                self.log_manager.detection(f"检测到人数: {detected_count}", f"摄像头 {camera_id}")
                
                # 更新统计数据
                self.update_detection_stats(detected_count)
                
                # 更新系统状态
                with self.status_lock:
                    camera_status = self.camera_manager.get_camera_status()
                    if camera_id in camera_status:
                        self.system_status["last_detection"] = {
                            "camera_id": camera_id,
                            "count": detected_count,
                            "time": camera_status[camera_id]['last_capture']
                        }
                
                if self.socketio:
                    camera_status = self.camera_manager.get_camera_status()
                    last_update = camera_status[camera_id]['last_capture'] if camera_id in camera_status else "未知"
                    
                    self.socketio.emit('detection_result', {
                        'camera_id': camera_id, 
                        'count': detected_count,
                        'time': last_update
                    })
            
            return True
        except Exception as e:
            error_msg = f"上传结果失败: {str(e)}"
            self.log_manager.error(error_msg, f"摄像头 {camera_id}")
            
            self.camera_manager.update_camera_status(camera_id, '离线', str(e))
            
            if self.socketio:
                self.socketio.emit('camera_status', {'id': camera_id, 'status': '离线', 'error': str(e)})
            
            return False
    
    def reset_daily_stats(self):
        """重置日统计数据"""
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        with self.stats_lock:
            if self.detection_stats['last_day_reset'] != current_date:
                self.detection_stats['today_count'] = 0
                self.detection_stats['last_day_reset'] = current_date
                self.log_manager.info(f'重置每日统计数据: {current_date}')
    
    def update_detection_stats(self, count):
        """更新检测统计"""
        # 检查是否需要重置每日统计
        self.reset_daily_stats()
        
        # 更新统计数据
        with self.stats_lock:
            self.detection_stats['today_count'] += 1
            self.detection_stats['total_count'] += 1
            self.detection_stats['max_count'] = max(self.detection_stats['max_count'], count)
            self.detection_stats['detection_sum'] += count
            
            if self.detection_stats['total_count'] > 0:
                self.detection_stats['avg_count'] = self.detection_stats['detection_sum'] / self.detection_stats['total_count']
            else:
                self.detection_stats['avg_count'] = 0
        
        # 发送统计更新
        if self.socketio:
            self.socketio.emit('stats_update', self.detection_stats)
    
    def get_detection_stats(self):
        """获取检测统计数据"""
        self.reset_daily_stats()
        with self.stats_lock:
            return self.detection_stats.copy()
    
    def get_system_status(self):
        """获取系统状态"""
        with self.status_lock:
            # 合并摄像头状态
            status = self.system_status.copy()
            status['cameras'] = self.camera_manager.get_camera_status()
            return status
    
    def process_received_frame(self, camera_id, image_data):
        """处理接收到的图像帧（用于被动接收模式）"""
        if not self.push_running:
            return {'status': 'error', 'message': '被动接收模式未启动'}
        
        try:
            # 将图像数据转换为OpenCV格式
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return {'status': 'error', 'message': '无效的图像数据'}
            
            # 如果配置为保存图像，则保存图像
            if self.config_manager.get('save_image', True):
                self.camera_manager.save_image(image, camera_id)
            
            # 分析图像
            count = self.analyze_image(image, camera_id)
            
            # 上传结果
            self.upload_result(camera_id, count)
            
            return {'status': 'success', 'detected_count': count}
        except Exception as e:
            error_msg = f"处理接收帧失败: {str(e)}"
            self.log_manager.error(error_msg)
            return {'status': 'error', 'message': error_msg}
