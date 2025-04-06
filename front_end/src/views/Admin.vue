<template>
  <div class="admin-container">
    <div class="admin-layout">
      <!-- 左侧导航栏 -->
      <div class="sidebar-container" :class="sidebarWidthClass">
        <div class="admin-sidebar">
          <div class="sidebar-header">
            <h2 class="admin-title" v-if="!isCollapse">系统管理</h2>
            <el-icon class="collapse-icon" @click="toggleCollapse">
              <component :is="isCollapse ? 'Expand' : 'Fold'"></component>
            </el-icon>
          </div>
          <el-menu
            :default-active="activeModule"
            class="admin-menu"
            @select="handleModuleChange"
            :collapse="isCollapse"
            :collapse-transition="false"
            >
            <el-menu-item v-for="item in modules" :key="item.name" :index="item.name">
              <el-icon><component :is="item.icon"></component></el-icon>
              <template v-if="!isCollapse" #title>{{ item.label }}</template>
            </el-menu-item>
          </el-menu>
        </div>  
      </div>
      
      <!-- 右侧内容区 -->
      <div class="content-container">
        <div class="admin-content">
          <div class="content-header">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item>首页</el-breadcrumb-item>
              <el-breadcrumb-item>系统管理</el-breadcrumb-item>
              <el-breadcrumb-item>{{ currentModuleTitle }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          <component 
            :is="currentComponent" 
            :title="currentModuleTitle"
            :search-query="searchQuery"
            @update-search="updateSearchQuery"
          ></component>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, markRaw, onMounted, shallowRef, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter, useRoute } from 'vue-router'
import { 
  User, Document, Monitor, OfficeBuilding, Operation, Histogram,
  Fold, Expand
} from '@element-plus/icons-vue'
import UserManager from '../components/admin/UserManager.vue'
import NodeManager from '../components/admin/NodeManager.vue'
import TerminalManager from '../components/admin/TerminalManager.vue'
import BuildingManager from '../components/admin/BuildingManager.vue'
import AreaManager from '../components/admin/AreaManager.vue'
import HistoricalDataManager from '../components/admin/HistoricalDataManager.vue'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

// 搜索查询参数
const searchQuery = ref('')

// 检查用户是否登录
onMounted(() => {
  if (!authStore.isAuthenticated) {
    router.push('/auth?mode=login')
  }
  
  // 从路由参数中获取模块和搜索参数（如果有）
  if (route.query.module && modules.some(m => m.name === route.query.module)) {
    activeModule.value = route.query.module
    updateCurrentComponent(route.query.module)
  }
  
  // 初始化搜索查询（如果URL中有）
  if (route.query.search) {
    searchQuery.value = route.query.search
  }
})

// 导航折叠状态
const isCollapse = ref(false)

// 侧边栏宽度类计算属性
const sidebarWidthClass = computed(() => {
  return isCollapse.value ? 'collapse-width' : 'uncollapse-width'
})

// 切换折叠状态
const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

// 定义模块列表
const modules = [
  { name: 'users', label: '用户管理', icon: markRaw(User), component: UserManager },
  { name: 'nodes', label: '硬件节点', icon: markRaw(Monitor), component: NodeManager },
  { name: 'terminals', label: '终端管理', icon: markRaw(Document), component: TerminalManager },
  { name: 'buildings', label: '建筑管理', icon: markRaw(OfficeBuilding), component: BuildingManager },
  { name: 'areas', label: '区域管理', icon: markRaw(Operation), component: AreaManager },
  { name: 'historical', label: '历史数据', icon: markRaw(Histogram), component: HistoricalDataManager }
]

// 激活的模块
const activeModule = ref('users')

// 当前显示的组件
const currentComponent = shallowRef(modules[0].component)

// 当前模块标题
const currentModuleTitle = computed(() => {
  const module = modules.find(m => m.name === activeModule.value)
  return module ? module.label : ''
})

// 更新当前组件
const updateCurrentComponent = (moduleName) => {
  const module = modules.find(m => m.name === moduleName)
  if (module) {
    currentComponent.value = module.component
  }
}

