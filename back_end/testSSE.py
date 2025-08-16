import requests
import json

URL = "http://127.0.0.1:8000/api/llm/chat/"
payload = {"message": "树莓派现在什么状态", "history": []}
headers = {"Content-Type": "application/json"}

with requests.post(URL, json=payload, headers=headers, stream=True) as response:
    response.encoding = 'utf-8'  # 强制使用 UTF-8 解码
    print("开始接收SSE消息...")
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue  # 跳过空行
        if line.startswith("data: "):
            decoded = line[len("data: "):]  # 去掉 "data: " 前缀
        else:
            decoded = line
        try:
            data = json.loads(decoded)
        except json.JSONDecodeError:
            data = decoded

        if data == "[DONE]":
            print("\n消息结束")
            break
        else:
            # 将模型输出追加在一行上
            print(data)
