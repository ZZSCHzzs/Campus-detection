# 前端文档

## 1. 项目概述

校园人员检测系统前端是一个基于 Vue 3 + TypeScript 构建的现代化 Web 应用，提供直观的用户界面用于监控和管理校园检测系统。前端通过 HTTP API 与后端进行数据交互，支持实时数据展示、设备管理、用户认证等功能。

## 2. 技术栈

### 核心技术

- **框架**: Vue 3 (Composition API)
- **语言**: TypeScript
- **构建工具**: Vite 6.2.0
- **路由**: Vue Router 4.5.0
- **状态管理**: Pinia 3.0.1

### UI 和样式

- **UI 组件库**: Element Plus 2.9.6
- **图标**: @element-plus/icons-vue 2.3.1
- **图表库**: ECharts 5.6.0 + ECharts GL 2.0.9
- **地图**: Leaflet 1.9.4

### 工具库

- **HTTP 客户端**: Axios 1.8.4
- **工具函数**: @vueuse/core 13.0.0
- **加密**: crypto-js 4.2.0
- **数字动画**: vue3-count-to 1.1.2
- **WebSocket**: socket.io-client 4.7.2

### 开发工具

- **自动导入**: unplugin-auto-import 19.1.1
- **组件自动注册**: unplugin-vue-components 28.4.1
- **TypeScript**: 5.7.2

## 3. 项目结构

```
front_end/
├── public/                 # 静态资源
├── src/                    # 源代码目录
│   ├── views/              # 页面组件
│   │   ├── HomePage.vue        # 首页
│   │   ├── AreasView.vue       # 区域管理
│   │   ├── DataScreen.vue      # 数据大屏
│   │   ├── AuthView.vue        # 登录注册
│   │   ├── AdminView.vue       # 管理面板
│   │   ├── UserView.vue        # 用户中心
│   │   ├── AlertNotice.vue     # 告警通知
│   │   ├── TerminalView.vue    # 终端详情
│   │   └── NotFound.vue        # 404页面
│   ├── components/         # 可复用组件
│   │   ├── admin/              # 管理面板组件
│   │   │   ├── BaseManager.vue     # 基础管理组件
│   │   │   ├── TerminalManager.vue # 终端管理
│   │   │   ├── NodeManager.vue     # 节点管理
│   │   │   ├── UserManager.vue     # 用户管理
│   │   │   └── NoticeManager.vue   # 公告管理
│   │   ├── chart/              # 图表组件
│   │   │   ├── EnvironmentalChart.vue # 环境数据图表
│   │   │   ├── TrendChart.vue         # 趋势图表
│   │   │   └── BaseChart.vue          # 基础图表
│   │   ├── data/               # 数据展示组件
│   │   │   ├── AreaList.vue           # 区域列表
│   │   │   └── HardwareNodeStatus.vue # 硬件节点状态
│   │   └── layout/             # 布局组件
│   │       └── Navbar.vue             # 导航栏
│   ├── router/             # 路由配置
│   │   └── index.ts
│   ├── stores/             # Pinia状态管理
│   │   └── auth.ts                # 认证状态
│   ├── services/           # API服务层
│   │   ├── index.ts               # 服务入口
│   │   ├── ResourceManager.ts     # 资源管理器
│   │   ├── ResourceServiceCreator.ts # 服务创建器
│   │   └── AuthService.ts         # 认证服务
│   ├── network/            # 网络层
│   │   ├── index.ts               # 网络入口
│   │   ├── axios.ts               # Axios配置
│   │   └── http.ts                # HTTP工具函数
│   ├── types.ts            # TypeScript类型定义
│   ├── assets/             # 静态资源
│   ├── plugins/            # 插件配置
│   │   └── element-plus.ts        # Element Plus配置
│   ├── App.vue             # 根组件
│   └── main.ts             # 程序入口
├── components.d.ts         # 组件类型声明
├── package.json            # 项目依赖和脚本
├── vite.config.ts          # Vite配置
├── tsconfig.json           # TypeScript配置
└── readme.md               # 项目说明
```

## 4. 路由结构

