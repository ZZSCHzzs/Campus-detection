# 前端开发文档

## 项目概览

校园人员检测系统前端采用Vue 3 + TypeScript构建，使用Element Plus作为UI组件库，集成了Echarts数据可视化和axios进行API请求。项目采用Pinia进行状态管理，Vue Router进行路由导航。

## 项目结构

```
front_end/
├── src/                    # 源代码目录
│   ├── views/              # 页面组件
│   ├── components/         # 可复用组件
│   │   ├── admin/          # 管理面板组件
│   ├── router/             # 路由配置
│   ├── stores/             # Pinia状态管理
│   ├── services/           # API服务
│   │   ├── api.ts                # 基础API配置
│   │   ├── apiService.ts         # 通用API服务
│   │   ├── apiResourceManager.ts # API资源管理器
│   │   └── authApi.ts            # 认证相关API
│   ├── types.ts            # TypeScript类型定义
│   ├── assets/             # 静态资源
│   └── plugins/            # 插件配置
├── public/                 # 公共资源
└── main.ts                 # 程序入口
```

## 路由结构

| 路径 | 组件 | 描述 | 权限要求 |
|------|------|------|----------|
| `/` | HomePage | 首页，系统概览 | 无 |
| `/areas` | AreasView | 区域列表和详情 | 无 |
| `/screen` | DataScreen | 数据大屏可视化 | 无 |
| `/auth` | AuthView | 登录和注册 | 无 |
| `/alerts` | AlertNotice | 告警和通知 | 无 |
| `/profile` | UserView | 用户个人中心 | 需要登录 |
| `/admin` | AdminView | 管理控制面板 | 需要管理员权限 |

## 组件间引用说明

### 路由实现

路由使用Vue Router实现，主要配置在`router/index.ts`中：

```typescript
// 路由配置示例
const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomePage.vue')
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/AdminView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      // 子路由配置
    ]
  }
]
```

路由守卫用于权限控制：

```typescript
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();
  
  // 需要认证的路由检查
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return next('/auth');
  }
  
  // 管理员权限检查
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return next('/');
  }
  
  next();
});
```

### 组件间引用关系

#### 主要视图组件引用结构

```
HomePage.vue
 └── AreaList.vue           


AreasView.vue
 └── Areacard.vue

AlertNotice.vue


DataScreen.vue


UserView.vue
 └── Areacard.vue

AdminView.vue
 ├── UserManager.vue──BaseManager.vue        // 用户管理组件
 ├── AreaManager.vue──BaseManager.vue         // 区域管理组件
 ├── BuildingManager.vue──BaseManager.vue     // 建筑管理组件
 ├── NodeManager.vue──BaseManager.vue         // 硬件节点管理组件
 ├── TerminalManager.vue──BaseManager.vue     // 终端管理组件
 ├── AlertManager.vue──BaseManager.vue        // 告警管理组件
 ├── NoticeManager.vue──BaseManager.vue       // 通知管理组件
 └── HistoricalManager.vue──BaseManager.vue   // 历史数据管理组件
```



#### 工具组件

```
Navbar.vue                
./admin/Jump.vue  //跳转相关
./admin/View.vue  //查看相关
```

## 核心数据类型

### 区域(AreaItem)
```typescript
export interface AreaItem {
  id: number
  name: string
  bound_node: number      // 关联的硬件节点ID
  description?: string
  building: number        // 所属建筑ID
  capacity: number        // 区域容量
  floor: number           // 所属楼层
  status?: boolean        // 区域状态
  current_count?: number  // 当前人数
  updated_at?: string     // 最后更新时间
  is_favorite?: boolean   // 是否收藏
}
```

### 用户(User)
```typescript
export interface User {
  id: number
  username: string
  role: 'user' | 'staff'| 'admin'  // 用户角色
  phone?: string
  email?: string
  register_time?: string  // 注册时间
  favorite_areas?: number[]  // 收藏的区域ID列表
}
```

