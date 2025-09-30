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
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
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
# 导入蜂鸣器管理模块
from buzzer_manager import BuzzerManager, BuzzerPattern

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
buzzer_manager = None  # 添加蜂鸣器管理实例

logger = logging.getLogger('main')
# 初始化应用
def initialize_app():
    """初始化应用程序"""
    global config_manager, log_manager, node_manager, detection_manager, ws_client, system_monitor, buzzer_manager
    
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

    # 将标准 logging 输出桥接到 LogManager 的内存与 WS
    log_manager.attach_bridge()
    
    # 初始化摄像头管理器
    node_manager = NodeManager(config_manager)
    
    # 初始化WebSocket客户端
    ws_client = init_websocket_client()
    
    log_manager.ws_client = ws_client
    
    # 初始化蜂鸣器管理器
    try:
        buzzer_manager = BuzzerManager(
            pin_trigger=2,  # 触发引脚
            pin_echo=9,     # 回声引脚
            pin_buzzer=11,  # 蜂鸣器引脚
            log_manager=log_manager
        )
    except Exception as e:
        logger.error(f"蜂鸣器初始化失败: {str(e)}，系统将继续运行，但蜂鸣器功能将不可用")
        buzzer_manager = None
    
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
    
    logger.info("应用程序初始化完成")
    
    # 等待一段时间，确保所有组件就绪
    time.sleep(2)
    
    # 系统初始化完成后，启动检测线程
    logger.info("系统准备就绪，开始启动检测线程...")
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
    
    from websocket_client import TerminalWebSocketClient
    client = TerminalWebSocketClient(ws_url, terminal_id, on_command=handle_ws_command)
    client.max_reconnect_attempts = None

    def start_ws_client():
        # 若事件循环意外停止，自动重建并继续运行，直到外部设置 client.running=False
        while True:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # 显式暴露给跨线程投递
                client.loop = loop

                # 事件循环异常处理器：忽略 websockets 的已知噪声异常，避免 loop 因错误停止
                def exception_handler(loop_, context):
                    exc = context.get("exception")
                    msg = context.get("message")
                    handle = context.get("handle")
                    text = f"{msg or exc or ''}"
                    handle_str = str(handle or "")
                    if (exc and isinstance(exc, AttributeError) and "recv_messages" in str(exc)) \
                       or (isinstance(exc, ConnectionResetError)) \
                       or ("Connection.connection_lost" in handle_str):
                        # logger.warning(f"忽略 websockets 内部异常: {exc or msg}")
                        return
                    logger.error(f"事件循环异常: {text}")

                loop.set_exception_handler(exception_handler)

                async def boot():
                    try:
                        await client.start()
                    except Exception as e:
                        logger.error(f'WebSocket启动失败: {e}')
                        logger.error(f'异常详情: {traceback.format_exc()}')
                        # 由客户端内部无限重连逻辑继续尝试

                loop.create_task(boot())
                loop.run_forever()
            except Exception as e:
                log_manager.error(f'WebSocket线程循环错误: {str(e)}')
                log_manager.error(f'异常详情: {traceback.format_exc()}')
            finally:
                try:
                    # 关闭前清理异步生成器
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception:
                    pass
                try:
                    loop.close()
                except Exception:
                    pass

            # 外部已请求停止，退出线程
            if not getattr(client, "running", False):
                break

            # 若并非正常停止，说明 loop 意外退出；短暂等待后重建
            logger.warning("WebSocket事件循环意外停止，1秒后重建并继续运行...")
            time.sleep(1)

    ws_thread = Thread(target=start_ws_client, daemon=True)
    ws_thread.start()
    return client

