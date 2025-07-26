# 节点端文档

## 概述

节点端是基于ESP32-CAM开发板的智能摄像头节点，负责图像采集和数据传输。节点通过WiFi网络与检测端通信，支持多种工作模式。

## 硬件平台

- **主控芯片**：ESP32-CAM
- **摄像头**：OV2640 200万像素摄像头
- **网络连接**：WiFi 802.11 b/g/n
- **供电方式**：5V USB供电或外部电源

## 核心功能

### 1. 图像采集

- **分辨率支持**：
  - PSRAM可用时：SVGA (800x600)
  - PSRAM不可用时：VGA (640x480)
- **图像格式**：JPEG压缩格式
- **采集间隔**：可配置（默认5秒）
- **图像质量**：可调节（12-15级别）

### 2. 网络通信

- **WiFi连接**：自动连接配置的WiFi网络
- **断线重连**：网络断开时自动重连
- **数据传输**：HTTP POST方式上传图像数据
- **超时处理**：10秒传输超时保护

### 3. 工作模式

#### Push模式（推送模式）
- 节点主动定时采集图像
- 自动上传到检测端服务器
- 适用于实时监控场景
- 当前代码实现的默认模式

#### Pull模式（拉取模式）
- 节点等待检测端请求
- 按需提供图像数据
- 适用于节能或按需检测场景
- 需要配合检测端实现

### 4. 环境数据采集（扩展功能）

虽然当前代码主要实现摄像头功能，但ESP32-CAM平台支持扩展：

- **温湿度传感器**：可连接DHT22、SHT30等传感器
- **环境监测**：温度、湿度、光照等环境参数
- **数据同步**：与图像数据一同上传

## 技术特性

### 硬件配置

```cpp
// 摄像头引脚定义（ESP32-CAM标准配置）
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
// ... 其他引脚配置
```

### 网络配置

```cpp
// WiFi连接配置
const char* ssid = "WiFi名称";
const char* password = "WiFi密码";
const char* serverUrl = "http://检测端IP:5000/upload";
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
1. 节点定时采集图像
2. 通过HTTP POST上传到检测端
3. 检测端接收图像进行人数检测
4. 检测结果存储到数据库

### Pull模式协作
1. 检测端主动请求图像
2. 节点响应请求并提供图像
3. 支持按需检测，节省带宽
4. 适合低功耗应用场景

## 部署配置

### 1. 硬件准备
- ESP32-CAM开发板
- USB转串口模块（用于烧录）
- 5V电源适配器
- WiFi网络环境

### 2. 软件配置
- 修改WiFi连接信息
- 配置检测端服务器地址
- 调整采集间隔和图像质量
- 编译上传到ESP32-CAM

### 3. 网络部署
- 确保节点与检测端网络连通
- 配置防火墙允许通信端口
- 测试图像传输功能

## 扩展功能

### 温湿度传感器集成
```cpp
// 可扩展的传感器接口
#include "DHT.h"
#define DHT_PIN 2
#define DHT_TYPE DHT22

// 在数据上传时包含环境数据
void uploadImageWithEnvironmentData() {
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();
    // 与图像一同上传
}
```

### 多传感器支持
- 光照传感器
- 运动检测传感器
- 声音传感器
- CO2传感器

## 性能特点

- **低功耗**：ESP32深度睡眠模式支持
- **稳定性**：自动重连和错误恢复机制
- **实时性**：5秒采集间隔，满足实时监控需求
- **可扩展**：支持多种传感器和通信协议
- **成本低**：基于成熟的ESP32平台，成本控制良好

## 总结

节点端作为系统的数据采集前端，通过ESP32-CAM平台实现了图像采集和网络传输功能。支持Push/Pull两种工作模式，可根据应用场景灵活配置。未来可扩展温湿度等环境传感器，构建完整的智能监控节点。
        