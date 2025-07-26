# 后端文档

## 项目概述
本项目是基于Django REST Framework开发的智慧校园人员检测系统后端，提供完整的API服务支持前端应用和检测终端的数据交互。系统采用微服务架构，支持实时数据处理、WebSocket通信、环境监测等功能。

## 技术栈
- **框架**: Django 5.1.6 + Django REST Framework
- **数据库**: MySQL (生产环境) / SQLite (开发环境)
- **缓存**: Redis
- **消息队列**: Celery + Redis
- **实时通信**: Django Channels + WebSocket
- **认证**: JWT (Simple JWT)
- **权限管理**: 自定义权限系统

## 业务逻辑说明
本系统围绕以下核心逻辑进行实现：

1. **用户管理**: 通过自定义用户模型(CustomUser)，实现用户注册、角色分配和权限控制
2. **硬件节点与终端**: HardwareNode 绑定到 ProcessTerminal，终端集中管理多个检测节点
3. **建筑与区域**: Building 下包含若干 Area，Area 绑定硬件节点记录检测数据
4. **数据采集**: 支持人流量、温湿度、CO2浓度等多维度环境数据采集
5. **实时通信**: 通过WebSocket实现终端状态监控和命令下发
6. **告警系统**: 支持多级别告警和公开性控制
7. **缓存优化**: 使用Redis缓存热点数据，提升系统性能

## 接口文档

### 接口基础信息
- **基础URL**: `http://smarthit.top/api`
- **数据格式**: 所有接口均返回JSON格式数据
- **认证方式**: Bearer Token (JWT)
- **跨域支持**: 已配置CORS，支持跨域请求

### 通用响应格式
```json
{
  "code": 200,       
  "message": "操作成功", 
  "data": {}         
}
```

### 错误码说明
| 错误码 | 说明 |
|-------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权或token过期 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

### 用户认证接口

#### 用户注册
- **URL**: `/auth/users/`
- **方法**: `POST`
- **描述**: 创建新用户账号
- **请求参数**:
  ```json
  {
    "username": "user1",
    "password": "securepassword",
    "email": "user1@example.com",
    "role": "user",
    "phone": "13800138000"
  }
  ```
- **响应示例**:
  ```json
  {
    "id": 1,
    "username": "user1",
    "email": "user1@example.com",
    "role": "user",
    "phone": "13800138000"
  }
  ```

#### 用户登录
- **URL**: `/auth/jwt/create/`
- **方法**: `POST`
- **描述**: 通过用户名密码获取JWT令牌
- **请求参数**:
  ```json
  {
    "username": "user1",
    "password": "securepassword"
  }
  ```
- **响应示例**:
  ```json
  {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
  ```

#### 刷新令牌
- **URL**: `/auth/jwt/refresh/`
- **方法**: `POST`
- **描述**: 使用refresh token获取新的access token
- **请求参数**:
  ```json
  {
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
  ```

#### 获取当前用户信息
- **URL**: `/auth/users/me/`
- **方法**: `GET`
- **描述**: 获取当前已登录用户的详细信息
- **请求头**: 需要包含有效的JWT令牌
  ```
  Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
  ```

### 核心资源接口

#### 用户管理接口
- **URL**: `/api/users/`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 用户资源管理，支持角色权限控制
- **特殊方法**:
  - `GET /api/users/me/`: 获取当前用户信息

#### 硬件节点接口
- **URL**: `/api/nodes/`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 硬件节点管理，包含检测数据和环境数据
- **数据字段**: `name`, `detected_count`, `terminal`, `status`, `temperature`, `humidity`

#### 终端管理接口
- **URL**: `/api/terminals/`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 检测终端管理，支持状态监控和配置管理
- **特殊方法**:
  - `GET /api/terminals/{id}/nodes/`: 获取终端关联的节点
  - `GET /api/terminals/{id}/status/`: 获取终端实时状态
  - `GET /api/terminals/{id}/logs/`: 获取终端日志
  - `GET|POST /api/terminals/{id}/config/`: 获取或更新终端配置
  - `GET /api/terminals/{id}/co2_data/`: 获取CO2数据
  - `POST /api/terminals/{id}/command/`: 发送命令到终端

