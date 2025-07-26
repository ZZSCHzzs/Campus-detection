# 节点端文档

## 概述

节点端是基于ESP32-CAM开发板的智能摄像头节点，集成了图像采集、环境数据监测和Web服务功能。节点通过WiFi网络与检测端通信，支持Push模式数据上传和本地Web访问。

## 硬件平台

- **主控芯片**：ESP32-CAM
- **摄像头**：OV2640 200万像素摄像头
- **环境传感器**：DHT22温湿度传感器（GPIO 13）
- **网络连接**：WiFi 802.11 b/g/n
- **供电方式**：5V USB供电或外部电源

## 核心功能

### 1. 图像采集

- **分辨率支持**：
  - PSRAM可用时：SVGA (800x600)
  - PSRAM不可用时：VGA (640x480)
- **图像格式**：JPEG压缩格式
- **采集间隔**：5秒定时采集
- **图像质量**：
  - PSRAM可用：质量级别12（高质量）
  - PSRAM不可用：质量级别15（标准质量）

### 2. 环境数据采集

- **传感器类型**：DHT22温湿度传感器
- **数据类型**：温度（°C）、湿度（%）
- **采集频率**：与图像同步采集
- **数据验证**：自动检测传感器读取失败
- **数据格式**：JSON格式输出

### 3. 网络通信

- **WiFi连接**：智能连接管理
  - 自动连接配置的WiFi网络
  - 断线自动重连（10秒检查间隔）
  - 连接超时保护（30秒）
  - 重试机制（最多5次，失败后等待30秒）
- **数据传输**：HTTP POST multipart/form-data格式
- **传输内容**：图像文件 + 温度数据 + 湿度数据
- **超时处理**：15秒传输超时保护

### 4. Web服务功能

节点提供本地Web服务器（端口81），支持以下端点：

#### 主页面 (`/`)
- 实时显示摄像头画面
- 显示当前温湿度数据
- 提供友好的Web界面
- 支持中文显示

#### 视频流 (`/stream`)
- 实时MJPEG视频流
- 支持多客户端同时访问
- 自动帧率控制

#### 环境数据API (`/environment`)
- 返回JSON格式的环境数据
- 支持CORS跨域访问
- 包含时间戳信息
- 错误状态处理

```json
// 成功响应示例
{
  "status": "success",
  "data": {
    "temperature": 25.60,
    "humidity": 65.30,
    "timestamp": 123456789
  }
}

// 错误响应示例
{
  "status": "error",
  "message": "Sensor read failed",
  "timestamp": 123456789
}
```

### 5. 工作模式

#### Push模式（当前实现）
- 节点主动定时采集图像和环境数据
- 自动上传到检测端服务器
- 5秒间隔持续监控
- 适用于实时监控场景
- 包含完整的环境数据

#### Pull模式（通过Web API实现）
- 检测端可通过HTTP请求获取数据
- 支持按需获取环境数据
- 适用于节能或按需检测场景

## 技术特性

### 硬件配置

```cpp
// 摄像头引脚定义（ESP32-CAM标准配置）
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// 温湿度传感器配置
#define DHT_PIN 13
DHT dht(DHT_PIN, DHT22);
```

### 网络配置

```cpp
// WiFi连接配置
const char* ssid = "smart";
const char* password = "smart123";
const char* serverUrl = "http://smarthit.top:5000/api/push_frame/2";
```

### 图像参数

```cpp
// 根据PSRAM可用性自动调整
if (psramFound()) {
    config.frame_size = FRAMESIZE_SVGA;  // 800x600
    config.jpeg_quality = 12;            // 高质量
    config.fb_count = 2;                 // 双缓冲
} else {
    config.frame_size = FRAMESIZE_VGA;   // 640x480
    config.jpeg_quality = 15;            // 标准质量
    config.fb_count = 1;                 // 单缓冲
}
```

## 与检测端协作

### Push模式协作
1. 节点定时采集图像和环境数据
2. 通过HTTP POST multipart格式上传到检测端
3. 上传内容包括：
   - 图像文件（JPEG格式）
   - 温度数据（浮点数）
   - 湿度数据（浮点数）
4. 检测端接收数据进行人数检测和环境分析
5. 检测结果存储到数据库

### Web API协作
1. 检测端可通过HTTP GET请求获取实时数据
2. 支持获取环境数据JSON
3. 支持获取实时视频流
4. 适合监控面板和数据分析

## 部署配置

### 1. 硬件连接
- ESP32-CAM开发板
- DHT22温湿度传感器连接到GPIO 13
- USB转串口模块（用于烧录）
- 5V电源适配器
- WiFi网络环境

### 2. 软件配置
```cpp
// 修改网络配置
const char* ssid = "你的WiFi名称";
const char* password = "你的WiFi密码";
const char* serverUrl = "http://检测端IP:5000/api/push_frame/节点ID";

// 调整采集间隔（毫秒）
const unsigned long captureInterval = 5000; // 5秒
```

### 3. 网络部署
- 确保节点与检测端网络连通
- 配置防火墙允许通信端口
- 测试图像传输和Web访问功能
- 验证环境数据采集正常

### 4. 访问方式
```bash
# Web界面访问
http://节点IP地址:81/

# 环境数据API
http://节点IP地址:81/environment

# 视频流
http://节点IP地址:81/stream
```

## 数据上传格式

### HTTP POST请求格式
```
POST /api/push_frame/2 HTTP/1.1
Host: smarthit.top:5000
Content-Type: multipart/form-data; boundary=ESP32CAMBoundary
Content-Length: [总长度]

--ESP32CAMBoundary
Content-Disposition: form-data; name="image"; filename="esp32cam.jpg"
Content-Type: image/jpeg

[JPEG图像数据]
--ESP32CAMBoundary
Content-Disposition: form-data; name="temperature"

25.60
--ESP32CAMBoundary
Content-Disposition: form-data; name="humidity"

65.30
--ESP32CAMBoundary--
```

## 错误处理机制

### WiFi连接错误
- 连接超时自动重试
- 最多重试5次后等待30秒
- 连接状态实时监控
- 断线自动重连

### 传感器错误
- DHT22读取失败检测
- NaN值过滤
- 传感器故障时跳过上传

### 摄像头错误
- 图像捕获失败检测
- 内存分配失败处理
- 帧缓冲区管理

### 网络传输错误
- HTTP请求超时处理
- 服务器响应状态检查
- 内存泄漏防护

## 性能特点

- **多功能集成**：图像采集 + 环境监测 + Web服务
- **稳定性强**：完善的错误处理和自动恢复机制
- **实时性好**：5秒采集间隔，满足实时监控需求
- **易于访问**：提供Web界面和API接口
- **数据完整**：同时上传图像和环境数据
- **成本低廉**：基于成熟的ESP32平台
- **部署简单**：即插即用，自动连接管理

## 监控和调试

### 串口输出信息
- WiFi连接状态
- 图像采集结果
- 数据上传状态
- 环境数据读取
- Web服务器状态
- 错误信息详情

### Web界面监控
- 实时视频预览
- 当前环境数据显示
- 系统状态指示

## 总结

节点端作为系统的数据采集前端，基于ESP32-CAM平台实现了图像采集、环境数据监测和Web服务的完整功能。通过DHT22传感器集成，提供了温湿度环境监测能力。支持Push模式主动上传和Web API被动查询两种工作方式，可根据应用场景灵活使用。完善的错误处理机制和自动重连功能确保了系统的稳定性和可靠性。