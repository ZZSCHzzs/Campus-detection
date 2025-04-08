# 后端文档

## 业务逻辑说明
本系统围绕以下逻辑进行实现：
1. 用户管理：通过自定义用户模型(CustomUser)，实现注册及角色分配；
2. 硬件节点与终端：HardwareNode 绑定到 ProcessTerminal，并由终端集中管理多个节点；
3. 建筑与区域：Building 下包含若干 Area，Area 可绑定硬件节点以记录检测数据；
4. 数据上传与历史数据：上传人流量信息后，自动更新对应节点的检测数，并在 HistoricalData 中保存记录。

## 接口文档

### 接口基础信息
- 基础URL: `http://smarthit.top/api`
- 数据格式: 所有接口均返回JSON格式数据
- 认证方式: Bearer Token (JWT)(开发阶段未启用认证)

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
- **说明**: access token用于验证请求，refresh token用于刷新access token

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
- **响应示例**:
  ```json
  {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
  ```

#### 验证令牌
- **URL**: `/auth/jwt/verify/`
- **方法**: `POST`
- **描述**: 验证JWT令牌的有效性
- **请求参数**:
  ```json
  {
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }
  ```
- **响应**: 
  - 如果令牌有效，返回HTTP 200，无响应内容
  - 如果令牌无效，返回HTTP 401

#### 获取当前用户信息
- **URL**: `/auth/users/me/`
- **方法**: `GET`
- **描述**: 获取当前已登录用户的详细信息
- **请求头**: 需要包含有效的JWT令牌
  ```
  Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
  ```
- **响应示例**:
  ```json
  {
    "id": 1,
    "username": "user1",
    "email": "user1@example.com",
    "role": "user",
    "phone": "13800138000",
    "register_time": "2023-10-11T08:00:00Z",
    "favorite_areas": [1, 3, 5]
  }
  ```

#### 修改用户信息
- **URL**: `/auth/users/me/`
- **方法**: `PUT`, `PATCH`
- **描述**: 更新当前已登录用户的信息
- **请求头**: 需要包含有效的JWT令牌
- **请求参数(PATCH示例)**:
  ```json
  {
    "email": "newemail@example.com",
    "phone": "13900139000"
  }
  ```
- **响应**: 返回更新后的用户信息

### 如何调用ViewSet提供的接口

使用DRF ViewSet时，接口调用主要区分为两种方式：

1. 集合访问（不带索引）：直接访问如 `/api/users` 时，
   - **GET**: 获取所有资源（列表）。
   - **POST**: 创建新资源。
   这些方法针对整个资源集合操作，不需要指定具体索引。

2. 详情访问（带索引）：访问如 `/api/users/1` 时，
   - **GET**: 获取指定资源的详细信息。
   - **PUT/PATCH**: 更新指定资源。
   - **DELETE**: 删除指定资源。
   这些方法需要在URL中指定资源索引，操作对象为具体的单个资源。

对于自定义视图方法，如 `/api/terminals/{id}/nodes`，通常用于获取资源的关联数据，调取方式与上述类似，根据接口设计决定是否需要索引。

### 接口列表

#### 用户接口
- **URL**: `/api/users`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 用户资源管理

#### 硬件节点接口
- **URL**: `/api/nodes`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 硬件节点相关操作

#### 终端接口
- **URL**: `/api/terminals`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 终端管理

#### 建筑接口
- **URL**: `/api/buildings`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 建筑信息管理

#### 区域接口
- **URL**: `/api/areas`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 区域资源管理

#### 历史数据接口
- **URL**: `/api/historical`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 历史数据查看与操作

#### 告警接口
- **URL**: `/api/alerts`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 用于告警记录的增删改查
- **示例**:
  - **GET**: 获取所有告警列表
  - **POST**: 创建新的告警记录

#### 公告接口
- **URL**: `/api/notice`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 管理系统公告，支持查询及编辑

#### 数据上传接口
- **URL**: `/api/upload`
- **方法**: `POST`
- **描述**: 上传检测结果并自动存储历史记录
- **请求参数**:
  ```json
  {
    "id": 1,
    "detected_count": 15,
    "timestamp": "2023-10-11T08:00:00Z"
  }
  ```
- **响应示例**:
  ```json
  {
    "message": "检测结果上传成功"
  }
  ```

### 自定义视图方法

#### 获取终端关联的节点
- **URL**: `/api/terminals/{id}/nodes`
- **方法**: `GET`
- **描述**: 获取指定终端下绑定的所有硬件节点

#### 获取建筑的区域
- **URL**: `/api/buildings/{id}/areas`
- **方法**: `GET`
- **描述**: 获取指定建筑下的所有区域

