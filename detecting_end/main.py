import cv2
import time
import os
import datetime
import requests
import numpy as np
import detect.run as detect
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from threading import Thread, Lock, Event
import json
import psutil
import asyncio
from websocket_client import TerminalWebSocketClient
import logging
from logging.handlers import RotatingFileHandler

# 创建Flask应用
app = Flask(__name__, 
            static_folder='static',
            template_folder='static')  # 修改模板目录为static目录
# 添加CORS支持，允许前端跨域访问
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局配置变量
MODE = "push"  # 默认为被动接收模式
PULL_MODE_INTERVAL = 1  # 主动拉取模式的间隔时间（秒）
PRE_LOAD_MODEL = True  # 是否预加载模型
LOADED_MODEL = None  # 全局变量存储预加载的模型
SAVE_IMAGE = True   # 是否保存图像
CAMERAS = {1: "http://192.168.1.101:81"}
TERMINAL_ID = 1  # 当前终端的ID
SERVER_URL = "wss://smarthit.top"  # 服务器基础URL（用于WebSocket）
API_URL = "https://smarthit.top/api/upload/"  # API上传URL

# 存储系统状态的全局变量
system_status = {
    "cameras": {},
    "detection_count": {},
    "last_update": {},
    "cpu_usage": 0,
    "memory_usage": 0,
    "model_loaded": False,
    "mode": MODE,
    "push_running": False,  # 被动模式状态
    "pull_running": False,  # 主动模式状态
    "started_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}
status_lock = Lock()  # 用于线程安全地更新状态

# 存储和加载配置
def save_config_to_file(config):
    """保存配置到文件"""
    try:
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"保存配置失败: {e}")
        return False

def load_config_from_file():
    """从文件加载配置"""
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载配置失败: {e}")
    return None

