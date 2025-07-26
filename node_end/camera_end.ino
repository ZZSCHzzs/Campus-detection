#include "esp_camera.h"   
#include <WiFi.h>   
#include <HTTPClient.h>   
#include <WiFiClientSecure.h>   
#include "esp_http_server.h"   
#include "esp_timer.h"   
#include "DHT.h"   
     
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
    

#define DHT_PIN 13
DHT dht(DHT_PIN, DHT22); 
    

const char* ssid = "smart";   
const char* password = "smart123";   
const char* serverUrl = "http://smarthit.top:5000/api/push_frame/2"; 
    

bool cameraInitialized = false;   
unsigned long lastCaptureTime = 0;   
const unsigned long captureInterval = 5000; 
httpd_handle_t camera_httpd = NULL;   
    

unsigned long lastWiFiCheck = 0;   
const unsigned long wifiCheckInterval = 10000; 
bool wifiConnecting = false;   
unsigned long wifiConnectStartTime = 0;   
const unsigned long wifiConnectTimeout = 30000;  
int wifiRetryCount = 0;   
const int maxWifiRetries = 5;   
    

const char* STREAM_CONTENT =    
    "<html><head>"   
    "<meta charset=\"UTF-8\">" 
    "<title>ESP32-CAM Stream</title>"   
    "<style>"   
    "body { font-family: Arial, sans-serif; margin: 20px; background-color: #f0f0f0; }"   
    "h1 { color: #333; text-align: center; }"   
    "h2, h3 { color: #666; }"   
    "img { border: 2px solid #ddd; border-radius: 8px; display: block; margin: 20px auto; }"   
    "p { font-size: 18px; margin: 10px 0; }"   
    "a { color: #007bff; text-decoration: none; }"   
    "a:hover { text-decoration: underline; }"   
    "</style>"   
    "</head>"   
    "<body>"   
    "<h1>ESP32-CAM 摄像头监控</h1>"   
    "<img src=\"/stream\" style=\"width:640px; height:480px;\">"   
    "<br>"   
    "<h2>实时环境数据:</h2>"   
    "<p>温度: %s °C</p>"   
    "<p>湿度: %s %%</p>"   
    "<br>"   
    "<h3>API接口:</h3>"   
    "<p><a href=\"/environment\" target=\"_blank\">/environment - 获取环境数据JSON</a></p>"   
    "</body></html>";   
    

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
    

static esp_err_t index_handler(httpd_req_t *req) {   
    float temperature = dht.readTemperature();   
    float humidity = dht.readHumidity();   
  
    char tempStr[10];   
    char humStr[10];   
    snprintf(tempStr, sizeof(tempStr), "%.2f", isnan(temperature) ? 0.0 : temperature);   
    snprintf(humStr, sizeof(humStr), "%.2f", isnan(humidity) ? 0.0 : humidity);   

    char response[2048];
    snprintf(response, sizeof(response), STREAM_CONTENT, tempStr, humStr);   
        
    httpd_resp_set_type(req, "text/html; charset=utf-8");   
    httpd_resp_set_hdr(req, "Cache-Control", "no-cache");   
    return httpd_resp_send(req, response, strlen(response));   
}   
    
static esp_err_t stream_handler(httpd_req_t *req) {   
    camera_fb_t *fb = NULL;   
    esp_err_t res = ESP_OK;   
    size_t _jpg_buf_len = 0;   
    uint8_t *_jpg_buf = NULL;   
    char *part_buf[64];   

    static int64_t last_frame = 0;   
    if (!last_frame) {   
        last_frame = esp_timer_get_time();   
    }   

    res = httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=123456789000000000000987654321");   
    if (res != ESP_OK) {   
        return res;   
    }   

    while (true) {   
        fb = esp_camera_fb_get();   
        if (!fb) {   
            Serial.println("获取图像失败");   
            res = ESP_FAIL;   
        } else {   
            if (fb->format != PIXFORMAT_JPEG) {   
                res = ESP_FAIL;   
            } else {   
                _jpg_buf_len = fb->len;   
                _jpg_buf = fb->buf;   
            }   
        }   

        if (res == ESP_OK) {   
            size_t hlen = snprintf((char *)part_buf, 64,   
                "Content-Type: image/jpeg\r\n"   
                "Content-Length: %u\r\n\r\n",   
                _jpg_buf_len);   

            res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);   
            if (res == ESP_OK) {   
                res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);   
            }   
            if (res == ESP_OK) {   
                res = httpd_resp_send_chunk(req, "\r\n--123456789000000000000987654321\r\n", 37);   
            }   
        }   
            
        if (fb) {   
            esp_camera_fb_return(fb);   
            fb = NULL;   
            _jpg_buf = NULL;   
        }   
            
        if (res != ESP_OK) {   
            break;   
        }   
    }   
    return res;   
}

