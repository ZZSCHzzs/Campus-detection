import os
import sys
import time
import logging
import asyncio
from threading import Thread
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
import psutil

# 导入自定义模块
from config_manager import ConfigManager
from logger_manager import LogManager
from camera_manager import CameraManager
from detection_manager import DetectionManager
from utils import ensure_dirs_exist, fix_ws_url, get_system_info

# 创建Flask应用
app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局管理器实例
config_manager = None
log_manager = None
camera_manager = None
detection_manager = None
ws_client = None

# 初始化应用
def initialize_app():
    """初始化应用程序"""
    global config_manager, log_manager, camera_manager, detection_manager, ws_client
    
    # 创建必要的目录
    ensure_dirs_exist('logs', 'temp', 'captures', 'static')
    
    # 初始化配置管理器
    config_manager = ConfigManager('config.json')
    
    # 初始化日志管理器（暂时不设置socketio和ws_client）
    log_manager = LogManager(log_dir='logs', max_memory_logs=1000)
    
    # 初始化摄像头管理器
    camera_manager = CameraManager(config_manager)
    
    # 初始化WebSocket客户端
    ws_client = init_websocket_client()
    
    # 更新日志管理器的WebSocket客户端和SocketIO
    log_manager.socketio = socketio
    log_manager.ws_client = ws_client
    
    # 初始化检测管理器
    detection_manager = DetectionManager(
        config_manager=config_manager,
        camera_manager=camera_manager,
        log_manager=log_manager,
        socketio=socketio,
        ws_client=ws_client
    )
    
    # 启动检测服务
    detection_manager.initialize()
    
    # 启动系统状态监控
    start_system_monitor()
    
    log_manager.info("应用程序初始化完成")
    return True

# 初始化WebSocket客户端
def init_websocket_client():
    """初始化WebSocket客户端"""
    # 获取WebSocket服务器URL和终端ID
    server_url = config_manager.get('server_url')
    terminal_id = config_manager.get('terminal_id')
    
    # 确保WebSocket URL正确
    ws_url = fix_ws_url(f"{server_url}/ws/terminal/{terminal_id}/")
    
    # 导入WebSocket客户端模块
    from websocket_client import TerminalWebSocketClient
    
    # 创建WebSocket客户端实例
    client = TerminalWebSocketClient(ws_url, terminal_id, on_command=handle_ws_command)
    
    # 启动WebSocket连接
    def start_ws_client():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_client():
            try:
                connected = await client.start()
                if connected:
                    log_manager.info(f'WebSocket客户端已连接到服务器')
                    socketio.emit('system_message', {'message': '已连接到远程服务器'})
                    socketio.emit('system_update', {'ws_connected': True})
                    
                    # 发送初始状态
                    status_data = detection_manager.get_system_status()
                    status_data['terminal_id'] = terminal_id
                    await client.send_status(status_data)
                else:
                    log_manager.error('无法连接到WebSocket服务器')
                    socketio.emit('system_error', {'message': '无法连接到远程服务器'})
                    socketio.emit('system_update', {'ws_connected': False})
            except Exception as e:
                log_manager.error(f'WebSocket客户端启动错误: {str(e)}')
                socketio.emit('system_error', {'message': f'WebSocket连接错误: {str(e)}'})
                socketio.emit('system_update', {'ws_connected': False})
        
        loop.run_until_complete(run_client())
        loop.run_forever()
    
    # 在新线程中启动WebSocket客户端
    ws_thread = Thread(target=start_ws_client, daemon=True)
    ws_thread.start()
    
    return client

