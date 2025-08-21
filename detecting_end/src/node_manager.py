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
        self.data_nodes = {}  # 存储数据节点信息（key 统一为 str）
        self.control_nodes = {}  # 存储控制节点信息（key 统一为 str）
        self.node_status = {}  # 存储节点状态（key 统一为 str）
        self.lock = Lock()
        
        # 从配置中加载节点设置
        self._load_nodes()
        
    # 新增：统一标准化 node_id 为字符串，避免 int/str 不一致导致的 key 匹配失败
    def _normalize_node_id(self, node_id):
        try:
            return str(node_id)
        except Exception:
            return f"{node_id}"
    
    def _load_nodes(self):
        """从配置中加载节点信息"""
        node_config = self.config_manager.get('nodes', {})
        
        with self.lock:
            # 兼容旧版本配置格式
            if isinstance(node_config, dict) and 'data_nodes' in node_config:
                # 新版结构，标准化键为字符串
                raw_data = node_config.get('data_nodes', {}) or {}
                raw_ctrl = node_config.get('control_nodes', {}) or {}
                self.data_nodes = {self._normalize_node_id(k): v for k, v in raw_data.items()}
                self.control_nodes = {self._normalize_node_id(k): v for k, v in raw_ctrl.items()}
            else:
                # 旧版结构：直接是 {id: url} 映射，当作数据节点处理，标准化键为字符串
                self.data_nodes = {self._normalize_node_id(k): v for k, v in (node_config or {}).items()}
                self.control_nodes = {}
            
            # 初始化/迁移所有节点状态（数据节点和控制节点），使用标准化后的键
            new_status = {}
            all_nodes = list(self.data_nodes.keys()) + list(self.control_nodes.keys())
            for nid in all_nodes:
                # 迁移旧 key（若存在）
                prev = self.node_status.get(nid)
                if prev is None:
                    # 可能旧的 int 键
                    prev = self.node_status.get(nid if isinstance(nid, int) else None)
                
                st = dict(prev or {})
                st.setdefault('status', '未知')
                st.setdefault('last_capture', None)
                st.setdefault('detection_count', 0)
                st.setdefault('error', None)
                st.setdefault('last_seen', None)
                # 根据归属设置默认类型
                st.setdefault('device_type', 'data' if nid in self.data_nodes else ('control' if nid in self.control_nodes else '未知'))
                st.setdefault('ip', None)
                st.setdefault('rssi', None)
                st.setdefault('uptime_ms', None)
                st.setdefault('capabilities', [])
                st.setdefault('data', None)
                new_status[nid] = st
            self.node_status = new_status
        
        logger.info(f"已加载 {len(self.data_nodes)} 个数据节点和 {len(self.control_nodes)} 个控制节点")
    
    def get_nodes(self):
        """获取所有数据节点信息（向后兼容）"""
        with self.lock:
            return self.data_nodes.copy()
    
    def get_data_nodes(self):
        """获取所有数据节点信息"""
        with self.lock:
            return self.data_nodes.copy()
    
    def get_control_nodes(self):
        """获取所有控制节点信息"""
        with self.lock:
            return self.control_nodes.copy()
    
    def get_node_status(self):
        """获取所有节点状态（详细信息，供前端 node_details 使用）"""
        with self.lock:
            return self.node_status.copy()
    
    def update_node_status(self, node_id, status, error=None):
        """更新节点状态"""
        node_id = self._normalize_node_id(node_id)
        with self.lock:
            if node_id not in self.node_status:
                # 若不存在则初始化，确保后续能被前端读到
                self.node_status[node_id] = {
                    'status': '未知',
                    'last_capture': None,
                    'detection_count': 0,
                    'error': None,
                    'last_seen': None,
                    'device_type': 'data' if node_id in self.data_nodes else ('control' if node_id in self.control_nodes else '未知'),
                    'ip': None,
                    'rssi': None,
                    'uptime_ms': None,
                    'capabilities': [],
                    'data': None,
                }
            self.node_status[node_id]['status'] = status
            self.node_status[node_id]['error'] = error
            return True
    
    def update_detection_count(self, node_id, count):
        """更新节点检测计数"""
        node_id = self._normalize_node_id(node_id)
        with self.lock:
            if node_id not in self.node_status:
                # 确保存在
                self.update_node_status(node_id, '在线')
            self.node_status[node_id]['detection_count'] = count
            self.node_status[node_id]['last_capture'] = datetime.datetime.now().strftime("%H:%M:%S")
            return True
    
    def check_node_connection(self, node_id):
        """检查节点连接状态，并同步 /status 数据"""
        node_id = self._normalize_node_id(node_id)
        # 首先在数据节点中查找
        node_url = None
        if node_id in self.data_nodes:
            node_info = self.data_nodes[node_id]
            if isinstance(node_info, dict):
                node_url = f"http://{node_info.get('ip','')}:{node_info.get('port', 80)}"
            else:
                node_url = str(node_info)  # 兼容旧格式
        elif node_id in self.control_nodes:
            node_info = self.control_nodes[node_id]
            if isinstance(node_info, dict):
                node_url = f"http://{node_info.get('ip','')}:{node_info.get('port', 80)}"
            else:
                node_url = str(node_info)  # 兼容旧格式
        
        if not node_url:
            logger.warning(f"未找到节点ID: {node_id}")
            return False
        
        try:
            response = requests.get(f"{node_url}/status", timeout=2)
            if response.status_code == 200:
                # 尝试解析标准化JSON；若解析失败，仍按在线处理
                payload = None
                try:
                    payload = response.json()
                except Exception:
                    payload = None

                with self.lock:
                    st = self.node_status.get(node_id, {})
                    # 若不存在则初始化
                    if not st:
                        st = {}
                    st['status'] = '在线'
                    st['error'] = None
                    st['last_seen'] = datetime.datetime.now().isoformat(timespec='seconds')
                    # 补充默认类型（如果尚未设置）
                    st.setdefault('device_type', 'data' if node_id in self.data_nodes else ('control' if node_id in self.control_nodes else '未知'))

                    if isinstance(payload, dict):
                        device = payload.get('device', {}) or {}
                        data = payload.get('data', None)

                        # 同步标准字段（若不存在则不覆盖）
                        if 'type' in device:
                            st['device_type'] = device.get('type') or st.get('device_type', '未知')
                        if 'ip' in device:
                            st['ip'] = device.get('ip')
                        if 'rssi' in device:
                            st['rssi'] = device.get('rssi')
                        if 'uptime_ms' in device:
                            st['uptime_ms'] = device.get('uptime_ms')
                        if 'capabilities' in device and isinstance(device.get('capabilities'), list):
                            st['capabilities'] = device.get('capabilities') or []

                        st['data'] = data
                    self.node_status[node_id] = st

                return True
            else:
                self.update_node_status(node_id, '错误', f"HTTP错误: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.update_node_status(node_id, '离线', str(e))
            return False
    
    def apply_node_config(self, node_id):
        """应用节点配置"""
        node_url = self._get_node_url(node_id)
        if not node_url:
            logger.warning(f"未找到节点ID: {node_id}")
            return False
        
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
    
    def _get_node_url(self, node_id):
        """获取节点URL"""
        node_id = self._normalize_node_id(node_id)
        # 首先在数据节点中查找
        if node_id in self.data_nodes:
            node_info = self.data_nodes[node_id]
            if isinstance(node_info, dict):
                return f"http://{node_info['ip']}:{node_info.get('port', 80)}"
            else:
                return str(node_info)  # 兼容旧格式
        elif node_id in self.control_nodes:
            node_info = self.control_nodes[node_id]
            if isinstance(node_info, dict):
                return f"http://{node_info['ip']}:{node_info.get('port', 80)}"
            else:
                return str(node_info)  # 兼容旧格式
        return None
    
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
        """从指定节点捕获一帧图像（优先使用 /capture，然后尝试 /stream）"""
        node_url = self._get_node_url(node_id)
        if not node_url:
            logger.warning(f"未找到节点ID: {node_id}")
            return None

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Connection": "close",
            "Accept": "image/jpeg,*/*"
        }
        
        # 尝试新的 /capture 路由
        capture_url = f"{node_url}/capture"
        try:
            with requests.Session() as session:
                logger.info(f"尝试从 {capture_url} 获取图像")
                response = session.get(capture_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "image/jpeg" in content_type:
                        image_array = np.frombuffer(response.content, dtype=np.uint8)
                        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                        if image is not None:
                            logger.info(f"从 {capture_url} 成功获取图像")
                            self.update_node_status(node_id, '在线')
                            return image
        except Exception as e:
            logger.info(f"从 {capture_url} 获取失败: {e}，尝试使用 /stream")
        
        # 如果 /capture 失败，尝试 /stream（兼容旧固件）
        stream_url = f"{node_url}/stream"
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
    
    def rotate_light(self, node_id, angle=90):
        """控制节点灯光旋转"""
        node_id = self._normalize_node_id(node_id)
        # 首先尝试在控制节点中查找
        node_url = None
        if node_id in self.control_nodes:
            node_info = self.control_nodes[node_id]
            if isinstance(node_info, dict):
                # 检查节点是否支持 rotate 功能
                capabilities = node_info.get('capabilities', [])
                if 'rotate' not in capabilities:
                    logger.warning(f"控制节点 {node_id} 不支持灯光旋转功能")
                    return False
                node_url = f"http://{node_info['ip']}:{node_info.get('port', 80)}"
            else:
                node_url = str(node_info)  # 兼容旧格式
        elif node_id in self.data_nodes:
            # 如果在数据节点中找到，也允许旋转（向后兼容）
            node_info = self.data_nodes[node_id]
            if isinstance(node_info, dict):
                node_url = f"http://{node_info['ip']}:{node_info.get('port', 80)}"
            else:
                node_url = str(node_info)  # 兼容旧格式
        
        if not node_url:
            logger.warning(f"未找到节点ID: {node_id}")
            return False
        
        # 发送旋转命令
        rotate_url = f"{node_url}/rotate?angle={angle}"
        try:
            response = requests.get(rotate_url, timeout=5)
            if response.status_code == 200:
                logger.info(f"节点 {node_id} 灯光旋转至 {angle} 度成功")
                return True
            else:
                logger.error(f"节点 {node_id} 灯光旋转失败，状态码: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"节点 {node_id} 灯光旋转请求失败: {e}")
            return False
    
    def get_node_info(self, node_id):
        """获取节点信息"""
        node_id = self._normalize_node_id(node_id)
        with self.lock:
            node_url = self._get_node_url(node_id)
            if node_url:
                return {
                    'id': node_id,
                    'url': node_url,
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
