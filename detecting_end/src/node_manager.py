import cv2
import requests
import numpy as np
import os
import datetime
import logging
import time
from threading import Lock

logger = logging.getLogger('node_manager')

class Node:
    """节点类，负责节点的连接和图像获取"""
    
    def __init__(self, node_id, url):
        self.id = node_id
        self.url = url
        self._cap = None
        self._last_check = 0
        self._available = False
        self._check_interval = 10  # 每10秒检查一次可用性
        
    def is_available(self):
        """检查节点是否可用"""
        # 如果上次检查在10秒内，直接返回缓存的结果
        current_time = time.time()
        if current_time - self._last_check < self._check_interval:
            return self._available
            
        # 重新检查可用性
        try:
            if self._cap is None:
                # 尝试打开节点
                self._cap = cv2.VideoCapture(self.url)
                
            # 尝试读取一帧
            ret = self._cap.grab()
            
            self._available = ret
            self._last_check = current_time
            
            return self._available
        except Exception as e:
            logger.error(f"检查节点 {self.id} 可用性失败: {e}")
            self._available = False
            self._last_check = current_time
            return False

class NodeManager:
    """节点管理器，负责管理多个节点"""
    
    # 节点分辨率对照表
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
        """初始化节点管理器"""
        self.config_manager = config_manager
        self.nodes = {}  # 存储节点信息
        self.node_status = {}  # 存储节点状态
        self.lock = Lock()
        
        # 从配置中加载节点设置
        self._load_nodes()
        
    def _load_nodes(self):
        """从配置中加载节点信息"""
        node_config = self.config_manager.get('nodes', {})
        
        with self.lock:
            self.nodes = node_config.copy()
            # 初始化节点状态
            for node_id in self.nodes:
                if node_id not in self.node_status:
                    self.node_status[node_id] = {
                        'status': '未知',
                        'last_capture': None,
                        'detection_count': 0,
                        'error': None
                    }
        
        logger.info(f"已加载{len(self.nodes)}个节点配置")
    
    def get_nodes(self):
        """获取所有节点信息"""
        with self.lock:
            return self.nodes.copy()
    
    def get_node_status(self):
        """获取所有节点状态"""
        with self.lock:
            return self.node_status.copy()
    
    def update_node_status(self, node_id, status, error=None):
        """更新节点状态"""
        with self.lock:
            if node_id in self.node_status:
                self.node_status[node_id]['status'] = status
                self.node_status[node_id]['error'] = error
                return True
            return False
    
    def update_detection_count(self, node_id, count):
        """更新节点检测计数"""
        with self.lock:
            if node_id in self.node_status:
                self.node_status[node_id]['detection_count'] = count
                self.node_status[node_id]['last_capture'] = datetime.datetime.now().strftime("%H:%M:%S")
                return True
            return False
    
    def check_node_connection(self, node_id):
        """检查节点连接状态"""
        if node_id not in self.nodes:
            logger.warning(f"未找到节点ID: {node_id}")
            return False
        
        node_url = self.nodes[node_id]
        try:
            response = requests.get(f"{node_url}/status", timeout=2)
            if response.status_code == 200:
                self.update_node_status(node_id, '在线')
                return True
            else:
                self.update_node_status(node_id, '错误', f"HTTP错误: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.update_node_status(node_id, '离线', str(e))
            return False
    
    def apply_node_config(self, node_id):
        """应用节点配置"""
        if node_id not in self.nodes:
            logger.warning(f"未找到节点ID: {node_id}")
            return False
        
        node_url = self.nodes[node_id]
        if not self.check_node_connection(node_id):
            logger.error(f"无法连接到节点: {node_url}")
            return False
        
        # 获取节点配置
        config = self.config_manager.get('node_config', {})
        
        # 应用配置
        for param, value in config.items():
            self._configure_node(param, value, node_url)
        
        logger.info(f"已应用节点{node_id}的配置")
        return True
    
    def _configure_node(self, parameter, value, base_url):
        """配置远程节点的参数"""
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
            logger.error(f"无法连接节点: {e}")
            return False
    
    def capture_image(self, node_id):
        """从指定节点捕获一帧图像（支持 image/jpeg 和 MJPEG 流）"""
        if node_id not in self.nodes:
            logger.warning(f"未找到节点ID: {node_id}")
            return None
        
        node_url = self.nodes[node_id]
        stream_url = f"http://{node_url}/stream"

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Connection": "close",
            "Accept": "image/jpeg,*/*"
        }
        
        try:
            with requests.Session() as session:
                logger.info(f"尝试从 {stream_url} 获取图像")
                response = session.get(stream_url, headers=headers, stream=True, timeout=15)
                
                content_type = response.headers.get("Content-Type", "")
                # 支持 image/jpeg 或 multipart/x-mixed-replace
                if "image/jpeg" in content_type:
                    # 单帧JPEG
                    image_array = np.frombuffer(response.content, dtype=np.uint8)
                    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                    response.close()
                    if image is not None:
                        logger.info(f"从 {stream_url} 成功获取图像")
                        self.update_node_status(node_id, '在线')
                        return image
                    else:
                        logger.error("无法解码图像数据")
                        self.update_node_status(node_id, '错误', "无法解码图像数据")
                        return None
                elif "multipart/x-mixed-replace" in content_type:
                    # MJPEG流，提取第一帧JPEG
                    boundary = None
                    # 提取boundary字符串
                    if "boundary=" in content_type:
                        boundary = content_type.split("boundary=")[-1]
                        if boundary.startswith('"') and boundary.endswith('"'):
                            boundary = boundary[1:-1]
                    if not boundary:
                        boundary = "--"  # 默认
                    
                    boundary_bytes = (("--" + boundary).encode() if boundary else b"--")
                    bytes_data = b""
                    for chunk in response.iter_content(chunk_size=1024):
                        bytes_data += chunk
                        a = bytes_data.find(b'\xff\xd8')
                        b = bytes_data.find(b'\xff\xd9')
                        if a != -1 and b != -1:
                            jpg = bytes_data[a:b+2]
                            response.close()
                            image = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                            if image is not None:
                                logger.info(f"从 {stream_url} 成功获取MJPEG流首帧")
                                self.update_node_status(node_id, '在线')
                                return image
                            else:
                                logger.error("无法解码MJPEG流首帧")
                                self.update_node_status(node_id, '错误', "无法解码MJPEG流首帧")
                                return None
                    logger.error("未找到MJPEG流中的有效JPEG帧")
                    self.update_node_status(node_id, '错误', "未找到MJPEG流中的有效JPEG帧")
                    response.close()
                    return None
                else:
                    logger.error(f"响应类型不支持: {content_type}")
                    self.update_node_status(node_id, '错误', f"响应类型不支持: {content_type}")
                    response.close()
                    return None
        except Exception as e:
            error_msg = f"捕获图像失败: {str(e)}"
            logger.error(error_msg)
            self.update_node_status(node_id, '离线', error_msg)
            return None
    
    def get_node_info(self, node_id):
        """获取节点信息"""
        with self.lock:
            if node_id in self.nodes:
                return {
                    'id': node_id,
                    'url': f"http://{self.nodes[node_id]}", # 添加http://前缀
                    'status': self.node_status.get(node_id, {})
                }
            return None
    
    def save_image(self, image, node_id, directory='captures'):
        """保存图像到指定目录"""
        if image is None:
            logger.warning("尝试保存空图像")
            return None
        
        # 确保目录存在
        node_dir = os.path.join(directory, f"node_{node_id}")
        os.makedirs(node_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}.jpg"
        filepath = os.path.join(node_dir, filename)
        
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
        framesize = self.config_manager.get('node_config', {}).get('framesize', 8)
        return self.FRAME_SIZES.get(framesize, (1024, 768))  # 默认返回XGA
    
    def get_environmental_data(self, node_id, headers=None, retry=1):
        """获取节点相关的环境数据"""
        node_info = self.get_node_info(node_id)
        if not node_info or 'url' not in node_info:
            raise ValueError(f"节点 {node_id} 信息不完整，无法获取环境数据")
        
        url = node_info['url'] + '/environment'
        logger.info(f"尝试获取环境数据: {url}")

        # 确保添加关闭连接的头信息
        if headers is None:
            headers = {}
        headers['Connection'] = 'close'
        
        last_exception = None
        for attempt in range(retry):
            try:
                with requests.Session() as session:
                    response = session.get(url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        json_data = response.json()
                        if isinstance(json_data, dict) and 'data' in json_data:
                            return json_data['data']
                        return json_data
                    else:
                        raise ValueError(f"获取环境数据失败: 状态码 {response.status_code}")
            except Exception as e:
                last_exception = e
                logger.warning(f"获取环境数据第{attempt+1}次尝试失败: {str(e)}")
                if attempt < retry - 1:
                    time.sleep(2)
        if last_exception:
            raise ValueError(f"获取环境数据异常(已尝试{retry}次): {str(last_exception)}")
        else:
            raise ValueError(f"获取环境数据失败，未知错误")