| 路径              | 组件           | 描述      | 权限要求    |
| --------------- | ------------ | ------- | ------- |
| `/`             | HomePage     | 首页，系统概览 | 无       |
| `/areas`        | AreasView    | 区域列表和详情 | 无       |
| `/screen`       | DataScreen   | 数据大屏可视化 | 无       |
| `/login`        | AuthView     | 登录      | 无       |
| `/register`     | AuthView     | 注册      | 无       |
| `/alerts`       | AlertNotice  | 告警和通知   | 无       |
| `/profile`      | UserView     | 用户个人中心  | 需要登录    |
| `/terminal`     | TerminalView | 终端管理    | 需要管理员权限 |
| `/terminal/:id` | TerminalView | 终端详情    | 需要管理员权限 |
| `/admin`        | AdminView    | 管理控制面板  | 需要管理员权限 |

### 路由守卫

```typescript
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!authStore.isAuthenticated) {
      next({ path: '/login' })
    } 
    else if (to.matched.some(record => record.meta.requiresAdmin) && authStore.user?.role !== 'admin') {
      ElMessage.error('您没有访问管理面板的权限')
      next({ path: '/' }) 
    }
    else {
      next() 
    }
  } else {
    next() 
  }
})
```

## 5. 状态管理

### 认证状态 (auth.ts)

使用 Pinia 管理用户认证状态，包括：

- **Token 管理**: 自动刷新 access token，持久化存储
- **用户信息**: 用户基本信息和权限
- **会话管理**: 登录状态验证，自动登出
- **安全机制**: Token 过期检查，定时刷新

```typescript
const TOKEN_REFRESH_INTERVAL = 50 * 60 * 1000; // 50分钟刷新一次token
const TOKEN_CHECK_INTERVAL = 5 * 60 * 1000;    // 5分钟检查一次token状态
const TOKEN_PERSIST_DAYS = 3;                  // token持久化保存天数
```

## 6. API 服务层

### 服务架构

采用分层架构设计：

1. **网络层** (`network/`): Axios 配置和 HTTP 工具函数
2. **资源管理层** (`ResourceManager.ts`): 统一的资源管理和缓存
3. **服务创建层** (`ResourceServiceCreator.ts`): 动态创建资源服务
4. **业务服务层**: 各种具体的业务服务

### 主要服务

```typescript
// 各个资源服务
export const areaService = createResourceService<AreaItem>('areas', areaCustomMethods);
export const buildingService = createResourceService<Building>('buildings', buildingCustomMethods);
export const nodeService = createResourceService<HardwareNode>('nodes', nodeCustomMethods);
export const terminalService = createResourceService<ProcessTerminal>('terminals', terminalCustomMethods);
export const alertService = createResourceService<Alert>('alerts', alertCustomMethods);
export const noticeService = createResourceService<Notice>('notice', noticeCustomMethods);
export const userService = createResourceService<User>('users', userCustomMethods);
```

### 缓存机制

- **智能缓存**: 根据数据类型设置不同的缓存时间
- **缓存失效**: 支持手动清除和自动过期
- **性能优化**: 减少重复请求，提升用户体验

## 7. 组件设计

### 基础管理组件 (BaseManager.vue)

提供统一的 CRUD 操作界面，支持：

- 数据表格展示
- 搜索和分页
- 新增、编辑、删除操作
- 自定义表单字段
- 响应式设计

### 图表组件

- **EnvironmentalChart.vue**: 环境数据图表（温度、湿度、CO2）
- **TrendChart.vue**: 趋势分析图表
- **BaseChart.vue**: 基础图表组件，封装 ECharts

### 数据展示组件

- **AreaList.vue**: 区域列表展示
- **HardwareNodeStatus.vue**: 硬件节点状态监控

## 8. 数据大屏部分

**（此部分由其他开发人员负责，完成后将在此处补充详细文档）**

数据大屏 (`DataScreen.vue`) 提供实时数据可视化展示，包括：

- 系统概览统计
- 实时消息滚动
- 区域状态展示
- 硬件节点监控
- 全屏显示支持

*注：数据大屏的具体实现细节、图表配置、动画效果等将由负责该模块的开发人员补充完善。*



## 前端 API 服务详细说明

本前端项目采用了模块化的API服务架构，通过统一的资源管理器和服务工厂模式，为开发人员提供了简洁、高效的API调用接口。整个API服务层包含了缓存管理、认证处理、错误处理和类型安全等特性。

