import os
import logging
import datetime
from logging.handlers import RotatingFileHandler
import threading
import asyncio

class LogManager:
    """日志管理器，负责记录和管理系统日志"""
    
    def __init__(self, log_dir='logs', max_memory_logs=1000, socketio=None, ws_client=None):
        """初始化日志管理器"""
        self.log_dir = log_dir
        self.max_memory_logs = max_memory_logs
        self.memory_logs = []
        self.socketio = socketio
        self.ws_client = ws_client
        self.lock = threading.Lock()
        
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        
        # 配置根日志记录器
        self._setup_logger()
        
        # 获取模块级日志记录器
        self.logger = logging.getLogger('log_manager')
        self.logger.info("日志管理器初始化完成")
    
    def _setup_logger(self):
        """设置日志记录器"""
        # 获取根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # 清除现有的处理程序
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 创建控制台处理程序
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)
        
        # 创建文件处理程序
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(self.log_dir, f'{today}.log')
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        file_handler.setLevel(logging.INFO)
        file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        
        # 添加处理程序到根日志记录器
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    
    def log(self, level, message, source=None):
        """记录日志并同步到内存、WebSocket和远程服务器"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 创建日志条目
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'source': source or 'system'
        }
        
        # 更新内存中的日志列表
        with self.lock:
            if len(self.memory_logs) >= self.max_memory_logs:
                self.memory_logs.pop()  # 移除最老的日志
            self.memory_logs.insert(0, log_entry)  # 新日志添加到开头
        
        # 写入日志文件
        logger = logging.getLogger('detect_app')
        if level == 'info':
            logger.info(f"{source or 'System'}: {message}")
        elif level == 'warning':
            logger.warning(f"{source or 'System'}: {message}")
        elif level == 'error':
            logger.error(f"{source or 'System'}: {message}")
        elif level == 'detection':
            logger.info(f"Detection - {source or 'Unknown Camera'}: {message}")
        
        # 通过SocketIO发送日志
        if self.socketio:
            self.socketio.emit('new_log', log_entry)
        
        # 通过WebSocket发送日志到远程服务器
        if self.ws_client and self.ws_client.connected:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # 如果没有事件循环，创建一个新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            asyncio.run_coroutine_threadsafe(
                self.ws_client.send_log(level, message, source),
                loop
            )
    
    def info(self, message, source=None):
        """记录信息级别的日志"""
        self.log('info', message, source)
    
    def warning(self, message, source=None):
        """记录警告级别的日志"""
        self.log('warning', message, source)
    
    def error(self, message, source=None):
        """记录错误级别的日志"""
        self.log('error', message, source)
    
    def detection(self, message, source=None):
        """记录检测事件"""
        self.log('detection', message, source)
    
    def get_logs(self, count=None):
        """获取最近的日志"""
        with self.lock:
            if count is None:
                return self.memory_logs.copy()
            return self.memory_logs[:count]