#### 建筑管理接口
- **URL**: `/api/buildings/`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 建筑信息管理
- **特殊方法**:
  - `GET /api/buildings/{id}/areas/`: 获取建筑的区域
  - `GET /api/buildings/{id}/areas_paginated/`: 分页获取建筑区域
  - `GET /api/buildings/list_basic/`: 获取建筑基本信息

#### 区域管理接口
- **URL**: `/api/areas/`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 区域资源管理，支持收藏功能
- **特殊方法**:
  - `GET /api/areas/{id}/data/`: 获取区域节点数据
  - `GET /api/areas/popular/`: 获取热门区域
  - `GET /api/areas/{id}/historical/`: 获取区域历史数据
  - `GET /api/areas/{id}/temperature_humidity/`: 获取区域温湿度数据
  - `POST /api/areas/{id}/favor/`: 收藏/取消收藏区域

#### 历史数据接口
- **URL**: `/api/historical/`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 人流量历史数据管理
- **特殊方法**:
  - `GET /api/historical/latest/`: 获取最新历史数据

#### 环境数据接口

##### 温湿度数据
- **URL**: `/api/temperature-humidity/`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **特殊方法**:
  - `GET /api/temperature-humidity/latest/`: 获取最新温湿度数据
  - `GET /api/temperature-humidity/by_area/`: 按区域获取温湿度数据

##### CO2数据
- **URL**: `/api/co2/`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **特殊方法**:
  - `GET /api/co2/latest/`: 获取最新CO2数据
  - `GET /api/co2/by_terminal/`: 按终端获取CO2数据

#### 告警管理接口
- **URL**: `/api/alerts/`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 告警记录管理，支持多级别告警
- **特殊方法**:
  - `GET /api/alerts/unsolved/`: 获取未解决的告警
  - `POST /api/alerts/{id}/solve/`: 解决告警
  - `GET /api/alerts/public/`: 获取公开告警

#### 公告管理接口
- **URL**: `/api/notice/`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 系统公告管理
- **特殊方法**:
  - `GET /api/notice/latest/`: 获取最新公告
  - `GET /api/notice/{id}/areas/`: 获取公告相关区域

### 数据上传接口

#### 检测数据上传
- **URL**: `/api/upload/`
- **方法**: `POST`
- **描述**: 上传人流量检测结果
- **请求参数**:
  ```json
  {
    "id": 1,
    "detected_count": 15,
    "timestamp": "2023-10-11T08:00:00Z",
    "temperature": 25.5,
    "humidity": 60.2
  }
  ```

#### 温湿度数据上传
- **URL**: `/api/upload/temperature-humidity/`
- **方法**: `POST`
- **描述**: 上传温湿度数据
- **请求参数**:
  ```json
  {
    "area_id": 1,
    "temperature": 25.5,
    "humidity": 60.2,
    "timestamp": "2023-10-11T08:00:00Z"
  }
  ```

#### CO2数据上传
- **URL**: `/api/upload/co2/`
- **方法**: `POST`
- **描述**: 上传CO2浓度数据
- **请求参数**:
  ```json
  {
    "terminal_id": 1,
    "co2_level": 450,
    "timestamp": "2023-10-11T08:00:00Z"
  }
  ```

### 系统接口

#### 系统概览
- **URL**: `/api/summary/`
- **方法**: `GET`
- **描述**: 获取系统整体统计信息
- **响应示例**:
  ```json
  {
    "nodes_count": 12,
    "terminals_count": 5,
    "buildings_count": 3,
    "areas_count": 20,
    "historical_data_count": 1560,
    "people_count": 523,
    "notice_count": 8,
    "alerts_count": 15,
    "users_count": 25,
    "nodes_online_count": 10,
    "terminals_online_count": 4
  }
  ```