// 处理模块切换
const handleModuleChange = (name) => {
  // 避免重复切换到相同模块
  if (activeModule.value === name) return;
  
  // 切换模块时清空搜索条件
  searchQuery.value = '';
  
  activeModule.value = name;
  updateCurrentComponent(name);
  
  // 更新路由参数，仅保留必要的参数
  router.replace({
    path: route.path,
    query: { 
      module: name
      // 不再传递搜索参数
    }
  });
}

// 更新搜索查询
const updateSearchQuery = (query) => {
  // 避免重复更新相同的查询
  if (searchQuery.value === query) return;
  
  searchQuery.value = query;
  
  // 更新路由参数，使用replace避免产生过多的历史记录
  router.replace({
    path: route.path,
    query: { 
      module: activeModule.value, 
      search: query || undefined // 如果为空则不添加该参数
    }
  });
}

// 监听路由变化，使用防抖处理以避免循环更新
let isUpdatingFromRoute = false;
watch(() => route.query, (newQuery) => {
  // 避免在程序内部触发的路由更新再次触发组件更新
  if (isUpdatingFromRoute) return;
  
  try {
    isUpdatingFromRoute = true;
    
    // 更新模块
    const newModule = newQuery.module;
    if (newModule && modules.some(m => m.name === newModule) && newModule !== activeModule.value) {
      activeModule.value = newModule;
      updateCurrentComponent(newModule);
    }
    
    // 更新搜索查询
    const newSearch = newQuery.search || '';
    if (newSearch !== searchQuery.value) {
      searchQuery.value = newSearch;
    }
  } finally {
    // 确保标志位恢复
    setTimeout(() => {
      isUpdatingFromRoute = false;
    }, 0);
  }
}, { deep: true })
</script>

<style scoped>
.admin-container {
  min-height: calc(100vh - 60px);
  padding: 20px;
  background-color: #f5f7fa;
}

.admin-layout {
  display: flex;
  height: calc(100vh - 100px);
  gap: 20px;
}

.sidebar-container {
  height: 100%;
  transition: width 0.3s ease-in-out;
}

.content-container {
  flex: 1;
  height: 100%;
}

.admin-sidebar {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  padding: 0;
  height: 100%;
  width: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

.sidebar-header {
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #f0f0f0;
}

.admin-title {
  margin: 0;
  color: var(--el-color-primary);
  font-weight: bold;
  font-size: 1.2rem;
}

.collapse-width {
  width: 64px;
}
.uncollapse-width {
  width: 220px;
}

.collapse-icon {
  cursor: pointer;
  font-size: 1.2rem;
  color: var(--el-color-primary);
  transition: transform 0.3s ease;
}

.collapse-icon:hover {
  transform: scale(1.1);
}

.admin-menu {
  border-right: none;
  flex: 1;
  width: 100%;
}

.admin-menu :deep(.el-menu-item.is-active) {
  background-color: var(--el-color-primary-light-9);
  border-right: 3px solid var(--el-color-primary);
  font-weight: bold;
  color: var(--el-color-primary);
}

.admin-menu :deep(.el-menu-item) {
  transition: all 0.2s ease;
}

.admin-menu :deep(.el-menu-item:hover) {
  background-color: var(--el-color-primary-light-9);
  padding-left: 25px;
}

.admin-content {
  background-color: white;
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  padding: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.3s ease;
}

.el-menu-item.is-active::after {
  width: 0 !important;
}

.content-header {
  padding: 18px 24px;
  border-bottom: 1px solid #f0f0f0;
  background-color: #fafbfc;
}

.content-header :deep(.el-breadcrumb__item) {
  color: #909399;
}

.content-header :deep(.el-breadcrumb__item:last-child) {
  font-weight: bold;
  color: var(--el-color-primary);
}

.admin-content > :last-child {
  flex: 1;
  padding: 24px;
  overflow: auto;
  background-color: #ffffff;
}

@media (max-width: 768px) {
  .admin-container {
    padding: 10px;
  }
  
  .admin-layout {
    height: calc(100vh - 80px);
    gap: 10px;
  }
  
  .content-header {
    padding: 14px 16px;
  }
  
  .admin-content > :last-child {
    padding: 16px;
  }

  .sidebar-container {
    min-width: 50px;
    max-width: 160px;
  }
}
</style>
