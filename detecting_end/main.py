import cv2
import time
import os
import datetime
import requests
import numpy as np
import detect.run as detect
from flask import Flask, request, jsonify
from threading import Thread
from camera import apply_camera_config

app = Flask(__name__)

# 运行模式
MODE = "push"  # "pull" 或 "push"
PULL_MODE_INTERVAL = 1  # 主动拉取模式的间隔时间（秒）
PRE_LOAD_MODEL = True # 是否预加载模型
LOADED_MODEL = None # 全局变量存储预加载的模型
SAVE_IMAGE = True  # 是否保存图像
INITIALIZE_CAMERA = True  # 是否初始化摄像头
CAMERAS = {
    1: "http://192.168.1.101:81",
    2: "http://192.168.1.102:81"
}
STREAM_URL = "/stream"


# 预加载模型函数
def initialize_model():
    global LOADED_MODEL
    print("正在预加载YOLO模型...")
    LOADED_MODEL = detect.load_model()
    print("模型加载完成！")

def initialize_cameras():
    for camera_id, camera_url in CAMERAS.items():
        print(f"初始化摄像头 {camera_id}:{camera_url} ...")
        if not apply_camera_config(camera_url):
            print(f"摄像头 {camera_id} 初始化失败！")
            continue
        print(f"摄像头 {camera_id} 初始化完成！")

# 从 WiFi 摄像头捕获图像
def capture_image_from_camera(camera_url):
    cap = cv2.VideoCapture(camera_url+STREAM_URL)
    if not cap.isOpened():
        raise Exception("无法连接到摄像头")
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise Exception("无法读取图像")
    return frame


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
    
    return camera_results


# 上传检测结果到服务器
def upload_result(camera_id, detected_count):
    url = "http://smarthit.top:8000/api/upload/"
    data = {
        "id": camera_id,
        "detected_count": detected_count,
        "timestamp": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")  # 标准化时间格式
    }
    try:
        response = requests.post(url, json=data, timeout=5)
        if response.status_code != 201:
            print(f"上传警告: 状态码 {response.status_code}, 响应: {response.text}")
        return response.json()
    except Exception as e:
        print(f"上传结果失败: {e}")
        return None


# 主动拉取模式处理
def pull_mode_handler():
    interval = 1
    print("运行在主动拉取模式...")
    # 初始化摄像头

    while True:
        images_to_process = []
        
        # 收集多个摄像头的图像
        for camera_id, camera_url in CAMERAS.items():
            try:
                # 捕获图像
                image = capture_image_from_camera(camera_url)
                images_to_process.append((image, camera_id))
            except Exception as e:
                print(f"摄像头 {camera_id} 捕获失败: {e}")
        
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

        time.sleep(interval)


# Flask接收端点
@app.route('/api/push_frame/<int:camera_id>', methods=['POST'])  # 指定camera_id为整数
def receive_frame(camera_id):
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


def start_flask_server():
    app.run(host='0.0.0.0', port=5000)


# 主函数
def main():
    print("启动人数检测系统...")

    if INITIALIZE_CAMERA:
        initialize_cameras()


    # 预加载模型
    if PRE_LOAD_MODEL:
        print("预加载模型...")
        initialize_model()

    if MODE == "pull":
        # 主动拉取模式
        pull_mode_handler()
    else:
        # 被动接收模式
        print("运行在被动接收模式...")
        flask_thread = Thread(target=start_flask_server)
        flask_thread.daemon = True
        flask_thread.start()

        # 保持主线程运行
        while True:
            time.sleep(1)


if __name__ == '__main__':
    main()