#### 环境信息
- **URL**: `/api/environment/`
- **方法**: `GET`
- **描述**: 获取系统环境信息
- **响应示例**:
  ```json
  {
    "type": "server",
    "version": "2.0.0",
    "name": "服务端",
    "id": 0,
    "features": {
      "local_detection": false,
      "websocket": true,
      "push_mode": false,
      "pull_mode": false
    }
  }
  ```

#### 终端命令控制
- **URL**: `/api/terminals/{id}/command/`
- **功能**: 向指定终端发送控制命令
- **请求参数**:
  ```json
  {
    "command": "start_push",  // 命令类型
    "params": {              // 可选参数
      "interval": 5,         // 检测间隔(秒)
      "mode": "realtime"     // 工作模式
    }
  }
  ```
- **支持的命令**:
  - `start_push`: 启动推送模式
  - `stop_push`: 停止推送模式
  - `start_pull`: 启动拉取模式
  - `stop_pull`: 停止拉取模式
  - `get_status`: 获取终端状态
  - `update_config`: 更新终端配置
  - `restart`: 重启终端服务
- **处理流程**:
  1. 验证命令参数合法性
  2. 通过WebSocket Channel Layer发送命令
  3. 更新终端状态记录
  4. 刷新Redis缓存
  5. 返回命令执行结果

## 数据模型说明

### 核心模型

#### CustomUser (用户模型)
- **继承**: `AbstractUser`
- **核心字段**:
  - `username`: 用户名
  - `role`: 角色 (user/staff/admin)
  - `phone`: 电话号码
  - `email`: 邮箱
  - `register_time`: 注册时间
  - `favorite_areas`: 收藏区域 (多对多关系)
- **权限控制**: 根据角色自动设置 `is_staff` 和 `is_superuser`

#### HardwareNode (硬件节点)
- **核心字段**:
  - `name`: 节点名称
  - `detected_count`: 检测人数
  - `terminal`: 关联终端 (外键)
  - `status`: 在线状态
  - `updated_at`: 更新时间
  - `temperature`: 温度
  - `humidity`: 湿度
  - `description`: 描述

#### ProcessTerminal (处理终端)
- **核心字段**:
  - `name`: 终端名称
  - `status`: 在线状态
  - `last_active`: 最后活跃时间
  - `cpu_usage`: CPU使用率
  - `memory_usage`: 内存使用率
  - `disk_usage`: 磁盘使用率
  - `co2_level`: CO2浓度
  - `co2_status`: CO2传感器状态
  - `model_loaded`: 模型加载状态
  - `push_running`: 推送服务状态
  - `pull_running`: 拉取服务状态
  - `mode`: 工作模式 (pull/push/both)
  - `interval`: 检测间隔
  - `nodes`: 节点状态数据 (JSON)
  - `node_config`: 节点配置 (JSON)

#### Building (建筑)
- **核心字段**:
  - `name`: 建筑名称
  - `description`: 描述

#### Area (区域)
- **核心字段**:
  - `name`: 区域名称
  - `bound_node`: 绑定节点 (外键)
  - `type`: 所属建筑 (外键)
  - `floor`: 楼层
  - `capacity`: 容量
  - `description`: 描述

### 数据记录模型

#### HistoricalData (历史数据)
- **核心字段**:
  - `area`: 关联区域
  - `detected_count`: 检测人数
  - `timestamp`: 检测时间

#### TemperatureHumidityData (温湿度数据)
- **核心字段**:
  - `area`: 关联区域
  - `temperature`: 温度
  - `humidity`: 湿度
  - `timestamp`: 记录时间

#### CO2Data (CO2数据)
- **核心字段**:
  - `terminal`: 关联终端
  - `co2_level`: CO2浓度
  - `timestamp`: 记录时间

