import cv2
import time
import os
import datetime
import requests
import numpy as np
import detect.run as detect
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO, emit
from threading import Thread, Lock, Event
from camera import apply_camera_config
import json
import psutil
import asyncio
from websocket_client import TerminalWebSocketClient
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
socketio = SocketIO(app, cors_allowed_origins="*")

# 运行模式
MODE = "push"  # 默认为被动接收模式
PULL_MODE_INTERVAL = 1  # 主动拉取模式的间隔时间（秒）
PRE_LOAD_MODEL = True  # 是否预加载模型
LOADED_MODEL = None  # 全局变量存储预加载的模型
SAVE_IMAGE = True   # 是否保存图像
INITIALIZE_CAMERA = False  # 是否初始化摄像头
CAMERAS = {
    1: "http://192.168.1.101:81"
}
STREAM_URL = "/stream"

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

# 预加载模型
def initialize_model():
    global LOADED_MODEL
    print("正在预加载YOLO模型...")
    LOADED_MODEL = detect.load_model()
    with status_lock:
        system_status["model_loaded"] = True
    print("模型加载完成！")
    socketio.emit('system_update', {'model_loaded': True})

def initialize_cameras():
    for camera_id, camera_url in CAMERAS.items():
        print(f"初始化摄像头 {camera_id}:{camera_url} ...")
        if not apply_camera_config(camera_url):
            print(f"摄像头 {camera_id} 初始化失败！")
            continue
        print(f"摄像头 {camera_id} 初始化完成！")

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


# 配置日志
LOG_FILE = 'system.log'
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)

# 配置根日志记录器
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        RotatingFileHandler(
            f'logs/{LOG_FILE}',
            maxBytes=LOG_MAX_SIZE,
            backupCount=LOG_BACKUP_COUNT
        ),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)

# 获取应用日志记录器
logger = logging.getLogger('detect_app')

# 存储检测日志
detection_logs = []
MAX_LOGS = 1000  # 内存中保存的最大日志数

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
    url = "https://smarthit.top/api/upload/"
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

# 主动拉取模式处理
def pull_mode_handler():
    interval = PULL_MODE_INTERVAL
    print("运行在主动拉取模式...")
    
    # 初始化摄像头状态
    for camera_id in CAMERAS:
        with status_lock:
            system_status["cameras"][camera_id] = "未知"
            system_status["detection_count"][camera_id] = 0
            system_status["last_update"][camera_id] = "从未"
    
    while True:
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

        time.sleep(interval)


# Flask接收端点
@app.route('/api/push_frame/<int:camera_id>', methods=['POST'])  # 指定camera_id为整数
def receive_frame(camera_id):
    # 检查被动模式是否开启
    if not detection_manager.push_running:
        print("被动接收模式未启用，拒绝请求")
        return jsonify({"error": "被动接收模式未启用"}), 403
        
    if camera_id not in CAMERAS:
        print(f"无效的摄像头ID: {camera_id}")
        return jsonify({"error": "无效的摄像头ID"}), 404

    if 'file' not in request.files:
        print("没有文件上传")
        return jsonify({"error": "没有文件上传"}), 400

    file = request.files['file']
    try:
        # 读取图像
        img_data = file.read()
        if len(img_data) == 0:
            print("空文件内容")
            return jsonify({"error": "空文件内容"}), 415

        image = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            print("无效的图片格式")
            return jsonify({"error": "无效的图片格式"}), 415

        # 分析图像
        detected_count = analyze_image(image, camera_id)
        print(f"摄像头 {camera_id} 检测到人数: {detected_count}")

        # 上传结果
        result = upload_result(camera_id, detected_count)
        if result is None:
            return jsonify({"error": "云端上传失败"}), 504
        print("\033[92m" + f"摄像头 {camera_id} 处理成功" + "\033[0m")
        return jsonify({
            "status": "success",
        }), 201

    except Exception as e:
        print(f"处理异常: {str(e)}")
        return jsonify({"error": str(e)}), 500


# UI路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/config')
def config_page():
    return render_template('config.html')

# 日志页面
@app.route('/logs')
def logs_page():
    return render_template('logs.html')

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
    # 检查是否需要重置每日统计
    reset_daily_stats()
    return jsonify(detection_stats)

