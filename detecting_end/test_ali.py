import requests
import datetime
url = "https://smarthit.top/api/upload/"
data = {
    "id": 11,
    "detected_count": 40,
    "timestamp": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")  # 标准化时间格式
}
try:
    response = requests.post(url, json=data, timeout=5)
    if response.status_code != 201:
        print(f"上传警告: 状态码 {response.status_code}, 响应: {response.text}")
    print(f"上传结果: {response.status_code}, 响应: {response.json()}")
except Exception as e:
    print(f"上传结果失败: {e}")