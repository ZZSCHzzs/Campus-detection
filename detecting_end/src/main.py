import os
import sys
import time
import logging
import asyncio
from threading import Thread
from flask import Flask, request, jsonify, send_file, send_from_directory
import traceback

from flask_cors import CORS
import psutil

# 获取项目根目录（src的父目录）
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 导入自定义模块
from config_manager import ConfigManager
from logger_manager import LogManager
from node_manager import NodeManager
from detection_manager import DetectionManager
from utils import ensure_dirs_exist, fix_ws_url, get_system_info
# 导入系统监控模块
from system_monitor import SystemMonitor

# 创建Flask应用
app = Flask(__name__, static_folder=os.path.join(ROOT_DIR, 'static'))
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 全局管理器实例
config_manager = None
log_manager = None
node_manager = None
detection_manager = None
ws_client = None
system_monitor = None  # 添加系统监控实例

# 初始化应用
def initialize_app():
    """初始化应用程序"""
    global config_manager, log_manager, node_manager, detection_manager, ws_client, system_monitor
    
    # 创建必要的目录，确保它们位于根目录而非src目录下
    ensure_dirs_exist(
        os.path.join(ROOT_DIR, 'logs'), 
        os.path.join(ROOT_DIR, 'temp'), 
        os.path.join(ROOT_DIR, 'captures'), 
        os.path.join(ROOT_DIR, 'static')
    )
    
    # 初始化配置管理器，使用根目录下的配置文件
    config_manager = ConfigManager(os.path.join(ROOT_DIR, './config.json'))
    
    # 初始化日志管理器，使用根目录下的日志目录
    log_manager = LogManager(log_dir=os.path.join(ROOT_DIR, 'logs'), max_memory_logs=1000)
    
    # 初始化摄像头管理器
    node_manager = NodeManager(config_manager)
    
    # 初始化WebSocket客户端
    ws_client = init_websocket_client()
    
    log_manager.ws_client = ws_client
    
    # 初始化检测管理器 - 仅初始化，暂不启动检测线程
    detection_manager = DetectionManager(
        config_manager=config_manager,
        node_manager=node_manager,
        log_manager=log_manager,
        ws_client=ws_client,
        system_monitor=system_monitor
    )
    
    # 只进行初始化，不启动检测线程
    detection_manager.initialize()
    
    # 初始化并启动系统监控模块
    system_monitor = SystemMonitor(
        config_manager=config_manager,
        node_manager=node_manager,
        detection_manager=detection_manager,
        log_manager=log_manager,
        ws_client=ws_client
    )
    system_monitor.start()
    
    log_manager.info("应用程序初始化完成")
    
    # 等待一段时间，确保所有组件就绪
    time.sleep(2)
    
    # 系统初始化完成后，启动检测线程
    log_manager.info("系统准备就绪，开始启动检测线程...")
    detection_manager.start_detection()
    
    return True

