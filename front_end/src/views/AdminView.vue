<template>
  <div class="admin-container">

    <div class="mobile-header" v-if="isMobile">
      <div class="mobile-title">
        <h2>系统管理</h2>
      </div>

      <el-select 
        :model-value="activeModule"
        class="mobile-module-select"
        @change="handleMobileModuleChange"
        placeholder="选择管理模块"
      >
        <el-option
          v-for="item in modules"
          :key="item.name"
          :label="item.label"
          :value="item.name"
        >
          <div class="module-option">
            <el-icon><component :is="item.icon"></component></el-icon>
            <span>{{ item.label }}</span>
          </div>
        </el-option>
      </el-select>
    </div>

    <div class="admin-layout">

      <div class="sidebar-container" :class="sidebarWidthClass" v-if="!isMobile">
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
      
      <div class="content-container" :class="{'mobile-content': isMobile}">
        <div class="admin-content">
          <div class="content-header">
            <el-breadcrumb separator="/" v-if="!isMobile">
              <el-breadcrumb-item :to="{path:'/'}">首页</el-breadcrumb-item>
              <el-breadcrumb-item :to="{path:'/admin'}">系统管理</el-breadcrumb-item>
              <el-breadcrumb-item>{{ currentModuleTitle }}</el-breadcrumb-item>
            </el-breadcrumb>
            <h3 v-else class="mobile-breadcrumb">{{ currentModuleTitle }}</h3>
          </div>
          <component 
            :is="currentComponent" 
            :title="currentModuleTitle"
            :search-query="searchQuery"
            @update-search="updateSearchQuery"
            :data-link="dataLink"
            :is-mobile="isMobile"
          ></component>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, markRaw, onMounted, shallowRef, watch, onUnmounted, nextTick } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter, useRoute } from 'vue-router'
import { 
  User, Monitor, OfficeBuilding, Location, Histogram, Camera,
  Bell, Document, Upload
} from '@element-plus/icons-vue'
import UserManager from '../components/admin/UserManager.vue'
import NodeManager from '../components/admin/NodeManager.vue'
import TerminalManager from '../components/admin/TerminalManager.vue'
import BuildingManager from '../components/admin/BuildingManager.vue'
import AreaManager from '../components/admin/AreaManager.vue'
import HistoricalDataManager from '../components/admin/HistoricalDataManager.vue'
import AlertManager from '../components/admin/AlertManager.vue'
import NoticeManager from '../components/admin/NoticeManager.vue'
import UploadManager from '../components/admin/UploadManager.vue'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const searchQuery = ref('')
const dataLink = ref('')

onMounted(() => {
  if (!authStore.isAuthenticated) {
    router.push('/auth?mode=login')
  }

  checkIsMobile()

  window.addEventListener('resize', checkIsMobile)

  if (route.query.module && modules.some(m => m.name === route.query.module)) {
    activeModule.value = route.query.module
    updateCurrentComponent(route.query.module)
  }

  if (route.query.search) {
    searchQuery.value = route.query.search
  }
})

onUnmounted(() => {

  window.removeEventListener('resize', checkIsMobile)
})

const isCollapse = ref(false)
const isMobile = ref(false)

const emitMobileStatus = () => {

}

const checkIsMobile = () => {
  const screenWidth = window.innerWidth
  isMobile.value = screenWidth < 768

  if (isMobile.value) {
    isCollapse.value = true
  }
  
  emitMobileStatus()
}

const sidebarWidthClass = computed(() => {
  return isCollapse.value ? 'collapse-width' : 'uncollapse-width'
})

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

const modules = [
  { name: 'users', label: '用户管理', icon: markRaw(User), component: UserManager },
  { name: 'nodes', label: '节点管理', icon: markRaw(Camera), component: NodeManager },
  { name: 'terminals', label: '终端管理', icon: markRaw(Monitor), component: TerminalManager },
  { name: 'buildings', label: '建筑管理', icon: markRaw(OfficeBuilding), component: BuildingManager },
  { name: 'areas', label: '区域管理', icon: markRaw(Location), component: AreaManager },
  { name: 'historical', label: '历史数据', icon: markRaw(Histogram), component: HistoricalDataManager },
  { name: 'alerts', label: '告警管理', icon: markRaw(Bell), component: AlertManager },
  { name: 'notice', label: '通知管理', icon: markRaw(Document), component: NoticeManager },
  { name: 'upload', label: '上传接口', icon: markRaw(Upload), component: UploadManager }
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

const handleMobileModuleChange = (value) => {

  
  if (!value || activeModule.value === value) return;

  activeModule.value = value;
  updateCurrentComponent(value);

  setTimeout(() => {

    router.replace({
      path: '/admin',
      query: { module: value }
    }).then(() => {


      nextTick(() => {

        searchQuery.value = '';
        dataLink.value = '';
      });
    }).catch(err => {
      console.error('Route update failed:', err);
    });
  }, 0);
}

const handleModuleChange = (name) => {

  
  if (activeModule.value === name) return;

  searchQuery.value = '';
  dataLink.value = '';

  activeModule.value = name;
  updateCurrentComponent(name);

  router.push({
    path: '/admin',
    query: { 
      module: name 
    }
  }).catch(err => {
    if (err.name !== 'NavigationDuplicated') {
      console.error('Navigation error:', err);
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
      dataLink.value = `/api/${newData}/${newId}/${activeModule.value}`;
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
  position: fixed;
  top: 60px;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 10px;
  background-color: #f5f7fa;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);
  max-height: calc(100vh - 60px);
}

.admin-layout {
  display: flex;
  flex: 1;
  height: calc(100vh - 80px);
  max-height: calc(100vh - 80px);
  gap: 20px;
  width: 100%;
  padding: 10px;
  max-width: 100%;
  position: relative;
  overflow: hidden;
}

.sidebar-container {
  height: 100%;
  max-height: 100%;
  transition: width 0.3s ease-in-out;
  flex-shrink: 0;
  position: relative;
  z-index: 10;
  overflow: hidden;
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
  max-width: calc(100% - 20px - 64px);
  width: calc(100% - 20px - 220px);
}

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
  max-height: 100%;
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
  overflow: hidden;
  background-color: #ffffff;
  max-height: calc(100% - 57px); /* 减去内容标题高度 */
}

@media (max-width: 768px) {
  .admin-container {
    padding: 5px;
    top: 60px;
    height: calc(100vh - 60px);
    max-height: calc(100vh - 60px);
  }
  
  .admin-layout {
    height: calc(100vh - 120px);
    max-height: calc(100vh - 120px);
    gap: 5px;
    flex-direction: column;
    overflow: hidden;
  }
  
  .content-header {
    padding: 14px 16px;
  }
  
  .admin-content > :last-child {
    padding: 10px;
  }
  
  .content-container {
    height: 100%;
    max-height: 100%;
    overflow: hidden;
  }
  
  .admin-content {
    height: 100%;
    max-height: 100%;
    overflow: hidden;
  }
}

.mobile-header {
  background-color: white;
  padding: 15px;
  margin-bottom: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,.1);
}

.mobile-title {
  margin-bottom: 15px;
}

.mobile-title h2 {
  margin: 0;
  color: var(--el-color-primary);
  font-size: 1.5rem;
}

.mobile-module-select {
  width: 100%;
  margin-bottom: 10px;
}

.module-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
}

.mobile-breadcrumb {
  margin: 0;
  color: var(--el-color-primary);
  font-size: 1.2rem;
}

.mobile-content {
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
}
</style>
