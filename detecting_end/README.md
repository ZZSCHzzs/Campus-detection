1. 系统概述

本系统实现基于计算机视觉的多摄像头人数实时检测方案，主要功能包括：
    
    支持主动/被动两种检测模式

    多摄像头并发管理

    YOLOv8深度学习模型推理

    检测结果云端同步

    RESTful API服务
2. 技术架构
graph TD
A[摄像头] -->|RTSP/HTTP| B{检测系统}
B --> C[YOLOv8模型]
C --> D[结果处理]
D -->|HTTP POST| E[云端服务器]
E --> F[数据分析平台]
B -->|API| G[外部系统]

3. 快速入门
环境要求

    Python 3.8+

    RAM ≥ 2GB

    存储空间 ≥ 500MB
安装步骤
sudo apt update && sudo apt install -y libjpeg-dev

# 安装Python依赖
pip install -r requirements.txt

# 目录结构
.
├── config/               # 配置文件
├── models/               # 模型文件
├── logs/                 # 运行日志
└── main.py               # 主程序
4. 配置说明
核心配置文件 (config/settings.py)
# 摄像头配置
CAMERAS = {
    "gate": "rtsp://admin:password@192.168.1.100:554/Streaming/Channels/1",
    "lobby": "rtsp://admin:password@192.168.1.101:554/Streaming/Channels/1"
}

# 运行参数
SETTINGS = {
    "MODE": "pull",        # pull/push
    "INTERVAL": 1,         # 检测间隔(秒)
    "API_ENDPOINT": "http://api.example.com/v1/detections"
}
环境变量
# 设置硬件ID
export HARDWARE_ID="device_001"

# 设置调试模式
export DEBUG_MODE="true"
5. API文档
被动接收接口

Endpoint
POST /api/push_frame/<camera_id>
请求格式
Content-Type: multipart/form-data
参数说明
参数	        类型	       必填	          说明
camera_id	string	    是	     预配置的摄像头ID
file	    file	    是	     JPEG格式图像文件
响应示例
{
    "status": "success",
    "camera_id": "gate",
    "count": 5,
    "timestamp": "2024-03-15T08:30:00Z"
}
6. 运行模式说明
主动拉取模式 (Pull)

    特点

        系统主动获取摄像头画面

        默认1秒检测间隔

        需要持续摄像头连接

    启动命令
    python main.py --mode pull
被动接收模式 (Push)

    特点

        摄像头主动推送画面

        按需唤醒检测系统

        支持分布式部署

    启动命令
    python main.py --mode push --port 5001
7. 性能参数
指标	规格
最大摄像头数量	8路
单帧处理时间	≤300ms (RPi4)
网络延迟要求	≤100ms
内存占用	常驻500MB，峰值1.2GB
推荐硬件配置	四核CPU/4GB RAM
8. 维护与监控
系统监控
# 实时资源监控
watch -n 1 "free -m && top -bn1 | grep 'PID' -A10"

# 网络连接检查
netstat -ant | grep ':5000'
日志管理
# 日志配置示例
import logging
logging.basicConfig(
    filename='logs/system.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
故障恢复策略
自动重启机制
# 使用systemd服务
[Unit]
Description=People Detection Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/detection/main.py
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