# WebSocket客户端初始化函数
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
        # 确保任何未捕获的异常都被记录
        try:
            # 创建一个新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 设置异常处理
            def exception_handler(loop, context):
                exception = context.get('exception')
                if exception:
                    log_manager.error(f'WebSocket异常: {str(exception)}')
                    import traceback
                    log_manager.error(f'异常详情: {traceback.format_exc()}')
                else:
                    log_manager.error(f'WebSocket异常: {context.get("message", "未知错误")}')
                
                # 当客户端仍在运行时，尝试重启客户端连接
                if client.running:
                    log_manager.info("正在尝试重新连接WebSocket服务器...")
                    try:
                        # 创建任务重启连接
                        loop.create_task(client.stop())
                        loop.create_task(client.start())
                    except Exception as e:
                        log_manager.error(f"重新连接WebSocket失败: {str(e)}")
            
            loop.set_exception_handler(exception_handler)
            
            async def run_client():
                try:
                    connected = await client.start()
                    if connected:
                        log_manager.info('WebSocket连接成功')

                        # 发送初始状态
                        try:
                            if detection_manager:
                                status_data = detection_manager.get_system_status()
                                status_data['terminal_id'] = terminal_id
                                await client.send_status(status_data)
                        except Exception as e:
                            log_manager.error(f'发送初始状态失败: {str(e)}')
                    else:
                        log_manager.error('WebSocket连接失败')                
                except Exception as e:
                    import traceback
                    log_manager.error(f'WebSocket客户端错误: {str(e)}')
                    log_manager.error(f'异常详情: {traceback.format_exc()}')


            # 运行客户端，并保持事件循环运行
            try:
                loop.run_until_complete(run_client())
                
                # 保持事件循环运行，处理未来的任务
                while True:
                    try:
                        loop.run_forever()
                    except Exception as e:
                        import traceback
                        log_manager.error(f'事件循环错误: {str(e)}')
                        log_manager.error(f'异常详情: {traceback.format_exc()}')
                        # 短暂等待后继续
                        time.sleep(1)
                        continue
                    # 如果正常退出循环，跳出
                    break
            except Exception as e:
                import traceback
                log_manager.error(f'WebSocket主循环错误: {str(e)}')
                log_manager.error(f'异常详情: {traceback.format_exc()}')
            finally:
                # 关闭循环前确保所有任务完成
                try:
                    # 取消所有挂起的任务
                    pending = asyncio.all_tasks(loop)
                    if pending:
                        log_manager.info(f"正在取消{len(pending)}个挂起的任务")
                        for task in pending:
                            task.cancel()
                        
                        # 等待所有任务完成取消
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                    
                    # 正常关闭循环
                    loop.run_until_complete(loop.shutdown_asyncgens())
                    loop.close()
                    log_manager.info("WebSocket事件循环已关闭")
                except Exception as e:
                    import traceback
                    log_manager.error(f'关闭事件循环错误: {str(e)}')
                    log_manager.error(f'异常详情: {traceback.format_exc()}')
        except Exception as e:
            import traceback
            log_manager.error(f'WebSocket线程启动错误: {str(e)}')
            log_manager.error(f'异常详情: {traceback.format_exc()}')
    
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
    
    try:
        if command == "start":
            # 开始指定模式的检测
            mode = params.get("mode", "both")
            success = False
            
            if mode == "push" or mode == "both":
                success = detection_manager.start_push()
                
            if mode == "pull" or mode == "both":
                success = detection_manager.start_pull()
                           
            # 发送更新后的状态
            status_data = detection_manager.get_system_status()
            status_data['terminal_id'] = config_manager.get('terminal_id')
            await ws_client.send_status(status_data)
            
            # 发送命令执行结果
            await ws_client.send_command_response(command, {"success": success, "mode": mode}, success=True)
        
        elif command == "stop":
            # 停止指定模式的检测
            mode = params.get("mode", "both")
            log_manager.info(f"处理停止命令: 模式={mode}")
            
            push_success = False
            pull_success = False
            
            if mode == "push" or mode == "both":
                push_success = detection_manager.stop_push()
                
            if mode == "pull" or mode == "both":
                pull_success = detection_manager.stop_pull()
                
            # 综合结果
            success = (mode == "push" and push_success) or (mode == "pull" and pull_success) or (mode == "both" and (push_success or pull_success))
                 
            # 添加验证，确保状态正确更新
            log_manager.info(f"停止后状态: push_running={detection_manager.push_running}, pull_running={detection_manager.pull_running}")
            
            # 发送更新后的状态
            status_data = detection_manager.get_system_status()
            status_data['terminal_id'] = config_manager.get('terminal_id')
            await ws_client.send_status(status_data)
            
            # 发送命令执行结果
            response_data = {
                "success": success, 
                "mode": mode,
                "push_success": push_success if mode in ["push", "both"] else None,
                "pull_success": pull_success if mode in ["pull", "both"] else None,
                "push_running": detection_manager.push_running,
                "pull_running": detection_manager.pull_running
            }
            await ws_client.send_command_response(command, response_data, success=success)
        
        elif command == "set_mode":
            mode = params.get("mode")
            if mode in ["push", "pull", "both"]:
                detection_manager.change_mode(mode)
            else:
                log_manager.warning(f"无效的模式: {mode}")
        
        elif command == "set_interval":
            interval = params.get("interval")
            if isinstance(interval, (int, float)) and interval > 0:
                detection_manager.update_interval(interval)
            else:
                log_manager.warning(f"无效的间隔值: {interval}")        
        
        elif command == "update_nodes":
            nodes = params.get("nodes")
            if isinstance(nodes, dict):
                # 更新配置
                config_manager.set('nodes', nodes)
                config_manager.save_config()
                
                # 重新加载节点
                node_manager._load_nodes()
                
            else:
                log_manager.warning(f"无效的摄像头配置: {nodes}")
        
        elif command == "restart":
            log_manager.info("正在重启服务...")
            time.sleep(2)  # 模拟重启延迟
            os.execv(sys.executable, ['python'] + sys.argv)
        
        elif command == "get_status":
            # 发送当前系统状态
            status_data = detection_manager.get_system_status()
            status_data['terminal_id'] = config_manager.get('terminal_id')
            await ws_client.send_status(status_data)
        
        elif command == "get_config":
            # 获取并返回当前配置 - 增强错误处理
            try:
                # 使用深度复制避免共享对象的问题
                import copy
                config_data = copy.deepcopy(config_manager.get_all())
                
                # 确保所有值都是可序列化的
                config_data = make_json_serializable(config_data)
                
                log_manager.info(f"返回配置数据: {len(str(config_data))} 字节")
                
                # 通过WebSocket发送配置
                send_success = await ws_client.send_command_response(command, config_data, success=True)
                if not send_success:
                    log_manager.warning("通过WebSocket发送配置失败")
                                
            except Exception as e:
                log_manager.error(f"处理get_config命令失败: {str(e)}")
                log_manager.error(f"异常堆栈: {traceback.format_exc()}")
                
                # 发送错误响应
                await ws_client.send_command_response(
                    command, 
                    {"error": f"获取配置失败: {str(e)}"}, 
                    success=False
                )
        
        elif command == "update_config" or command == "change_config":
            # 更新配置
            config_data = params
            if not config_data:
                await ws_client.send_command_response(command, {"error": "无效的配置数据"}, success=False)
                return
                
            # 保存原始配置用于比较
            old_config = config_manager.get_all()
            
            # 应用新配置
            changed = config_manager.update(config_data)
            if changed:
                config_manager.save_config()
                log_manager.info("配置已更新并保存")
                
                # 如果摄像头配置变更，重新加载摄像头
                if 'nodes' in config_data:
                    node_manager._load_nodes()
                    log_manager.info("摄像头配置已重新加载")
                
                # 如果模式变更，应用新模式
                if 'mode' in config_data and config_data['mode'] != old_config.get('mode'):
                    detection_manager.change_mode(config_data['mode'])
                    log_manager.info(f"检测模式已更改为: {config_data['mode']}")
                
                # 如果拉取间隔变更，更新
                if 'interval' in config_data and config_data['interval'] != old_config.get('interval'):
                    detection_manager.update_interval(config_data['interval'])
                    log_manager.info(f"拉取间隔已更新为: {config_data['interval']}秒")
                                
                # 发送更新后的状态
                status_data = detection_manager.get_system_status()
                status_data['terminal_id'] = config_manager.get('terminal_id')
                await ws_client.send_status(status_data)
                
                # 发送命令执行结果
                await ws_client.send_command_response(command, {"success": True, "changed": changed}, success=True)
            else:
                await ws_client.send_command_response(command, {"success": True, "changed": False}, success=True)
        
        else:
            log_manager.warning(f"未知的WebSocket命令: {command}")

            await ws_client.send_command_response(command, {"error": f"未知的命令: {command}"}, success=False)
            
    except Exception as e:
        error_msg = f"执行WebSocket命令 {command} 时出错: {str(e)}"
        log_manager.error(error_msg)
        log_manager.error(f"异常堆栈: {traceback.format_exc()}")

        
        # 发送错误响应
        try:
            await ws_client.send_command_response(command, {"error": str(e)}, success=False)
        except Exception as send_err:
            log_manager.error(f"发送错误响应失败: {str(send_err)}")
        
        # 如果出现异常，确保上传最新状态
        try:
            status_data = detection_manager.get_system_status()
            status_data['terminal_id'] = config_manager.get('terminal_id')
            await ws_client.send_status(status_data)
        except Exception as status_err:
            log_manager.error(f"发送状态更新失败: {str(status_err)}")