### 硬件节点(HardwareNode)
```typescript
export interface HardwareNode {
  id: number
  name: string
  detected_count: number  // 检测到的人数
  status: boolean         // 节点状态
  terminal: number        // 关联的终端ID
  updated_at: string
}
```

### 处理终端(ProcessTerminal)
```typescript
export interface ProcessTerminal {
  id: number
  name: string
  status: boolean         // 终端状态
  nodes_count: number     // 关联的硬件节点数量
}
```

### 建筑(Building)
```typescript
export interface Building {
  id: number
  name: string
  description?: string
  areas_count: number     // 区域数量
  areas?: AreaItem[]      // 关联的区域列表
}
```

### 历史数据(HistoricalData)
```typescript
export interface HistoricalData {
  id: number
  area: number            // 关联区域ID
  detected_count: number  // 检测到的人数
  timestamp: string       // 时间戳
}
```

### 告警(Alert)
```typescript
export interface Alert {
  id: number
  area: number            // 关联区域ID
  grade: number           // 告警等级 (0-3)
  alert_type: string      // 告警类型
  publicity: boolean      // 是否公开
  message: string         // 告警信息
  timestamp: string       // 时间戳
  solved: boolean         // 是否已处理
}
```

### 公告(Notice)
```typescript
export interface Notice {
  id: number
  title: string           // 公告标题
  content: string         // 公告内容
  timestamp: string       // 发布时间
  related_areas?: number[] // 相关区域ID列表
}
```

## API服务架构

### API服务分层

1. **api.ts**: 基础Axios实例，处理请求/响应拦截
   - 自动添加JWT认证头
   - 处理401错误和token刷新

2. **apiResourceManager.ts**: 资源管理器
   - 提供资源缓存机制
   - 封装CRUD基础操作

3. **apiService.ts**: 业务API服务
   - 针对各资源类型提供专用服务
   - 封装自定义API调用

4. **authApi.ts**: 认证相关API
   - 处理登录、注册、验证等认证操作

### 资源服务概览

apiService为以下资源提供标准CRUD操作：

| 资源名称 | 描述 | 对应类型 |
|---------|------|---------|
| areas | 区域管理 | AreaItem |
| buildings | 建筑管理 | Building |
| nodes | 硬件节点管理 | HardwareNode |
| terminals | 处理终端管理 | ProcessTerminal |
| users | 用户管理 | User |
| alerts | 告警管理 | Alert |
| notice/notices | 通知管理 | Notice |
| historical | 历史数据管理 | HistoricalData |

每个资源服务都提供以下基础方法：
- `getAll(params?)`: 获取所有资源，支持查询参数
- `getById(id)`: 根据ID获取单个资源
- `create(data)`: 创建新资源
- `update(id, data)`: 全量更新资源
- `patch(id, data)`: 部分更新资源
- `delete(id)`: 删除资源

### 各资源自定义接口

#### areaService
```typescript
// 获取区域详细数据
const areaData = await areaService.getAreaData(id);

// 获取热门区域，默认返回5个
const popularAreas = await areaService.getPopularAreas(count);

// 获取区域历史数据
const historical = await areaService.getAreaHistorical(id);

// 切换区域收藏状态
await areaService.toggleFavoriteArea(id);
```

#### buildingService
```typescript
// 获取建筑内的所有区域
const areas = await buildingService.getBuildingAreas(buildingId);
```

#### terminalService
```typescript
// 获取终端下的所有硬件节点
const nodes = await terminalService.getTerminalNodes(terminalId);
```

#### alertService
```typescript
// 获取未解决的告警
const unsolvedAlerts = await alertService.getUnsolvedAlerts();

// 获取公开的告警
const publicAlerts = await alertService.getPublicAlerts();

// 标记告警为已解决
await alertService.solveAlert(alertId);
```