#### Alert (告警)
- **核心字段**:
  - `area`: 关联区域
  - `alert_type`: 告警类型 (fire/guard/crowd/health/other)
  - `grade`: 告警等级 (0-3)
  - `publicity`: 是否公开
  - `message`: 告警信息
  - `timestamp`: 告警时间
  - `solved`: 是否已解决

#### Notice (公告)
- **核心字段**:
  - `title`: 公告标题
  - `content`: 公告内容
  - `timestamp`: 发布时间
  - `related_areas`: 相关区域 (多对多关系)
  - `outdated`: 是否过期

## 权限系统

### 权限级别
1. **未认证用户**: 只读权限
2. **普通用户 (user)**: 只读权限
3. **工作人员 (staff)**: 可编辑标记为 `allow_staff_edit=True` 的资源
4. **管理员 (admin)**: 全部权限

### 权限控制实现
- 使用自定义权限类 `StaffEditSelected`
- 在ViewSet中通过 `allow_staff_edit` 属性控制Staff编辑权限
- JWT认证确保接口安全性

## 缓存策略

### Redis缓存应用
1. **终端状态缓存**: 缓存终端实时状态，减少数据库查询
2. **热门区域缓存**: 缓存人流量排行，提升查询性能
3. **系统概览缓存**: 缓存统计数据，减少计算开销
4. **配置缓存**: 缓存终端配置信息

### 缓存更新策略
- 使用Django信号自动清除相关缓存
- 设置合理的过期时间
- 支持手动刷新缓存

## WebSocket支持

### 实时通信功能
1. **终端状态监控**: 实时获取终端运行状态
2. **命令下发**: 向检测终端发送控制命令
3. **日志推送**: 实时推送终端日志信息
4. **数据同步**: 实时同步检测数据

### 使用Django Channels
- 基于Redis作为消息后端
- 支持分组广播
- 异步消息处理

### WebSocket工作逻辑

#### 架构设计

```
检测端 <--WebSocket--> Django后端 <--HTTP API--> 前端客户端
                          ↓
                  Redis Channel Layer
                          ↓
                      MySQL数据库

```


#### 连接管理
1. **连接建立**:
   - 验证终端ID的有效性
   - 将连接加入到对应的Channel Group (`terminal_{id}`)
   - 区分检测端和前端客户端连接类型
   - 启动心跳检查任务
   - 主动请求终端状态、配置和日志信息

2. **连接分类**:
   - **检测端连接**: 发送系统状态、心跳、节点数据、日志等
   - **前端客户端连接**: 接收状态更新、发送控制命令

3. **连接断开**:
   - 清理Channel Group
   - 更新终端离线状态
   - 取消心跳检查任务
   - 清理相关缓存

#### 消息处理机制

1. **状态更新消息** (`system_status`):
   - 接收CPU、内存、磁盘使用率
   - 更新推拉模式运行状态
   - 同步模型加载状态
   - 实时更新数据库和Redis缓存

2. **节点数据消息** (`nodes_data`):
   - 接收硬件节点检测数据
   - 更新节点的人数统计和环境数据
   - 自动创建历史检测记录
   - 广播数据更新到所有客户端

3. **日志消息** (`log`):
   - 接收终端运行日志
   - 缓存到Redis（最多500条，30分钟过期）
   - 实时推送到前端客户端

4. **命令响应** (`command_response`):
   - 处理终端执行命令的结果
   - 特殊处理配置和日志获取响应
   - 广播执行结果到相关客户端

#### 命令控制系统

1. **支持的命令类型**:
   - `get_status`: 获取终端状态
   - `get_config`: 获取终端配置
   - `get_logs`: 获取历史日志
   - `start_push`: 启动推送模式
   - `stop_push`: 停止推送模式
   - `start_pull`: 启动拉取模式
   - `stop_pull`: 停止拉取模式

2. **命令传递流程**:
```
前端发起 → REST API → Channel Layer → WebSocket → 检测端
                                                 ↓
前端接收 ← WebSocket ← Channel Layer ← 命令响应 ← 检测端
```

