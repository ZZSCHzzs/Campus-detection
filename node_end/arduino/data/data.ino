#include "esp_camera.h"
#include "esp_http_server.h"
#include "esp_timer.h"
#include "img_converters.h"
#include "fb_gfx.h"
#include "esp32-hal-ledc.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include "DHT.h"
#include "index.h"  // 包含从示例程序复制的 gzip 压缩 HTML

// =================== ESP32-CAM AI-THINKER 引脚定义 ===================
// 直接定义 AI-THINKER 的引脚，去掉多版本支持
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

#define LED_GPIO_NUM       4  // 闪光灯

// =================== DHT 配置 ===================
#define DHT_PIN 13
DHT dht(DHT_PIN, DHT22);

// =================== LED 控制配置 ===================
#define LED_FLASH_PIN 4   // 白光闪光灯
#define LED_STATUS_PIN 33 // 状态灯

// 摄像头视频流状态，仅影响LED4
volatile bool streamActive = false;

// LED4（闪光灯）单次脉冲窗口：在截帧时点亮约120ms
unsigned long led4PulseUntil = 0;

// LED33（状态灯）事件闪烁：按次数与间隔控制
bool led33Override = false;
unsigned long led33FlashStart = 0;
int led33FlashCount = 0;
int led33FlashTargetToggles = 0;
unsigned long led33FlashInterval = 140;
bool led33State = LOW;
// 新增：LED33 开机常亮保持与慢闪节拍
unsigned long led33InitHoldUntil = 0;   // 开机常亮截止时间
unsigned long led33LastBlink = 0;       // 慢速频闪节拍


// =================== 网络配置 ===================
const char* ssid = "smarthit";
const char* password = "smart123";
const char* serverUrl = "http://192.168.1.100:5000/api/push_frame/2";


// =================== HTTP 服务器配置 ===================
httpd_handle_t camera_httpd = NULL;
httpd_handle_t stream_httpd = NULL;

// =================== 定时上传配置 ===================
bool cameraInitialized = false;
unsigned long lastCaptureTime = 0;
const unsigned long captureInterval = 5000;

// =================== WiFi 连接管理 ===================
unsigned long lastWiFiCheck = 0;
const unsigned long wifiCheckInterval = 10000;
bool wifiConnecting = false;
unsigned long wifiConnectStartTime = 0;
const unsigned long wifiConnectTimeout = 30000;
int wifiRetryCount = 0;
const int maxWifiRetries = 5;

// =================== LED 滤波器 ===================
#define CONFIG_LED_MAX_INTENSITY 255
int led_duty = 0;
bool isStreaming = false;

// =================== 摄像头配置 ===================
// 可以根据需求修改这些默认值
struct CameraDefaults {
  // 硬件配置
  framesize_t initial_framesize = FRAMESIZE_QVGA;    // 初始分辨率：QVGA(320x240)
  framesize_t psram_framesize = FRAMESIZE_SVGA;      // PSRAM可用时分辨率：UXGA(1600x1200)
  framesize_t noram_framesize = FRAMESIZE_SVGA;      // 无PSRAM时分辨率：SVGA(800x600)
  
  // 质量设置
  int jpeg_quality_psram = 10;                       // PSRAM时JPEG质量(0-63, 越小越好)
  int jpeg_quality_normal = 12;                      // 普通时JPEG质量
  
  // 帧缓冲设置
  int fb_count_psram = 2;                           // PSRAM时帧缓冲数量(双缓冲)
  int fb_count_normal = 1;                          // 普通时帧缓冲数量
  
  // 时钟频率
  uint32_t xclk_freq_hz = 20000000;                 // 20MHz时钟频率
  
  // OV2640优化设置
  int brightness = 0;                               // 亮度 (-2 到 2)
  int contrast = 0;                                 // 对比度 (-2 到 2)
  int saturation = 0;                              // 饱和度 (-2 到 2)
  bool vflip = true;                                // 垂直翻转
  bool hmirror = false;                             // 水平镜像
  
  // 自动控制
  bool awb = true;                                  // 自动白平衡
  bool aec = true;                                  // 自动曝光控制
  bool agc = true;                                  // 自动增益控制
};