# 新增函数: 确保数据可JSON序列化
def make_json_serializable(obj):
    """递归处理对象，确保所有值都是可JSON序列化的"""
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    else:
        # 对于其他类型，转换为字符串
        return str(obj)

# API路由 - 终端信息
@app.route('/api/info/')
def get_info():
    """返回终端基本信息"""
    return jsonify({
        "id": config_manager.get('terminal_id'),
        "name": f"终端 #{config_manager.get('terminal_id')}",
        "server_url": config_manager.get('server_url'),
        "version": "2.0.0"
    })

# API路由 - 系统状态
@app.route('/api/status/')
def get_status():
    """获取系统状态"""
    # 使用系统监控模块的状态而不是检测管理器的状态
    status = system_monitor.get_status()
    # 合并检测管理器的一些额外信息
    detection_status = detection_manager.get_system_status()
    status.update({
        'model_loaded': detection_status.get('model_loaded', False),
        'push_running': detection_status.get('push_running', False),
        'pull_running': detection_status.get('pull_running', False),
        'mode': detection_status.get('mode', 'both')
    })
    return jsonify(status)

# API路由 - 系统信息
@app.route('/api/system/')
def get_system():
    """获取系统详细信息"""
    return jsonify(get_system_info())

# API路由 - 日志
@app.route('/api/logs/')
def get_logs():
    """获取日志"""
    count = request.args.get('count', default=None, type=int)
    return jsonify(log_manager.get_logs(count))

