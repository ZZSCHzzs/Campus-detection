import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
import threading
import asyncio

# 定义日志级别的颜色代码
COLORS = {
    'debug': '\033[36m',  # 青色
    'info': '\033[32m',   # 绿色
    'warning': '\033[33m', # 黄色
    'error': '\033[31m',  # 红色
    'detection': '\033[35m', # 紫色
    'reset': '\033[0m'    # 重置颜色
}

# 定义前端CSS颜色类
CSS_COLORS = {
    'debug': 'text-info',     # 浅蓝色
    'info': 'text-success',   # 绿色
    'warning': 'text-warning', # 黄色
    'error': 'text-danger',   # 红色
    'detection': 'text-primary' # 蓝色
}

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    def format(self, record):
        # 获取日志级别对应的颜色
        if record.levelno == logging.DEBUG:
            color = COLORS['debug']
        elif record.levelno == logging.INFO:
            # 检查是否是检测日志
            if record.getMessage().startswith('Detection'):
                color = COLORS['detection']
            else:
                color = COLORS['info']
        elif record.levelno == logging.WARNING:
            color = COLORS['warning']
        elif record.levelno == logging.ERROR:
            color = COLORS['error']
        else:
            color = COLORS['reset']
            
        # 添加颜色代码并格式化日志
        colored_message = color + super().format(record) + COLORS['reset']
        return colored_message

class LogManager:
    """日志管理器，负责记录和管理系统日志"""
    
    def __init__(self, log_dir='logs', max_memory_logs=1000, ws_client=None):
        """初始化日志管理器"""
        self.log_dir = log_dir
        self.max_memory_logs = max_memory_logs
        self.memory_logs = []
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
        
        # 创建控制台处理程序，带颜色
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)
        
        # 创建文件处理程序，不带颜色
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(self.log_dir, f'{today}.log')
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        file_handler.setLevel(logging.INFO)
        file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        
        # 添加处理程序到根日志记录器
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    
    def log(self, level, message, source=None):
        """记录日志并通过WebSocket发送（如果可用）"""
        # 创建日志条目，添加CSS颜色类
        log_entry = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'level': level,
            'message': message,
            'source': source or 'system',
            'color_class': CSS_COLORS.get(level, '')  # 添加CSS颜色类
        }
        
        # 更新内存中的日志列表
        with self.lock:
            if len(self.memory_logs) >= self.max_memory_logs:
                self.memory_logs.pop()  # 移除最老的日志
            self.memory_logs.insert(0, log_entry)  # 新日志添加到开头
        
        # 写入日志文件
        logger = logging.getLogger('detect_app')
        
        if level == 'debug':
            logger.debug(f"{message}")
        elif level == 'info':
            logger.info(f"{message}")
        elif level == 'warning':
            logger.warning(f"{message}")
        elif level == 'error':
            logger.error(f"{message}")
        elif level == 'detection':
            logger.info(f"[Detection] {message}")
        
        
        # 如果WebSocket客户端可用且已连接，通过WebSocket发送日志
        if self.ws_client and hasattr(self.ws_client, 'is_connected') and self.ws_client.is_connected():
            self._send_log_to_websocket(level, message, source)
    
    def _send_log_to_websocket(self, level, message, source=None):
        """安全地通过WebSocket发送日志，处理异步问题"""
        try:
            # 优先使用同步方法发送日志
            if hasattr(self.ws_client, 'send_log_safe'):
                self.ws_client.send_log_safe(level, message, source)
                return
                
            # 如果没有同步方法，使用异步方法
            try:
                # 获取当前事件循环或创建新的
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    # 如果当前线程没有事件循环，创建一个新的
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                if loop.is_running():
                    # 如果循环正在运行，安排协程执行
                    asyncio.run_coroutine_threadsafe(
                        self.ws_client.send_log(level, message, source), 
                        loop
                    )
                else:
                    # 创建单独的线程运行事件循环
                    def run_in_thread():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            new_loop.run_until_complete(
                                self.ws_client.send_log(level, message, source)
                            )
                        finally:
                            new_loop.close()
                    
                    threading.Thread(target=run_in_thread, daemon=True).start()
            
            except Exception as e:
                # 记录错误但不再递归调用日志方法避免无限循环
                print(f"通过WebSocket发送日志失败: {str(e)}")
        
        except Exception as e:
            # 记录错误但不再递归调用日志方法避免无限循环
            print(f"WebSocket日志发送器错误: {str(e)}")

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
    
    def debug(self, message, source=None):
        """记录调试级别日志"""
        self._log('debug', message, source)
        
        # 如果WebSocket客户端连接且不在安静模式，发送日志
        if self.ws_client and self.ws_client.is_connected() and not self.quiet_mode:
            self._send_log_to_server('debug', message, source)
    
    def get_logs(self, count=None):
        """获取最近的日志"""
        with self.lock:
            # 确保每条日志都有颜色类
            logs = self.memory_logs.copy()
            for log in logs:
                if 'color_class' not in log:
                    log['color_class'] = CSS_COLORS.get(log['level'], '')
                    
            if count is None:
                return logs
            return logs[:count]
    
    # 添加同步日志记录方法
    def info_sync(self, message, source=None):
        """同步记录信息日志，不使用asyncio"""
        self._log_sync('info', message, source)
    
    def error_sync(self, message, source=None):
        """同步记录错误日志，不使用asyncio"""
        self._log_sync('error', message, source)
    
    def warning_sync(self, message, source=None):
        """同步记录警告日志，不使用asyncio"""
        self._log_sync('warning', message, source)
    
    def debug_sync(self, message, source=None):
        """同步记录调试日志，不使用asyncio"""
        self._log_sync('debug', message, source)
    
    def _log_sync(self, level, message, source=None):
        """同步记录日志的内部方法，不使用asyncio"""
        try:
            # 创建日志条目
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': level,
                'message': message,
                'source': source or 'system'
            }
            
            # 将日志添加到内存缓存
            self.memory_logs.append(log_entry)
            if len(self.memory_logs) > self.max_memory_logs:
                self.memory_logs.pop(0)
            
            # 使用系统日志记录器记录日志
            if level == 'info':
                self.logger.info(f"[{source or 'system'}] {message}")
            elif level == 'error':
                self.logger.error(f"[{source or 'system'}] {message}")
            elif level == 'warning':
                self.logger.warning(f"[{source or 'system'}] {message}")
            elif level == 'debug':
                self.logger.debug(f"[{source or 'system'}] {message}")
            
        except Exception as e:
            # 如果记录日志失败，至少尝试使用系统日志记录这个错误
            self.logger.error(f"记录日志失败: {str(e)}, 原始消息: {message}")