// 全局默认配置实例 - 你可以在这里修改默认值
CameraDefaults cameraDefaults;

// =================== 流媒体常量 ===================
#define PART_BOUNDARY "123456789000000000000987654321"
static const char *_STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char *_STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char *_STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\nX-Timestamp: %d.%06d\r\n\r\n";

// =================== LED 控制函数 ===================
void ledSetup() {
  pinMode(LED_FLASH_PIN, OUTPUT);
  pinMode(LED_STATUS_PIN, OUTPUT);
  digitalWrite(LED_FLASH_PIN, LOW);   // 默认熄灭
  
  // LED33 开机常亮
  digitalWrite(LED_STATUS_PIN, HIGH);
  led33State = HIGH;
  led33InitHoldUntil = millis() + 3000; // 开机常亮3秒
  led33LastBlink = millis();
  led33FlashStart = millis();
  
  // 设置闪光灯 PWM
  ledcAttach(LED_GPIO_NUM, 5000, 8);
}

void ledUpdate() {
  unsigned long now = millis();

  // LED4：视频流时常亮；截帧脉冲窗口内亮；其余熄灭
  if (streamActive) {
    digitalWrite(LED_FLASH_PIN, HIGH);
  } else if (led4PulseUntil && now < led4PulseUntil) {
    digitalWrite(LED_FLASH_PIN, HIGH);
  } else {
    digitalWrite(LED_FLASH_PIN, LOW);
  }

  // LED33：事件连闪 > 开机常亮 > 默认慢闪
  if (led33Override) {
    if (now - led33FlashStart >= led33FlashInterval) {
      led33FlashStart = now;
      led33State = !led33State;
      digitalWrite(LED_STATUS_PIN, led33State ? HIGH : LOW);
      led33FlashCount++;
      if (led33FlashCount >= led33FlashTargetToggles) {
        led33Override = false;
        led33FlashCount = 0;
      }
    }
  } else if (now < led33InitHoldUntil) {
    // 开机常亮阶段
    if (!led33State) {
      led33State = HIGH;
      digitalWrite(LED_STATUS_PIN, HIGH);
    }
  } else {
    // 默认慢速频闪
    const unsigned long led33SlowPeriod = 700;
    if (now - led33LastBlink >= led33SlowPeriod) {
      led33LastBlink = now;
      led33State = !led33State;
      digitalWrite(LED_STATUS_PIN, led33State ? HIGH : LOW);
    }
  }
}

void enable_led(bool en) {
  int duty = en ? led_duty : 0;
  if (en && isStreaming && (led_duty > CONFIG_LED_MAX_INTENSITY)) {
    duty = CONFIG_LED_MAX_INTENSITY;
  }
  ledcWrite(LED_GPIO_NUM, duty);
}

// =================== WiFi 事件处理 ===================
void WiFiEvent(WiFiEvent_t event) {
    switch(event) {
        case ARDUINO_EVENT_WIFI_STA_GOT_IP:
            Serial.println("WiFi连接成功");
            Serial.print("IP地址: ");
            Serial.println(WiFi.localIP());
            wifiConnecting = false;
            wifiRetryCount = 0;
            break;
        case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
            Serial.println("WiFi连接断开");
            wifiConnecting = false;
            break;
        case ARDUINO_EVENT_WIFI_STA_CONNECTED:
            Serial.println("WiFi已连接，等待获取IP...");
            break;
        default:
            break;
    }
}

void connectToWiFi() {
    if (wifiConnecting) {
        if (millis() - wifiConnectStartTime > wifiConnectTimeout) {
            Serial.println("WiFi连接超时");
            WiFi.disconnect();
            wifiConnecting = false;
            wifiRetryCount++;
            
            if (wifiRetryCount >= maxWifiRetries) {
                Serial.println("WiFi重试次数过多，等待更长时间后重试");
                delay(30000);
                wifiRetryCount = 0;
            }
        }
        return;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        return;
    }
    
    Serial.println("开始连接WiFi...");
    wifiConnecting = true;
    wifiConnectStartTime = millis();
    
    WiFi.disconnect(true);
    delay(1000);
    WiFi.begin(ssid, password);
}

