import cv2
import time
import os
import datetime
import requests
import detect.run as detect


# 从 WiFi 摄像头捕获图像
def capture_image_from_camera(camera_url):
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        raise Exception("无法连接到摄像头")

    ret, frame = cap.read()
    if not ret:
        raise Exception("无法读取图像")

    cap.release()
    return frame


# 调用 detect.detect() 分析人数
def analyze_image(image_path):
    return detect.detect(image_path)


# 获取硬件 ID
def get_hardware_id():
    hardware_id = os.getenv("HARDWARE_ID", "default_hardware_id")  # 从环境变量中读取硬件 ID
    return hardware_id


# 上传检测结果到服务器
def upload_result(hardware_id, detected_count):
    url = "http://smarthit.top:8000/api/upload"
    data = dict(id=hardware_id, detected_count=detected_count,
                timestamp=datetime.datetime.now(datetime.UTC).isoformat() + "Z")
    response = requests.post(url, json=data)
    return response.json()


# 主函数
def main():
    # WiFi 摄像头的 URL（RTSP 或 HTTP）
    camera_url = "rtsp://username:password@your-camera-ip:554/stream"  # 替换为实际的摄像头 URL

    # 检测间隔时间（秒）
    interval = 3

    # 获取硬件 ID
    hardware_id = get_hardware_id()
    print(f"硬件 ID: {hardware_id}")

    try:
        while True:
            # 捕获图像
            print("正在从摄像头捕获图像...")
            image = capture_image_from_camera(camera_url)

            # 保存图像到本地
            image_path = "captured_image.png"
            cv2.imwrite(image_path, image)
            print(f"图像已保存到: {image_path}")

            # 分析图像中的人数
            print("正在分析图像中的人数...")
            detected_count = analyze_image(image_path)
            print(f"检测到的人数: {detected_count}")

            # 上传结果到服务器
            print("正在上传检测结果到服务器...")
            result = upload_result(hardware_id, detected_count)
            print("上传成功，服务器响应:", result)

            # 等待 3 秒
            print(f"等待 {interval} 秒后继续...")
            time.sleep(interval)

    except KeyboardInterrupt:
        print("程序已手动停止")
    except Exception as e:
        print(f"程序运行出错: {e}")


if __name__ == '__main__':
    main()
