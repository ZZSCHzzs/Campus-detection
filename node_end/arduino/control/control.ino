#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>

const char* ssid = "smarthit";
const char* password = "smart123";

Servo myServo;
const int servoPin = 14;
int currentAngle = 90;

WebServer server(80);

// 板载 LED 设置（ESP32-CAM 一般是 GPIO 33）
const int ledPin = 33;
unsigned long lastBlink = 0;
bool ledState = LOW;
bool rotating = false;
bool ledOverride = false;

// 新增：自动回正相关
unsigned long autoReturnAt = 0;              // 0 表示未调度
const unsigned long autoReturnDelay = 3000;  // 3s 后回正

void setup() {
  Serial.begin(115200);

  // 舵机初始化
  myServo.attach(servoPin);
  myServo.write(currentAngle);
  delay(1000);

  // LED 初始化
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);

  // Wi-Fi 连接
  WiFi.begin(ssid, password);
  Serial.print("正在连接WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("WiFi连接成功!");
  Serial.print("IP地址: ");
  Serial.println(WiFi.localIP());

  // Web server 路由
  server.on("/", handleRoot);
  server.on("/rotate", handleRotate);
  server.on("/status", handleStatus);
  server.onNotFound(handleNotFound);

  server.begin();
  Serial.println("HTTP服务器已启动");
}

void loop() {
  server.handleClient();

  // 新增：到期自动回正到 90°
  if (autoReturnAt && millis() >= autoReturnAt && currentAngle != 90 && !rotating) {
    rotating = true;
    myServo.write(90);
    int rotateTime = abs(currentAngle - 90) * 15 / 6; // 与原估算一致
    currentAngle = 90;
    delay(rotateTime);
    rotating = false;
    autoReturnAt = 0; // 清除调度
  }

  updateLed();
}

void updateLed() {
  // 旋转中 LED 常亮
  if (rotating) {
    digitalWrite(ledPin, HIGH);
    return;
  }

  // 收到指令快速闪两下
  static unsigned long flashStart = 0;
  static int flashCount = 0;
  if (ledOverride) {
    if (millis() - flashStart >= 150) {
      flashStart = millis();
      ledState = !ledState;
      digitalWrite(ledPin, ledState);
      flashCount++;
      if (flashCount >= 4) { // 两次闪烁（亮灭算一次）
        ledOverride = false;
        flashCount = 0;
      }
    }
    return;
  }

  // 正常慢频闪（500ms）
  if (millis() - lastBlink >= 500) {
    lastBlink = millis();
    ledState = !ledState;
    digitalWrite(ledPin, ledState);
  }
}

void handleRoot() {
  // 保持原有 HTML 不变
  String html = "<!DOCTYPE html>";
  html += "<html><head><meta charset='UTF-8'><title>ESP32-CAM 舵机控制</title></head>";
  html += "<body style='font-family: Arial; text-align: center; margin: 50px;'>";
  html += "<h1>ESP32-CAM SG90舵机控制</h1>";
  html += "<p>当前角度: <span id='angle'>" + String(currentAngle) + "</span>°</p>";
  html += "<div style='margin: 20px;'>";
  html += "<input type='range' id='angleSlider' min='0' max='180' value='" + String(currentAngle) + "' style='width: 300px;'>";
  html += "<br><br>";
  html += "<button onclick='rotateServo()' style='padding: 10px 20px; font-size: 16px;'>旋转到指定角度</button>";
  html += "</div>";
  html += "<div style='margin: 20px;'>";
  html += "<button onclick='setAngle(0)'>0°</button> ";
  html += "<button onclick='setAngle(45)'>45°</button> ";
  html += "<button onclick='setAngle(90)'>90°</button> ";
  html += "<button onclick='setAngle(135)'>135°</button> ";
  html += "<button onclick='setAngle(180)'>180°</button>";
  html += "</div>";
  html += "<script>";
  html += "function rotateServo() {";
  html += "  var angle = document.getElementById('angleSlider').value;";
  html += "  fetch('/rotate?angle=' + angle)";
  html += "    .then(response => response.text())";
  html += "    .then(data => {";
  html += "      document.getElementById('angle').innerText = angle;";
  html += "      console.log(data);";
  html += "    });";
  html += "}";
  html += "function setAngle(angle) {";
  html += "  document.getElementById('angleSlider').value = angle;";
  html += "  fetch('/rotate?angle=' + angle)";
  html += "    .then(response => response.text())";
  html += "    .then(data => {";
  html += "      document.getElementById('angle').innerText = angle;";
  html += "      console.log(data);";
  html += "    });";
  html += "}";
  html += "</script>";
  html += "</body></html>";

  server.send(200, "text/html", html);
}

void handleRotate() {
  if (server.hasArg("angle")) {
    int angle = server.arg("angle").toInt();
    if (angle < 0) angle = 0;
    if (angle > 180) angle = 180;

    // 收到指令，快速闪两下
    ledOverride = true;

    // 设置旋转状态
    rotating = true;
    myServo.write(angle);
    int rotateTime = abs(currentAngle - angle) * 15 / 6; // 粗略估算旋转时间
    currentAngle = angle;

    Serial.println("舵机旋转到: " + String(angle) + "°");

    // 延迟模拟旋转过程（阻塞式）
    delay(rotateTime);
    rotating = false; // 旋转结束，LED 恢复慢闪

    // 新增：调度 3 秒后回正到 90°
    autoReturnAt = millis() + autoReturnDelay;

    String response = "{\"status\":\"success\",\"angle\":" + String(angle) + "}";
    server.send(200, "application/json", response);
  } else {
    String response = "{\"status\":\"error\",\"message\":\"缺少angle参数\"}";
    server.send(400, "application/json", response);
  }
}

void handleStatus() {
  String response = "{\"current_angle\":" + String(currentAngle) + ",\"wifi_status\":\"connected\",\"ip\":\"" + WiFi.localIP().toString() + "\"}";
  server.send(200, "application/json", response);
}

void handleNotFound() {
  String message = "页面未找到\n\n";
  message += "URI: ";
  message += server.uri();
  message += "\nMethod: ";
  message += (server.method() == HTTP_GET) ? "GET" : "POST";
  message += "\nArguments: ";
  message += server.args();
  message += "\n";
  for (uint8_t i = 0; i < server.args(); i++) {
    message += " " + server.argName(i) + ": " + server.arg(i) + "\n";
  }
  server.send(404, "text/plain", message);
}