# WebSocket命令处理函数
async def handle_ws_command(command_data):
    """处理从服务器接收到的WebSocket命令"""
    command = command_data.get('command')
    params = command_data.get('params', {})
    
    log_manager.info(f"接收到WebSocket命令: {command}, 参数: {params}")
    
    if command == "set_mode":
        mode = params.get("mode")
        if mode in ["push", "pull", "both"]:
            detection_manager.change_mode(mode)
            socketio.emit('system_message', {'message': f'模式已切换为: {mode}'})
        else:
            socketio.emit('system_error', {'message': '无效的模式'})
    
    elif command == "set_interval":
        interval = params.get("interval")
        if isinstance(interval, (int, float)) and interval > 0:
            detection_manager.update_interval(interval)
            socketio.emit('system_message', {'message': f'拉取间隔已更新为: {interval}秒'})
        else:
            socketio.emit('system_error', {'message': '无效的间隔值'})
    
    elif command == "update_cameras":
        cameras = params.get("cameras")
        if isinstance(cameras, dict):
            # 更新配置
            config_manager.set('cameras', cameras)
            config_manager.save_config()
            
            # 重新加载摄像头
            camera_manager._load_cameras()
            
            socketio.emit('system_message', {'message': '摄像头配置已更新'})
        else:
            socketio.emit('system_error', {'message': '无效的摄像头配置'})
    
    elif command == "restart":
        socketio.emit('system_message', {'message': '正在重启服务...'})
        time.sleep(2)  # 模拟重启延迟
        os.execv(sys.executable, ['python'] + sys.argv)
    
    elif command == "get_status":
        # 发送当前系统状态
        status_data = detection_manager.get_system_status()
        status_data['terminal_id'] = config_manager.get('terminal_id')
        await ws_client.send_status(status_data)
    
    else:
        socketio.emit('system_error', {'message': f'未知的命令: {command}'})

# API路由 - 终端信息
@app.route('/api/info')
def get_info():
    """返回终端基本信息"""
    return jsonify({
        "id": config_manager.get('terminal_id'),
        "name": f"终端 #{config_manager.get('terminal_id')}",
        "server_url": config_manager.get('server_url'),
        "version": "2.0.0"
    })

# API路由 - 系统状态
@app.route('/api/status')
def get_status():
    """获取系统状态"""
    return jsonify(detection_manager.get_system_status())

# API路由 - 系统信息
@app.route('/api/system')
def get_system():
    """获取系统详细信息"""
    return jsonify(get_system_info())

# API路由 - 日志
@app.route('/api/logs')
def get_logs():
    """获取日志"""
    count = request.args.get('count', default=None, type=int)
    return jsonify(log_manager.get_logs(count))

# API路由 - 日志统计
@app.route('/api/logs/stats')
def get_log_stats():
    """获取日志统计数据"""
    return jsonify(detection_manager.get_detection_stats())

# API路由 - 配置
@app.route('/api/config', methods=['GET', 'POST'])
def config_endpoint():
    """获取或更新终端配置"""
    if request.method == 'GET':
        return jsonify(config_manager.get_all())
    elif request.method == 'POST':
        data = request.json
        
        if not data:
            return jsonify({"status": "error", "message": "无效的配置数据"}), 400
        
        # 保存原始配置用于比较
        old_config = config_manager.get_all()
        mode_changed = 'mode' in data and data['mode'] != old_config.get('mode')
        
        # 更新配置
        changed = config_manager.update(data)
        
        # 保存配置
        if changed:
            config_manager.save_config()
            
            # 如果摄像头配置发生变化，重新加载摄像头
            if 'cameras' in data:
                camera_manager._load_cameras()
            
            # 如果模式发生变化，应用新模式
            if mode_changed:
                detection_manager.change_mode(data['mode'])
                log_manager.info(f"检测模式已更改为: {data['mode']}")
            
            # 如果间隔时间发生变化
            if 'interval' in data and data['interval'] != old_config.get('interval'):
                detection_manager.update_interval(data['interval'])
                log_manager.info(f"拉取间隔已更新为: {data['interval']}秒")
            
            log_manager.info("配置已更新并应用")
            
            # 通知前端配置已应用
            if socketio:
                socketio.emit('system_message', {'message': '配置已更新并应用'})
                socketio.emit('system_update', {'config_updated': True})
        
        return jsonify({"status": "success", "changed": changed, "applied": changed})

