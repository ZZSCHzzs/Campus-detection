# 检测端到服务端的同步机制

## 概述

本文档详细说明了检测端（detecting_end）与服务端（back_end）之间的日志和配置数据同步机制。确保前端能够实时获取检测端的状态、配置和日志信息。

## 同步架构

```
检测端 (WebSocket Client) <---> 服务端 (WebSocket Consumer) <---> 前端 (HTTP API)
     |                                    |                           |
     |                                    |                           |
  本地数据                              Redis缓存                    API请求
- 配置文件                              - 配置数据                   - 获取配置
- 日志记录                              - 日志数据                   - 获取日志
- 系统状态                              - 状态数据                   - 获取状态
```

## 同步流程

### 1. 连接建立阶段

当检测端连接到服务端时：

1. **检测端连接**: 检测端通过WebSocket连接到服务端
2. **身份识别**: 服务端通过检测端发送的特定消息类型识别其为检测端
3. **主动请求**: 服务端向检测端发送以下命令：
   - `get_status`: 请求系统状态
   - `get_config`: 请求配置信息
   - `get_logs`: 请求日志数据

### 2. 数据同步阶段

#### 配置同步

**检测端响应配置请求**:
```python
# detecting_end/src/main.py - handle_ws_command()
elif command == "get_config":
    config_data = copy.deepcopy(config_manager.get_all())
    config_data = make_json_serializable(config_data)
    await ws_client.send_command_response(command, config_data, success=True)
```

**服务端处理配置响应**:
```python
# back_end/webapi/consumers.py - handle_command_response()
if command == 'get_config' and success and result:
    cache_key = f"terminal:{self.terminal_id}:config"
    cache.set(cache_key, result, timeout=300)  # 5分钟过期
    await self.update_terminal_config_from_response(self.terminal_id, result)
```

#### 日志同步

**检测端响应日志请求**:
```python
# detecting_end/src/main.py - handle_ws_command()
elif command == "get_logs":
    count = params.get("count", 100)
    logs_data = log_manager.get_logs(count)
    await ws_client.send_command_response(command, logs_data, success=True)
```

**服务端处理日志响应**:
```python
# back_end/webapi/consumers.py - handle_command_response()
elif command == 'get_logs' and success and result:
    cache_key = f"terminal:{self.terminal_id}:logs"
    cache.set(cache_key, result, timeout=1800)  # 30分钟过期
```

### 3. 持续同步阶段

#### 实时日志同步
检测端在产生新日志时，通过WebSocket实时发送：
```python
# detecting_end/src/logger_manager.py
def log(self, level, message, source=None):
    # ... 记录到本地
    if self.ws_client and self.ws_client.is_connected():
        self._send_log_to_websocket(level, message, source)
```

#### 状态变更同步
检测端定期发送系统状态更新：
```python
# detecting_end/src/system_monitor.py
def _send_ws_status_update(self):
    status_data = self.get_status()
    loop.run_until_complete(self.ws_client.send_system_status(status_data))
```

## 前端数据获取

前端通过HTTP API获取同步后的数据：

### 配置数据
```typescript
// front_end/src/services/ResourceServiceDefinitions.ts
getTerminalConfig(id: number): Promise<any> {
  return this.http.get(`/terminals/${id}/config/`)
}
```

### 日志数据
```typescript
getTerminalLogs(id: number, params?: any): Promise<any> {
  return this.http.get(`/terminals/${id}/logs/`, { params })
}
```

### 状态数据
```typescript
getTerminalStatus(id: number): Promise<any> {
  return this.http.get(`/terminals/${id}/status/`)
}
```

## 缓存策略

| 数据类型 | 缓存键 | 过期时间 | 更新机制 |
|---------|--------|----------|----------|
| 配置数据 | `terminal:{id}:config` | 5分钟 | 命令响应更新 |
| 日志数据 | `terminal:{id}:logs` | 30分钟 | 实时更新+批量同步 |
| 状态数据 | `terminal:{id}:status` | 1分钟 | 实时更新 |

## 错误处理

### 连接断开处理
1. 检测端断开时，服务端标记终端离线
2. 重连时自动触发数据同步
3. 缓存数据在一定时间内仍可用

### 同步失败处理
1. 命令响应超时处理
2. 数据格式验证
3. 降级到本地缓存或数据库数据

## 测试验证

### 同步功能测试
运行测试脚本验证同步机制：
```bash
python test_sync.py          # 测试WebSocket同步
python test_frontend_sync.py # 测试前端API获取
```

### 监控指标
- WebSocket连接状态
- 缓存命中率
- 数据同步延迟
- API响应时间

## 配置参数

### 检测端配置
```json
{
  "terminal_id": 1,
  "server_url": "wss://smarthit.top",
  "websocket_timeout": 30,
  "reconnect_attempts": 10
}
```

### 服务端配置
```python
# 缓存超时设置
CONFIG_CACHE_TIMEOUT = 300    # 5分钟
LOGS_CACHE_TIMEOUT = 1800     # 30分钟
STATUS_CACHE_TIMEOUT = 60     # 1分钟

# WebSocket设置
HEARTBEAT_INTERVAL = 30       # 心跳间隔
COMMAND_TIMEOUT = 10          # 命令超时
```

## 故障排查

### 常见问题

1. **配置未同步**
   - 检查WebSocket连接状态
   - 验证get_config命令是否发送和响应
   - 查看Redis缓存是否更新

2. **日志缺失**
   - 检查检测端日志管理器配置
   - 验证WebSocket日志发送功能
   - 查看服务端日志处理逻辑

3. **数据延迟**
   - 检查网络连接质量
   - 调整缓存过期时间
   - 优化数据传输频率

### 调试工具

1. **WebSocket调试**: 使用浏览器开发者工具监控WebSocket消息
2. **缓存检查**: 使用Redis客户端查看缓存数据
3. **日志分析**: 查看Django和检测端的详细日志

## 性能优化

1. **批量传输**: 合并多条日志为批次传输
2. **数据压缩**: 对大量数据进行压缩传输
3. **缓存预热**: 在连接建立后主动拉取关键数据
4. **增量同步**: 只传输变更的配置和新增的日志

## 安全考虑

1. **认证验证**: WebSocket连接需要验证终端身份
2. **数据加密**: 敏感配置数据应加密传输
3. **访问控制**: 限制前端用户对日志和配置的访问权限
4. **审计记录**: 记录所有配置变更和敏感操作 