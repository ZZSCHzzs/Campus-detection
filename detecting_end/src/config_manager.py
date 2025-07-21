import os
import json
import logging

# 获取项目根目录（src的父目录）
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger('config_manager')

class ConfigManager:
    """配置管理器，负责加载、保存和管理系统配置"""
    
    DEFAULT_CONFIG = {
        'mode': 'push',  # 默认为被动接收模式，可选值: push, pull, both
        'interval': 1,   # 主动拉取模式的间隔时间（秒）
        'cameras': {1: "http://192.168.1.101:81"},  # 摄像头配置
        'save_image': True,   # 是否保存图像
        'preload_model': True,  # 是否预加载模型
        'terminal_id': 1,  # 当前终端的ID
        'server_url': "wss://smarthit.top",  # WebSocket服务器URL
        'api_url': "https://smarthit.top/api/upload/",  # API上传URL
        'camera_config': {
            'framesize': 8,  # XGA(1024x768)
            'quality': 10,
            'brightness': 1,
            'contrast': 0,
            'saturation': 0,
            'special_effect': 0,
            'hmirror': False,
            'vflip': False,
        }
    }
    
    def __init__(self, config_file='config.json'):
        """初始化配置管理器"""
        self.config_file = os.path.join(ROOT_DIR, config_file)
        self.config = self.load_config()
        
    def load_config(self):
        """从文件加载配置，如果文件不存在则使用默认配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"已从{self.config_file}加载配置")
                return self._validate_config(config)
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
        
        # 如果加载失败或文件不存在，使用默认配置
        logger.info("使用默认配置")
        return self.DEFAULT_CONFIG.copy()
    
    def _validate_config(self, config):
        """验证配置并填充缺失的值"""
        validated = self.DEFAULT_CONFIG.copy()
        
        # 更新配置
        for key, value in config.items():
            if key in validated:
                validated[key] = value
        
        return validated
    
    def save_config(self):
        """保存当前配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info(f"配置已保存到{self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        if key in self.config and self.config[key] == value:
            return False  # 值未改变
        
        self.config[key] = value
        return True
    
    def update(self, updates):
        """批量更新配置"""
        changed = False
        
        for key, value in updates.items():
            if key in self.config and self.config[key] != value:
                self.config[key] = value
                changed = True
            elif key not in self.config:
                self.config[key] = value
                changed = True
        
        return changed
    
    def get_all(self):
        """获取所有配置，返回可安全序列化的副本"""
        import copy
        # 返回深度复制以避免意外修改
        config_copy = copy.deepcopy(self.config)
        
        # 确保所有值都是可序列化的
        for key, value in config_copy.items():
            if not isinstance(value, (dict, list, str, int, float, bool, type(None))):
                config_copy[key] = str(value)
        
        return config_copy