## 核心架构

### 1. 网络层 (Network Layer)

#### API 核心服务 (ApiCore)

位置：<mcfile name="axios.ts" path=".\src\network\axios.ts"></mcfile>

```typescript
// 创建API实例
const defaultApi = apiCore.createInstance('default', {
  baseURL: 'https://smarthit.top',
  mode: ApiMode.REMOTE,
  addTrailingSlash: true
});

const localApi = apiCore.createInstance('local', {
  baseURL: 'http://localhost:5000',
  timeout: 5000,
  mode: ApiMode.LOCAL
});
```

**特性：**

- 支持多实例管理（远程API、本地API、认证API）
- 自动添加JWT认证头
- 自动token刷新机制
- 请求/响应拦截器
- 超时和重试机制

#### HTTP 工具函数

位置：<mcfile name="http.ts" path=".\src\network\http.ts"></mcfile>

```typescript
// 使用示例
import { http } from '../network';

// GET 请求
const data = await http.get('/api/areas/');

// POST 请求
const result = await http.post('/api/areas/', { name: '新区域' });

// 本地API调用
const status = await http.local.get('/api/status');
```

### 2. 资源管理器 (ResourceManager)

位置：<mcfile name="ResourceManager.ts" path=".\src\services\ResourceManager.ts"></mcfile>

#### 核心功能

**缓存管理：**

```typescript
// 设置全局缓存时间
resourceManager.setGlobalCacheDuration(5 * 60 * 1000); // 5分钟

// 设置特定资源缓存时间
resourceManager.setResourceCacheDuration('areas', 60 * 1000); // 1分钟

// 清空缓存
resourceManager.clearCache();

// 使缓存失效
resourceManager.invalidateCache('areas');
```

**CRUD 操作：**

```typescript
// 获取资源列表
const areas = await resourceManager.getList<AreaItem>('areas');

// 获取单个资源
const area = await resourceManager.getById<AreaItem>('areas', 1);

// 创建资源
const newArea = await resourceManager.create<AreaItem>('areas', areaData);

// 更新资源
const updatedArea = await resourceManager.update<AreaItem>('areas', 1, updateData);

// 部分更新
const patchedArea = await resourceManager.patch<AreaItem>('areas', 1, patchData);

// 删除资源
await resourceManager.delete('areas', 1);
```

**自定义API调用：**

```typescript
// 自定义API调用
const result = await resourceManager.customCall<CustomType>(
  '/api/custom/endpoint/',
  'post',
  requestData,
  queryParams,
  defaultApi,
  true, // 使用缓存
  30000 // 缓存时间
);
```

### 3. 服务创建器 (ResourceServiceCreator)

位置：<mcfile name="ResourceServiceCreator.ts" path=".\src\services\ResourceServiceCreator.ts"></mcfile>

#### 工厂函数

```typescript
// 创建标准化服务
const areaService = createResourceService<AreaItem>('areas', areaCustomMethods);

// 服务包含的标准方法
interface ResourceService<T> {
  getAll: (params?: any, forceRefresh?: boolean) => Promise<T[]>;
  getById: (id: number | string, forceRefresh?: boolean) => Promise<T>;
  create: (data: any) => Promise<T>;
  update: (id: number | string, data: any) => Promise<T>;
  patch: (id: number | string, data: any) => Promise<T>;
  delete: (id: number | string) => Promise<void>;
  refreshCache: () => void;
  clearCache: () => void;
  // ... 自定义方法
}
```

### 4. 认证服务 (AuthService)

位置：<mcfile name="AuthService.ts" path=".\src\services\AuthService.ts"></mcfile>

#### 使用示例

```typescript
import { authService } from '../services/AuthService';

// 用户登录
const tokens = await authService.login('username', 'password');

// 用户注册
const user = await authService.register(userData);

// 获取用户信息
const userInfo = await authService.getUserInfo();

// 更新用户信息
const updatedUser = await authService.updateUserInfo(updateData);

// 更新密码
await authService.updatePassword({
  current_password: 'oldPassword',
  new_password: 'newPassword',
  re_new_password: 'newPassword'
});

// 检查认证状态
const isAuth = authService.isAuthenticated();

// 退出登录
authService.logout();
```

