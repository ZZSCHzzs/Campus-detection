#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

//引脚定义
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

//网络配置
const char* ssid = "WiFi名称";
const char* password = "WiFi密码";
const char* serverUrl = "http://树莓派IP:5000/upload";

//全局变量
bool cameraInitialized = false;
unsigned long lastCaptureTime = 0;
const unsigned long captureInterval = 5000; // 5秒间隔

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);

  //WiFi连接
  connectToWiFi();

  //摄像头初始化
  if (!initCamera()) {
    Serial.println("摄像头初始化失败，系统停止");
    while (1) delay(1000);
  }
  cameraInitialized = true;
}

void loop() {
  //维持网络连接
  if (WiFi.status() != WL_CONNECTED) {
    connectToWiFi();
    return;
  }

  //定时捕获和传输
  if (millis() - lastCaptureTime >= captureInterval && cameraInitialized) {
    captureAndSendImage();
    lastCaptureTime = millis();
  }
}

//功能函数
void connectToWiFi() {
  Serial.println("正在连接WiFi...");
  WiFi.disconnect(true);
  WiFi.begin(ssid, password);

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 10) {
    delay(500);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi连接成功");
    Serial.print("IP地址: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi连接失败");
  }
}

bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 15;
    config.fb_count = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("摄像头初始化失败: 0x%x\n", err);
    return false;
  }
  return true;
}

void captureAndSendImage() {
  // 获取图像帧
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb || fb->len == 0) {
    Serial.println("图像捕获失败");
    if (fb) esp_camera_fb_return(fb);
    return;
  }

  // 创建HTTP客户端
  WiFiClient client;
  HTTPClient http;
  
  if (http.begin(client, serverUrl)) {
    http.addHeader("Content-Type", "image/jpeg");
    http.setTimeout(10000); // 10秒超时
    
    Serial.println("正在上传图片...");
    int httpCode = http.POST(fb->buf, fb->len);
    
    if (httpCode > 0) {
      Serial.printf("上传成功，状态码: %d\n", httpCode);
      if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();
        Serial.println("服务器响应: " + payload);
      }
    } else {
      Serial.printf("上传失败，错误: %s\n", http.errorToString(httpCode).c_str());
    }
    
    http.end();
  } else {
    Serial.println("HTTP连接初始化失败");
  }

  // 释放图像缓冲区
  esp_camera_fb_return(fb);
}