# 检测线程 - 支持两种模式同时运行
class DetectionManager:
    def __init__(self):
        self.pull_thread = None
        self.stop_pull_event = Event()
        self.interval = PULL_MODE_INTERVAL
        self.pull_running = False
        self.push_running = False
        self.error_count = 0
        self.max_errors = 5
    
    def start_push(self):
        """启动被动接收模式"""
        if self.push_running:
            return False
        
        self.push_running = True
        
        with status_lock:
            system_status["push_running"] = True
        
        socketio.emit('system_message', {'message': '已启动被动接收模式'})
        socketio.emit('system_update', {'push_running': True})
        return True
    
    def stop_push(self):
        """停止被动接收模式"""
        if not self.push_running:
            return False
        
        self.push_running = False
        
        with status_lock:
            system_status["push_running"] = False
        
        socketio.emit('system_message', {'message': '已停止被动接收模式'})
        socketio.emit('system_update', {'push_running': False})
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
        print(f"启动了Pull模式线程: {self.pull_thread.name}")
        
        self.pull_running = True
        
        with status_lock:
            system_status["pull_running"] = True
        
        socketio.emit('system_message', {'message': '已启动主动拉取模式'})
        socketio.emit('system_update', {'pull_running': True})
        return True
    
    def stop_pull(self):
        """停止主动拉取模式"""
        if not self.pull_running:
            return False
        
        print("正在停止主动拉取模式...")
        self.stop_pull_event.set()
        
        if self.pull_thread and self.pull_thread.is_alive():
            print(f"等待线程{self.pull_thread.name}结束...")
            self.pull_thread.join(timeout=3.0)
            print(f"线程状态: {'活跃' if self.pull_thread.is_alive() else '已停止'}")
        
        self.pull_running = False
        
        with status_lock:
            system_status["pull_running"] = False
        
        socketio.emit('system_message', {'message': '已停止主动拉取模式'})
        socketio.emit('system_update', {'pull_running': False})
        return True
    
    # 添加模式切换方法
    def change_mode(self, new_mode):
        """根据模式启动或停止相应服务"""
        global MODE
        if new_mode == MODE:
            return False
            
        print(f"切换模式: {MODE} -> {new_mode}")
        MODE = new_mode
        
        # 根据新模式决定是否启动或停止服务
        if new_mode == "push":
            # 如果切换到被动模式，确保被动模式开启，可选择停止主动拉取
            self.start_push()
        elif new_mode == "pull":
            # 如果切换到主动模式，确保主动模式开启
            self.start_pull()
        elif new_mode == "both":
            # 如果是双模式，确保两种模式都开启
            self.start_push()
            self.start_pull()
        
        return True
    
    def update_interval(self, new_interval):
        """更新拉取间隔"""
        if new_interval == self.interval:
            return False
        
        self.interval = new_interval
        socketio.emit('system_message', {'message': f'拉取间隔已更新为{new_interval}秒'})
        return True
    
    def update_cameras(self, new_cameras):
        """更新摄像头配置"""
        global CAMERAS
        CAMERAS = new_cameras
        
        # 重新初始化摄像头状态
        with status_lock:
            system_status["cameras"] = {}
            system_status["detection_count"] = {}
            system_status["last_update"] = {}
            
            for camera_id in CAMERAS:
                system_status["cameras"][camera_id] = "未知"
                system_status["detection_count"][camera_id] = 0
                system_status["last_update"][camera_id] = "从未"
        
        socketio.emit('system_message', {'message': '摄像头配置已更新'})
        return True
    
    def _pull_mode_handler(self):
        """主动拉取模式处理函数"""
        print("运行在主动拉取模式...")
        
        # 初始化摄像头状态
        with status_lock:
            for camera_id in CAMERAS:
                if camera_id not in system_status["cameras"]:
                    system_status["cameras"][camera_id] = "未知"
                    system_status["detection_count"][camera_id] = 0
                    system_status["last_update"][camera_id] = "从未"
        
        try:  # 添加外层异常处理
            while not self.stop_pull_event.is_set():
                try:
                    images_to_process = []
                    
                    # 更新系统资源使用情况
                    with status_lock:
                        system_status["cpu_usage"] = psutil.cpu_percent()
                        system_status["memory_usage"] = psutil.virtual_memory().percent
                    socketio.emit('system_resources', {
                        'cpu': system_status["cpu_usage"], 
                        'memory': system_status["memory_usage"]
                    })
                    
                    # 收集多个摄像头的图像
                    for camera_id, camera_url in CAMERAS.items():
                        try:
                            # 捕获图像
                            image = capture_image_from_camera(camera_url)
                            with status_lock:
                                system_status["cameras"][camera_id] = "在线"
                            socketio.emit('camera_status', {'id': camera_id, 'status': '在线'})
                            images_to_process.append((image, camera_id))
                        except Exception as e:
                            print(f"摄像头 {camera_id} 捕获失败: {e}")
                            with status_lock:
                                system_status["cameras"][camera_id] = "离线"
                            socketio.emit('camera_status', {'id': camera_id, 'status': '离线', 'error': str(e)})
                    
                    if images_to_process:
                        try:
                            # 批量分析图像
                            results = analyze_images(images_to_process)
                            
                            # 上传结果
                            for camera_id, detected_count in results.items():
                                print(f"摄像头 {camera_id} 检测到人数: {detected_count}")
                                upload_result(camera_id, detected_count)
                        except Exception as e:
                            print(f"批量处理失败: {e}")
                            socketio.emit('system_error', {'message': f'批量处理失败: {str(e)}'})
                
                except Exception as e:
                    self.error_count += 1
                    print(f"拉取模式循环异常 ({self.error_count}/{self.max_errors}): {e}")
                    socketio.emit('system_error', {'message': f'拉取模式异常: {str(e)}'})
                    
                    # 如果错误次数过多，退出循环
                    if self.error_count >= self.max_errors:
                        print(f"错误次数过多，停止检测线程")
                        break
                    
                    # 短暂延迟后继续尝试
                    time.sleep(2)
                
                # 使用事件对象的wait方法，允许提前中断
                if self.stop_pull_event.wait(self.interval):
                    break
        
        except Exception as e:
            print(f"严重错误，拉取模式线程退出: {e}")
        
        finally:
            # 确保线程退出时更新状态
            if self.pull_running:
                print("拉取模式线程异常退出，更新状态")
                self.pull_running = False
                with status_lock:
                    system_status["pull_running"] = False
                socketio.emit('system_update', {'pull_running': False})
                socketio.emit('system_error', {'message': '拉取模式异常退出，请检查日志'})
            
            print("主动拉取模式已停止")

# 全局检测线程实例
detection_manager = DetectionManager()

# 配置日志
logger = logging.getLogger('detect_app')
detection_logs = []
MAX_LOGS = 1000  # 内存中保存的最大日志数

# 预加载模型
def initialize_model():
    global LOADED_MODEL
    print("正在预加载YOLO模型...")
    LOADED_MODEL = detect.load_model()
    with status_lock:
        system_status["model_loaded"] = True
    print("模型加载完成！")
    socketio.emit('system_update', {'model_loaded': True})

