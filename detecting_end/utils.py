"""
辅助工具模块，提供检测和通信所需的工具函数
"""
import os
import cv2
import json
import datetime
import logging
import requests
import numpy as np

logger = logging.getLogger('utils')

def ensure_dirs_exist(*dirs):
    """确保所有指定的目录存在"""
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)

def save_image(image, directory, filename=None):
    """保存图像到指定目录"""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    
    if filename is None:
        time_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{time_str}.jpg"
    
    filepath = os.path.join(directory, filename)
    success = cv2.imwrite(filepath, image)
    
    if not success:
        logger.error(f"保存图像失败: {filepath}")
        return None
    
    return filepath

def load_config(config_file='config.json'):
    """从JSON文件加载配置"""
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
    return None

def save_config(config, config_file='config.json'):
    """保存配置到JSON文件"""
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        return False

def fix_ws_url(url):
    """修复WebSocket URL，确保使用正确的协议"""
    url = url.rstrip('/')
    
    # 如果URL不是以ws或wss开头，修正协议
    if not (url.startswith('ws://') or url.startswith('wss://')):
        if url.startswith('https://'):
            url = 'wss://' + url[8:]
        elif url.startswith('http://'):
            url = 'ws://' + url[7:]
        else:
            url = 'wss://' + url
    
    return url

def capture_frame_from_stream(stream_url, timeout=5):
    """从HTTP流中捕获单帧图像"""
    try:
        # 使用Requests流模式读取数据
        response = requests.get(stream_url, stream=True, timeout=timeout)
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
                    return image
        
        raise Exception("未找到有效的JPEG帧")
    except Exception as e:
        logger.error(f"捕获帧失败: {e}")
        raise