# API路由 - 控制
@app.route('/api/control', methods=['POST'])
def control_detection():
    """控制检测服务的启动和停止"""
    action = request.json.get('action')
    mode = request.json.get('mode')
    
    # 处理模式切换命令
    if action == "change_mode":
        if mode in ["push", "pull", "both"]:
            result = detection_manager.change_mode(mode)
            # 更新配置
            config_manager.set('mode', mode)
            config_manager.save_config()
            # 广播状态更新
            socketio.emit('system_update', {'mode': mode})
            return jsonify({"status": "success", "message": f"模式已切换为: {mode}"})
        else:
            return jsonify({"status": "error", "message": "无效的模式"}), 400
    
    # 处理启动/停止特定模式命令
    action = action + "_" + mode
    
    if action == "start_push":
        result = detection_manager.start_push()
        socketio.emit('system_update', {'push_running': result})
        return jsonify({"status": "success" if result else "error", "message": "已启动被动接收模式" if result else "被动接收模式已在运行"})
    
    elif action == "stop_push":
        result = detection_manager.stop_push()
        socketio.emit('system_update', {'push_running': not result})
        return jsonify({"status": "success" if result else "error", "message": "已停止被动接收模式" if result else "被动接收模式未在运行"})
    
    elif action == "start_pull":
        result = detection_manager.start_pull()
        socketio.emit('system_update', {'pull_running': result})
        return jsonify({"status": "success" if result else "error", "message": "已启动主动拉取模式" if result else "主动拉取模式已在运行"})
    
    elif action == "stop_pull":
        result = detection_manager.stop_pull()
        socketio.emit('system_update', {'pull_running': not result})
        return jsonify({"status": "success" if result else "error", "message": "已停止主动拉取模式" if result else "主动拉取模式未在运行"})
    
    else:
        return jsonify({"status": "error", "message": "无效的操作"}), 400

# 新增：切换终端模式API路由
@app.route('/api/switch_mode', methods=['POST'])
def switch_terminal_mode():
    """切换终端操作模式（本地/远程）"""
    try:
        data = request.json
        mode = data.get('mode')
        server_url = data.get('server_url')
        terminal_id = data.get('terminal_id')
        
        if mode not in ['local', 'remote']:
            return jsonify({"status": "error", "message": "无效的模式"}), 400
        
        if mode == 'remote' and not server_url:
            return jsonify({"status": "error", "message": "远程模式需要提供服务器URL"}), 400
            
        # 更新配置
        if mode == 'remote':
            config_manager.set('mode', 'remote')
            config_manager.set('server_url', server_url)
            if terminal_id:
                config_manager.set('terminal_id', terminal_id)
        else:
            config_manager.set('mode', 'local')
            
        config_manager.save_config()
        
        # 通知前端
        socketio.emit('system_message', {'message': f'已切换到{mode}模式'})
        socketio.emit('system_update', {'terminal_mode': mode})
        
        # 如果切换到远程模式，尝试重新连接WebSocket
        if mode == 'remote':
            global ws_client
            # 断开现有连接
            if ws_client:
                asyncio.run(ws_client.close())
            # 重新初始化WebSocket客户端
            ws_client = init_websocket_client()
            # 更新日志管理器的WebSocket客户端
            log_manager.ws_client = ws_client
            # 更新检测管理器的WebSocket客户端
            detection_manager.ws_client = ws_client
            
        return jsonify({
            "status": "success", 
            "message": f"已切换到{mode}模式",
            "terminal_mode": mode
        })
    except Exception as e:
        log_manager.error(f"切换模式失败: {str(e)}")
        return jsonify({"status": "error", "message": f"切换模式失败: {str(e)}"}), 500