# 存储和加载配置
def save_config_to_file(config):
    try:
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"保存配置失败: {e}")
        return False

def load_config_from_file():
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载配置失败: {e}")
    return None

# 修改配置API
@app.route('/api/config', methods=['POST'])
def update_config():
    global MODE, PULL_MODE_INTERVAL, CAMERAS, SAVE_IMAGE, PRE_LOAD_MODEL
    
    data = request.json
    config_changed = False
    restart_required = False
    
    try:
        # 保存原始配置用于恢复
        original_config = {
            'mode': MODE,
            'interval': PULL_MODE_INTERVAL,
            'cameras': CAMERAS,
            'save_image': SAVE_IMAGE,
            'preload_model': PRE_LOAD_MODEL
        }
        
        # 更新配置
        if 'mode' in data and data['mode'] != MODE:
            # 使用detection_manager来处理模式切换
            if detection_manager.change_mode(data['mode']):
                with status_lock:
                    system_status['mode'] = MODE
                config_changed = True
        
        if 'interval' in data and float(data['interval']) != PULL_MODE_INTERVAL:
            PULL_MODE_INTERVAL = float(data['interval'])
            detection_manager.update_interval(PULL_MODE_INTERVAL)
            config_changed = True
        
        if 'cameras' in data and data['cameras'] != CAMERAS:
            CAMERAS = data['cameras']
            detection_manager.update_cameras(CAMERAS)
            config_changed = True
        
        if 'save_image' in data and data['save_image'] != SAVE_IMAGE:
            SAVE_IMAGE = data['save_image']
            config_changed = True
        
        if 'preload_model' in data and data['preload_model'] != PRE_LOAD_MODEL:
            PRE_LOAD_MODEL = data['preload_model']
            restart_required = True
            config_changed = True
        
        # 如果配置有变化，保存到文件
        if config_changed:
            config_data = {
                'mode': MODE,
                'interval': PULL_MODE_INTERVAL,
                'cameras': CAMERAS,
                'save_image': SAVE_IMAGE,
                'preload_model': PRE_LOAD_MODEL,
                'server_url': data.get('server_url', 'https://smarthit.top/api/upload/')
            }
            save_config_to_file(config_data)
        
        response_data = {'status': 'success', 'config_changed': config_changed}
        if restart_required:
            response_data['restart_required'] = True
            socketio.emit('config_updated', {'success': True, 'restart_required': True})
        else:
            socketio.emit('config_updated', {'success': True})
            
        return jsonify(response_data)
    
    except Exception as e:
        print(f"配置更新失败: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

# 新增控制API
@app.route('/api/control', methods=['POST'])
def control_detection():
    action = request.json.get('action')
    mode = request.json.get('mode', 'both')  # 默认操作两种模式
    
    if action == 'start':
        if mode == 'push' or mode == 'both':
            detection_manager.start_push()
        
        if mode == 'pull' or mode == 'both':
            detection_manager.start_pull()
        
        return jsonify({'status': 'success', 'message': f'已启动{mode}模式'})
    
    elif action == 'stop':
        if mode == 'push' or mode == 'both':
            detection_manager.stop_push()
        
        if mode == 'pull' or mode == 'both':
            detection_manager.stop_pull()
        
        return jsonify({'status': 'success', 'message': f'已停止{mode}模式'})
    
    elif action == 'restart':
        if mode == 'push' or mode == 'both':
            detection_manager.stop_push()
            time.sleep(0.5)
            detection_manager.start_push()
        
        if mode == 'pull' or mode == 'both':
            detection_manager.stop_pull()
            time.sleep(0.5)
            detection_manager.start_pull()
        
        return jsonify({'status': 'success', 'message': f'已重启{mode}模式'})
    
    else:
        return jsonify({'status': 'error', 'message': '无效的操作'}), 400

# WebSocket事件 - 控制事件
@socketio.on('control_detection')
def handle_control_detection(data):
    action = data.get('action')
    mode = data.get('mode', 'both')
    
    if action == 'start':
        success = False
        if mode == 'push':
            success = detection_manager.start_push()
        elif mode == 'pull':
            success = detection_manager.start_pull()
        elif mode == 'both':
            success1 = detection_manager.start_push()
            success2 = detection_manager.start_pull()
            success = success1 or success2
        
        emit('system_message', {'message': f'已启动{mode}模式' if success else f'{mode}模式已在运行'})
    
    elif action == 'stop':
        success = False
        if mode == 'push':
            success = detection_manager.stop_push()
        elif mode == 'pull':
            success = detection_manager.stop_pull()
        elif mode == 'both':
            success1 = detection_manager.stop_push()
            success2 = detection_manager.stop_pull()
            success = success1 or success2
        
        emit('system_message', {'message': f'已停止{mode}模式' if success else f'{mode}模式未在运行'})
    

# 添加全局WebSocket客户端实例
ws_client = None

# 添加WebSocket命令处理函数
async def handle_ws_command(command_data):
    """处理从服务器接收到的WebSocket命令"""
    command = command_data.get('command')
    params = command_data.get('params', {})
    
    log_event('info', f'收到服务器命令: {command}', 'websocket')
    socketio.emit('system_message', {'message': f'收到服务器命令: {command}'})
    
    if command == 'restart':
        # 重启检测服务
        delay = params.get('delay', 0)
        log_event('info', f'系统将在{delay}秒后重启...', 'command')
        socketio.emit('system_message', {'message': f'系统将在{delay}秒后重启...'})
        
        # 延迟执行重启
        if delay > 0:
            await asyncio.sleep(delay)
        
        # 重启检测服务
        detection_manager.stop_pull()
        detection_manager.stop_push()
        time.sleep(1)
        detection_manager.start_push()
        detection_manager.start_pull()
        
        log_event('info', '检测服务已重启', 'command')
        socketio.emit('system_message', {'message': '检测服务已重启'})
        
        # 报告状态更新
        await send_status_update()
    
    elif command == 'update_config':
        # 更新配置
        log_event('info', '正在更新配置...', 'command')
        socketio.emit('system_message', {'message': '正在更新配置...'})
        
        config_changed = False
        
        if 'cameras' in params:
            detection_manager.update_cameras(params['cameras'])
            config_changed = True
        
        if 'interval' in params and float(params['interval']) != PULL_MODE_INTERVAL:
            PULL_MODE_INTERVAL = float(params['interval'])
            detection_manager.update_interval(PULL_MODE_INTERVAL)
            config_changed = True
        
        if 'mode' in params and params['mode'] != MODE:
            detection_manager.change_mode(params['mode'])
            config_changed = True
        
        if 'save_image' in params and params['save_image'] != SAVE_IMAGE:
            global SAVE_IMAGE
            SAVE_IMAGE = params['save_image']
            config_changed = True
        
        if 'preload_model' in params and params['preload_model'] != PRE_LOAD_MODEL:
            # 这个选项需要重启才能生效
            global PRE_LOAD_MODEL
            PRE_LOAD_MODEL = params['preload_model']
            config_changed = True
            
            # 通知用户需要重启
            log_event('warning', '修改预加载模型设置需要重启终端才能生效', 'command')
            socketio.emit('system_message', {'message': '修改预加载模型设置需要重启终端才能生效'})
        
        # 如果配置有变化，保存到文件
        if config_changed:
            config_data = {
                'mode': MODE,
                'interval': PULL_MODE_INTERVAL,
                'cameras': CAMERAS,
                'save_image': SAVE_IMAGE,
                'preload_model': PRE_LOAD_MODEL
            }
            save_config_to_file(config_data)
            
            log_event('info', '配置已更新并保存', 'command')
            socketio.emit('system_message', {'message': '配置已更新并保存'})
        else:
            log_event('info', '无配置变更', 'command')
            socketio.emit('system_message', {'message': '无配置变更'})
        
        # 报告状态更新
        await send_status_update()
    
    elif command == 'get_status':
        # 发送状态
        await send_status_update()
        return {
            'status': 'success',
            'data': get_system_status()
        }
    
    elif command == 'get_config':
        # 发送配置
        return {
            'status': 'success',
            'data': {
                'mode': MODE,
                'interval': PULL_MODE_INTERVAL,
                'cameras': CAMERAS,
                'save_image': SAVE_IMAGE,
                'preload_model': PRE_LOAD_MODEL
            }
        }
    
    elif command == 'get_logs':
        # 发送日志
        return {
            'status': 'success',
            'data': detection_logs
        }
    
    elif command == 'start':
        # 启动服务
        mode = params.get('mode', 'both')
        success = False
        
        if mode == 'push' or mode == 'both':
            success = detection_manager.start_push() or success
            
        if mode == 'pull' or mode == 'both':
            success = detection_manager.start_pull() or success
        
        log_event('info', f'通过命令启动{mode}模式: {"成功" if success else "失败"}', 'command')
        
        # 报告状态更新
        await send_status_update()
        
        return {
            'status': 'success' if success else 'error',
            'message': f'启动{mode}模式{"成功" if success else "失败"}'
        }
    
    elif command == 'stop':
        # 停止服务
        mode = params.get('mode', 'both')
        success = False
        
        if mode == 'push' or mode == 'both':
            success = detection_manager.stop_push() or success
            
        if mode == 'pull' or mode == 'both':
            success = detection_manager.stop_pull() or success
        
        log_event('info', f'通过命令停止{mode}模式: {"成功" if success else "失败"}', 'command')
        
        # 报告状态更新
        await send_status_update()
        
        return {
            'status': 'success' if success else 'error',
            'message': f'停止{mode}模式{"成功" if success else "失败"}'
        }
    
    else:
        log_event('warning', f'未知命令: {command}', 'command')
        return {
            'status': 'error',
            'message': f'未知命令: {command}'
        }

# 获取系统状态数据
def get_system_status():
    with status_lock:
        return {
            'cameras': system_status["cameras"],
            'cpu_usage': system_status["cpu_usage"],
            'memory_usage': system_status["memory_usage"],
            'model_loaded': system_status["model_loaded"],
            'push_running': system_status["push_running"],
            'pull_running': system_status["pull_running"],
            'started_at': system_status["started_at"],
            'mode': MODE
        }

# 发送状态更新到WebSocket服务器
async def send_status_update():
    if ws_client and ws_client.connected:
        await ws_client.send_system_status(get_system_status())

# 异步运行WebSocket客户端
def run_websocket_client():
    """创建新线程运行事件循环，用于WebSocket客户端"""
    try:
        logger.info("启动WebSocket客户端线程...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 运行WebSocket客户端
        loop.run_until_complete(init_websocket_client())
        loop.run_forever()
    except Exception as e:
        logger.error(f"WebSocket客户端线程异常: {e}")
    finally:
        if loop.is_running():
            loop.close()

# 初始化WebSocket客户端
async def init_websocket_client():
    global ws_client
    
    # 从配置中获取终端ID和服务器地址
    terminal_id = os.environ.get('TERMINAL_ID', '1')  # 可以通过环境变量设置
    server_url = os.environ.get('WS_SERVER_URL', 'ws://smarthit.top')
    
    logger.info(f"初始化WebSocket客户端: 终端ID={terminal_id}, 服务器={server_url}")
    
    ws_client = TerminalWebSocketClient(
        server_url=server_url,
        terminal_id=terminal_id,
        on_command=handle_ws_command
    )
    
    # 启动WebSocket客户端
    return await ws_client.start()

# 日志记录函数增强
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

# 启动Web服务器
def start_server():
    """启动Flask服务器"""
    try:
        log_event('info', '系统启动中...')
        # 添加allow_unsafe_werkzeug=True参数来解决Werkzeug生产环境警告
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
        log_event('info', 'Web服务器已启动')
        print("Web服务器已启动")
    except Exception as e:
        error_msg = f"启动Web服务器失败: {e}"
        log_event('error', error_msg)
        print(error_msg)

# 系统监控线程
def monitor_system():
    """监控系统资源并通过WebSocket发送更新"""
    print("系统监控线程已启动")
    
    while True:
        try:
            # 获取CPU和内存使用率
            cpu_usage = psutil.cpu_percent()
            memory_usage = psutil.virtual_memory().percent
            
            # 发送系统资源数据
            with status_lock:
                system_status["cpu_usage"] = cpu_usage
                system_status["memory_usage"] = memory_usage
                
            socketio.emit('system_resources', {
                'cpu': cpu_usage,
                'memory': memory_usage
            })
            
        except Exception as e:
            print(f"系统监控错误: {e}")
        
        # 每2秒更新一次
        time.sleep(2)

# 异步运行WebSocket客户端
def run_websocket_client():
    """创建新线程运行事件循环，用于WebSocket客户端"""
    try:
        logger.info("启动WebSocket客户端线程...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 运行WebSocket客户端
        loop.run_until_complete(init_websocket_client())
        loop.run_forever()
    except Exception as e:
        logger.error(f"WebSocket客户端线程异常: {e}")
    finally:
        if loop.is_running():
            loop.close()

# 初始化WebSocket客户端
async def init_websocket_client():
    global ws_client
    
    # 从配置中获取终端ID和服务器地址
    terminal_id = os.environ.get('TERMINAL_ID', '1')  # 可以通过环境变量设置
    server_url = os.environ.get('WS_SERVER_URL', 'ws://smarthit.top')
    
    logger.info(f"初始化WebSocket客户端: 终端ID={terminal_id}, 服务器={server_url}")
    
    ws_client = TerminalWebSocketClient(
        server_url=server_url,
        terminal_id=terminal_id,
        on_command=handle_ws_command
    )
    
    # 启动WebSocket客户端
    return await ws_client.start()

# 日志记录函数增强
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

# 修改主函数，添加日志记录
def main():
    print("启动人数检测系统...")
    log_event('info', '启动人数检测系统')

    # 加载保存的配置
    config = load_config_from_file()
    if config:
        global MODE, PULL_MODE_INTERVAL, CAMERAS, SAVE_IMAGE, PRE_LOAD_MODEL
        MODE = config.get('mode', MODE)
        PULL_MODE_INTERVAL = config.get('interval', PULL_MODE_INTERVAL)
        CAMERAS = config.get('cameras', CAMERAS)
        SAVE_IMAGE = config.get('save_image', SAVE_IMAGE)
        PRE_LOAD_MODEL = config.get('preload_model', PRE_LOAD_MODEL)
        log_event('info', '从文件加载配置成功')
        print("从文件加载配置成功")
        
        # 更新系统状态和检测线程配置
        with status_lock:
            system_status['mode'] = MODE
        
        detection_manager.interval = PULL_MODE_INTERVAL

    if INITIALIZE_CAMERA:
        log_event('info', '初始化摄像头')
        initialize_cameras()

    # 预加载模型
    if PRE_LOAD_MODEL:
        log_event('info', '预加载模型开始')
        print("预加载模型...")
        initialize_model()
        log_event('info', '预加载模型完成')

    # 启动WebSocket客户端线程
    print("启动WebSocket客户端...")
    log_event('info', '启动WebSocket客户端')
    websocket_thread = Thread(target=run_websocket_client)
    websocket_thread.daemon = True
    websocket_thread.start()
    
    # 启动系统监控线程
    print("启动系统监控...")
    log_event('info', '启动系统监控')
    monitor_thread = Thread(target=monitor_system)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # 延迟1秒确保线程启动
    time.sleep(1)
    
    # 根据配置模式启动相应服务
    if MODE == "push" or MODE == "both":
        print("启动被动接收模式...")
        log_event('info', '启动被动接收模式')
        detection_manager.start_push()
    
    if MODE == "pull" or MODE == "both":
        print("启动主动拉取模式...")
        log_event('info', '启动主动拉取模式')
        detection_manager.start_pull()
    
    # 启动Web服务器（这是阻塞的，应放在最后）
    print("启动Web服务器...")
    start_server()
    
    # 下面的代码只有在Web服务器停止时才会执行
    log_event('info', 'Web服务器已停止，正在清理...')
    print("Web服务器已停止，正在清理...")
    detection_manager.stop_push()
    detection_manager.stop_pull()
    log_event('info', '系统已停止')
    print("系统已停止")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("接收到终止信号，正在关闭...")
    except Exception as e:
        print(f"系统异常: {e}")
    finally:
        # 确保优雅退出
        print("正在清理资源...")
        if 'detection_manager' in globals():
            detection_manager.stop_push()
            detection_manager.stop_pull()
        print("系统已停止")