void maintainWiFiConnection() {
    unsigned long currentTime = millis();
    
    if (currentTime - lastWiFiCheck >= wifiCheckInterval) {
        lastWiFiCheck = currentTime;
        
        if (WiFi.status() != WL_CONNECTED && !wifiConnecting) {
            Serial.println("检测到WiFi断开，尝试重连...");
            connectToWiFi();
        }
    }
    
    if (wifiConnecting) {
        connectToWiFi();
    }
}

// =================== HTTP 端点处理函数 ===================
static esp_err_t index_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html");
  httpd_resp_set_hdr(req, "Content-Encoding", "gzip");
  sensor_t *s = esp_camera_sensor_get();
  if (s != NULL) {
    return httpd_resp_send(req, (const char *)index_ov2640_html_gz, index_ov2640_html_gz_len);
  } else {
    Serial.println("Camera sensor not found");
    return httpd_resp_send_500(req);
  }
}

static esp_err_t capture_handler(httpd_req_t *req) {
  camera_fb_t *fb = NULL;
  esp_err_t res = ESP_OK;
  
  enable_led(true);
  vTaskDelay(150 / portTICK_PERIOD_MS);
  fb = esp_camera_fb_get();
  enable_led(false);

  if (!fb) {
    Serial.println("Camera capture failed");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  char ts[32];
  snprintf(ts, 32, "%lld.%06ld", fb->timestamp.tv_sec, fb->timestamp.tv_usec);
  httpd_resp_set_hdr(req, "X-Timestamp", (const char *)ts);

  // LED4：成功获取帧后，闪一次（短脉冲约120ms）
  led4PulseUntil = millis() + 120;

  if (fb->format == PIXFORMAT_JPEG) {
    res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  } else {
    // 转换为 JPEG 格式
    uint8_t *_jpg_buf = NULL;
    size_t _jpg_buf_len = 0;
    bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
    esp_camera_fb_return(fb);
    fb = NULL;
    if (!jpeg_converted) {
      Serial.println("JPEG compression failed");
      return httpd_resp_send_500(req);
    }
    res = httpd_resp_send(req, (const char *)_jpg_buf, _jpg_buf_len);
    free(_jpg_buf);
  }
  
  if (fb) {
    esp_camera_fb_return(fb);
  }
  
  return res;
}

static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t *fb = NULL;
  struct timeval _timestamp;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t *_jpg_buf = NULL;
  char part_buf[128];

  static int64_t last_frame = 0;
  if (!last_frame) {
    last_frame = esp_timer_get_time();
  }

  res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
  if (res != ESP_OK) {
    return res;
  }

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "X-Framerate", "60");

  // LED4：视频流访问期间常亮
  streamActive = true;
  isStreaming = true;
  enable_led(true);

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      res = ESP_FAIL;
    } else {
      _timestamp.tv_sec = fb->timestamp.tv_sec;
      _timestamp.tv_usec = fb->timestamp.tv_usec;
      if (fb->format != PIXFORMAT_JPEG) {
        bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
        esp_camera_fb_return(fb);
        fb = NULL;
        if (!jpeg_converted) {
          Serial.println("JPEG compression failed");
          res = ESP_FAIL;
        }
      } else {
        _jpg_buf_len = fb->len;
        _jpg_buf = fb->buf;
      }
    }

    if (res == ESP_OK) {
      res = httpd_resp_sendstr_chunk(req, _STREAM_BOUNDARY);
    }
    if (res == ESP_OK) {
      size_t hlen = snprintf((char *)part_buf, 128, _STREAM_PART, _jpg_buf_len, _timestamp.tv_sec, _timestamp.tv_usec);
      res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    }
    if (fb) {
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if (_jpg_buf) {
      free(_jpg_buf);
      _jpg_buf = NULL;
    }
    if (res != ESP_OK) {
      break;
    }
    int64_t fr_end = esp_timer_get_time();
    int64_t frame_time = fr_end - last_frame;
    last_frame = fr_end;
    frame_time /= 1000;
  }

  streamActive = false;
  isStreaming = false;
  enable_led(false);
  
  return res;
}