## 可用服务列表

### 1. 区域服务 (areaService)

```typescript
import { areaService } from '../services';

// 标准CRUD操作
const areas = await areaService.getAll();
const area = await areaService.getById(1);
const newArea = await areaService.create(areaData);
const updatedArea = await areaService.update(1, updateData);
await areaService.delete(1);

// 自定义方法
const popularAreas = await areaService.getPopularAreas(5);
const historicalData = await areaService.getAreaHistorical(1, { hours: 24 });
const tempHumidityData = await areaService.getAreaTemperatureHumidity(1, 24);
const favoriteAreas = await areaService.getFavoriteAreas();
await areaService.toggleFavoriteArea(1);
```

### 2. 建筑服务 (buildingService)

```typescript
import { buildingService } from '../services';

// 标准操作
const buildings = await buildingService.getAll();
const building = await buildingService.getById(1);

// 自定义方法
const buildingAreas = await buildingService.getBuildingAreas(1);
const paginatedAreas = await buildingService.getBuildingAreasPaginated(1, 1, 20);
const basicBuildings = await buildingService.getBuildingsBasic();
const batchResults = await buildingService.loadBuildingsWithAreas([1, 2, 3], 20);
```

### 3. 节点服务 (nodeService)

```typescript
import { nodeService } from '../services';

// 标准操作
const nodes = await nodeService.getAll();
const node = await nodeService.getById(1);

// 自定义方法
const areaNodes = await nodeService.getDatabyAreaId(1);
```

### 4. 终端服务 (terminalService)

```typescript
import { terminalService } from '../services';

// 标准操作
const terminals = await terminalService.getAll();
const terminal = await terminalService.getById(1);

// 自定义方法
const terminalNodes = await terminalService.getTerminalNodes(1);
const status = await terminalService.getTerminalStatus(1);
const logs = await terminalService.getTerminalLogs(1, { level: 'error' });
const config = await terminalService.getTerminalConfig(1);
const co2Data = await terminalService.getTerminalCO2Data(1, 24);

// 发送命令
await terminalService.sendTerminalCommand(1, {
  action: 'start_detection',
  params: { mode: 'push' }
});

// 更新配置
await terminalService.updateTerminalConfig(1, {
  mode: 'push',
  interval: 30,
  save_image: true
});
```

### 5. 本地终端服务 (localTerminalService)

```typescript
import { localTerminalService } from '../services';

// 获取本地终端状态
const status = await localTerminalService.getStatus();

// 获取配置
const config = await localTerminalService.getConfig();

// 更新配置
await localTerminalService.updateConfig(newConfig);

// 获取日志
const logs = await localTerminalService.getLogs();

// 发送控制命令
await localTerminalService.sendCommand('start_detection', { mode: 'push' });

// 获取环境信息
const envInfo = await localTerminalService.getEnvironmentInfo();

// 检查本地终端可用性
const isAvailable = await localTerminalService.checkLocalAvailable();

// 自动检测环境
const environment = await localTerminalService.autoDetectEnvironment();
```

### 6. 告警服务 (alertService)

```typescript
import { alertService } from '../services';

// 标准操作
const alerts = await alertService.getAll();
const alert = await alertService.getById(1);

// 自定义方法
const unsolvedAlerts = await alertService.getUnsolvedAlerts();
const publicAlerts = await alertService.getPublicAlerts();
await alertService.solveAlert(1);
```

### 7. 通知服务 (noticeService)

```typescript
import { noticeService } from '../services';

// 标准操作
const notices = await noticeService.getAll();
const notice = await noticeService.getById(1);

// 自定义方法
const latestNotices = await noticeService.getLatestNotices(5);
const noticeAreas = await noticeService.getNoticeAreas(1);
```

### 8. 历史数据服务 (historicalService)

```typescript
import { historicalService } from '../services';

// 标准操作
const historicalData = await historicalService.getAll();

// 自定义方法
const areaHistorical = await historicalService.getAreaHistorical(1, {
  start_date: '2024-01-01',
  end_date: '2024-01-31'
});

const dateRangeData = await historicalService.getHistoricalByDateRange(
  '2024-01-01',
  '2024-01-31',
  { area_id: 1 }
);

const latestData = await historicalService.getLatestHistorical(10);
```