# 从 WiFi 摄像头捕获图像
def capture_image_from_camera(camera_url):
    print(f"捕获图像: {camera_url}")
    stream_url = camera_url + "/stream"

    try:
        # 使用 Requests 流模式读取数据
        response = requests.get(stream_url, stream=True, timeout=5)
        if response.status_code != 200:
            raise Exception(f"HTTP 错误码: {response.status_code}")

        bytes_data = bytes()
        for chunk in response.iter_content(chunk_size=1024):
            bytes_data += chunk
            # 查找 JPEG 起始和结束标记
            a = bytes_data.find(b'\xff\xd8')
            b = bytes_data.find(b'\xff\xd9')
            if a != -1 and b != -1:
                jpg = bytes_data[a:b + 2]
                bytes_data = bytes_data[b + 2:]
                # 转换为 OpenCV 图像格式
                image = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if image is not None:
                    return image
        raise Exception("未找到有效的 JPEG 帧")
    except Exception as e:
        raise Exception(f"流捕获失败: {str(e)}")

# 调用 detect.detect() 分析人数
def analyze_image(image, node_id):
    # 保存图像
    time_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    os.makedirs(f"temp/node{node_id}", exist_ok=True)
    temp_path = f"temp/node{node_id}/{time_str}.jpg"
    cv2.imwrite(temp_path, image)
    # 使用预加载模型
    count = detect.detect(temp_path, model=LOADED_MODEL)
    return count

def analyze_images(images_data):
    """
    批量处理多个图像，使用预加载模型
    
    images_data: 列表，每个元素是 (image, node_id) 的元组
    返回: 字典，键为 node_id，值为检测结果
    """
    temp_paths = []
    path_to_camera = {}
    
    # 保存所有图像到文件
    for image, node_id in images_data:
        time_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        os.makedirs(f"temp/node{node_id}", exist_ok=True)
        temp_path = f"temp/node{node_id}/{time_str}.jpg"
        cv2.imwrite(temp_path, image)
        temp_paths.append(temp_path)
        path_to_camera[temp_path] = node_id
    
    # 批量处理图像，传入预加载模型
    results = detect.detect_series(temp_paths, model=LOADED_MODEL)
    
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
    if ws_client and ws_client.connected:
        asyncio.run_coroutine_threadsafe(
            ws_client.send_nodes_data(nodes_data),
            asyncio.get_event_loop()
        )
    
    return camera_results


