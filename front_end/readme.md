# 前端文档

## 项目结构
- src/: 核心源代码，包括 View、Component、Router 等。
- public/: 公共资源目录。
- main.ts: 程序入口，创建 Vue App 并挂载到页面。

## 页面逻辑
- HomePage.vue: 首页，展示概览信息并调用后端接口 `/api/historical` 获取统计数据。
- AreasView.vue: 展示区域列表及检测状况，常用的后端接口包括 `/api/areas` 与 `/api/nodes` 等，用来获取区域和节点信息。
- DataScreen.vue: 数据大屏视图，用 ECharts 显示可视化数据，通过 `/api/historical` 或自定义接口获取历史数据。
- 2DMap.vue: 利用地图组件（Leaflet）在二维地图中展示学校平面设置，可能需要调用 `/api/areas` 获取坐标与名称信息。
- Navbar.vue: 顶部导航菜单，通过 router.push() 实现页面跳转，不直接调用后端接口。

## 核心组件
- Navbar.vue: 顶部导航菜单，通过 router.push() 控制页面跳转。
- AreaCard.vue: 区域卡片组件，显示实时检测数据和状态标签。

## 后端接口调用示例
- 获取区域列表: `axios.get('/api/areas')`
- 获取节点列表: `axios.get('/api/nodes')`
- 获取历史数据: `axios.get('/api/historical')`
- 上传检测数据: `axios.post('/api/upload', { id, detected_count, timestamp })`

## 启动与构建
- 开发调试: 运行 “npm run dev” 启动开发服务器。
- 正式打包: 运行 “npm run build” 构建发布版本。