# API路由 - 接收图像
@app.route('/api/push_frame/<int:camera_id>', methods=['POST'])
def receive_frame(camera_id):
    """接收并处理上传的图像"""
    if not detection_manager.push_running:
        return jsonify({"status": "error", "message": "被动接收模式未启动"}), 400
    
    try:
        # 从请求中获取图像数据
        image_file = request.files.get('image')
        if not image_file:
            return jsonify({"status": "error", "message": "未接收到图像数据"}), 400
        
        # 读取图像数据
        image_data = image_file.read()
        
        # 处理图像
        result = detection_manager.process_received_frame(camera_id, image_data)
        
        return jsonify(result)
    except Exception as e:
        log_manager.error(f"处理接收帧失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 静态文件路由 - 增强以更好地支持Vue前端
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    """提供静态文件，支持Vue前端路由"""
    # 检查是否为API请求
    if path.startswith('api/'):
        return jsonify({"error": "Invalid API request"}), 404
        
    # 检查是否存在实际文件
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
        
    # 对于所有其他请求，返回index.html以支持Vue路由
    return send_file(os.path.join(app.static_folder, 'index.html'))

# 修改：系统状态监控线程
def start_system_monitor():
    """启动系统状态监控线程，定期广播系统状态"""
    def monitor_system_status():
        """系统状态监控线程函数"""
        log_manager.info("系统状态监控线程已启动")
        
        # 创建用于异步操作的事件循环
        monitor_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(monitor_loop)
        
        # 获取配置的监控间隔，默认3秒
        monitor_interval = config_manager.get('monitor_interval', 3)
        
        last_error_time = 0
        consecutive_errors = 0
        
        # 上次CPU测量的时间点，用于计算CPU使用率
        last_cpu_times = psutil.cpu_times()
        
        while True:
            try:
                # 获取系统状态
                status_data = detection_manager.get_system_status()
                
                # 更精确地获取CPU使用率 - 计算相对于上次测量的使用率
                current_cpu_times = psutil.cpu_times()
                
                # 计算所有CPU时间差值
                user_diff = current_cpu_times.user - last_cpu_times.user
                system_diff = current_cpu_times.system - last_cpu_times.system
                idle_diff = current_cpu_times.idle - last_cpu_times.idle
                
                # 计算总时间差
                total_diff = user_diff + system_diff + idle_diff
                
                # 计算CPU使用率
                if total_diff > 0:
                    cpu_usage = 100.0 * (1.0 - (idle_diff / total_diff))
                    status_data['cpu_usage'] = round(cpu_usage, 1)
                else:
                    # 如果差值为0（极少发生），则获取即时值
                    status_data['cpu_usage'] = round(psutil.cpu_percent(interval=0.1), 1)
                
                # 更新CPU时间点用于下次计算
                last_cpu_times = current_cpu_times
                
                # 获取内存使用情况
                memory = psutil.virtual_memory()
                status_data['memory_usage'] = round(memory.percent, 1)
                
                # 添加额外的系统信息
                status_data['memory_used_mb'] = round(memory.used / (1024 * 1024), 1)
                status_data['memory_total_mb'] = round(memory.total / (1024 * 1024), 1)
                
                # 获取主要进程的CPU使用率
                process = psutil.Process()
                status_data['process_cpu_percent'] = round(process.cpu_percent(interval=0.1) / psutil.cpu_count(), 1)
                status_data['process_memory_percent'] = round(process.memory_percent(), 1)
                
                # 通过SocketIO广播系统状态
                socketio.emit('system_status', status_data)
                
                # 如果WebSocket客户端已连接，也发送状态更新
                if ws_client and ws_client.is_connected():
                    terminal_id = config_manager.get('terminal_id')
                    status_data['terminal_id'] = terminal_id
                    
                    # 使用事件循环运行异步任务
                    async def send_status():
                        await ws_client.send_status(status_data)
                    
                    try:
                        monitor_loop.run_until_complete(send_status())
                    except Exception as ws_error:
                        log_manager.error(f"发送WebSocket状态更新失败: {str(ws_error)}")
                
                # 重置错误计数
                consecutive_errors = 0
                
                # 使用配置的间隔时间
                time.sleep(monitor_interval)
            except Exception as e:
                current_time = time.time()
                consecutive_errors += 1
                
                # 计算错误频率和严重程度
                error_interval = current_time - last_error_time
                last_error_time = current_time
                
                # 记录错误
                log_manager.error(f"系统状态监控错误 ({consecutive_errors}): {str(e)}")
                
                if consecutive_errors > 10:
                    # 多次连续错误，可能需要重启监控线程
                    log_manager.warning("系统监控连续出错过多，尝试重新初始化...")
                    try:
                        # 关闭旧的事件循环
                        monitor_loop.close()
                        # 创建新的事件循环
                        monitor_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(monitor_loop)
                        consecutive_errors = 0
                    except Exception as loop_error:
                        log_manager.error(f"重新初始化事件循环失败: {str(loop_error)}")
                
                # 错误后延长等待时间，但不超过30秒
                backoff_time = min(30, monitor_interval * (2 ** min(5, consecutive_errors - 1)))
                time.sleep(backoff_time)
    
    # 启动监控线程
    monitor_thread = Thread(target=monitor_system_status, daemon=True)
    monitor_thread.start()
    return monitor_thread

# 添加API路由 - 更新监控设置
@app.route('/api/monitor/settings', methods=['POST'])
def update_monitor_settings():
    """更新系统监控设置"""
    try:
        data = request.json
        interval = data.get('interval')
        
        if interval is not None:
            # 验证间隔值是否合理
            if not isinstance(interval, (int, float)) or interval < 1 or interval > 60:
                return jsonify({"status": "error", "message": "监控间隔必须在1-60秒之间"}), 400
            
            # 更新配置
            config_manager.set('monitor_interval', interval)
            config_manager.save_config()
            
            log_manager.info(f"系统监控间隔已更新为: {interval}秒")
            socketio.emit('system_message', {'message': f'系统监控间隔已更新为: {interval}秒'})
            
            return jsonify({
                "status": "success", 
                "message": f"监控间隔已更新为: {interval}秒"
            })
        else:
            return jsonify({"status": "error", "message": "未提供监控间隔值"}), 400
    except Exception as e:
        log_manager.error(f"更新监控设置失败: {str(e)}")
        return jsonify({"status": "error", "message": f"更新监控设置失败: {str(e)}"}), 500

# 添加版本信息和环境标识API
@app.route('/api/environment')
def get_environment():
    """返回环境信息，帮助前端识别当前运行环境"""
    terminal_mode = config_manager.get('mode', 'local')
    return jsonify({
        "type": "detector",  # 标识这是检测端
        "version": "2.0.0",
        "name": f"终端 #{config_manager.get('terminal_id')}",
        "id": config_manager.get('terminal_id'),
        "features": {
            "local_detection": True,
            "websocket": True,
            "push_mode": True,
            "pull_mode": True
        },
        "terminal_mode": terminal_mode  # 添加终端模式信息
    })

# 修改 Socket.IO 事件处理
@socketio.on('connect')
def handle_connect():
    """处理客户端连接事件"""
    log_manager.info(f"Socket.IO客户端已连接: {request.sid}")
    # 发送初始系统状态
    status_data = detection_manager.get_system_status()
    socketio.emit('system_status', status_data, room=request.sid)
    # 不要返回 true，否则表示异步响应
    # return True

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接事件"""
    log_manager.info(f"Socket.IO客户端已断开连接: {request.sid}")

@socketio.on('client_connected')
def handle_client_connected(data):
    """处理客户端发送的连接初始化消息"""
    log_manager.info(f"收到客户端初始化消息: {data}")
    # 发送确认消息
    socketio.emit('system_message', {'message': '已连接到本地终端'}, room=request.sid)
    # 发送系统状态
    status_data = detection_manager.get_system_status()
    socketio.emit('system_status', status_data, room=request.sid)

# 辅助函数，供其他模块访问全局管理器实例
def get_config_manager():
    """获取配置管理器实例"""
    return config_manager

def get_log_manager():
    """获取日志管理器实例"""
    return log_manager

def get_camera_manager():
    """获取摄像头管理器实例"""
    return camera_manager

def get_detection_manager():
    """获取检测管理器实例"""
    return detection_manager

def get_ws_client():
    """获取WebSocket客户端实例"""
    return ws_client

# 主程序入口点
if __name__ == "__main__":
    # 初始化应用
    initialize_app()
    
    # 使用socketio.run启动Flask应用
    port = config_manager.get('port', 5000)
    debug = config_manager.get('debug', False)
    
    log_manager.info(f"服务启动在端口 {port}")
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=port, 
        debug=debug, 
        allow_unsafe_werkzeug=True
    )