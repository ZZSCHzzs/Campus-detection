import cv2
import requests
import numpy as np
import os
import datetime
import logging
import time
from threading import Lock

logger = logging.getLogger('camera_manager')

class Camera:
    """摄像头类，负责摄像头的连接和图像获取"""
    
    def __init__(self, camera_id, url):
        self.id = camera_id
        self.url = url
        self._cap = None
        self._last_check = 0
        self._available = False
        self._check_interval = 10  # 每10秒检查一次可用性
        
    def is_available(self):
        """检查摄像头是否可用"""
        # 如果上次检查在10秒内，直接返回缓存的结果
        current_time = time.time()
        if current_time - self._last_check < self._check_interval:
            return self._available
            
        # 重新检查可用性
        try:
            if self._cap is None:
                # 尝试打开摄像头
                self._cap = cv2.VideoCapture(self.url)
                
            # 尝试读取一帧
            ret = self._cap.grab()
            
            self._available = ret
            self._last_check = current_time
            
            return self._available
        except Exception as e:
            logger.error(f"检查摄像头 {self.id} 可用性失败: {e}")
            self._available = False
            self._last_check = current_time
            return False

class CameraManager:
    """摄像头管理器，负责管理多个摄像头"""
    
    # 摄像头分辨率对照表
    FRAME_SIZES = {
        10: (1600, 1200),  # UXGA
        9: (1280, 1024),   # SXGA
        8: (1024, 768),    # XGA
        7: (800, 600),     # SVGA
        6: (640, 480),     # VGA
        5: (400, 296),     # CIF
        4: (320, 240),     # QVGA
        3: (240, 176),     # HQVGA
        0: (160, 120)      # QQVGA
    }
    
    def __init__(self, config_manager):
        """初始化摄像头管理器"""
        self.config_manager = config_manager
        self.cameras = {}  # 存储摄像头信息
        self.camera_status = {}  # 存储摄像头状态
        self.lock = Lock()
        
        # 从配置中加载摄像头设置
        self._load_cameras()
        
    def _load_cameras(self):
        """从配置中加载摄像头信息"""
        camera_config = self.config_manager.get('cameras', {})
        
        with self.lock:
            self.cameras = camera_config.copy()
            # 初始化摄像头状态
            for camera_id in self.cameras:
                if camera_id not in self.camera_status:
                    self.camera_status[camera_id] = {
                        'status': '未知',
                        'last_capture': None,
                        'detection_count': 0,
                        'error': None
                    }
        
        logger.info(f"已加载{len(self.cameras)}个摄像头配置")
    
    def get_cameras(self):
        """获取所有摄像头信息"""
        with self.lock:
            return self.cameras.copy()
    
    def get_camera_status(self):
        """获取所有摄像头状态"""
        with self.lock:
            return self.camera_status.copy()
    
    def update_camera_status(self, camera_id, status, error=None):
        """更新摄像头状态"""
        with self.lock:
            if camera_id in self.camera_status:
                self.camera_status[camera_id]['status'] = status
                self.camera_status[camera_id]['error'] = error
                return True
            return False
    
    def update_detection_count(self, camera_id, count):
        """更新摄像头检测计数"""
        with self.lock:
            if camera_id in self.camera_status:
                self.camera_status[camera_id]['detection_count'] = count
                self.camera_status[camera_id]['last_capture'] = datetime.datetime.now().strftime("%H:%M:%S")
                return True
            return False
    
    def check_camera_connection(self, camera_id):
        """检查摄像头连接状态"""
        if camera_id not in self.cameras:
            logger.warning(f"未找到摄像头ID: {camera_id}")
            return False
        
        camera_url = self.cameras[camera_id]
        try:
            response = requests.get(f"{camera_url}/status", timeout=2)
            if response.status_code == 200:
                self.update_camera_status(camera_id, '在线')
                return True
            else:
                self.update_camera_status(camera_id, '错误', f"HTTP错误: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.update_camera_status(camera_id, '离线', str(e))
            return False
    
    def apply_camera_config(self, camera_id):
        """应用摄像头配置"""
        if camera_id not in self.cameras:
            logger.warning(f"未找到摄像头ID: {camera_id}")
            return False
        
        camera_url = self.cameras[camera_id]
        if not self.check_camera_connection(camera_id):
            logger.error(f"无法连接到摄像头: {camera_url}")
            return False
        
        # 获取摄像头配置
        config = self.config_manager.get('camera_config', {})
        
        # 应用配置
        for param, value in config.items():
            self._configure_camera(param, value, camera_url)
        
        logger.info(f"已应用摄像头{camera_id}的配置")
        return True
    
    def _configure_camera(self, parameter, value, base_url):
        """配置远程摄像头的参数"""
        if isinstance(value, bool):
            value = 1 if value else 0
        
        config_url = f"{base_url}/control?var={parameter}&val={value}"
        try:
            response = requests.get(config_url, timeout=2)
            if response.status_code == 200:
                return True
            else:
                logger.warning(f"配置失败: {parameter} = {value}, 状态码: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"无法连接摄像头: {e}")
            return False
    
    def capture_image(self, camera_id):
        """从指定摄像头捕获图像"""
        if camera_id not in self.cameras:
            logger.warning(f"未找到摄像头ID: {camera_id}")
            return None
        
        camera_url = self.cameras[camera_id]
        stream_url = f"{camera_url}/stream"
        
        try:
            # 使用Requests流模式读取数据
            response = requests.get(stream_url, stream=True, timeout=5)
            if response.status_code != 200:
                raise Exception(f"HTTP错误: {response.status_code}")
            
            bytes_data = bytes()
            for chunk in response.iter_content(chunk_size=1024):
                bytes_data += chunk
                # 查找JPEG起始和结束标记
                a = bytes_data.find(b'\xff\xd8')
                b = bytes_data.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    jpg = bytes_data[a:b+2]
                    bytes_data = bytes_data[b+2:]
                    # 转换为OpenCV图像格式
                    image = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if image is not None:
                        self.update_camera_status(camera_id, '在线')
                        return image
            
            raise Exception("未找到有效的JPEG帧")
        except Exception as e:
            error_msg = f"捕获图像失败: {str(e)}"
            logger.error(error_msg)
            self.update_camera_status(camera_id, '离线', error_msg)
            return None
    
    def save_image(self, image, camera_id, directory='captures'):
        """保存图像到指定目录"""
        if image is None:
            logger.warning("尝试保存空图像")
            return None
        
        # 确保目录存在
        camera_dir = os.path.join(directory, f"camera_{camera_id}")
        os.makedirs(camera_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}.jpg"
        filepath = os.path.join(camera_dir, filename)
        
        # 保存图像
        try:
            success = cv2.imwrite(filepath, image)
            if success:
                logger.debug(f"图像已保存: {filepath}")
                return filepath
            else:
                logger.error(f"保存图像失败: {filepath}")
                return None
        except Exception as e:
            logger.error(f"保存图像异常: {e}")
            return None
    
    def get_frame_size(self):
        """获取当前配置的帧大小"""
        framesize = self.config_manager.get('camera_config', {}).get('framesize', 8)
        return self.FRAME_SIZES.get(framesize, (1024, 768))  # 默认返回XGA