# API路由 - 日志统计
@app.route('/api/logs/stats/')
def get_log_stats():
    """获取日志统计数据"""
    return jsonify(detection_manager.get_detection_stats())

# API路由 - 配置
@app.route('/api/config/', methods=['GET', 'POST'])
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
            if 'nodes' in data:
                node_manager._load_nodes()
            
            # 如果模式发生变化，应用新模式
            if mode_changed:
                detection_manager.change_mode(data['mode'])
                log_manager.info(f"检测模式已更改为: {data['mode']}")
            
            # 如果间隔时间发生变化
            if 'interval' in data and data['interval'] != old_config.get('interval'):
                detection_manager.update_interval(data['interval'])
                log_manager.info(f"拉取间隔已更新为: {data['interval']}秒")
            
            log_manager.info("配置已更新并应用")

        return jsonify({"status": "success", "changed": changed, "applied": changed})

# API路由 - 控制
@app.route('/api/control/', methods=['POST'])
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
            return jsonify({"status": "success", "message": f"模式已切换为: {mode}"})
        else:
            return jsonify({"status": "error", "message": "无效的模式"}), 400
    
    # 处理启动/停止特定模式命令
    action = action + "_" + mode
    
    if action == "start_push":
        result = detection_manager.start_push()
        return jsonify({"status": "success" if result else "error", "message": "已启动被动接收模式" if result else "被动接收模式已在运行"})
    
    elif action == "stop_push":
        result = detection_manager.stop_push()

        return jsonify({"status": "success" if result else "error", "message": "已停止被动接收模式" if result else "被动接收模式未在运行"})
    
    elif action == "start_pull":
        result = detection_manager.start_pull()

        return jsonify({"status": "success" if result else "error", "message": "已启动主动拉取模式" if result else "主动拉取模式已在运行"})
    
    elif action == "stop_pull":
        result = detection_manager.stop_pull()

        return jsonify({"status": "success" if result else "error", "message": "已停止主动拉取模式" if result else "主动拉取模式未在运行"})
    
    else:
        return jsonify({"status": "error", "message": "无效的操作"}), 400


