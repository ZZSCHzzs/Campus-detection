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
    
    def __init__(self, config_manager, camera_manager, log_manager, ws_client=None):
        """初始化检测管理器"""
        self.config_manager = config_manager
        self.camera_manager = camera_manager
        self.log_manager = log_manager
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
        
        # 添加状态变化标志
        self.status_changed = False
        
        # 添加帧统计
        self.frames_processed = 0
        self.frames_lock = Lock()

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
        if self.model_loaded or self.model_loading:
            self.log_manager.info("模型已经加载或正在加载中")
            return False
            
        self.model_loading = True
        
        # 使用线程进行模型加载
        def load_model_thread():
            try:
                self._load_model()
                   
            except Exception as e:
                error_msg = f"加载模型失败: {str(e)}"
                # 使用同步日志记录方法，避免异步问题
                if hasattr(self.log_manager, 'error_sync'):
                    self.log_manager.error_sync(error_msg)
                else:
                    self.log_manager.error(error_msg)
                    
            finally:
                self.model_loading = False
        
        # 启动模型加载线程
        import threading
        thread = threading.Thread(target=load_model_thread, daemon=True)
        thread.start()
        
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
                      
            return True
        except Exception as e:
            error_msg = f"加载模型失败: {str(e)}"
            self.log_manager.error(error_msg)
            
            self.model_loading = False
            with self.model_lock:
                self.model_loaded = False
            
            with self.status_lock:
                self.system_status['model_loaded'] = False
                    
            return False
    
    def start_push(self):
        """启动被动接收模式"""
        if self.push_running:
            return False
        
        self.push_running = True
        self.status_changed = True  # 标记状态已变化
        
        with self.status_lock:
            self.system_status["push_running"] = True
        
        self.log_manager.info("已启动被动接收模式")
            
        return True
    
    def stop_push(self):
        """停止被动接收模式"""
        self.log_manager.info("尝试停止被动接收模式...")
        
        if not self.push_running:
            self.log_manager.info("被动接收模式未运行，无需停止")
            return False
        
        # 确保状态标记更新
        self.push_running = False
        self.status_changed = True  # 标记状态已变化
        
        with self.status_lock:
            self.system_status["push_running"] = False
        
        self.log_manager.info("已停止被动接收模式")
         
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
        self.status_changed = True  # 标记状态已变化
        
        with self.status_lock:
            self.system_status["pull_running"] = True
        
        self.log_manager.info("已启动主动拉取模式")
        
        return True
    
    def stop_pull(self):
        """停止主动拉取模式"""
        self.log_manager.info("尝试停止主动拉取模式...")
        
        if not self.pull_running:
            self.log_manager.info("主动拉取模式未运行，无需停止")
            return False
        
        try:
            # 设置停止事件，通知线程结束
            self.stop_pull_event.set()
            self.log_manager.info("已设置停止信号，等待线程结束...")
            
            # 等待线程结束，适当增加超时时间
            if self.pull_thread and self.pull_thread.is_alive():
                self.pull_thread.join(timeout=5.0)
                
                # 检查线程是否真正结束
                if self.pull_thread.is_alive():
                    self.log_manager.warning("拉取线程在超时时间内未结束，将强制标记为停止")
            
            # 无论线程是否真正结束，都更新状态标记
            self.pull_running = False
            self.status_changed = True  # 标记状态已变化
            
            with self.status_lock:
                self.system_status["pull_running"] = False
            
            self.log_manager.info("已停止主动拉取模式")
            
            return True
        except Exception as e:
            self.log_manager.error(f"停止主动拉取模式时出错: {str(e)}")
            # 确保即使出错，也更新状态
            self.pull_running = False
            with self.status_lock:
                self.system_status["pull_running"] = False
            
            return False
    
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
        
        return True
    
    def _pull_mode_handler(self):
        """主动拉取模式处理函数"""
        self.log_manager.info("运行在主动拉取模式...")
        
        try:
            while not self.stop_pull_event.is_set():
                try:
                    # 添加检查点，更频繁地检查停止信号
                    if self.stop_pull_event.is_set():
                        self.log_manager.info("检测到停止信号，中断拉取循环")
                        break
                    
                    images_to_process = []
                    env_data_to_process = []  # 存储环境数据
                    
                    # 更新系统资源使用情况
                    cpu_usage = psutil.cpu_percent()
                    memory_usage = psutil.virtual_memory().percent
                    
                    with self.status_lock:
                        self.system_status["cpu_usage"] = cpu_usage
                        self.system_status["memory_usage"] = memory_usage
                    
                    # 收集CO2数据（假设本地有传感器）
                    try:
                        co2_level = self.read_co2_sensor()  
                        if co2_level is not None:
                            with self.status_lock:
                                self.system_status["co2_level"] = co2_level
                            
                            # 通过WebSocket发送系统状态
                            if self.ws_client and self.ws_client.connected:
                                try:
                                    status_data = self.get_system_status()
                                    loop = asyncio.get_event_loop()
                                    asyncio.run_coroutine_threadsafe(
                                        self.ws_client.send_status(status_data),
                                        loop
                                    )
                                except Exception as e:
                                    self.log_manager.error(f"发送CO2数据失败: {str(e)}")
                    except Exception as e:
                        self.log_manager.error(f"读取CO2传感器失败: {str(e)}")
                    
                    # 收集多个摄像头的图像和环境数据
                    cameras = self.camera_manager.get_cameras()
                    for camera_id in cameras:
                        try:
                            # 捕获图像
                            image = self.camera_manager.capture_image(camera_id)
                            
                            if image is not None:
                                self.camera_manager.update_camera_status(camera_id, '在线')
                                
                                # 如果配置为保存图像，则保存图像
                                if self.config_manager.get('save_image', True):
                                    self.camera_manager.save_image(image, camera_id)
                                
                                images_to_process.append((image, camera_id))
                            else:
                                self.camera_manager.update_camera_status(camera_id, '离线', "捕获图像失败")
                            
                            # 尝试获取环境数据 - 假设与摄像头URL相关的路由
                            try:
                                env_data = self.get_environmental_data(camera_id)
                                if env_data:
                                    env_data_to_process.append((camera_id, env_data))
                            except Exception as e:
                                self.log_manager.error(f"获取节点 {camera_id} 环境数据失败: {str(e)}")
                                
                        except Exception as e:
                            error_msg = f"摄像头 {camera_id} 捕获失败: {str(e)}"
                            self.log_manager.error(error_msg)
                            
                            self.camera_manager.update_camera_status(camera_id, '离线', str(e))
                
                    # 处理环境数据
                    if env_data_to_process:
                        nodes_data = []
                        for camera_id, env_data in env_data_to_process:
                            node_data = {"id": camera_id}
                            
                            if 'temperature' in env_data:
                                node_data["temperature"] = env_data['temperature']
                            if 'humidity' in env_data:
                                node_data["humidity"] = env_data['humidity']
                            
                            nodes_data.append(node_data)
                        
                        # 通过WebSocket发送环境数据
                        if nodes_data and self.ws_client and self.ws_client.connected:
                            try:
                                loop = asyncio.get_event_loop()
                                asyncio.run_coroutine_threadsafe(
                                    self.ws_client.send_nodes_data(nodes_data),
                                    loop
                                )
                            except Exception as e:
                                self.log_manager.error(f"发送环境数据失败: {str(e)}")
                    
                    # 处理图像
                    if images_to_process:
                        try:
                            # 批量分析图像
                            results = self.analyze_images(images_to_process)
                            
                            # 上传结果
                            for camera_id, detected_count in results.items():
                                self.log_manager.detection(f"检测到人数: {detected_count}", f"摄像头 {camera_id}")
                                
                                # 获取节点的环境数据（如果有）
                                env_data = {}
                                for cid, data in env_data_to_process:
                                    if cid == camera_id:
                                        env_data = data
                                        break
                                
                                # 上传包含环境数据的结果
                                self.upload_result(camera_id, detected_count, env_data)
                        except Exception as e:
                            error_msg = f"批量处理失败: {str(e)}"
                            self.log_manager.error(error_msg)
                
                except Exception as e:
                    self.error_count += 1
                    error_msg = f"拉取模式循环异常 ({self.error_count}/{self.max_errors}): {str(e)}"
                    self.log_manager.error(error_msg)
                    
                   
                    # 如果错误次数过多，退出循环
                    if self.error_count >= self.max_errors:
                        self.log_manager.error("错误次数过多，停止检测线程")
                        break
                    
                    # 短暂延迟后继续尝试
                    time.sleep(2)
                
                # 检查停止事件，更频繁地响应停止信号
                if self.stop_pull_event.is_set():
                    self.log_manager.info("检测到停止信号，中断拉取循环")
                    break
                
                # 使用更短的等待间隔，提高响应性
                interval = self.config_manager.get('interval', 1)
                # 将长等待分解为多个短等待，以便更快响应停止信号
                short_interval = min(1.0, interval)
                remaining = interval
                while remaining > 0 and not self.stop_pull_event.is_set():
                    wait_time = min(short_interval, remaining)
                    if self.stop_pull_event.wait(wait_time):
                        self.log_manager.info("等待间隔期间检测到停止信号")
                        break
                    remaining -= wait_time
                
                # 再次检查停止信号
                if self.stop_pull_event.is_set():
                    break
                
            self.log_manager.info("主动拉取模式已停止")
        
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
        
        try:
            # 保存图像到临时文件
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp", f"camera_{camera_id}")
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, f"{timestamp}.jpg")
            
            cv2.imwrite(temp_path, image)
            
            # 导入检测模块
            detect_module = importlib.import_module('detect.run')
            
            # 使用模型进行检测
            with self.model_lock:
                count = detect_module.detect(temp_path, model=self.model)
            
            # 增加帧统计
            with self.frames_lock:
                self.frames_processed += 1
            
            return count
        except Exception as e:
            self.log_manager.error(f"分析图像失败: {str(e)}")
            # 返回默认值而不是抛出异常，以避免中断处理流程
            return 0
    
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
    
    def upload_result(self, camera_id, detected_count, env_data=None):
        """上传检测结果和环境数据到服务器"""
        api_url = self.config_manager.get('api_url')
        
        data = {
            "id": camera_id,
            "detected_count": detected_count,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
        # 添加环境数据（如果有）
        if env_data:
            if 'temperature' in env_data and env_data['temperature'] is not None:
                data['temperature'] = env_data['temperature']
            if 'humidity' in env_data and env_data['humidity'] is not None:
                data['humidity'] = env_data['humidity']
        
        # 添加CO2数据（如果有）
        with self.status_lock:
            if 'co2_level' in self.system_status and self.system_status['co2_level'] is not None:
                data['co2_level'] = self.system_status['co2_level']
        
        try:
            response = requests.post(api_url, json=data, timeout=5)
            if response.status_code != 201:
                error_msg = f"上传警告: 状态码 {response.status_code}, 响应: {response.text}"
                self.log_manager.warning(error_msg, f"摄像头 {camera_id}")
                
                self.camera_manager.update_camera_status(camera_id, '错误', response.text)
                
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
            
            return True
        except Exception as e:
            error_msg = f"上传结果失败: {str(e)}"
            self.log_manager.error(error_msg, f"摄像头 {camera_id}")
            
            self.camera_manager.update_camera_status(camera_id, '离线', str(e))
              
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
    
    def on_config_changed(self, old_config=None, new_config=None):
        """处理配置变更"""
        # 如果没有提供新旧配置，直接从配置管理器获取当前配置
        if new_config is None:
            new_config = self.config_manager.get_all()
            old_config = {}  # 没有旧配置进行比较时假设所有配置都已更改
        
        # 标记状态已变化，触发状态同步
        self.status_changed = True
        
        # 1. 处理模式变更
        if 'mode' in new_config and new_config['mode'] != old_config.get('mode'):
            new_mode = new_config['mode']
            self.log_manager.info(f"配置变更: 检测模式 {old_config.get('mode', '未知')} -> {new_mode}")
            
            with self.status_lock:
                self.system_status["mode"] = new_mode
            
            # 应用新模式
            self.change_mode(new_mode)
        
        # 2. 处理拉取间隔变更
        if 'interval' in new_config and new_config['interval'] != old_config.get('interval'):
            new_interval = new_config['interval']
            self.log_manager.info(f"配置变更: 拉取间隔 {old_config.get('interval', '未知')} -> {new_interval}秒")
            
            # 如果正在运行拉取模式，需要重启以应用新间隔
            if self.pull_running:
                self.log_manager.info("重启拉取服务以应用新间隔")
                self.stop_pull()
                self.start_pull()
        
        # 3. 处理预加载模型设置变更
        if 'preload_model' in new_config and new_config['preload_model'] != old_config.get('preload_model'):
            preload_model = new_config['preload_model']
            self.log_manager.info(f"配置变更: 预加载模型 {old_config.get('preload_model', '未知')} -> {preload_model}")
            
            # 如果启用预加载且模型未加载，启动模型加载
            if preload_model and not self.model_loaded and not self.model_loading:
                self.log_manager.info("开始加载模型...")
                self.load_model_async()

    def read_co2_sensor(self):
        """读取CO2传感器数据"""
        pass

    def get_environmental_data(self, camera_id):
        """获取摄像头相关的环境数据"""
        camera_info = self.camera_manager.get_camera_info(camera_id)
        if not camera_info or 'url' not in camera_info:
            raise ValueError(f"摄像头 {camera_id} 信息不完整，无法获取环境数据")
        
        url = camera_info['url'] + '/environment'
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                raise ValueError(f"获取环境数据失败: 状态码 {response.status_code}")
        except Exception as e:
            raise ValueError(f"获取环境数据异常: {str(e)}")