3. **命令执行**:
- 通过Channel Layer异步发送
- 只向检测端连接发送命令
- 支持命令参数传递
- 记录命令执行日志

#### 心跳机制

1. **客户端心跳**:
- 检测端每30秒发送心跳消息
- 包含时间戳和基本状态信息
- 服务端回复心跳确认

2. **服务端检查**:
- 每60秒检查连接活跃状态
- 超过2分钟无活动自动断开
- 更新终端在线状态

3. **超时处理**:
- WebSocket连接超时断开
- 数据库状态标记为离线
- 清理相关缓存数据

#### 缓存策略

1. **状态缓存**:
- 终端状态缓存60秒
- 连接状态缓存300秒
- 配置数据缓存300秒

2. **日志缓存**:
- 最多保存500条日志
- 缓存时间1800秒（30分钟）
- 按时间倒序存储

3. **数据同步**:
- 实时更新数据库
- 异步更新缓存
- 确保数据一致性

#### 错误处理

1. **连接异常**:
- 自动重连机制
- 指数退避重连策略
- 连接状态监控

2. **消息异常**:
- JSON解析错误处理
- 消息类型验证
- 异常日志记录

3. **数据库异常**:
- 事务回滚保护
- 数据完整性检查
- 错误恢复机制

#### 性能优化

1. **连接管理**:
- 连接池复用
- 异步消息处理
- 内存使用优化

2. **数据传输**:
- 消息压缩
- 批量数据处理
- 增量数据同步

3. **缓存优化**:
- Redis集群支持
- 缓存预热
- 过期策略优化

## 部署配置

### 环境要求
- Python 3.8+
- Django 5.1.6
- MySQL 8.0+
- Redis 6.0+

### 关键配置
1. **数据库**: MySQL配置，支持utf8mb4字符集
2. **缓存**: Redis缓存配置
3. **CORS**: 跨域请求支持
4. **JWT**: 令牌认证配置
5. **Channels**: WebSocket支持配置
6. **Celery**: 异步任务配置

### 安全配置
- HTTPS支持
- CSRF保护
- 安全头配置
- 环境变量管理

## API调用说明

### ViewSet接口调用规则

1. **集合操作** (不带ID):
   - `GET /api/resource/`: 获取资源列表
   - `POST /api/resource/`: 创建新资源

2. **详情操作** (带ID):
   - `GET /api/resource/{id}/`: 获取指定资源
   - `PUT /api/resource/{id}/`: 完整更新资源
   - `PATCH /api/resource/{id}/`: 部分更新资源
   - `DELETE /api/resource/{id}/`: 删除资源

3. **自定义操作**:
   - `@action` 装饰器定义的特殊方法
   - 支持 `detail=True/False` 控制是否需要ID

### 认证头格式

Authorization: JWT <access_token>


### 分页参数
- `page`: 页码
- `page_size`: 每页大小
- `count`: 返回数量限制

## 开发指南

### 添加新接口
1. 在 `models.py` 中定义数据模型
2. 在 `serializers.py` 中创建序列化器
3. 在 `views.py` 中实现ViewSet
4. 在 `urls.py` 中注册路由
5. 更新权限配置

### 缓存使用
```python
from django.core.cache import cache

# 设置缓存
cache.set(key, value, timeout=300)

# 获取缓存
data = cache.get(key)

# 删除缓存
cache.delete(key)
```

### WebSocket消息发送
```python
from channels.layers import 
get_channel_layer
from asgiref.sync import async_to_sync

channel_layer = get_channel_layer()
async_to_sync(channel_layer.group_send)(
    "terminal_1",
    {
        "type": "send_command",
        "command": "start",
        "params": {}
    }
)
```

## 更新日志

### v2.0.0 (当前版本)
- 新增温湿度数据模型和接口
- 新增CO2数据监测功能
- 增强终端管理功能
- 优化缓存策略
- 完善权限控制
- 新增WebSocket实时通信
- 增加环境信息接口
- 优化数据上传接口
- 完善告警系统
- 新增分页功能
