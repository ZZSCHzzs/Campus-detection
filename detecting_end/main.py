import cv2
import time
import os
import datetime
import requests
import numpy as np
import detect.run as detect
from flask import Flask, request, jsonify
from threading import Thread

app = Flask(__name__)

CAMERAS = {
    1: "rtsp://username:password@192.168.1.101:554/stream",
    2: "rtsp://username:password@192.168.1.102:554/stream"
}

# 运行模式
MODE = "push"  # "pull" 或 "push"


# 从 WiFi 摄像头捕获图像
def capture_image_from_camera(camera_url):
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        raise Exception("无法连接到摄像头")

    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise Exception("无法读取图像")

    return frame


# 调用 detect.detect() 分析人数
def analyze_image(image):
    # 临时保存图像
    temp_path = "temp_capture.jpg"
    cv2.imwrite(temp_path, image)
    count = detect.detect(temp_path)
    os.remove(temp_path)
    return count


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
        if response.status_code != 200:
            print(f"上传警告: 状态码 {response.status_code}, 响应: {response.text}")
        return response.json()
    except Exception as e:
        print(f"上传结果失败: {e}")
        return None


# 主动拉取模式处理
def pull_mode_handler():
    interval = 1
    print("运行在主动拉取模式...")

    while True:
        for camera_id, camera_url in CAMERAS.items():
            try:
                # 捕获图像
                image = capture_image_from_camera(camera_url)

                # 分析图像
                detected_count = analyze_image(image)
                print(f"摄像头 {camera_id} 检测到人数: {detected_count}")

                # 上传结果
                upload_result(camera_id, detected_count)

            except Exception as e:
                print(f"摄像头 {camera_id} 处理失败: {e}")

        time.sleep(interval)


# Flask接收端点
@app.route('/api/push_frame/<int:camera_id>', methods=['POST'])  # 指定camera_id为整数
def receive_frame(camera_id):
    if camera_id not in CAMERAS:
        print(f"无效的摄像头ID: {camera_id}")
        return jsonify({"error": "无效的摄像头ID"}), 400

    if 'file' not in request.files:
        print("没有文件上传")
        return jsonify({"error": "没有文件上传"}), 400

    file = request.files['file']
    try:
        # 读取图像
        img_data = file.read()
        if len(img_data) == 0:
            print("空文件内容")
            return jsonify({"error": "空文件内容"}), 400

        image = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            print("无效的图片格式")
            return jsonify({"error": "无效的图片格式"}), 400

        # 分析图像
        detected_count = analyze_image(image)
        print(f"摄像头 {camera_id} 检测到人数: {detected_count}")

        # 上传结果
        result = upload_result(camera_id, detected_count)
        if result is None:
            return jsonify({"error": "云端上传失败"}), 500

        return jsonify({
            "status": "success",
            "camera_id": camera_id,  
            "count": detected_count
        })
    except Exception as e:
        print(f"处理异常: {str(e)}")
        return jsonify({"error": str(e)}), 500


def start_flask_server():
    app.run(host='0.0.0.0', port=5000)


# 主函数
def main():
    print("启动人数检测系统...")

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