static esp_err_t environment_handler(httpd_req_t *req) { 
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

void startCameraServer() { 
    httpd_config_t config = HTTPD_DEFAULT_CONFIG(); 
    config.server_port = 81; 

    httpd_uri_t index_uri = { 
        .uri       = "/", 
        .method    = HTTP_GET, 
        .handler   = index_handler, 
        .user_ctx  = NULL 
    }; 

    httpd_uri_t stream_uri = { 
        .uri       = "/stream", 
        .method    = HTTP_GET, 
        .handler   = stream_handler, 
        .user_ctx  = NULL 
    }; 
    
    httpd_uri_t environment_uri = { 
        .uri       = "/environment", 
        .method    = HTTP_GET, 
        .handler   = environment_handler, 
        .user_ctx  = NULL 
    }; 

    if (httpd_start(&camera_httpd, &config) == ESP_OK) { 
        httpd_register_uri_handler(camera_httpd, &index_uri); 
        httpd_register_uri_handler(camera_httpd, &stream_uri); 
        httpd_register_uri_handler(camera_httpd, &environment_uri); // 注册新端点 
        Serial.println("Web服务器启动成功"); 
        Serial.println("可用端点:"); 
        Serial.println("  / - 主页面"); 
        Serial.println("  /stream - 视频流"); 
        Serial.println("  /environment - 环境数据JSON"); 
    } 
} 

// 改进的WiFi连接函数 
void connectToWiFi() { 
    if (wifiConnecting) { 
        // 检查连接超时 
        if (millis() - wifiConnectStartTime > wifiConnectTimeout) { 
            Serial.println("WiFi连接超时"); 
            WiFi.disconnect(); 
            wifiConnecting = false; 
            wifiRetryCount++; 
            
            if (wifiRetryCount >= maxWifiRetries) { 
                Serial.println("WiFi重试次数过多，等待更长时间后重试"); 
                delay(30000); // 等待30秒 
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

// 检查并维护WiFi连接 
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
    // 确保WiFi已连接 
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

    // 获取温湿度数据 
    float temperature = dht.readTemperature(); 
    float humidity = dht.readHumidity(); 
    
    // 检查温湿度读取是否有效 
    if (isnan(temperature) || isnan(humidity)) { 
        Serial.println("温湿度读取失败"); 
        esp_camera_fb_return(fb); 
        return; 
    } 

    WiFiClient client; 
    HTTPClient http; 
     
    if (http.begin(client, serverUrl)) { 
        String boundary = "ESP32CAMBoundary"; 
        String head = "--" + boundary + "\r\n"; 
        head += "Content-Disposition: form-data; name=\"image\"; filename=\"esp32cam.jpg\"\r\n"; 
        head += "Content-Type: image/jpeg\r\n\r\n"; 
        
        String middle1 = "\r\n--" + boundary + "\r\n"; 
        middle1 += "Content-Disposition: form-data; name=\"temperature\"\r\n\r\n"; 
        middle1 += String(temperature, 2); 
        
        String middle2 = "\r\n--" + boundary + "\r\n"; 
        middle2 += "Content-Disposition: form-data; name=\"humidity\"\r\n\r\n"; 
        middle2 += String(humidity, 2); 
        
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
        memcpy(buf, head.c_str(), head.length()); 
        pos += head.length(); 
        memcpy(buf + pos, fb->buf, fb->len); 
        pos += fb->len; 
        memcpy(buf + pos, middle1.c_str(), middle1.length()); 
        pos += middle1.length(); 
        memcpy(buf + pos, middle2.c_str(), middle2.length()); 
        pos += middle2.length(); 
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

void setup() { 
    Serial.begin(115200); 
    Serial.setDebugOutput(true); 
     
    WiFi.onEvent(WiFiEvent); 
     
    WiFi.mode(WIFI_STA); 
    WiFi.setAutoReconnect(true); 
    WiFi.persistent(true); 
     
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
        Serial.println("  /environment - 环境数据JSON"); 
    } else { 
        Serial.println("[WiFi未连接]"); 
    } 
} 

void loop() { 
    maintainWiFiConnection(); 
     
    if (WiFi.status() == WL_CONNECTED &&  
        millis() - lastCaptureTime >= captureInterval &&  
        cameraInitialized) { 
        captureAndSendImage(); 
        lastCaptureTime = millis(); 
    } 
     
    delay(100); 
}