static esp_err_t parse_get(httpd_req_t *req, char **obuf) {
  char *buf = NULL;
  size_t buf_len = 0;

  buf_len = httpd_req_get_url_query_len(req) + 1;
  if (buf_len > 1) {
    buf = (char *)malloc(buf_len);
    if (!buf) {
      httpd_resp_send_500(req);
      return ESP_FAIL;
    }
    if (httpd_req_get_url_query_str(req, buf, buf_len) == ESP_OK) {
      *obuf = buf;
      return ESP_OK;
    }
    free(buf);
  }
  httpd_resp_send_404(req);
  return ESP_FAIL;
}

static int parse_get_var(char *buf, const char *key, int def) {
  char val[16];
  if (httpd_query_key_value(buf, key, val, sizeof(val)) == ESP_OK) {
    return atoi(val);
  }
  return def;
}

static esp_err_t cmd_handler(httpd_req_t *req) {
  char *buf = NULL;
  char variable[32];
  char value[32];

  if (parse_get(req, &buf) != ESP_OK) {
    return ESP_FAIL;
  }
  if (httpd_query_key_value(buf, "var", variable, sizeof(variable)) != ESP_OK ||
      httpd_query_key_value(buf, "val", value, sizeof(value)) != ESP_OK) {
    free(buf);
    httpd_resp_send_404(req);
    return ESP_FAIL;
  }
  free(buf);

  int val = atoi(value);
  sensor_t *s = esp_camera_sensor_get();
  int res = 0;

  if (!strcmp(variable, "framesize")) {
    if (s->pixformat == PIXFORMAT_JPEG) {
      res = s->set_framesize(s, (framesize_t)val);
    }
  } else if (!strcmp(variable, "quality")) {
    res = s->set_quality(s, val);
  } else if (!strcmp(variable, "contrast")) {
    res = s->set_contrast(s, val);
  } else if (!strcmp(variable, "brightness")) {
    res = s->set_brightness(s, val);
  } else if (!strcmp(variable, "saturation")) {
    res = s->set_saturation(s, val);
  } else if (!strcmp(variable, "gainceiling")) {
    res = s->set_gainceiling(s, (gainceiling_t)val);
  } else if (!strcmp(variable, "colorbar")) {
    res = s->set_colorbar(s, val);
  } else if (!strcmp(variable, "awb")) {
    res = s->set_whitebal(s, val);
  } else if (!strcmp(variable, "agc")) {
    res = s->set_gain_ctrl(s, val);
  } else if (!strcmp(variable, "aec")) {
    res = s->set_exposure_ctrl(s, val);
  } else if (!strcmp(variable, "hmirror")) {
    res = s->set_hmirror(s, val);
  } else if (!strcmp(variable, "vflip")) {
    res = s->set_vflip(s, val);
  } else if (!strcmp(variable, "awb_gain")) {
    res = s->set_awb_gain(s, val);
  } else if (!strcmp(variable, "agc_gain")) {
    res = s->set_agc_gain(s, val);
  } else if (!strcmp(variable, "aec_value")) {
    res = s->set_aec_value(s, val);
  } else if (!strcmp(variable, "aec2")) {
    res = s->set_aec2(s, val);
  } else if (!strcmp(variable, "dcw")) {
    res = s->set_dcw(s, val);
  } else if (!strcmp(variable, "bpc")) {
    res = s->set_bpc(s, val);
  } else if (!strcmp(variable, "wpc")) {
    res = s->set_wpc(s, val);
  } else if (!strcmp(variable, "raw_gma")) {
    res = s->set_raw_gma(s, val);
  } else if (!strcmp(variable, "lenc")) {
    res = s->set_lenc(s, val);
  } else if (!strcmp(variable, "special_effect")) {
    res = s->set_special_effect(s, val);
  } else if (!strcmp(variable, "wb_mode")) {
    res = s->set_wb_mode(s, val);
  } else if (!strcmp(variable, "ae_level")) {
    res = s->set_ae_level(s, val);
  } else if (!strcmp(variable, "led_intensity")) {
    led_duty = val;
    if (isStreaming) {
      enable_led(true);
    }
  } else {
    res = -1;
  }

  if (res < 0) {
    return httpd_resp_send_500(req);
  }

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, NULL, 0);
}

