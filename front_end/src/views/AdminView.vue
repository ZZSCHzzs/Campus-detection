<template>
  <div class="admin-container">
    <div class="admin-layout">

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
      

      <div class="content-container">
        <div class="admin-content">
          <div class="content-header">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="{path:'/'}">首页</el-breadcrumb-item>
              <el-breadcrumb-item :to="{path:'/admin'}">系统管理</el-breadcrumb-item>
              <el-breadcrumb-item>{{ currentModuleTitle }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          <component 
            :is="currentComponent" 
            :title="currentModuleTitle"
            :search-query="searchQuery"
            @update-search="updateSearchQuery"
            :data-link="dataLink"
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
  User, Monitor, OfficeBuilding, Location, Histogram, Camera,
  Fold, Expand, Bell, Document
} from '@element-plus/icons-vue'
import UserManager from '../components/admin/UserManager.vue'
import NodeManager from '../components/admin/NodeManager.vue'
import TerminalManager from '../components/admin/TerminalManager.vue'
import BuildingManager from '../components/admin/BuildingManager.vue'
import AreaManager from '../components/admin/AreaManager.vue'
import HistoricalDataManager from '../components/admin/HistoricalDataManager.vue'
import AlertManager from '../components/admin/AlertManager.vue'
import NoticeManager from '../components/admin/NoticeManager.vue'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()


const searchQuery = ref('')
const dataLink = ref('')


onMounted(() => {
  if (!authStore.isAuthenticated) {
    router.push('/auth?mode=login')
  }
  

  if (route.query.module && modules.some(m => m.name === route.query.module)) {
    activeModule.value = route.query.module
    updateCurrentComponent(route.query.module)
  }
  

  if (route.query.search) {
    searchQuery.value = route.query.search
  }
})


const isCollapse = ref(false)


const sidebarWidthClass = computed(() => {
  return isCollapse.value ? 'collapse-width' : 'uncollapse-width'
})


const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}


const modules = [
  { name: 'users', label: '用户管理', icon: markRaw(User), component: UserManager },
  { name: 'nodes', label: '硬件节点', icon: markRaw(Camera), component: NodeManager },
  { name: 'terminals', label: '终端管理', icon: markRaw(Monitor), component: TerminalManager },
  { name: 'buildings', label: '建筑管理', icon: markRaw(OfficeBuilding), component: BuildingManager },
  { name: 'areas', label: '区域管理', icon: markRaw(Location), component: AreaManager },
  { name: 'historical', label: '历史数据', icon: markRaw(Histogram), component: HistoricalDataManager },
  { name: 'alerts', label: '告警管理', icon: markRaw(Bell), component: AlertManager },
  { name: 'notice', label: '公告管理', icon: markRaw(Document), component: NoticeManager }
]


const activeModule = ref('areas')


const currentComponent = shallowRef(modules[4].component)


const currentModuleTitle = computed(() => {
  const module = modules.find(m => m.name === activeModule.value)
  return module ? module.label : ''
})


const updateCurrentComponent = (moduleName) => {
  const module = modules.find(m => m.name === moduleName)
  if (module) {
    currentComponent.value = module.component
  }
}


const handleModuleChange = (name) => {

  if (activeModule.value === name) return;
  

  searchQuery.value = '';
  dataLink.value = '';
  activeModule.value = name;
  updateCurrentComponent(name);
  

  router.replace({
    path: route.path,
    query: { 
      module: name

    }
  });
}


const updateSearchQuery = (query) => {

  if (searchQuery.value === query) return;
  
  searchQuery.value = query;
  

  router.replace({
    path: route.path,
    query: { 
      module: activeModule.value, 
      search: query || undefined
    }
  });
}


let isUpdatingFromRoute = false;
watch(() => route.query, (newQuery) => {

  if (isUpdatingFromRoute) return;
  
  try {
    isUpdatingFromRoute = true;
    dataLink.value = '';

    const newModule = newQuery.module;
    if (newModule && modules.some(m => m.name === newModule) && newModule !== activeModule.value) {
      activeModule.value = newModule;
      updateCurrentComponent(newModule);
    }
    const newData = newQuery.data || '';
    const newId = newQuery.id || '';
    if (newData && newId) {
      dataLink.value = `${newData}/${newId}/${activeModule.value}`;
    }

    const newSearch = newQuery.search || '';
    if (newSearch !== searchQuery.value) {
      searchQuery.value = newSearch;
    }
  } finally {

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
  overflow-x: hidden; /* 防止水平溢出 */
}

.admin-layout {
  display: flex;
  height: calc(100vh - 100px);
  gap: 20px;
  width: 100%;
  max-width: 100%;
  position: relative;
  overflow: hidden; /* 防止内部元素溢出 */
}

.sidebar-container {
  height: 100%;
  transition: width 0.3s ease-in-out;
  flex-shrink: 0;
  position: relative;
  z-index: 10;
}

.collapse-width {
  width: 64px !important;
}

.uncollapse-width {
  width: 220px !important;
}

.content-container {
  flex: 1;
  height: 100%;
  transition: all 0.3s ease-in-out;
  max-width: calc(100% - 20px - 64px); /* 折叠时最大宽度 */
  width: calc(100% - 20px - 220px); /* 展开时基础宽度 */
}

/* 当侧边栏折叠时调整内容区宽度 */
.collapse-width + .content-container {
  width: calc(100% - 20px - 64px);
  max-width: none;
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