# WebSocket命令处理函数
async def handle_ws_command(command_data):
    """处理从服务器接收到的WebSocket命令"""
    command = command_data.get('command')
    params = command_data.get('params', {})
    
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
            # 注入节点详情
            try:
                node_details = node_manager.get_node_status()
                status_data['node_details'] = node_details
                status_data['nodes'] = {nid: (st.get('status', '未知') or '未知') for nid, st in node_details.items()}
            except Exception as _:
                pass
            await ws_client.send_status(status_data)
            
            # 发送命令执行结果
            await ws_client.send_command_response(command, {"success": success, "mode": mode}, success=True)
        
        elif command == "stop":
            # 停止指定模式的检测
            mode = params.get("mode", "both")
            
            push_success = False
            pull_success = False
            
            if mode == "push" or mode == "both":
                push_success = detection_manager.stop_push()
                
            if mode == "pull" or mode == "both":
                pull_success = detection_manager.stop_pull()
                
            # 综合结果
            success = (mode == "push" and push_success) or (mode == "pull" and pull_success) or (mode == "both" and (push_success or pull_success))
                 
            # 发送更新后的状态
            status_data = detection_manager.get_system_status()
            status_data['terminal_id'] = config_manager.get('terminal_id')
            # 注入节点详情
            try:
                node_details = node_manager.get_node_status()
                status_data['node_details'] = node_details
                status_data['nodes'] = {nid: (st.get('status', '未知') or '未知') for nid, st in node_details.items()}
            except Exception as _:
                pass
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
                logger.warning(f"无效的模式: {mode}")
        
        elif command == "set_interval":
            interval = params.get("interval")
            if isinstance(interval, (int, float)) and interval > 0:
                detection_manager.update_interval(interval)
            else:
                logger.warning(f"无效的间隔值: {interval}")        
        
        elif command == "update_nodes":
            nodes = params.get("nodes")
            if isinstance(nodes, dict):
                # 更新配置
                config_manager.set('nodes', nodes)
                config_manager.save_config()
                
                # 重新加载节点
                node_manager._load_nodes()
                
            else:
                logger.warning(f"无效的摄像头配置: {nodes}")
        
        elif command == "restart":
            logger.info("正在重启服务...")
            time.sleep(2)  # 模拟重启延迟
            os.execv(sys.executable, ['python'] + sys.argv)
        
        elif command == "get_status":
            # 发送当前系统状态
            status_data = detection_manager.get_system_status()
            status_data['terminal_id'] = config_manager.get('terminal_id')
            # 注入节点详情
            try:
                node_details = node_manager.get_node_status()
                status_data['node_details'] = node_details
                status_data['nodes'] = {nid: (st.get('status', '未知') or '未知') for nid, st in node_details.items()}
            except Exception as _:
                pass
            await ws_client.send_status(status_data)
        
        elif command == "get_config":
            # 获取并返回当前配置 - 增强错误处理
            try:
                # 使用深度复制避免共享对象的问题
                import copy
                config_data = copy.deepcopy(config_manager.get_all())
                
                # 确保所有值都是可序列化的
                config_data = make_json_serializable(config_data)
                
                logger.info(f"返回配置数据: {len(str(config_data))} 字节")
                
                # 通过WebSocket发送配置
                send_success = await ws_client.send_command_response(command, config_data, success=True)
                if not send_success:
                    logger.warning("通过WebSocket发送配置失败")

            except Exception as e:
                logger.error(f"处理get_config命令失败: {str(e)}")
                logger.error(f"异常堆栈: {traceback.format_exc()}")

                # 发送错误响应
                await ws_client.send_command_response(
                    command, 
                    {"error": f"获取配置失败: {str(e)}"}, 
                    success=False
                )
        
        elif command == "get_logs":
            # 获取并返回当前日志 - 批量发送到服务端
            try:
                # 获取最近的日志
                count = params.get("count", 100)  # 默认获取100条日志
                logs_data = log_manager.get_logs(count)

                logger.info(f"返回 {len(logs_data)} 条日志数据")

                # 通过WebSocket发送日志批次
                send_success = await ws_client.send_command_response(command, logs_data, success=True)
                if not send_success:
                    logger.warning("通过WebSocket发送日志失败")

            except Exception as e:
                logger.error(f"处理get_logs命令失败: {str(e)}")
                logger.error(f"异常堆栈: {traceback.format_exc()}")

                # 发送错误响应
                await ws_client.send_command_response(
                    command, 
                    {"error": f"获取日志失败: {str(e)}"}, 
                    success=False
                )
        # 蜂鸣器控制命令
        elif command == "buzzer":
            if not buzzer_manager:
                await ws_client.send_command_response(command, {"error": "蜂鸣器管理器未初始化"}, success=False)
                return
                
            action = params.get("action")
            
            if action == "beep":
                # 简单鸣叫
                duration = params.get("duration", 0.5)
                buzzer_manager.beep(duration)
                await ws_client.send_command_response(command, {"success": True}, success=True)
                
            elif action == "start":
                # 开始指定模式的鸣叫
                pattern_name = params.get("pattern", "SINGLE_BEEP")
                repeat = params.get("repeat", 1)
                
                # 获取模式枚举值
                try:
                    pattern = BuzzerPattern[pattern_name]
                except (KeyError, ValueError):
                    pattern = BuzzerPattern.SINGLE_BEEP
                    log_manager.warning(f"无效的蜂鸣器模式: {pattern_name}，使用默认模式")
                
                # 获取自定义模式
                custom_pattern = params.get("custom_pattern")
                
                # 启动蜂鸣器
                buzzer_manager.start_buzzer(pattern, repeat, custom_pattern)
                await ws_client.send_command_response(command, {"success": True}, success=True)
                
            elif action == "stop":
                # 停止鸣叫
                buzzer_manager.stop_buzzer()
                await ws_client.send_command_response(command, {"success": True}, success=True)
                
            else:
                await ws_client.send_command_response(command, {"error": f"未知的蜂鸣器操作: {action}"}, success=False)
        
        elif command == "light_rotate":
            # 远程灯光旋转控制
            try:
                node_id = params.get("node_id")
                angle = params.get("angle")
                if node_id is None or angle is None:
                    await ws_client.send_command_response(command, {"error": "缺少参数: node_id/angle"}, success=False)
                    return
                try:
                    node_id_int = int(node_id)
                except Exception:
                    node_id_int = node_id
                try:
                    angle_val = float(angle)
                except Exception:
                    await ws_client.send_command_response(command, {"error": "angle 必须为数字"}, success=False)
                    return
                if angle_val < 0 or angle_val > 180:
                    await ws_client.send_command_response(command, {"error": "角度必须在 0-180 之间"}, success=False)
                    return
                ok = node_manager.rotate_light(node_id_int, angle_val)
                await ws_client.send_command_response(
                    command,
                    {"success": bool(ok), "node_id": node_id, "angle": angle_val},
                    success=bool(ok)
                )
            except Exception as e:
                logger.error(f"处理 light_rotate 命令失败: {e}")
                await ws_client.send_command_response(command, {"error": str(e)}, success=False)
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
                logger.info("配置已更新并保存")
                
                # 如果摄像头配置变更，重新加载摄像头
                if 'nodes' in config_data:
                    node_manager._load_nodes()
                    logger.info("摄像头配置已重新加载")

                # 如果模式变更，应用新模式
                if 'mode' in config_data and config_data['mode'] != old_config.get('mode'):
                    detection_manager.change_mode(config_data['mode'])
                    logger.info(f"检测模式已更改为: {config_data['mode']}")

                # 如果拉取间隔变更，更新
                if 'interval' in config_data and config_data['interval'] != old_config.get('interval'):
                    detection_manager.update_interval(config_data['interval'])
                    logger.info(f"拉取间隔已更新为: {config_data['interval']}秒")

                # 发送更新后的状态
                status_data = detection_manager.get_system_status()
                status_data['terminal_id'] = config_manager.get('terminal_id')
                # 注入节点详情
                try:
                    node_details = node_manager.get_node_status()
                    status_data['node_details'] = node_details
                    status_data['nodes'] = {nid: (st.get('status', '未知') or '未知') for nid, st in node_details.items()}
                except Exception as _:
                    pass
                await ws_client.send_status(status_data)
                
                # 发送命令执行结果
                await ws_client.send_command_response(command, {"success": True, "changed": changed}, success=True)
            else:
                await ws_client.send_command_response(command, {"success": True, "changed": False}, success=True)
        
        else:
            logger.warning(f"未知的WebSocket命令: {command}")

            await ws_client.send_command_response(command, {"error": f"未知的命令: {command}"}, success=False)
            
    except Exception as e:
        error_msg = f"执行WebSocket命令 {command} 时出错: {str(e)}"
        logger.error(error_msg)
        logger.error(f"异常堆栈: {traceback.format_exc()}")

        
        # 发送错误响应
        try:
            await ws_client.send_command_response(command, {"error": str(e)}, success=False)
        except Exception as send_err:
            log_manager.error(f"发送错误响应失败: {str(send_err)}")
        
        # 如果出现异常，确保上传最新状态
        try:
            status_data = detection_manager.get_system_status()
            status_data['terminal_id'] = config_manager.get('terminal_id')
            # 注入节点详情
            try:
                node_details = node_manager.get_node_status()
                status_data['node_details'] = node_details
                status_data['nodes'] = {nid: (st.get('status', '未知') or '未知') for nid, st in node_details.items()}
            except Exception as _:
                pass
            await ws_client.send_status(status_data)
        except Exception as status_err:
            logger.error(f"发送状态更新失败: {str(status_err)}")

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
    
    # 新增：对齐前端期望的节点字段
    try:
        node_details = node_manager.get_node_status()  # 详细信息
        # 简化状态映射：{ id: '在线' | '离线' | '错误' | '未知' }
        nodes_map = {nid: (st.get('status', '未知') or '未知') for nid, st in node_details.items()}
        status['node_details'] = node_details
        status['nodes'] = nodes_map
    except Exception as e:
        log_manager.error(f"构建节点状态返回值失败: {str(e)}")
        # 兜底字段，防止前端报错
        status.setdefault('node_details', {})
        status.setdefault('nodes', {})
    
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
    
    # 新增：处理重启命令（HTTP 版本）
    if action == "restart":
        try:
            log_manager.info("收到重启命令（HTTP）...")
            # 短暂延迟以便响应返回
            time.sleep(1)
            os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            log_manager.error(f"重启失败: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500
        # 正常情况下 execv 不会返回，这里给出兜底响应
        return jsonify({"status": "success", "message": "正在重启"})

    # 新增：处理动态设置拉取间隔
    if action == "set_interval":
        interval = request.json.get('interval')
        if not isinstance(interval, (int, float)) or interval <= 0:
            return jsonify({"status": "error", "message": "无效的间隔值"}), 400
        detection_manager.update_interval(interval)
        # 同步到配置文件，确保持久化
        try:
            config_manager.set('interval', interval)
            config_manager.save_config()
        except Exception as e:
            log_manager.warning(f"保存间隔到配置失败: {str(e)}")
        return jsonify({"status": "success", "message": f"拉取间隔已更新为: {interval}秒"})
    
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
            # 同步写入本地节点环境数据
            try:
                if temperature is not None or humidity is not None:
                    node_manager.update_environment_data(node_id, temperature, humidity)
            except Exception as _:
                pass
            # 如果有环境数据，通过WebSocket发送
            if (temperature is not None or humidity is not None) and ws_client and ws_client.connected:
                try:
                    node_data = {
                        "id": node_id,
                        "temperature": temperature,
                        "humidity": humidity
                    }
                    if 'detected_count' in result and result['status'] == 'success':
                        node_data["detected_count"] = result['detected_count']

                    log_manager.info(f"接收到节点{node_id}的数据: 温度={temperature}, 湿度={humidity}, 检测结果={node_data.get('detected_count', 'N/A')}")
                    # 使用 WebSocket 线程事件循环发送
                    loop = getattr(ws_client, 'loop', None)
                    if loop and ws_client.connected:
                        asyncio.run_coroutine_threadsafe(
                            ws_client.send_nodes_data([node_data]),
                            loop
                        )
                    else:
                        log_manager.warning("WebSocket循环不可用或未连接，跳过环境数据上报")
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
                        loop = getattr(ws_client, 'loop', None)
                        if loop and ws_client.connected:
                            asyncio.run_coroutine_threadsafe(
                                ws_client.send_nodes_data([node_data]),
                                loop
                            )
                        else:
                            log_manager.warning("WebSocket循环不可用或未连接，跳过环境数据上报")
                    except Exception as e:
                        log_manager.error(f"通过WebSocket发送环境数据失败: {str(e)}")
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
                if co2_level is not None:
                    status_data = system_monitor.get_status()
                    status_data["co2_level"] = co2_level
                    # 注入节点详情
                    try:
                        node_details = node_manager.get_node_status()
                        status_data['node_details'] = node_details
                        status_data['nodes'] = {nid: (st.get('status', '未知') or '未知') for nid, st in node_details.items()}
                    except Exception as _:
                        pass
                if temperature is not None or humidity is not None:
                    # 同步写入本地节点环境数据
                    try:
                        node_manager.update_environment_data(node_id, temperature, humidity)
                    except Exception as _:
                        pass
                   
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

# 蜂鸣器API控制接口
@app.route('/api/buzzer/', methods=['POST'])
def control_buzzer():
    """控制蜂鸣器"""
    if not buzzer_manager:
        return jsonify({"status": "error", "message": "蜂鸣器管理器未初始化"}), 500
        
    try:
        data = request.json
        action = data.get('action')
        
        if action == "beep":
            duration = data.get("duration", 0.5)
            buzzer_manager.beep(duration)
            return jsonify({"status": "success", "message": f"蜂鸣器鸣叫 {duration} 秒"})
            
        elif action == "start":
            pattern_name = data.get("pattern", "SINGLE_BEEP")
            repeat = data.get("repeat", 1)
            
            # 获取模式枚举值
            try:
                pattern = BuzzerPattern[pattern_name]
            except (KeyError, ValueError):
                pattern = BuzzerPattern.SINGLE_BEEP
                log_manager.warning(f"无效的蜂鸣器模式: {pattern_name}，使用默认模式")
            
            # 获取自定义模式
            custom_pattern = data.get("custom_pattern")
            
            # 启动蜂鸣器
            buzzer_manager.start_buzzer(pattern, repeat, custom_pattern)
            return jsonify({"status": "success", "message": f"蜂鸣器已启动，模式: {pattern_name}"})
            
        elif action == "stop":
            buzzer_manager.stop_buzzer()
            return jsonify({"status": "success", "message": "蜂鸣器已停止"})
            
        else:
            return jsonify({"status": "error", "message": f"未知的蜂鸣器操作: {action}"}), 400
            
    except Exception as e:
        log_manager.error(f"控制蜂鸣器失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 蜂鸣器状态API接口
@app.route('/api/buzzer/status/')
def get_buzzer_status():
    """获取蜂鸣器状态"""
    try:
        # 优先使用蜂鸣器管理器的真实状态
        available = bool(buzzer_manager and getattr(buzzer_manager, "_available", False))
        active = bool(buzzer_manager and buzzer_manager.is_active())
        return jsonify({
            'available': available,
            'active': active
        })
    except Exception as e:
        log_manager.error(f"获取蜂鸣器状态失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/light/rotate/', methods=['POST'])
def control_light_rotate():
    """控制节点灯光旋转"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据不能为空'}), 400
        
        node_id = data.get('node_id')
        angle = data.get('angle', 90)  # 默认90度
        
        if node_id is None:
            return jsonify({'error': '缺少节点ID'}), 400
        
        # 统一 node_id 类型
        try:
            node_id_int = int(node_id)
        except Exception:
            # 允许直接传字符串，但 NodeManager 内部已规范化
            node_id_int = node_id
        
        # 验证角度范围
        if not isinstance(angle, (int, float)) or angle < 0 or angle > 180:
            return jsonify({'error': '角度必须在 0-180 度之间'}), 400
        
        # 调用节点管理器进行灯光旋转
        success = node_manager.rotate_light(node_id_int, angle)
        
        if success:
            return jsonify({
                'message': f'节点 {node_id} 灯光旋转至 {angle} 度成功',
                'node_id': node_id,
                'angle': angle
            })
        else:
            return jsonify({'error': f'节点 {node_id} 灯光旋转失败'}), 500
    except Exception as e:
        log_manager.error(f"控制灯光旋转失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/light/status/<int:node_id>/')
def get_light_status(node_id):
    """获取节点灯光控制状态"""
    try:
        # 规范化ID为字符串以匹配配置中的键
        node_id_str = str(node_id)
        
        # 检查节点是否存在
        node_info = node_manager.get_node_info(node_id)
        if not node_info:
            return jsonify({'error': f'节点 {node_id} 不存在'}), 404
        
        # 检查节点连接状态
        is_online = node_manager.check_node_connection(node_id)
        
        # 检查节点是否支持灯光控制
        control_nodes = node_manager.get_control_nodes()
        data_nodes = node_manager.get_data_nodes()
        
        supports_rotate = False
        if node_id_str in control_nodes:
            node_config = control_nodes[node_id_str]
            if isinstance(node_config, dict):
                capabilities = node_config.get('capabilities', [])
                supports_rotate = 'rotate' in capabilities
            else:
                supports_rotate = True  # 兼容旧格式，默认支持
        elif node_id_str in data_nodes:
            supports_rotate = True  # 数据节点也可能支持旋转（向后兼容）
        
        # 获取默认角度和自动回正时间配置
        light_config = config_manager.get('light_control', {})
        default_angle = light_config.get('default_angle', 90)
        auto_return_time = light_config.get('auto_return_time', 3)
        
        return jsonify({
            'node_id': node_id,
            'online': is_online,
            'supports_rotate': supports_rotate,
            'default_angle': default_angle,
            'auto_return_time': auto_return_time,
            'node_status': node_info.get('status', {})
        })
        
    except Exception as e:
        log_manager.error(f"获取节点 {node_id} 灯光状态失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/image/last/<int:node_id>/')
def get_last_image(node_id):
    """获取指定数据节点最近一次保存的图片"""
    try:
        base_dir = os.path.join(ROOT_DIR, 'captures', f'node_{node_id}')
        if not os.path.exists(base_dir):
            return jsonify({'error': '未找到该节点的图片目录'}), 404
        # 仅筛选常见图片格式
        files = [f for f in os.listdir(base_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if not files:
            return jsonify({'error': '未找到该节点的图片'}), 404
        # 文件名为时间戳(YYYYmmdd_HHMMSS.jpg)，按文件名倒序即可
        files.sort(reverse=True)
        latest_file = files[0]
        file_path = os.path.join(base_dir, latest_file)
        if not os.path.exists(file_path):
            return jsonify({'error': '图片文件不存在'}), 404
        return send_file(file_path, mimetype='image/jpeg')
    except Exception as e:
        if log_manager:
            log_manager.error(f"获取节点 {node_id} 最新图片失败: {str(e)}")
        return jsonify({'error': '内部错误', 'details': str(e)}), 500

# 改进清理函数，确保安全关闭WebSocket
def cleanup():
    """清理资源，确保优雅退出"""
    try:
        log_manager.info("开始清理应用程序资源...")
        
        # 清理蜂鸣器资源
        if buzzer_manager:
            log_manager.info("正在清理蜂鸣器资源...")
            buzzer_manager.cleanup()

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
            log_manager.info("关闭WebSocket连接...")
            try:
                loop = getattr(ws_client, 'loop', None)
                if loop:
                    # 在 WS 线程事件循环上停止客户端
                    fut = asyncio.run_coroutine_threadsafe(ws_client.stop(), loop)
                    try:
                        fut.result(timeout=10)
                    except Exception as e:
                        log_manager.warning(f"等待WebSocket停止超时或异常: {e}")
                    # 停止事件循环线程
                    loop.call_soon_threadsafe(loop.stop)
                else:
                    log_manager.warning("未找到WebSocket事件循环，跳过关闭")
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

