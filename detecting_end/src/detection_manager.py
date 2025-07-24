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
headers = {
    "User-Agent": "Mozilla/5.0",
    "Connection": "close",
    "Accept": "*/*"
}

class DetectionManager:
    """
    检测管理器，负责管理检测线程和任务
    支持两种模式：被动接收(push)和主动拉取(pull)
    """
    
    def __init__(self, config_manager, node_manager, log_manager, ws_client, system_monitor):
        """初始化检测管理器"""
        self.config_manager = config_manager
        self.node_manager = node_manager
        self.log_manager = log_manager
        self.ws_client = ws_client
        self.system_monitor = system_monitor
        
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
        self.system_status = {}
        self.status_lock = Lock()
        
        # 添加状态变化标志
        self.status_changed = False
        
        # 添加帧统计
        self.frames_processed = 0
        self.frames_lock = Lock()

    def initialize(self):
        """初始化检测管理器，但不启动检测线程"""
        # 如果配置为预加载模型，则启动模型加载线程
        if self.config_manager.get('preload_model', True):
            self.load_model_async()
        
        # 仅初始化，不启动任何模式
        logger.info("检测管理器初始化完成，等待系统准备就绪后启动检测线程")
        return True
    
    def start_detection(self):
        """在系统完全初始化后启动检测模式，确保模型已加载"""
        # 等待模型加载完成
        logger.info("等待YOLO模型加载完成...")
        wait_time = 0
        max_wait = 60  # 最长等待60秒
        while not self.model_loaded:
            if not self.model_loading:
                self.load_model_async()
            time.sleep(1)
            wait_time += 1
            if wait_time >= max_wait:
                logger.error("YOLO模型加载超时，检测线程未启动")
                return False
        # 根据配置的模式启动相应的检测服务
        mode = self.config_manager.get('mode', 'push')
        logger.info(f"系统初始化完成，正在启动检测: {mode}")
        
        if mode == 'push' or mode == 'both':
            self.start_push()
        
        if mode == 'pull' or mode == 'both':
            self.start_pull()
        
        return True
    
    def load_model_async(self):
        """异步加载模型"""
        if self.model_loaded or self.model_loading:
            logger.info("模型已经加载或正在加载中")
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
                    logger.error_sync(error_msg)
                else:
                    logger.error(error_msg)
                    
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
            logger.info("正在加载YOLO模型...")
            
            # 动态导入detect模块，避免循环导入
            detect_module = importlib.import_module('detect.run')
            
            with self.model_lock:
                self.model = detect_module.load_model()
                self.model_loaded = True
                self.model_loading = False
            
            with self.status_lock:
                self.system_status['model_loaded'] = True
            
            logger.info("YOLO模型加载完成")
                      
            return True
        except Exception as e:
            error_msg = f"加载模型失败: {str(e)}"
            logger.error(error_msg)
            
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
        self.status_changed = True
        
        with self.status_lock:
            self.system_status["push_running"] = True
        
        logger.info("已启动被动接收模式")
            
        return True
    
    def stop_push(self):
        """停止被动接收模式"""
        logger.info("停止被动接收模式...")
        
        if not self.push_running:
            logger.info("被动接收模式未运行，无需停止")
            return False
        
        # 确保状态标记更新
        self.push_running = False
        self.status_changed = True  # 标记状态已变化
        
        with self.status_lock:
            self.system_status["push_running"] = False

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
        self.status_changed = True
        
        with self.status_lock:
            self.system_status["pull_running"] = True
        
        logger.info("已启动主动拉取模式")
        
        return True
    
    def stop_pull(self):
        """停止主动拉取模式"""
        
        if not self.pull_running:
            logger.info("主动拉取模式未运行，无需停止")
            return False
        
        try:
            # 设置停止事件，通知线程结束
            self.stop_pull_event.set()
            logger.info("停止拉取线程，等待线程结束...")
            
            # 等待线程结束，适当增加超时时间
            if self.pull_thread and self.pull_thread.is_alive():
                self.pull_thread.join(timeout=5.0)
                
                # 检查线程是否真正结束
                if self.pull_thread.is_alive():
                    logger.warning("拉取线程在超时时间内未结束，将强制标记为停止")
            
            # 无论线程是否真正结束，都更新状态标记
            self.pull_running = False
            self.status_changed = True
            
            with self.status_lock:
                self.system_status["pull_running"] = False
            
            logger.info("已停止主动拉取模式")
            
            return True
        except Exception as e:
            logger.error(f"停止主动拉取模式时出错: {str(e)}")
            self.pull_running = False
            with self.status_lock:
                self.system_status["pull_running"] = False
            
            return False
    
    def change_mode(self, new_mode):
        """根据模式启动或停止相应服务"""
        current_mode = self.config_manager.get('mode')
        if new_mode == current_mode:
            return False
        
        logger.info(f"切换模式: {current_mode} -> {new_mode}")
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
        elif new_mode == 'none':
            self.stop_push()
            self.stop_pull()
        
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
        
        logger.info(f"拉取间隔已更新为{new_interval}秒")
        
        # 如果当前正在进行主动拉取，重启主动拉取使新间隔生效
        if self.pull_running:
            self.stop_pull()
            self.start_pull()
            logger.info("已重启拉取服务以应用新间隔")
        
        return True
    
    def _pull_mode_handler(self):
        """主动拉取模式处理函数"""
        logger.info("开始主动拉取...")
        
        # 设置浏览器样式的请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        try:
            while not self.stop_pull_event.is_set():
                try:
                    logger.info("开始新一轮拉取...")
                    
                    # 添加检查点，更频繁地检查停止信号
                    if self.stop_pull_event.is_set():
                        logger.info("检测到停止信号，中断拉取循环")
                        break
                    
                    images_to_process = []
                    env_data_to_process = []
                    
                    
                    # 收集多个摄像头的图像和环境数据
                    nodes = self.node_manager.get_nodes()
                    for node_id in nodes:
                        try:
                            # 添加摄像头处理日志
                            logger.info(f"尝试获取节点 {node_id} 的数据")
                            
                            # 优先访问环境数据
                            env_data = None
                            try:
                                env_data = self.node_manager.get_environmental_data(node_id, headers, retry=2)
                                if env_data:
                                    logger.info(f"成功获取节点 {node_id} 环境数据: {env_data}")
                                    env_data_to_process.append((node_id, env_data))
                            except Exception as e:
                                logger.error(f"获取节点 {node_id} 环境数据失败: {str(e)}")
                            
                            time.sleep(1.0)
                            
                            try:
                                logger.info(f"尝试获取节点 {node_id} 图像...")
                                
                                # 捕获图像，添加重试机制
                                for retry in range(2):
                                    try:
                                        image = self.node_manager.capture_image(node_id)
                                        if image is None:
                                            logger.warning(f"摄像头 {node_id} 图像获取失败，重试 {retry+1}/2")
                                            time.sleep(1)
                                    except Exception as e:
                                        logger.warning(f"摄像头 {node_id} 图像获取异常: {str(e)}，重试 {retry+1}/2")
                                        time.sleep(1)
                                
                                if image is not None:
                                    self.node_manager.update_node_status(node_id, '在线')
                                    if self.config_manager.get('save_image', True):
                                        self.node_manager.save_image(image, node_id)
                                    images_to_process.append((image, node_id))
                                else:
                                    self.node_manager.update_node_status(node_id, '离线', "捕获图像失败，已尝试2次")
                            except Exception as e:
                                logger.error(f"捕获摄像头 {node_id} 图像处理过程中发生错误: {str(e)}")
                                self.node_manager.update_node_status(node_id, '离线', str(e))
                            
                            time.sleep(0.5)
                            
                        except Exception as e:
                            error_msg = f"摄像头 {node_id} 处理失败: {str(e)}"
                            logger.error(error_msg)
                            self.node_manager.update_node_status(node_id, '离线', str(e))
                
                    if env_data_to_process:
                        nodes_data = []
                        for node_id, env_data in env_data_to_process:
                            node_data = {"id": node_id}
                            
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
                                logger.error(f"发送环境数据失败: {str(e)}")
                    
                    # 处理图像
                    if images_to_process:
                        try:
                            # 批量分析图像
                            results = self.analyze_images(images_to_process)
                            
                            # 上传结果
                            for node_id, detected_count in results.items():
                                logger.detection(f"检测到人数: {detected_count}", f"摄像头 {node_id}")
                                
                                # 获取节点的环境数据（如果有）
                                env_data = {}
                                for cid, data in env_data_to_process:
                                    if cid == node_id:
                                        env_data = data
                                        break
                                
                                # 上传包含环境数据的结果
                                self.upload_result(node_id, detected_count, env_data)
                        except Exception as e:
                            error_msg = f"批量处理失败: {str(e)}"
                            logger.error(error_msg)
                
                except Exception as e:
                    self.error_count += 1
                    error_msg = f"拉取模式循环异常 ({self.error_count}/{self.max_errors}): {str(e)}"
                    logger.error(error_msg)
                    
                   
                    # 如果错误次数过多，退出循环
                    if self.error_count >= self.max_errors:
                        logger.error("错误次数过多，停止检测线程")
                        break
                    
                    # 短暂延迟后继续尝试
                    time.sleep(2)
                
                # 检查停止事件，更频繁地响应停止信号
                if self.stop_pull_event.is_set():
                    logger.info("检测到停止信号，中断拉取循环")
                    break
                
                # 使用更短的等待间隔，提高响应性
                interval = self.config_manager.get('interval', 1)
                # 将长等待分解为多个短等待，以便更快响应停止信号
                short_interval = min(1.0, interval)
                remaining = interval
                while remaining > 0 and not self.stop_pull_event.is_set():
                    wait_time = min(short_interval, remaining)
                    if self.stop_pull_event.wait(wait_time):
                        logger.info("等待间隔期间检测到停止信号")
                        break
                    remaining -= wait_time
                
                # 再次检查停止信号
                if self.stop_pull_event.is_set():
                    break
                
            logger.info("主动拉取模式已停止")
        
        except Exception as e:
            error_msg = f"严重错误，拉取模式线程退出: {str(e)}"
            logger.error(error_msg)
        
        finally:
            # 确保线程退出时更新状态
            if self.pull_running:
                logger.warning("拉取模式线程异常退出，更新状态")
                self.pull_running = False
                
                with self.status_lock:
                    self.system_status["pull_running"] = False
                
  
    def analyze_image(self, image, node_id):
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
                    logger.error("模型加载失败或超时")
            else:
                logger.warning("模型正在加载中，请稍后再试")
        
        try:
            # 保存图像到临时文件
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp", f"node_{node_id}")
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
            logger.error(f"分析图像失败: {str(e)}")
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
        path_to_node = {}
        
        # 保存所有图像到文件
        for image, node_id in images_data:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            temp_dir = os.path.join("temp", f"node_{node_id}")
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, f"{timestamp}.jpg")
            
            cv2.imwrite(temp_path, image)
            temp_paths.append(temp_path)
            path_to_node[temp_path] = node_id
        
        # 导入检测模块
        detect_module = importlib.import_module('detect.run')
        
        # 批量处理图像
        with self.model_lock:
            results = detect_module.detect_series(temp_paths, model=self.model)
        
        # 整理结果
        node_results = {}
        for path, count in results.items():
            node_id = path_to_node[path]
            node_results[node_id] = count
        
        # 准备节点数据用于WebSocket发送
        nodes_data = []
        for node_id, count in node_results.items():
            nodes_data.append({
                "node_id": node_id,
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

        if self.config_manager.get('save_imgae') == False:
            # 删除缓存图片文件
            for temp_path in temp_paths:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception as e:
                    logger.warning(f"删除临时文件失败: {temp_path}, 错误: {str(e)}")
        
        return node_results
    
    def upload_result(self, node_id, detected_count, env_data=None):
        """上传检测结果和环境数据到服务器（优先通过WebSocket）"""
        api_url = self.config_manager.get('api_url')

        data = {
            "id": node_id,
            "detected_count": detected_count,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        }

        # 添加环境数据
        if env_data:
            if 'temperature' in env_data and env_data['temperature'] is not None:
                data['temperature'] = env_data['temperature']
            if 'humidity' in env_data and env_data['humidity'] is not None:
                data['humidity'] = env_data['humidity']


        # 优先通过WebSocket发送
        ws_sent = False
        if self.ws_client and getattr(self.ws_client, "is_connected", lambda: False)():
            try:
                # 组装节点数据格式
                node_data = {
                    "id": node_id,
                    "detected_count": detected_count,
                    "timestamp": data["timestamp"]
                }
                if "temperature" in data:
                    node_data["temperature"] = data["temperature"]
                if "humidity" in data:
                    node_data["humidity"] = data["humidity"]

                # 异步发送
                import asyncio
                loop = asyncio.get_event_loop()
                future = asyncio.run_coroutine_threadsafe(
                    self.ws_client.send_nodes_data([node_data]),
                    loop
                )
                ws_sent = future.result(timeout=5)
                if ws_sent:
                    self.node_manager.update_node_status(node_id, '在线')
                    self.node_manager.update_detection_count(node_id, detected_count)
                    logger.info(f"节点 {node_id} 检测并通过WebSocket上传成功")
                    self.update_detection_stats(detected_count)
                    with self.status_lock:
                        node_status = self.node_manager.get_node_status()
                        if node_id in node_status:
                            self.system_status["last_detection"] = {
                                "node_id": node_id,
                                "count": detected_count,
                                "time": node_status[node_id]['last_capture']
                            }
                    return True
            except Exception as e:
                logger.error(f"节点 {node_id} 通过WebSocket上传失败: {str(e)}")

        # 如果WebSocket不可用或失败则回退HTTP
        try:
            response = requests.post(api_url, json=data, timeout=5)
            if response.status_code != 201:
                error_msg = f"上传警告: 状态码 {response.status_code}, 响应: {response.text}"
                logger.warning(error_msg, f"摄像头 {node_id}")
                self.node_manager.update_node_status(node_id, '错误', response.text)
            else:
                self.node_manager.update_node_status(node_id, '在线')
                self.node_manager.update_detection_count(node_id, detected_count)
                logger.detection(f"检测到人数: {detected_count}", f"摄像头 {node_id}")
                self.update_detection_stats(detected_count)
                with self.status_lock:
                    node_status = self.node_manager.get_node_status()
                    if node_id in node_status:
                        self.system_status["last_detection"] = {
                            "node_id": node_id,
                            "count": detected_count,
                            "time": node_status[node_id]['last_capture']
                        }
            return True
        except Exception as e:
            error_msg = f"上传结果失败: {str(e)}"
            logger.error(error_msg, f"摄像头 {node_id}")
            self.node_manager.update_node_status(node_id, '离线', str(e))
            return False

    def reset_daily_stats(self):
        """重置日统计数据"""
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        with self.stats_lock:
            if self.detection_stats['last_day_reset'] != current_date:
                self.detection_stats['today_count'] = 0
                self.detection_stats['last_day_reset'] = current_date
                logger.info(f'重置每日统计数据: {current_date}')
    
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
            status['nodes'] = self.node_manager.get_node_status()
            return status
    
    def process_received_frame(self, node_id, image_data):
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
                self.node_manager.save_image(image, node_id)
            
            # 分析图像
            count = self.analyze_image(image, node_id)
            
            # 上传结果
            self.upload_result(node_id, count)
            
            return {'status': 'success', 'detected_count': count}
        except Exception as e:
            error_msg = f"处理接收帧失败: {str(e)}"
            logger.error(error_msg)
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
            logger.info(f"配置变更: 检测模式 {old_config.get('mode', '未知')} -> {new_mode}")
            
            with self.status_lock:
                self.system_status["mode"] = new_mode
            
            # 应用新模式
            self.change_mode(new_mode)
        
        # 2. 处理拉取间隔变更
        if 'interval' in new_config and new_config['interval'] != old_config.get('interval'):
            new_interval = new_config['interval']
            logger.info(f"配置变更: 拉取间隔 {old_config.get('interval', '未知')} -> {new_interval}秒")
            
            # 如果正在运行拉取模式，需要重启以应用新间隔
            if self.pull_running:
                logger.info("重启拉取服务以应用新间隔")
                self.stop_pull()
                self.start_pull()
        
        # 3. 处理预加载模型设置变更
        if 'preload_model' in new_config and new_config['preload_model'] != old_config.get('preload_model'):
            preload_model = new_config['preload_model']
            logger.info(f"配置变更: 预加载模型 {old_config.get('preload_model', '未知')} -> {preload_model}")
            
            # 如果启用预加载且模型未加载，启动模型加载
            if preload_model and not self.model_loaded and not self.model_loading:
                logger.info("开始加载模型...")
                self.load_model_async()

    def read_co2_sensor(self):
        """读取CO2传感器数据"""
        pass