static int print_reg(char *p, sensor_t *s, uint16_t reg, uint32_t mask) {
  return sprintf(p, "\"0x%x\":0x%x,", reg, s->get_reg(s, reg, mask));
}

static esp_err_t status_handler(httpd_req_t *req) {
  // 统一结构：
  // {
  //   "status":"ok",
  //   "device":{ "type":"data","ip":"...","rssi":-55,"uptime_ms":12345,"capabilities":["stream","capture","environment","control"] },
  //   "data":{ ...业务字段... }
  // }
  sensor_t *s = esp_camera_sensor_get();

  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  bool hasEnv = !(isnan(temperature) || isnan(humidity));

  String ip = WiFi.localIP().toString();
  long rssi = WiFi.RSSI();
  unsigned long up = millis();

  // 业务数据：挑选关键字段，避免超长
  String dataJson = "{";
  dataJson += "\"led_intensity\":" + String(led_duty);
  if (hasEnv) {
    dataJson += ",\"temperature\":" + String(temperature, 2);
    dataJson += ",\"humidity\":" + String(humidity, 2);
  }
  if (s != NULL) {
    dataJson += ",\"framesize\":" + String(s->status.framesize);
    dataJson += ",\"quality\":" + String(s->status.quality);
    dataJson += ",\"brightness\":" + String(s->status.brightness);
    dataJson += ",\"contrast\":" + String(s->status.contrast);
    dataJson += ",\"saturation\":" + String(s->status.saturation);
    dataJson += ",\"hmirror\":" + String(s->status.hmirror);
    dataJson += ",\"vflip\":" + String(s->status.vflip);
    dataJson += ",\"pixformat\":" + String((uint8_t)s->pixformat);
  }
  dataJson += "}";

  String json = "{";
  json += "\"status\":\"ok\",";
  json += "\"device\":{";
  json +=   "\"type\":\"data\",";
  json +=   "\"ip\":\"" + ip + "\",";
  json +=   "\"rssi\":" + String(rssi) + ",";
  json +=   "\"uptime_ms\":" + String(up) + ",";
  json +=   "\"capabilities\":[\"stream\",\"capture\",\"environment\",\"control\"]";
  json += "},";
  json += "\"data\":" + dataJson;
  json += "}";

  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, json.c_str(), json.length());
}

static esp_err_t environment_handler(httpd_req_t *req) {
    // LED33：环境数据被访问，连闪两下（4次翻转）
    led33Override = true;
    led33FlashTargetToggles = 4;
    led33FlashInterval = 140;
    led33FlashStart = millis();
    led33FlashCount = 0;

    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();
    
    char jsonResponse[300];
    if (isnan(temperature) || isnan(humidity)) {
        snprintf(jsonResponse, sizeof(jsonResponse),
            "{\"status\":\"error\",\"message\":\"Sensor read failed\",\"timestamp\":%lu}",
            millis());
    } else {
        snprintf(jsonResponse, sizeof(jsonResponse),
            "{\"status\":\"success\",\"data\":{\"temperature\":%.2f,\"humidity\":%.2f,\"timestamp\":%lu}}",
            temperature, humidity, millis());
    }
    
    httpd_resp_set_type(req, "application/json; charset=utf-8");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_set_hdr(req, "Cache-Control", "no-cache");
    
    return httpd_resp_send(req, jsonResponse, strlen(jsonResponse));
}