# 日志记录函数
def log_event(level, message, source=None):
    """记录事件到日志文件和内存"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 添加到内存中的日志列表
    log_entry = {
        'timestamp': timestamp,
        'level': level,
        'message': message,
        'source': source or 'system'
    }
    
    # 限制内存中的日志数量
    if len(detection_logs) >= MAX_LOGS:
        detection_logs.pop()  # 移除最老的日志
    
    detection_logs.insert(0, log_entry)  # 新日志添加到开头
    
    # 写入日志文件
    if level == 'info':
        logger.info(f"{source or 'System'}: {message}")
    elif level == 'warning':
        logger.warning(f"{source or 'System'}: {message}")
    elif level == 'error':
        logger.error(f"{source or 'System'}: {message}")
    elif level == 'detection':
        logger.info(f"Detection - {source or 'Unknown Camera'}: {message}")
    
    # 通过WebSocket发送新日志
    socketio.emit('new_log', log_entry)
    
    # 同时发送到Django WebSocket服务器
    if ws_client and ws_client.connected:
        asyncio.run_coroutine_threadsafe(
            ws_client.send_log(level, message, source),
            asyncio.get_event_loop()
        )

# 统计数据
detection_stats = {
    'today_count': 0,
    'total_count': 0,
    'max_count': 0,
    'avg_count': 0,
    'detection_sum': 0,
    'last_day_reset': datetime.datetime.now().strftime("%Y-%m-%d")
}

# 重置日统计数据
def reset_daily_stats():
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    if detection_stats['last_day_reset'] != current_date:
        detection_stats['today_count'] = 0
        detection_stats['last_day_reset'] = current_date
        log_event('info', f'重置每日统计数据: {current_date}')

# 更新检测统计
def update_detection_stats(count):
    # 检查是否需要重置每日统计
    reset_daily_stats()
    
    # 更新统计数据
    detection_stats['today_count'] += 1
    detection_stats['total_count'] += 1
    detection_stats['max_count'] = max(detection_stats['max_count'], count)
    detection_stats['detection_sum'] += count
    detection_stats['avg_count'] = detection_stats['detection_sum'] / detection_stats['total_count'] if detection_stats['total_count'] > 0 else 0
    
    # 发送统计更新
    socketio.emit('stats_update', detection_stats)

# 上传检测结果到服务器
def upload_result(camera_id, detected_count):
    url = API_URL  # 使用API_URL而不是硬编码
    data = {
        "id": camera_id,
        "detected_count": detected_count,
        "timestamp": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")  # 标准化时间格式
    }
    try:
        response = requests.post(url, json=data, timeout=5)
        if response.status_code != 201:
            log_event('warning', f"上传警告: 状态码 {response.status_code}, 响应: {response.text}", f"摄像头 {camera_id}")
            print(f"上传警告: 状态码 {response.status_code}, 响应: {response.text}")
            with status_lock:
                system_status["cameras"][camera_id] = "错误"
            socketio.emit('camera_status', {'id': camera_id, 'status': '错误', 'error': response.text})
        else:
            with status_lock:
                system_status["cameras"][camera_id] = "在线"
                system_status["detection_count"][camera_id] = detected_count
                system_status["last_update"][camera_id] = datetime.datetime.now().strftime("%H:%M:%S")
            
            # 记录检测事件
            log_event('detection', f"检测到人数: {detected_count}", f"摄像头 {camera_id}")
            
            # 更新统计数据
            update_detection_stats(detected_count)
            
            socketio.emit('detection_result', {
                'camera_id': camera_id, 
                'count': detected_count,
                'time': system_status["last_update"][camera_id]
            })
        return response.json()
    except Exception as e:
        error_msg = f"上传结果失败: {e}"
        log_event('error', error_msg, f"摄像头 {camera_id}")
        print(error_msg)
        with status_lock:
            system_status["cameras"][camera_id] = "离线"
        socketio.emit('camera_status', {'id': camera_id, 'status': '离线', 'error': str(e)})
        return None

# 构建实际的WebSocket URL
def get_ws_url():
    """获取正确格式的WebSocket URL"""
    base_url = SERVER_URL.rstrip('/')
    
    # 如果URL不是以ws或wss开头，修正协议
    if not (base_url.startswith('ws://') or base_url.startswith('wss://')):
        if base_url.startswith('https://'):
            base_url = 'wss://' + base_url[8:]
        elif base_url.startswith('http://'):
            base_url = 'ws://' + base_url[7:]
        else:
            base_url = 'wss://' + base_url
    
    # 构建完整WebSocket URL - 使用单数形式的路径
    return f"{base_url}/ws/terminal/{TERMINAL_ID}/"

# WebSocket命令处理函数
async def handle_ws_command(command_data):
    """处理从服务器接收到的WebSocket命令"""
    command_type = command_data.get('type')
    payload = command_data.get('payload')
    
    print(f"接收到WebSocket命令: {command_type}, 数据: {payload}")
    
    if command_type == "set_mode":
        new_mode = payload.get("mode")
        if new_mode in ["push", "pull", "both"]:
            detection_manager.change_mode(new_mode)
            socketio.emit('system_message', {'message': f'模式已切换为: {new_mode}'})
        else:
            socketio.emit('system_error', {'message': '无效的模式'})
    
    elif command_type == "set_interval":
        new_interval = payload.get("interval")
        if isinstance(new_interval, (int, float)) and new_interval > 0:
            detection_manager.update_interval(new_interval)
            socketio.emit('system_message', {'message': f'拉取间隔已更新为: {new_interval}秒'})
        else:
            socketio.emit('system_error', {'message': '无效的间隔值'})
    
    elif command_type == "update_cameras":
        new_cameras = payload.get("cameras")
        if isinstance(new_cameras, dict):
            detection_manager.update_cameras(new_cameras)
            socketio.emit('system_message', {'message': '摄像头配置已更新'})
        else:
            socketio.emit('system_error', {'message': '无效的摄像头配置'})
    
    elif command_type == "restart":
        socketio.emit('system_message', {'message': '正在重启服务...'})
        time.sleep(2)  # 模拟重启延迟
        os.execv(sys.executable, ['python'] + sys.argv)
    
    else:
        socketio.emit('system_error', {'message': '未知的命令类型'})

# 全局WebSocket客户端实例
ws_client = None

# 初始化WebSocket客户端
def init_websocket_client():
    global ws_client, TERMINAL_ID, SERVER_URL, API_URL
    
    # 从配置文件加载终端ID和服务器URL
    config = load_config_from_file()
    if config:
        TERMINAL_ID = config.get('terminal_id', TERMINAL_ID)
        SERVER_URL = config.get('server_url', SERVER_URL)
        API_URL = config.get('api_url', API_URL)
    
    # 检查并确保WebSocket URL正确性
    correct_ws_url = get_ws_url()
    log_event('info', f'初始化WebSocket客户端，终端ID: {TERMINAL_ID}，服务器URL: {correct_ws_url}', 'system')
    
    # 创建并启动WebSocket客户端
    from websocket_client import TerminalWebSocketClient
    ws_client = TerminalWebSocketClient(correct_ws_url, TERMINAL_ID, on_command=handle_ws_command)
    
    # 启动WebSocket连接
    def start_ws_client():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_client():
            try:
                connected = await ws_client.start()
                if connected:
                    log_event('info', f'WebSocket客户端已连接到服务器', 'system')
                    socketio.emit('system_message', {'message': '已连接到远程服务器'})
                    socketio.emit('system_update', {'ws_connected': True})
                    
                    # 发送初始状态，包含终端ID
                    with status_lock:
                        status_copy = dict(system_status)
                        status_copy['terminal_id'] = TERMINAL_ID
                    await ws_client.send_status(status_copy)
                else:
                    log_event('error', '无法连接到WebSocket服务器', 'system')
                    socketio.emit('system_error', {'message': '无法连接到远程服务器'})
                    socketio.emit('system_update', {'ws_connected': False})
            except Exception as e:
                log_event('error', f'WebSocket客户端启动错误: {str(e)}', 'system')
                socketio.emit('system_error', {'message': f'WebSocket连接错误: {str(e)}'})
                socketio.emit('system_update', {'ws_connected': False})
        
        loop.run_until_complete(run_client())
        loop.run_forever()
    
    # 在新线程中启动WebSocket客户端
    ws_thread = Thread(target=start_ws_client, daemon=True)
    ws_thread.start()
    
    return ws_thread

# API路由 
@app.route('/api/info')
def get_info():
    """返回终端基本信息，供Vue前端使用"""
    return jsonify({
        "id": TERMINAL_ID,
        "name": f"终端 #{TERMINAL_ID}",
        "server_url": SERVER_URL,
        "version": "1.0.0"
    })

# 获取系统状态API
@app.route('/api/status')
def get_status():
    with status_lock:
        return jsonify(system_status)

# 获取日志API
@app.route('/api/logs')
def get_logs():
    return jsonify(detection_logs)

# 获取日志统计数据
@app.route('/api/logs/stats')
def get_log_stats():
    reset_daily_stats()
    return jsonify(detection_stats)

# 配置API（供Vue前端使用）
@app.route('/api/config', methods=['GET', 'POST'])
def config_endpoint():
    """获取或更新终端配置"""
    if request.method == 'GET':
        config_data = {
            'mode': MODE,
            'interval': PULL_MODE_INTERVAL,
            'cameras': CAMERAS,
            'save_image': SAVE_IMAGE,
            'preload_model': PRE_LOAD_MODEL,
            'terminal_id': TERMINAL_ID,
            'server_url': SERVER_URL,
            'api_url': API_URL
        }
        return jsonify(config_data)
    elif request.method == 'POST':
        global MODE, PULL_MODE_INTERVAL, CAMERAS, SAVE_IMAGE, PRE_LOAD_MODEL, SERVER_URL, API_URL
        
        data = request.json
        config_changed = False
        restart_required = False
        
        try:
            # 更新模式
            new_mode = data.get('mode')
            if new_mode in ["push", "pull", "both"] and new_mode != MODE:
                MODE = new_mode
                config_changed = True
            
            # 更新拉取间隔
            new_interval = data.get('interval')
            if isinstance(new_interval, (int, float)) and new_interval > 0 and new_interval != PULL_MODE_INTERVAL:
                PULL_MODE_INTERVAL = new_interval
                config_changed = True
            
            # 更新摄像头配置
            new_cameras = data.get('cameras')
            if isinstance(new_cameras, dict) and new_cameras != CAMERAS:
                CAMERAS = new_cameras
                config_changed = True
            
            # 更新其他设置
            SAVE_IMAGE = data.get('save_image', SAVE_IMAGE)
            PRE_LOAD_MODEL = data.get('preload_model', PRE_LOAD_MODEL)
            SERVER_URL = data.get('server_url', SERVER_URL)
            API_URL = data.get('api_url', API_URL)
            
            # 如果配置有变化，保存到文件
            if config_changed:
                config_data = {
                    'mode': MODE,
                    'interval': PULL_MODE_INTERVAL,
                    'cameras': CAMERAS,
                    'save_image': SAVE_IMAGE,
                    'preload_model': PRE_LOAD_MODEL,
                    'terminal_id': TERMINAL_ID,
                    'server_url': SERVER_URL,
                    'api_url': API_URL
                }
                save_config_to_file(config_data)
            
            response_data = {'status': 'success', 'config_changed': config_changed}
            if restart_required:
                response_data['restart_required'] = True
            
            return jsonify(response_data)
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 400

# 控制API
@app.route('/api/control', methods=['POST'])
def control_detection():
    """控制检测服务的启动和停止"""
    action = request.json.get('action')
    
    if action == "start_push":
        detection_manager.start_push()
        return jsonify({"status": "success", "message": "已启动被动接收模式"})
    elif action == "stop_push":
        detection_manager.stop_push()
        return jsonify({"status": "success", "message": "已停止被动接收模式"})
    elif action == "start_pull":
        detection_manager.start_pull()
        return jsonify({"status": "success", "message": "已启动主动拉取模式"})
    elif action == "stop_pull":
        detection_manager.stop_pull()
        return jsonify({"status": "success", "message": "已停止主动拉取模式"})
    else:
        return jsonify({"status": "error", "message": "无效的操作"}), 400

# 接收图像API
@app.route('/api/push_frame/<int:camera_id>', methods=['POST'])
def receive_frame(camera_id):
    """接收并处理上传的图像"""
    if camera_id not in CAMERAS:
        return jsonify({"status": "error", "message": "无效的摄像头ID"}), 400
    
    try:
        # 从请求中获取图像数据
        image_file = request.files.get('image')
        if not image_file:
            return jsonify({"status": "error", "message": "未接收到图像数据"}), 400
        
        # 将图像数据保存到临时文件
        image_data = image_file.read()
        temp_path = f"temp/node{camera_id}/{"".join(str(datetime.datetime.now().timetuple()[:6]))}.jpg"
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, 'wb') as f:
            f.write(image_data)
        
        # 使用预加载模型分析图像
        count = detect.detect(temp_path, model=LOADED_MODEL)
        
        # 上传结果
        upload_result(camera_id, count)
        
        return jsonify({"status": "success", "message": "图像处理完成", "detected_count": count})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Vue单页应用入口
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_vue_app(path):
    """提供Vue单页应用入口点"""
    if path and (os.path.exists(os.path.join(app.static_folder, path))):
        return send_from_directory(app.static_folder, path)
    else:
        return send_file(os.path.join(app.static_folder, 'index.html'))

# 主程序入口点
if __name__ == "__main__":
    # 加载配置
    config = load_config_from_file()
    if config:
        MODE = config.get('mode', MODE)
        PULL_MODE_INTERVAL = config.get('interval', PULL_MODE_INTERVAL)
        CAMERAS = config.get('cameras', CAMERAS)
        SAVE_IMAGE = config.get('save_image', SAVE_IMAGE)
        PRE_LOAD_MODEL = config.get('preload_model', PRE_LOAD_MODEL)
        TERMINAL_ID = config.get('terminal_id', TERMINAL_ID)
        SERVER_URL = config.get('server_url', SERVER_URL)
        API_URL = config.get('api_url', API_URL)
    
    # 创建必要的目录
    os.makedirs('temp', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # 初始化摄像头状态
    with status_lock:
        for camera_id in CAMERAS:
            if camera_id not in system_status["cameras"]:
                system_status["cameras"][camera_id] = "未知"
                system_status["detection_count"][camera_id] = 0
                system_status["last_update"][camera_id] = "从未"
    
    log_event('info', f'系统启动，终端ID: {TERMINAL_ID}，模式: {MODE}', 'system')
    
    # 预加载模型（如果配置为True）
    if PRE_LOAD_MODEL:
        model_thread = Thread(target=initialize_model)
        model_thread.daemon = True
        model_thread.start()
    
    # 初始化WebSocket客户端
    ws_thread = init_websocket_client()
    
    # 根据配置的模式启动相应的检测服务
    if MODE == "push" or MODE == "both":
        detection_manager.start_push()
    
    if MODE == "pull" or MODE == "both":
        detection_manager.start_pull()
    
    # 使用socketio.run启动Flask应用
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)