# API路由 - 接收图像
@app.route('/api/push_frame/<int:node_id>', methods=['POST'])
def receive_frame(node_id):
    """接收并处理上传的图像和环境数据"""
    if not detection_manager.push_running:
        return jsonify({"status": "error", "message": "被动接收模式未启动"}), 400
    
    try:
        # 获取环境数据（如果有）
        temperature = request.form.get('temperature', type=float)
        humidity = request.form.get('humidity', type=float)
        
        # 处理图像
        image_file = request.files.get('image')
        if image_file:
            # 读取图像数据
            image_data = image_file.read()
            
            # 处理接收到的帧
            result = process_received_frame(node_id, image_data)
            
            # 如果有环境数据，更新到结果中
            if temperature is not None:
                result['temperature'] = temperature
            if humidity is not None:
                result['humidity'] = humidity
                
            # 如果有环境数据，通过WebSocket发送
            if (temperature is not None or humidity is not None) and ws_client and ws_client.connected:
                try:
                    node_data = {
                        "id": node_id,
                        "temperature": temperature,
                        "humidity": humidity
                    }
                    
                    # 如果有检测结果，也包含在内
                    if 'detected_count' in result and result['status'] == 'success':
                        node_data["detected_count"] = result['detected_count']
                    
                    log_manager.info(f"接收到节点{node_id}的数据: 温度={temperature}, 湿度={humidity}, 检测结果={node_data.get('detected_count', 'N/A')}")
                    # 获取事件循环
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # 发送节点数据
                    asyncio.run_coroutine_threadsafe(
                        ws_client.send_nodes_data([node_data]),
                        loop
                    )
                except Exception as e:
                    log_manager.error(f"通过WebSocket发送环境数据失败: {str(e)}")
            
            return jsonify(result)
        else:
            # 仅处理环境数据，没有图像
            if temperature is not None or humidity is not None:
                # 准备节点数据
                node_data = {
                    "id": node_id
                }
                if temperature is not None:
                    node_data["temperature"] = temperature
                if humidity is not None:
                    node_data["humidity"] = humidity
                
                log_manager.info(f"接收到节点{node_id}的环境数据: 温度={temperature}, 湿度={humidity}")
                
                # 通过WebSocket发送
                if ws_client and ws_client.connected:
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    asyncio.run_coroutine_threadsafe(
                        ws_client.send_nodes_data([node_data]),
                        loop
                    )
                
                return jsonify({"status": "success", "message": "环境数据已接收"})
            else:
                return jsonify({"status": "error", "message": "未接收到图像或环境数据"}), 400
    except Exception as e:
        log_manager.error(f"处理接收帧或环境数据失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 新增 - 专门用于环境数据的API
@app.route('/api/environmental_data/<int:node_id>', methods=['POST'])
def receive_environmental_data(node_id):
    """接收环境数据"""
    try:
        data = request.json or {}
        
        # 提取环境数据
        temperature = data.get('temperature')
        humidity = data.get('humidity')
        co2_level = data.get('co2_level')
        
        if temperature is None and humidity is None and co2_level is None:
            return jsonify({"status": "error", "message": "未提供任何环境数据"}), 400
        
        # 记录接收到的数据
        log_manager.info(f"接收到节点{node_id}的环境数据: 温度={temperature}, 湿度={humidity}, CO2={co2_level}")
        
        # 通过WebSocket发送环境数据
        if ws_client and ws_client.connected:
            try:
                # 如果有CO2数据，更新系统状态
                if co2_level is not None:
                    status_data = system_monitor.get_status()
                    status_data["co2_level"] = co2_level
                    
                    # 获取事件循环
                    loop = asyncio.get_event_loop()
                    asyncio.run_coroutine_threadsafe(
                        ws_client.send_status(status_data),
                        loop
                    )
                
                # 如果有温度或湿度数据，发送节点数据
                if temperature is not None or humidity is not None:
                    node_data = {
                        "id": node_id
                    }
                    if temperature is not None:
                        node_data["temperature"] = temperature
                    if humidity is not None:
                        node_data["humidity"] = humidity
                    
                    # 获取事件循环
                    loop = asyncio.get_event_loop()
                    asyncio.run_coroutine_threadsafe(
                        ws_client.send_nodes_data([node_data]),
                        loop
                    )
            except Exception as e:
                log_manager.error(f"通过WebSocket发送环境数据失败: {str(e)}")
        
        return jsonify({"status": "success", "message": "环境数据已接收"})
    except Exception as e:
        log_manager.error(f"处理环境数据失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 静态文件路由 - 增强以更好地支持Vue前端
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    """提供静态文件，支持Vue前端路由"""
    try:
        # 检查是否为API请求
        if path.startswith('api/'):
            return jsonify({"error": "Invalid API request"}), 404
            
        # 检查是否存在实际文件
        static_folder = os.path.join(ROOT_DIR, 'static')
        if path and os.path.exists(os.path.join(static_folder, path)):
            return send_from_directory(static_folder, path)
            
        # 对于所有其他请求，返回index.html以支持Vue路由
        return send_file(os.path.join(static_folder, 'index.html'))
    except Exception as e:
        log_manager.error(f"静态文件请求错误 ({path}): {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

# 修改帧处理函数，更新帧率计数
def process_received_frame(node_id, image_data):
    """处理接收到的图像帧（用于被动接收模式）"""
    if not detection_manager.push_running:
        return {'status': 'error', 'message': '被动接收模式未启动'}
    
    try:
        # 将图像数据转换为OpenCV格式
        import numpy as np
        import cv2
        
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return {'status': 'error', 'message': '无效的图像数据'}
        
        # 如果配置为保存图像，则保存图像
        if config_manager.get('save_image', True):
            node_manager.save_image(image, node_id)
        
        # 分析图像
        count = detection_manager.analyze_image(image, node_id)
        
        # 上传结果
        detection_manager.upload_result(node_id, count)
        
        # 更新帧率统计
        system_monitor.add_frame_processed()
        
        return {'status': 'success', 'detected_count': count}
    except Exception as e:
        error_msg = f"处理接收帧失败: {str(e)}"
        log_manager.error(error_msg)
        return {'status': 'error', 'message': error_msg}

# 修改API路由 - 系统环境信息
@app.route('/api/environment/')
def get_environment():
    """返回环境信息，帮助前端识别当前运行环境"""
    try:
        terminal_id = config_manager.get('terminal_id')
        terminal_mode = config_manager.get('mode', 'local')
        server_url = config_manager.get('server_url', '')
        
        return jsonify({
            "type": "detector",  # 标识这是检测端
            "version": "2.0.0",
            "name": f"检测终端 #{terminal_id}",
            "id": terminal_id,
            "features": {
                "local_detection": True,
                "websocket": True,
                "push_mode": True,
                "pull_mode": True
            },
            "terminal_mode": terminal_mode,
            "server_url": server_url
        })
    except Exception as e:
        log_manager.error(f"获取环境信息失败: {str(e)}")
        return jsonify({
            "type": "detector",
            "version": "2.0.0",
            "name": "检测终端",
            "id": 0,
            "features": {
                "local_detection": True,
                "websocket": True,
                "push_mode": True,
                "pull_mode": True
            }
        })

# 新增：添加心跳检查端点
@app.route('/api/heartbeat/')
def heartbeat():
    """心跳检查端点，用于检测服务是否运行"""
    return jsonify({
        "status": "running",
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "terminal_id": config_manager.get('terminal_id'),
        "uptime": int(time.time() - psutil.boot_time())
    })

# 改进清理函数，确保安全关闭WebSocket
def cleanup():
    """清理资源，确保优雅退出"""
    try:
        log_manager.info("开始清理应用程序资源...")
        
        # 确保先停止系统监控
        if system_monitor:
            log_manager.info("停止系统监控...")
            system_monitor.stop()
        
        if detection_manager:
            # 停止检测服务
            if detection_manager.pull_running:
                log_manager.info("停止主动拉取模式...")
                detection_manager.stop_pull()
            if detection_manager.push_running:
                log_manager.info("停止被动接收模式...")
                detection_manager.stop_push()
        
        if ws_client:
            # 关闭WebSocket连接 - 使用一个独立的事件循环
            log_manager.info("关闭WebSocket连接...")
            try:
                # 创建一个新的事件循环来执行关闭操作
                close_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(close_loop)
                
                # 在这个循环中执行停止操作
                close_loop.run_until_complete(ws_client.stop())
                
                # 确保循环正确关闭
                close_loop.run_until_complete(close_loop.shutdown_asyncgens())
                close_loop.close()
                log_manager.info("WebSocket连接已安全关闭")
            except Exception as e:
                log_manager.error(f"关闭WebSocket连接失败: {str(e)}")
                log_manager.error(f"异常堆栈: {traceback.format_exc()}")
        
        log_manager.info("应用程序已清理资源并退出")
    except Exception as e:
        error_msg = f"清理资源时出错: {str(e)}"
        print(error_msg)
        if log_manager:
            log_manager.error(error_msg)
            log_manager.error(f"异常堆栈: {traceback.format_exc()}")

# 主程序入口点
if __name__ == "__main__":
    # 初始化应用
    initialize_app()
    
    try:
        port = config_manager.get('port', 5000)
        debug = config_manager.get('debug', False)
        
        log_manager.info(f"服务启动在端口 {port}")
        app.run(
            host='0.0.0.0', 
            port=port, 
            debug=debug, 
        )
    finally:
        # 确保程序退出时清理资源
        cleanup()