// =================== 初始化摄像头 ===================
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
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = cameraDefaults.xclk_freq_hz;
    config.frame_size = cameraDefaults.psram_framesize; // 先按高配，后面根据是否有PSRAM调整
    config.pixel_format = PIXFORMAT_JPEG;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.jpeg_quality = cameraDefaults.jpeg_quality_normal;
    config.fb_count = cameraDefaults.fb_count_normal;

    // 根据PSRAM可用性调整
    if (config.pixel_format == PIXFORMAT_JPEG) {
        if (psramFound()) {
            config.jpeg_quality = cameraDefaults.jpeg_quality_psram;
            config.fb_count = cameraDefaults.fb_count_psram;
            config.grab_mode = CAMERA_GRAB_LATEST;
        } else {
            config.frame_size = cameraDefaults.noram_framesize;
            config.fb_location = CAMERA_FB_IN_DRAM;
        }
    }

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("摄像头初始化失败: 0x%x\n", err);
        return false;
    }

    sensor_t *s = esp_camera_sensor_get();
    if (s->id.PID == OV3660_PID) {
        // 对于OV3660的调整
        s->set_vflip(s, cameraDefaults.vflip);
        s->set_brightness(s, cameraDefaults.brightness);
        s->set_saturation(s, cameraDefaults.saturation);
    }

    // 应用通用默认参数
    s->set_framesize(s, cameraDefaults.initial_framesize);
    s->set_brightness(s, cameraDefaults.brightness);
    s->set_contrast(s, cameraDefaults.contrast);
    s->set_saturation(s, cameraDefaults.saturation);
    s->set_vflip(s, cameraDefaults.vflip);
    s->set_hmirror(s, cameraDefaults.hmirror);
    s->set_whitebal(s, cameraDefaults.awb);
    s->set_exposure_ctrl(s, cameraDefaults.aec);
    s->set_gain_ctrl(s, cameraDefaults.agc);

    return true;
}

// =================== 启动 Web 服务器 ===================
void startCameraServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.max_uri_handlers = 16;

    httpd_uri_t index_uri = {
        .uri = "/",
        .method = HTTP_GET,
        .handler = index_handler,
        .user_ctx = NULL
    };

    httpd_uri_t status_uri = {
        .uri = "/status",
        .method = HTTP_GET,
        .handler = status_handler,
        .user_ctx = NULL
    };

    httpd_uri_t cmd_uri = {
        .uri = "/control",
        .method = HTTP_GET,
        .handler = cmd_handler,
        .user_ctx = NULL
    };

    httpd_uri_t capture_uri = {
        .uri = "/capture",
        .method = HTTP_GET,
        .handler = capture_handler,
        .user_ctx = NULL
    };

    httpd_uri_t environment_uri = {
        .uri = "/environment",
        .method = HTTP_GET,
        .handler = environment_handler,
        .user_ctx = NULL
    };

    httpd_uri_t stream_uri = {
        .uri = "/stream",
        .method = HTTP_GET,
        .handler = stream_handler,
        .user_ctx = NULL
    };

    Serial.printf("Starting web server on port: '%d'\n", config.server_port);
    if (httpd_start(&camera_httpd, &config) == ESP_OK) {
        httpd_register_uri_handler(camera_httpd, &index_uri);
        httpd_register_uri_handler(camera_httpd, &cmd_uri);
        httpd_register_uri_handler(camera_httpd, &status_uri);
        httpd_register_uri_handler(camera_httpd, &capture_uri);
        httpd_register_uri_handler(camera_httpd, &environment_uri);
    }

    config.server_port += 1;
    config.ctrl_port += 1;
    Serial.printf("Starting stream server on port: '%d'\n", config.server_port);
    if (httpd_start(&stream_httpd, &config) == ESP_OK) {
        httpd_register_uri_handler(stream_httpd, &stream_uri);
    }
}