### 9. 温湿度数据服务 (temperatureHumidityService)

```typescript
import { temperatureHumidityService } from '../services';

// 自定义方法
const latestData = await temperatureHumidityService.getLatest(10);
const areaData = await temperatureHumidityService.getByArea(1, 24);

// 上传数据
await temperatureHumidityService.upload({
  area_id: 1,
  temperature: 25.5,
  humidity: 60.2,
  timestamp: new Date().toISOString()
});

const dateRangeData = await temperatureHumidityService.getByDateRange(
  '2024-01-01',
  '2024-01-31',
  1
);
```

### 10. CO2数据服务 (co2Service)

```typescript
import { co2Service } from '../services';

// 自定义方法
const latestData = await co2Service.getLatest(10);
const terminalData = await co2Service.getByTerminal(1, 24);

// 上传数据
await co2Service.upload({
  terminal_id: 1,
  co2_level: 400,
  timestamp: new Date().toISOString()
});

const dateRangeData = await co2Service.getByDateRange(
  '2024-01-01',
  '2024-01-31',
  1
);
```

### 11. 用户服务 (userService)

```typescript
import { userService } from '../services';

// 标准操作
const users = await userService.getAll();
const user = await userService.getById(1);

// 自定义方法
const userInfo = await userService.getUserInfo();
const updatedUser = await userService.updateUserInfo({
  phone: '13800138000',
  email: 'user@example.com'
});

await userService.updatePassword({
  current_password: 'oldPassword',
  new_password: 'newPassword',
  re_new_password: 'newPassword'
});
```

### 12. 汇总服务 (summaryService)

```typescript
import { summaryService } from '../services';

// 获取系统汇总数据
const summary = await summaryService.getSummary();
// 返回：节点数量、终端数量、建筑数量、区域数量、历史数据数量等
```

## 类型定义

所有的数据类型定义都在 <mcfile name="types.ts" path=".\src\types.ts"></mcfile> 文件中，包括：

- `AreaItem` - 区域类型
- `Building` - 建筑类型  
- `HardwareNode` - 硬件节点类型
- `ProcessTerminal` - 处理终端类型
- `User` - 用户类型
- `Alert` - 告警类型
- `Notice` - 通知类型
- `HistoricalData` - 历史数据类型
- `TemperatureHumidityData` - 温湿度数据类型
- `CO2Data` - CO2数据类型
- `TerminalMessage` - 终端消息类型
- `TerminalCommand` - 终端命令类型
- `TerminalStatus` - 终端状态类型
- `TerminalConfig` - 终端配置类型
- `LogEntry` - 日志记录类型
- `EnvironmentInfo` - 环境信息类型

## 配置和缓存

### 缓存配置

```typescript
// 默认缓存时间配置
export const DEFAULT_CACHE_DURATIONS = {
  areas: 60 * 1000, // 1分钟
  buildings: 5 * 60 * 1000, // 5分钟
  nodes: 30 * 1000, // 30秒
  terminals: 30 * 1000, // 30秒
  alerts: 30 * 1000, // 30秒
  notice: 60 * 1000, // 1分钟
  users: 5 * 60 * 1000, // 5分钟
  historical: 5 * 60 * 1000, // 5分钟
  'temperature-humidity': 2 * 60 * 1000, // 2分钟
  co2: 2 * 60 * 1000, // 2分钟
  global: 2 * 60 * 1000, // 全局默认2分钟
};
```

### 服务配置

```typescript
// 服务资源配置
export const serviceConfigs: Record<string, ResourceConfig> = {
  areas: {
    basePath: '/api',
    cacheDuration: 60 * 1000,
  },
  buildings: {
    basePath: '/api',
    cacheDuration: 5 * 60 * 1000,
  },
  // ... 其他配置
};
```

## 错误处理

### 统一错误处理

```typescript
try {
  const data = await areaService.getAll();
  // 处理成功响应
} catch (error) {
  // 错误会自动处理，包括：
  // 1. 网络错误
  // 2. 认证错误（自动token刷新）
  // 3. 服务器错误
  // 4. 超时错误
  console.error('API调用失败:', error);
}
```