#### 获取区域的节点数据
- **URL**: `/api/areas/{id}/data`
- **方法**: `GET`
- **描述**: 获取区域绑定的节点信息

#### 获取热门区域
- **URL**: `/api/areas/popular`
- **方法**: `GET`
- **描述**: 获取人流量最多的区域列表
- **查询参数**: `count` - 返回的区域数量，默认为5

#### 获取区域历史数据
- **URL**: `/api/areas/{id}/historical`
- **方法**: `GET`
- **描述**: 获取指定区域的历史人流量数据

#### 收藏/取消收藏区域
- **URL**: `/api/areas/{id}/favor`
- **方法**: `POST`
- **描述**: 用户收藏或取消收藏指定区域
- **响应示例**:
  ```json
  {
    "detail": "区域已收藏"
  }
  ```
  或
  ```json
  {
    "detail": "区域已取消收藏"
  }
  ```
- **说明**: 需要用户登录后才能使用此功能

#### 获取最新历史数据
- **URL**: `/api/historical/latest`
- **方法**: `GET`
- **描述**: 获取最新的历史数据记录
- **查询参数**: `count` - 返回的记录数量，默认为5

#### 获取未解决的告警
- **URL**: `/api/alerts/unsolved`
- **方法**: `GET`
- **描述**: 获取所有未解决的告警信息，按时间降序排列

#### 解决告警
- **URL**: `/api/alerts/{id}/solve`
- **方法**: `POST`
- **描述**: 将指定告警标记为已解决
- **响应示例**:
  ```json
  {
    "detail": "Alert marked as solved."
  }
  ```

#### 获取公开告警
- **URL**: `/api/alerts/public`
- **方法**: `GET`
- **描述**: 获取所有公开且未解决的告警信息，按时间降序排列

#### 获取最新公告
- **URL**: `/api/notice/latest`
- **方法**: `GET`
- **描述**: 获取最新的系统公告
- **查询参数**: `count` - 返回的公告数量，默认为5

#### 获取公告相关区域
- **URL**: `/api/notice/{id}/areas`
- **方法**: `GET`
- **描述**: 获取与指定公告相关的所有区域

#### 系统概览
- **URL**: `/api/summary`
- **方法**: `GET`
- **描述**: 获取系统整体统计信息，包括节点数量、终端数量、建筑数量、区域数量、历史数据记录数量及当前总人数
- **响应示例**:
  ```json
  {
    "nodes_count": 12,
    "terminals_count": 5,
    "buildings_count": 3,
    "areas_count": 20,
    "historical_data_count": 1560,
    "people_count": 523
  }
  ```

## 数据模型说明
本项目后端主要使用Django模型定义数据结构，各模型间通过外键关系进行关联：
- **CustomUser**：继承自`AbstractUser`
  - 核心字段：`username`, `role`, `phone`, `email`, `register_time`, `favorite_areas`
  - 关联接口：`/api/users`
  - 说明：用户表，用于存储登录相关信息，自定义了`groups`和`user_permissions`，支持收藏区域功能
- **HardwareNode**：硬件节点
  - 核心字段：`name`, `detected_count`, `terminal`, `status`, `updated_at`, `description`
  - 关联接口：`/api/nodes`
  - 说明：表示摄像头端点，与`ProcessTerminal`外键关联
- **ProcessTerminal**：终端模型
  - 核心字段：`name`, `status`
  - 关联接口：`/api/terminals`
  - 说明：表示数据处理终端（树莓派）
- **Building**：建筑模型
  - 核心字段：`name`, `description`
  - 关联接口：`/api/buildings`
  - 说明：记录建筑物相关信息，可用于关联区域`Area`
- **Area**：区域模型
  - 核心字段：`name`, `bound_node`, `description`, `type`, `floor`
  - 关联接口：`/api/areas`
  - 说明：用于描述建筑下的具体区域，`bound_node`与硬件节点`HardwareNode`关联， `type`和建筑`Building`关联
- **HistoricalData**：历史数据模型
  - 核心字段：`area`, `detected_count`, `timestamp`
  - 关联接口：`/api/historical` (数据上传通过`/api/upload`)
  - 说明：记录监测到的历史数据，配合区域信息使用
- **Alert**：告警模型
  - 核心字段：`area`, `alert_type`, `grade`, `publicity`, `message`, `timestamp`, `solved`
  - 关联接口：`/api/alerts`
  - 说明：用于记录系统告警信息，可设置公开性，支持标记解决状态
- **Notice**：公告模型
  - 核心字段：`title`, `content`, `timestamp`, `related_areas`
  - 关联接口：`/api/notice`
  - 说明：用于发布系统公告，可关联到特定区域

