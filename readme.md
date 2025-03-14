# 校园检测系统

## 目录
- [项目概述](#项目概述)
- [后端文档](#后端文档)
  - [接口文档](#接口文档)
  - [数据模型说明](#数据模型说明)
- [前端文档（待完善）](#前端文档)
- [其他](#其他)

## 项目概述
本项目为校园检测系统，提供了一系列API接口用于前端与后端的数据交互。

## 后端文档

### 接口文档

#### 接口基础信息
- 基础URL: `http://smarthit.top/api`
- 数据格式: 所有接口均返回JSON格式数据
- 认证方式: Bearer Token (JWT)(开发阶段未启用认证)

#### 通用响应格式
```json
{
  "code": 200,       // 状态码，200表示成功
  "message": "操作成功", // 状态描述
  "data": {}         // 返回的数据
}
```

#### 错误码说明
| 错误码 | 说明 |
|-------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权或token过期 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

#### 如何调用ViewSet提供的接口

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

#### 接口列表

##### 用户接口
- **URL**: `/api/users`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 用户资源管理

##### 硬件节点接口
- **URL**: `/api/nodes`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 硬件节点相关操作

##### 终端接口
- **URL**: `/api/terminals`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 终端管理

##### 建筑接口
- **URL**: `/api/buildings`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 建筑信息管理

##### 区域接口
- **URL**: `/api/areas`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 区域资源管理

##### 历史数据接口
- **URL**: `/api/historical`
- **Methods**: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`
- **描述**: 历史数据查看与操作

##### 数据上传接口
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

### 数据模型说明
本项目后端主要使用Django模型定义数据结构，各模型间通过外键关系进行关联：
- **CustomUser**：继承自`AbstractUser`
  - 核心字段：`username`, `role`, `phone`, `email`, `register_time`
  - 关联接口：`/api/users`
  - 说明：用户表，用于存储登录相关信息，自定义了`groups`和`user_permissions`
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

## 前端文档（待完善）
...existing code...

## 其他
...existing code...

## 开发环境
- 后端框架: Django REST_FRAMEWORK
- 数据库: MySQL 8.0
- 认证: JWT

## 安全说明
接口需要在请求头中携带token