### 缓存降级

当API调用失败时，系统会自动尝试返回过期的缓存数据作为降级方案：

```typescript
// 如果网络请求失败，会尝试返回过期缓存
const expiredCache = this.getFromCache<T[]>(cacheKey, true);
if (expiredCache) return expiredCache;
```

## 最佳实践

### 1. 使用TypeScript类型

```typescript
// 推荐：使用类型注解
const areas: AreaItem[] = await areaService.getAll();
const area: AreaItem = await areaService.getById(1);

// 避免：不使用类型
const areas = await areaService.getAll(); // 类型不明确
```

### 2. 合理使用缓存

```typescript
// 对于频繁访问的数据，使用缓存
const areas = await areaService.getAll(); // 使用缓存

// 对于需要最新数据的场景，强制刷新
const latestAreas = await areaService.getAll({}, true); // 强制刷新

// 手动清理缓存
areaService.clearCache();
```

### 3. 错误处理

```typescript
// 推荐：具体的错误处理
try {
  const data = await areaService.getAll();
  return data;
} catch (error) {
  if (error.response?.status === 401) {
    // 处理认证错误
    router.push('/login');
  } else if (error.response?.status >= 500) {
    // 处理服务器错误
    ElMessage.error('服务器错误，请稍后重试');
  } else {
    // 处理其他错误
    ElMessage.error('操作失败');
  }
  throw error;
}
```

### 4. 批量操作优化

```typescript
// 推荐：使用批量方法
const batchResults = await buildingService.loadBuildingsWithAreas([1, 2, 3]);

// 避免：循环调用
const results = [];
for (const id of [1, 2, 3]) {
  const result = await buildingService.getBuildingAreas(id); // 效率低
  results.push(result);
}
```

### 5. 环境检测

```typescript
// 自动检测本地/远程环境
const environment = await localTerminalService.autoDetectEnvironment();

if (environment.type === 'detector') {
  // 使用本地终端服务
  const status = await localTerminalService.getStatus();
} else {
  // 使用远程终端服务
  const terminals = await terminalService.getAll();
}
```

## 总结

本前端API服务架构提供了：

1. **统一的接口**：所有资源都遵循相同的CRUD模式
2. **类型安全**：完整的TypeScript类型定义
3. **缓存机制**：智能缓存管理，提升性能
4. **错误处理**：统一的错误处理和降级策略
5. **认证管理**：自动token管理和刷新
6. **扩展性**：易于添加新的资源服务
7. **本地支持**：支持本地终端和远程服务器双模式

开发人员只需要导入相应的服务，即可快速进行API调用，无需关心底层的网络请求、缓存管理和错误处理细节。

## 开发与部署

### 开发环境

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 类型检查
npm run build
```

### 构建配置

```typescript
export default defineConfig({
  base: '/',
  server: {
    allowedHosts: ['.localdomain', 'localhost', 'smarthit.top'],
  },
  plugins: [
    vue(),
    AutoImport({ resolvers: [ElementPlusResolver()] }),
    Components({ resolvers: [ElementPlusResolver()] }),
  ],
});
```

### 部署

1. **构建生产版本**:
   
   ```bash
   npm run build
   ```

2. **部署静态文件**: 将 `dist` 目录部署到静态文件服务器

3. **Nginx 配置**: 配置反向代理和静态文件服务

## 特性说明

### 响应式设计

- 支持桌面端和移动端
- 自适应布局
- 触摸友好的交互

### 实时数据

- 通过轮询获取最新数据
- 智能缓存减少请求频率
- 错误重试机制

### 用户体验

- 加载状态提示
- 错误信息展示
- 操作反馈
- 快捷键支持

### 安全性

- JWT Token 认证
- 权限控制
- 路由守卫
- XSS 防护

## 性能优化

- **代码分割**: 路由级别的懒加载
- **组件缓存**: 合理使用 keep-alive
- **图片优化**: 懒加载和压缩
- **网络优化**: 请求合并和缓存
- **构建优化**: Tree-shaking 和压缩

## 扩展性

- **模块化设计**: 组件和服务可独立开发
- **插件系统**: 支持第三方插件集成
- **主题定制**: 支持自定义主题
- **国际化**: 预留多语言支持接口