#### noticeService
```typescript
// 获取最新通知，默认返回5条
const latestNotices = await noticeService.getLatestNotices(count);

// 获取与通知相关的区域
const noticeAreas = await noticeService.getNoticeAreas(noticeId);
```

#### summaryService
```typescript
// 获取系统概览数据
const summary = await summaryService.getSummary();
```

#### historicalService
```typescript
// 获取区域历史数据，支持附加参数
const areaHistorical = await historicalService.getAreaHistorical(areaId, params);

// 按日期范围获取历史数据
const rangeData = await historicalService.getHistoricalByDateRange(
  startDate, endDate, additionalParams
);

// 获取最新历史数据，默认返回10条
const latestData = await historicalService.getLatestHistorical(count);
```

#### userService
```typescript
// 获取用户信息
const user = await userService.getUserInfo();

// 更新用户信息
await userService.updateUserInfo({ email, phone });

// 更新密码
await userService.updatePassword({
  current_password: encryptedPassword,
  new_password: encryptedNewPassword,
  re_new_password: encryptedConfirmPassword
});

// 获取收藏区域详情
const favoriteAreas = await userService.getFavoriteAreas(favoriteIds);
```

## 页面功能说明

### 首页 (HomePage.vue)
- 显示系统概览统计数据（节点数、区域数等）
- 展示热门区域和用户收藏区域列表
- 显示人流趋势图表
- 实时展示公开告警和最新通知
- 首次加载时优化显示loading状态

### 区域页面 (AreasView.vue)
- 展示区域列表，支持筛选和搜索
- 区域详情查看，展示实时人流数据
- 区域收藏功能
- 支持按建筑、楼层等分类筛选

### 用户中心 (UserView.vue)
- 个人资料管理（邮箱、电话等）
- 密码修改，包含密码强度检测
- 收藏区域管理
- 使用标签页结构分类展示内容

### 管理面板 (AdminView.vue)
- 用户管理：创建、编辑、删除用户
- 区域管理：管理区域信息和关联节点
- 硬件节点管理：配置和监控节点
- 终端管理：管理处理终端
- 历史数据管理：查看和管理历史记录
- 告警管理：处理系统告警
- 通知管理：发布系统通知

## 通用组件

### BaseManager.vue
通用管理组件，提供以下功能：
- 数据列表展示，支持自定义列
- 搜索和筛选
- 分页
- 添加/编辑/删除操作
- 自定义表单
- 数据加载状态

使用示例：
```vue
<template>
  <base-manager
    title="用户管理"
    resource-name="users"
    item-name="用户"
    :columns="columns"
    :default-form-data="defaultFormData"
  >
    <template #form="{ form }">
      <!-- 自定义表单内容 -->
    </template>
  </base-manager>
</template>
```

### AreaCard.vue
区域卡片组件，展示区域信息，支持收藏功能

### Jump.vue & View.vue
管理面板内跳转组件，用于不同模块间的数据关联导航

## 状态管理

使用Pinia进行状态管理，主要Store：

### AuthStore
处理用户认证和会话管理：
- 登录/注册功能
- 令牌刷新
- 会话验证
- 权限检查
- 用户信息管理

## 开发指南

### 添加新页面
1. 在`views`目录创建新Vue组件
2. 在`router/index.ts`添加路由配置
3. 根据需要添加权限控制

### 添加新API服务
1. 在`apiService.ts`中添加自定义方法
2. 注册到对应的服务中

### 添加新管理模块
1. 在`components/admin`目录创建新的管理组件
2. 在`AdminView.vue`中注册新模块
3. 配置路由和权限

## 构建与部署

### 开发环境
```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 生产环境
```bash
# 构建生产版本
npm run build

# 预览生产版本
npm run preview
```

## 常见问题

1. **认证失败**: 检查token是否过期，可能需要重新登录
2. **API请求失败**: 检查网络连接和API路径是否正确
3. **权限不足**: 确保用户拥有足够的权限访问相应功能