// =================== 定时上传功能 ===================
void captureAndSendImage() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi未连接，跳过图像上传");
        return;
    }

    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb || fb->len == 0) {
        Serial.println("图像捕获失败");
        if (fb) esp_camera_fb_return(fb);
        return;
    }

    // LED4：成功获取帧后，闪一次（短脉冲约120ms）
    led4PulseUntil = millis() + 120;

    // 获取温湿度数据（失败时也要上传图像）
    float temperature = dht.readTemperature();
    float humidity = dht.readHumidity();
    bool hasEnv = !(isnan(temperature) || isnan(humidity));
    if (!hasEnv) {
        Serial.println("温湿度读取失败，将仅上传图像");
    }

    WiFiClient client;
    HTTPClient http;
     
    if (http.begin(client, serverUrl)) {
        // LED33：开始上传，连闪三下（6次翻转）
        led33Override = true;
        led33FlashTargetToggles = 6;
        led33FlashInterval = 140;
        led33FlashStart = millis();
        led33FlashCount = 0;

        String boundary = "ESP32CAMBoundary";
        String head = "--" + boundary + "\r\n";
        head += "Content-Disposition: form-data; name=\"image\"; filename=\"esp32cam.jpg\"\r\n";
        head += "Content-Type: image/jpeg\r\n\r\n";
        
        // 根据有无环境数据有条件添加字段
        String middle1;
        String middle2;
        if (hasEnv) {
            middle1 = "\r\n--" + boundary + "\r\n";
            middle1 += "Content-Disposition: form-data; name=\"temperature\"\r\n\r\n";
            middle1 += String(temperature, 2);

            middle2 = "\r\n--" + boundary + "\r\n";
            middle2 += "Content-Disposition: form-data; name=\"humidity\"\r\n\r\n";
            middle2 += String(humidity, 2);
        }
        
        String tail = "\r\n--" + boundary + "--\r\n";

        uint32_t totalLen = head.length() + fb->len + middle1.length() + middle2.length() + tail.length();
         
        http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
        http.addHeader("Content-Length", String(totalLen));
        http.setTimeout(15000);
         
        uint8_t *buf = (uint8_t *)malloc(totalLen);
        if (!buf) {
            Serial.println("内存分配失败");
            esp_camera_fb_return(fb);
            http.end();
            return;
        }

        uint32_t pos = 0;
        memcpy(buf + pos, head.c_str(), head.length());
        pos += head.length();
        memcpy(buf + pos, fb->buf, fb->len);
        pos += fb->len;
        if (middle1.length() > 0) {
            memcpy(buf + pos, middle1.c_str(), middle1.length());
            pos += middle1.length();
        }
        if (middle2.length() > 0) {
            memcpy(buf + pos, middle2.c_str(), middle2.length());
            pos += middle2.length();
        }
        memcpy(buf + pos, tail.c_str(), tail.length());

        int httpCode = http.POST(buf, totalLen);
        free(buf);

        if (httpCode > 0) {
            Serial.printf("数据上传成功，状态码: %d\n", httpCode);
            if (httpCode == HTTP_CODE_OK || httpCode == HTTP_CODE_CREATED) {
                String payload = http.getString();
                Serial.println("服务器响应: " + payload);
            }
        } else {
            Serial.printf("数据上传失败，错误: %s\n", http.errorToString(httpCode).c_str());
        }

        http.end();
    } else {
        Serial.println("HTTP连接初始化失败");
    }

    esp_camera_fb_return(fb);
}

// =================== 主程序 ===================
void setup() {
    Serial.begin(115200);
    Serial.setDebugOutput(true);
    Serial.println();

    // LED 初始化
    ledSetup();
     
    WiFi.onEvent(WiFiEvent);
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.persistent(true);
    WiFi.setSleep(false);
     
    connectToWiFi();
     
    int waitCount = 0;
    while (WiFi.status() != WL_CONNECTED && waitCount < 60) {
        delay(500);
        Serial.print(".");
        waitCount++;
        maintainWiFiConnection();
    }
     
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("\n初始WiFi连接失败，将在后台继续尝试连接");
    }

    if (!initCamera()) {
        Serial.println("摄像头初始化失败，系统停止");
        while (1) delay(1000);
    }
    cameraInitialized = true;

    dht.begin();

    startCameraServer();
    Serial.print("摄像头准备就绪! 使用浏览器访问: http://");
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println(WiFi.localIP());
        Serial.println("可用端点:");
        Serial.println("  / - 主页面");
        Serial.println("  /stream - 视频流");
        Serial.println("  /capture - 截图");
        Serial.println("  /control - 摄像头参数控制");
        Serial.println("  /status - 系统状态");
        Serial.println("  /environment - 环境数据JSON");
    } else {
        Serial.println("[WiFi未连接]");
    }
}

void loop() {
    maintainWiFiConnection();

    // LED：每次循环刷新LED状态
    ledUpdate();
     
    if (WiFi.status() == WL_CONNECTED &&  
        millis() - lastCaptureTime >= captureInterval &&  
        cameraInitialized) {
        captureAndSendImage();
        lastCaptureTime = millis();
    }
     
    delay(100);
}