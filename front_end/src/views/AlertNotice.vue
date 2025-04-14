<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, computed, watch, onBeforeMount } from 'vue'
import { useAuthStore } from '../stores/auth'
import { areaService, alertService, noticeService } from '../services/apiService'
import apiService from '../services/apiService'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Bell, Warning, Document, Plus, Check, Search, Refresh, View, Clock, Grid, List } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import type { Alert, Notice, AreaItem } from '../types'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const userRole = computed(() => authStore.user?.role || '')
const isStaffOrAdmin = computed(() => ['staff', 'admin'].includes(userRole.value))

interface ExtendedAlert extends Alert {
  area_name?: string;
}

const areas = ref<AreaItem[]>([])
const areasLoading = ref(false)

const activeTab = ref('alerts')
const alertsLoading = ref(false)
const noticesLoading = ref(false)

const alerts = ref<ExtendedAlert[]>([])
const alertFilter = ref('unsolved')
const alertFilterOptions = [
  { value: 'all', label: '全部告警' },
  { value: 'unsolved', label: '未处理告警' },
  { value: 'solved', label: '已处理告警' }
]

const notices = ref<Notice[]>([])
const noticeForm = reactive({
  title: '',
  content: '',
  related_areas: [] as number[]
})
const noticeDialogVisible = ref(false)
const noticeSubmitting = ref(false)

const searchText = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

const alertDetailVisible = ref(false)
const noticeDetailVisible = ref(false)
const currentAlertDetail = ref<ExtendedAlert | null>(null)
const currentNoticeDetail = ref<Notice | null>(null)

const fetchAreas = async () => {
  if (areasLoading.value) return
  areasLoading.value = true
  try {
    
    areas.value = await areaService.getAll()
    console.log('区域数据加载完成，共加载:', areas.value.length, '个区域')
    return true
  } catch (error) {
    console.error('获取区域列表失败:', error)
    ElMessage.error('获取区域列表失败')
    return false
  } finally {
    areasLoading.value = false
  }
}

const getAreaName = (areaId: number): string => {
  if (!areaId) return '未知区域'
  const area = areas.value.find(a => a.id === areaId)
  return area ? area.name : '未知区域'
}

const processAlertData = (alertsData: ExtendedAlert[]) => {
  alertsData.forEach(alert => {
    if (alert.area) {
      alert.area_name = getAreaName(alert.area)
      console.log(`处理告警 ID: ${alert.id}, 区域ID: ${alert.area}, 区域名称: ${alert.area_name}`)
    } else {
      console.log(`告警 ID: ${alert.id} 没有关联区域`)
    }
  })
  alerts.value = alertsData
}

const processNoticeData = (noticesData: Notice[]) => {
  notices.value = noticesData
}

const fetchAlerts = async () => {
  alertsLoading.value = true
  try {
    let alertsData: ExtendedAlert[] = []
    if (alertFilter.value === 'unsolved') {
      alertsData = await alertService.getUnsolvedAlerts()
    } else {
      alertsData = await alertService.getAll()
      if (alertFilter.value === 'solved') {
        alertsData = alertsData.filter(alert => alert.solved)
      }
    }
    
    console.log(`获取到 ${alertsData.length} 条告警数据`)
    processAlertData(alertsData)

    checkUrlForDetails()
  } catch (error) {
    console.error('获取告警失败:', error)
    ElMessage.error('获取告警数据失败')
    alerts.value = []
  } finally {
    alertsLoading.value = false
  }
}

const fetchNotices = async () => {
  noticesLoading.value = true
  try {
    const noticesData = await noticeService.getAll()
    processNoticeData(noticesData)
    checkUrlForDetails()
  } catch (error) {
    console.error('获取通知失败:', error)
    ElMessage.error('获取通知数据失败')
    notices.value = []
  } finally {
    noticesLoading.value = false
  }
}

const solveAlert = async (alertId: number) => {
  try {
    await ElMessageBox.confirm('确定将此告警标记为已解决?', '确认操作', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await alertService.solveAlert(alertId)
    ElMessage.success('告警已成功标记为已解决')
    await fetchAlerts()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('处理告警失败:', error)
      ElMessage.error('处理告警失败')
    }
  }
}

const submitNotice = async () => {
  if (!noticeForm.title.trim() || !noticeForm.content.trim()) {
    ElMessage.warning('请填写完整的通知信息')
    return
  }
  noticeSubmitting.value = true
  try {
    
    await noticeService.createNotice({
      title: noticeForm.title,
      content: noticeForm.content,
      related_areas: noticeForm.related_areas
    })
    
    ElMessage.success('通知发布成功')
    noticeDialogVisible.value = false

    noticeForm.title = ''
    noticeForm.content = ''
    noticeForm.related_areas = []
    await noticeService.refreshAll()
    await fetchNotices()
  } catch (error) {
    console.error('发布通知失败:', error)
    ElMessage.error('发布通知失败')
  } finally {
    noticeSubmitting.value = false
  }
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const getAlertTypeName = (type: string) => {
    const alertTypeMap: { [key: string]: string } = {
        fire: '火灾',
        guard: '安保',
        crowd: '人群聚集',
        health: '生命危急',
        other: '其他'
    }
  return alertTypeMap[type] || '未知类型'
}

const getAlertGrade = (grade: number) => {
    const alertGradeMap: { [key: number]: { label: string, type: string } } = {
        0: { label: '普通', type: 'info' },
        1: { label: '注意', type: 'success' },
        2: { label: '警告', type: 'warning' },
        3: { label: '严重', type: 'danger' }
    }
  return alertGradeMap[grade] || { label: '未知', type: 'info' }
}

const filteredAlerts = computed(() => {
  if (!searchText.value) return alerts.value
  const keyword = searchText.value.toLowerCase()
  return alerts.value.filter(alert => 
    alert.message.toLowerCase().includes(keyword) || 
    (alert.area_name && alert.area_name.toLowerCase().includes(keyword))
  )
})

const filteredNotices = computed(() => {
  if (!searchText.value) return notices.value
  const keyword = searchText.value.toLowerCase()
  return notices.value.filter(notice => 
    notice.title.toLowerCase().includes(keyword) || 
    notice.content.toLowerCase().includes(keyword)
  )
})

const paginatedAlerts = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredAlerts.value.slice(start, end)
})

const paginatedNotices = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredNotices.value.slice(start, end)
})

const total = computed(() => {
  return activeTab.value === 'alerts' 
    ? filteredAlerts.value.length 
    : filteredNotices.value.length
})

const handlePageChange = (page: number) => {
  currentPage.value = page
}

const handleTabChange = (tab: string) => {
  currentPage.value = 1
  searchText.value = ''
  updateUrl({ tab })
}

onMounted(async () => {
  const tabParam = route.query.tab as string
  apiService.setResourceCacheOptions('alerts', { duration: 30000 });
  apiService.setResourceCacheOptions('notice', { duration: 30000 });
  if (tabParam && ['alerts', 'notices'].includes(tabParam)) {
    activeTab.value = tabParam
  }
  const areasLoaded = await fetchAreas()
  if (areasLoaded) {
    await Promise.all([fetchAlerts(), fetchNotices()])
  } else {
    await Promise.all([fetchAlerts(), fetchNotices()])
    console.warn('区域数据加载失败，告警和通知的区域信息可能不完整')
  }
  
  refreshIntervalId = setInterval(() => {
    if (activeTab.value === 'alerts') {
      fetchAlerts()
    } else {
      fetchNotices()
    }
  }, 30000)
})

const handleFilterChange = () => {
  currentPage.value = 1
  fetchAlerts()
}

const refreshData = () => {
  if (activeTab.value === 'alerts') {
    fetchAlerts()
  } else {
    fetchNotices()
  }
}

const prepareAlertDetail = (alert: ExtendedAlert) => {
  if (alert.area && !alert.area_name) {
    alert.area_name = getAreaName(alert.area)
  }
  currentAlertDetail.value = alert
  alertDetailVisible.value = true
  updateUrl({ tab: 'alerts', alertId: alert.id })
}

const prepareNoticeDetail = (notice: Notice) => {
  currentNoticeDetail.value = notice
  noticeDetailVisible.value = true
  updateUrl({ tab: 'notices', noticeId: notice.id })
}

const showAlertDetail = (alert: ExtendedAlert) => {
  prepareAlertDetail(alert)
}

const showNoticeDetail = (notice: Notice) => {
  prepareNoticeDetail(notice)
}

const updateUrl = (params: { tab?: string, alertId?: number, noticeId?: number }) => {
  const query = { ...route.query }
  if (params.tab) {
    query.tab = params.tab
  }
  delete query.alertId
  delete query.noticeId
  if (params.alertId) {
    query.alertId = params.alertId.toString()
  }
  if (params.noticeId) {
    query.noticeId = params.noticeId.toString()
  }
  router.replace({ query })
}

const checkUrlForDetails = () => {
  const { tab, alertId, noticeId } = route.query
  if (tab === 'alerts' && alertId && alerts.value.length > 0) {
    const id = parseInt(alertId as string)
    const alert = alerts.value.find(a => a.id === id)
    if (alert) {
      showAlertDetail(alert)
    }
  }
  if (tab === 'notices' && noticeId && notices.value.length > 0) {
    const id = parseInt(noticeId as string)
    const notice = notices.value.find(n => n.id === id)
    if (notice) {
      showNoticeDetail(notice)
    }
  }
}

const closeAlertDetail = () => {
  alertDetailVisible.value = false
  updateUrl({ tab: 'alerts' })
}

const closeNoticeDetail = () => {
  noticeDetailVisible.value = false
  updateUrl({ tab: 'notices' })
}

watch(
  () => route.query,
  () => {
    const tabParam = route.query.tab as string
    if (tabParam && ['alerts', 'notices'].includes(tabParam)) {
      activeTab.value = tabParam
    }
    checkUrlForDetails()
  }
)

const isMobileView = ref(false)
let refreshIntervalId: number | null = null

const checkScreenSize = () => {
  isMobileView.value = window.innerWidth < 768
}

onBeforeMount(() => {
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)

  viewMode.value = isMobileView.value ? 'card' : 'table'
})

onBeforeUnmount(() => {

  if (refreshIntervalId !== null) {
    clearInterval(refreshIntervalId)
    refreshIntervalId = null
  }

  window.removeEventListener('resize', checkScreenSize)
})

const viewMode = ref('table')

const actualViewMode = computed(() => viewMode.value)

const toggleViewMode = () => {
  viewMode.value = viewMode.value === 'table' ? 'card' : 'table'
}

const viewModeInfo = computed(() => {
  const modes = {
    table: { icon: Grid, text: '表格视图' },
    card: { icon: List, text: '卡片视图' }
  }
  return modes[viewMode.value]
})

const drawerDirection = ref('btt')
const drawerSize = ref('70%')
</script>

<template>
  <div class="alert-notice-container">
    <!-- 标题和操作区域 -->
    <div class="page-header">
      <div class="title-section">
        <h2 class="page-title">
          <el-icon class="header-icon"><Bell /></el-icon>
          告警与通知中心
        </h2>
      </div>
      <div class="header-actions">
        <el-tooltip :content="viewModeInfo.text" placement="top">
          <el-button 
            type="default"
            @click="toggleViewMode" 
            circle
            class="view-mode-button"
          >
            <el-icon><component :is="viewModeInfo.icon" /></el-icon>
          </el-button>
        </el-tooltip>
        <el-button type="primary" :icon="Refresh" circle @click="refreshData" />
      </div>
    </div>
    
    <!-- 主内容区域 -->
    <div class="main-content">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange" class="custom-tabs">

        <el-tab-pane name="alerts" lazy>
          <template #label>
            <div class="tab-label">
              <el-icon><Warning /></el-icon>
              <span>告警信息</span>
            </div>
          </template>
          <!-- 过滤栏保持不变 -->
          <div class="filter-bar">
            <div class="left-section">
              <el-select 
                v-model="alertFilter" 
                placeholder="筛选告警" 
                @change="handleFilterChange"
                class="filter-select"
              >
                <el-option 
                  v-for="option in alertFilterOptions" 
                  :key="option.value" 
                  :label="option.label" 
                  :value="option.value" 
                />
              </el-select>
            </div>
            
            <div class="right-section">
              <el-input
                v-model="searchText"
                placeholder="搜索告警内容..."
                class="search-input"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </div>
          </div>
          
          <!-- 表格视图 - 根据视图模式决定是否显示 -->
          <div v-if="actualViewMode === 'table'" class="table-container">
            <el-table
              :data="paginatedAlerts"
              stripe
              style="width: 100%"
              v-loading="alertsLoading"
              class="data-table"
              :row-class-name="() => 'hover-effect-row'"
              :header-cell-class-name="'custom-table-header'"
              highlight-current-row
            >
              <el-table-column prop="id" label="ID" width="80" align="center" />
              <el-table-column label="级别" width="100" align="center">
                <template #default="scope">
                  <el-tag 
                    :type="getAlertGrade(scope.row.grade).type" 
                    effect="dark"
                    size="small"
                    class="card-tag level-tag"
                  >
                    {{ getAlertGrade(scope.row.grade).label }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="类型" width="120" align="center">
                <template #default="scope">
                  <span class="alert-type">{{ getAlertTypeName(scope.row.alert_type) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="message" label="告警信息" min-width="250" show-overflow-tooltip>
                <template #default="scope">
                  <div class="alert-message-cell">{{ scope.row.message }}</div>
                </template>
              </el-table-column>
              <el-table-column label="区域" width="200">
                <template #default="scope">
                  <div v-if="scope.row.area && scope.row.area_name && scope.row.area_name !== '未知区域'" class="area-tags">
                    <el-tag size="small" effect="plain" class="card-tag area-tag">{{ scope.row.area_name }}</el-tag>
                  </div>
                  <span v-else-if="scope.row.area && (!scope.row.area_name || scope.row.area_name === '未知区域')" class="loading-area">
                    加载区域中...
                  </span>
                  <span v-else class="no-area">未指定区域</span>
                </template>
              </el-table-column>
              <el-table-column label="时间" width="180">
                <template #default="scope">
                  <div class="time-cell">
                    <el-icon><clock /></el-icon>
                    <span class="timestamp">{{ formatDate(scope.row.timestamp) }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="100" align="center">
                <template #default="scope">
                  <el-tag 
                    :type="scope.row.solved ? 'success' : 'danger'"
                    size="small"
                    class="card-tag status-tag"
                  >
                    {{ scope.row.solved ? '已处理' : '未处理' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="180" align="center">
                <template #default="scope">
                  <div class="action-buttons">
                    <el-button 
                      type="primary" 
                      :icon="View" 
                      circle 
                      size="small"
                      @click="showAlertDetail(scope.row)"
                      title="查看详情"
                      class="action-button view-button"
                    />
                    <el-button 
                      v-if="!scope.row.solved && isStaffOrAdmin"
                      type="success" 
                      :icon="Check" 
                      circle 
                      size="small"
                      @click="solveAlert(scope.row.id)"
                      title="标记为已解决"
                      class="action-button solve-button"
                    />
                  </div>
                </template>
              </el-table-column>
            </el-table>
            
            <div class="empty-placeholder" v-if="paginatedAlerts.length === 0 && !alertsLoading">
              <el-empty description="暂无告警数据" />
            </div>
          </div>
          
          <!-- 卡片视图 - 根据视图模式决定是否显示 -->
          <div v-if="actualViewMode === 'card'" class="cards-container">
            <div v-if="alertsLoading" class="cards-loading">
              <el-skeleton :rows="3" animated />
              <el-skeleton :rows="3" animated style="margin-top: 20px" />
            </div>
            <div v-else-if="paginatedAlerts.length === 0" class="empty-placeholder">
              <el-empty description="暂无告警数据" />
            </div>
            <div v-else class="alert-cards">
              <div 
                v-for="alert in paginatedAlerts" 
                :key="alert.id"
                class="alert-card"
                :data-grade="alert.grade"
                @click="showAlertDetail(alert)"
              >
                <div class="card-header">
                  <div class="card-header-left">
                    <div class="card-id">#{{ alert.id }}</div>
                    <el-tag 
                      :type="getAlertGrade(alert.grade).type" 
                      effect="dark"
                      size="small"
                      class="card-tag level-tag"
                    >
                      {{ getAlertGrade(alert.grade).label }}
                    </el-tag>
                    <span class="alert-type-badge">{{ getAlertTypeName(alert.alert_type) }}</span>
                  </div>
                  <el-tag 
                    :type="alert.solved ? 'success' : 'danger'"
                    size="small"
                    class="card-tag status-tag"
                  >
                    {{ alert.solved ? '已处理' : '未处理' }}
                  </el-tag>
                </div>
                
                <div class="card-content">
                  {{ alert.message }}
                </div>
                
                <div class="card-footer">
                  <div class="card-footer-left">
                    <div class="card-area">
                      <i class="el-icon-location"></i>
                      {{ alert.area_name || '未指定区域' }}
                    </div>
                    <div class="card-time">
                      <el-icon><Clock /></el-icon>
                      {{ formatDate(alert.timestamp).split(' ').join(' ') }}
                    </div>
                  </div>
                  <div class="card-actions">
                    <el-button 
                      v-if="!alert.solved && isStaffOrAdmin"
                      type="success" 
                      size="small"
                      @click.stop="solveAlert(alert.id)"
                      class="solve-button-compact"
                    >
                      解决
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="pagination-container" v-if="filteredAlerts.length > 0">
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              :layout="isMobileView ? 'prev, pager, next' : 'total, prev, pager, next, jumper'"
              :total="filteredAlerts.length"
              @current-change="handlePageChange"
              background
            />
          </div>
        </el-tab-pane>
        
        <el-tab-pane name="notices" lazy>
          <template #label>
            <div class="tab-label">
              <el-icon><Document /></el-icon>
              <span>通知公告</span>
            </div>
          </template>
          <!-- 过滤栏保持不变 -->
          <div class="filter-bar">
            <div class="left-section">
              <el-button 
                v-if="isStaffOrAdmin"
                type="primary" 
                :icon="Plus"
                @click="noticeDialogVisible = true"
                class="action-button"
              >
                发布通知
              </el-button>
            </div>
            
            <div class="right-section">
              <el-input
                v-model="searchText"
                placeholder="搜索通知内容..."
                class="search-input"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </div>
          </div>
          
          <!-- 表格视图 - 根据视图模式决定是否显示 -->
          <div v-if="actualViewMode === 'table'" class="table-container">
            <el-table
              :data="paginatedNotices"
              stripe
              style="width: 100%"
              v-loading="noticesLoading"
              class="data-table"
              :row-class-name="() => 'hover-effect-row'"
              :header-cell-class-name="'custom-table-header'"
              highlight-current-row
            >
              <el-table-column prop="id" label="ID" width="80" align="center" />
              <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip>
                <template #default="scope">
                  <div class="notice-title-cell">{{ scope.row.title }}</div>
                </template>
              </el-table-column>
              <el-table-column prop="content" label="内容" min-width="250" show-overflow-tooltip>
                <template #default="scope">
                  <div class="notice-content-cell">{{ scope.row.content }}</div>
                </template>
              </el-table-column>
              <el-table-column label="关联区域" width="200">
                <template #default="scope">
                  <div v-if="scope.row.related_areas && scope.row.related_areas.length" class="area-tags">
                    <el-tag 
                      v-for="areaId in scope.row.related_areas" 
                      :key="areaId"
                      size="small" 
                      effect="plain"
                      class="card-tag area-tag"
                    >
                      {{ getAreaName(areaId) }}
                    </el-tag>
                  </div>
                  <span v-else class="no-area">全校范围</span>
                </template>
              </el-table-column>
              <el-table-column label="发布时间" width="180">
                <template #default="scope">
                  <div class="time-cell">
                    <el-icon><Clock /></el-icon>
                    <span class="timestamp">{{ formatDate(scope.row.timestamp) }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="publisher_name" label="发布者" width="120" />
              <el-table-column label="操作" width="120" align="center">
                <template #default="scope">
                  <el-button 
                    type="primary" 
                    :icon="View" 
                    circle 
                    size="small"
                    @click="showNoticeDetail(scope.row)"
                    title="查看详情"
                    class="action-button view-button"
                  />
                </template>
              </el-table-column>
            </el-table>
            
            <div class="empty-placeholder" v-if="paginatedNotices.length === 0 && !noticesLoading">
              <el-empty description="暂无通知数据" />
            </div>
          </div>
          
          <!-- 卡片视图 - 根据视图模式决定是否显示 -->
          <div v-if="actualViewMode === 'card'" class="cards-container">
            <div v-if="noticesLoading" class="cards-loading">
              <el-skeleton :rows="3" animated />
              <el-skeleton :rows="3" animated style="margin-top: 20px" />
            </div>
            <div v-else-if="paginatedNotices.length === 0" class="empty-placeholder">
              <el-empty description="暂无通知数据" />
            </div>
            <div v-else class="notice-cards">
              <div 
                v-for="notice in paginatedNotices" 
                :key="notice.id"
                class="notice-card"
                @click="showNoticeDetail(notice)"
              >
                <div class="card-header">
                  <h3 class="notice-card-title">{{ notice.title }}</h3>
                
                </div>
                
                <div class="card-content notice-content">
                  {{ notice.content }}
                </div>
                
                <div class="card-footer">
                  <div class="card-footer-left">
                    <div class="card-area">
                      <template v-if="notice.related_areas && notice.related_areas.length">
                        <el-tag 
                          v-for="areaId in notice.related_areas.slice(0, 1)" 
                          :key="areaId"
                          size="small" 
                          effect="plain"
                          class="card-tag area-tag"
                        >
                          {{ getAreaName(areaId) }}
                        </el-tag>
                        <template v-if="notice.related_areas.length > 1">
                          <span class="more-areas">+{{ notice.related_areas.length - 1 }}</span>
                        </template>
                      </template>
                      <template v-else>全校范围</template>
                    </div>
                    <div class="card-time">
                      <el-icon><Clock /></el-icon>
                      {{ formatDate(notice.timestamp).split(' ').join(' ') }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="pagination-container" v-if="filteredNotices.length > 0">
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              :layout="isMobileView ? 'prev, pager, next' : 'total, prev, pager, next, jumper'"
              :total="filteredNotices.length"
              @current-change="handlePageChange"
              background
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- PC端展示对话框，移动端隐藏 -->
    <el-dialog
      v-model="noticeDialogVisible"
      title="发布新通知"
      width="600px"
      destroy-on-close
      class="detail-dialog"
      v-if="!isMobileView"
    >
      <el-form :model="noticeForm" label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="noticeForm.title" placeholder="请输入通知标题" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="noticeForm.content"
            type="textarea"
            :rows="5"
            placeholder="请输入通知内容"
          />
        </el-form-item>
        <el-form-item label="关联区域">
          <el-select
            v-model="noticeForm.related_areas"
            multiple
            placeholder="选择关联区域（可多选，不选则为全校通知）"
            style="width: 100%"
          >
            <el-option
              v-for="area in areas"
              :key="area.id"
              :label="area.name"
              :value="area.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="noticeDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitNotice" :loading="noticeSubmitting">
            发布
          </el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 移动端展示抽屉，PC端隐藏 -->
    <el-drawer
      v-model="noticeDialogVisible"
      title="发布新通知"
      :direction="drawerDirection"
      :size="drawerSize"
      destroy-on-close
      class="mobile-drawer"
      v-if="isMobileView"
    >
      <div class="drawer-content compact-drawer">
        <el-form :model="noticeForm" label-width="70px" class="compact-form">
          <el-form-item label="标题">
            <el-input v-model="noticeForm.title" placeholder="请输入通知标题" />
          </el-form-item>
          <el-form-item label="内容">
            <el-input
              v-model="noticeForm.content"
              type="textarea"
              :rows="4"
              placeholder="请输入通知内容"
            />
          </el-form-item>
          <el-form-item label="关联区域">
            <el-select
              v-model="noticeForm.related_areas"
              multiple
              placeholder="选择关联区域（可多选，不选则为全校通知）"
              style="width: 100%"
            >
              <el-option
                v-for="area in areas"
                :key="area.id"
                :label="area.name"
                :value="area.id"
              />
            </el-select>
          </el-form-item>
        </el-form>
        <div class="drawer-footer">
          <el-button @click="noticeDialogVisible = false" class="drawer-btn">取消</el-button>
          <el-button type="primary" @click="submitNotice" :loading="noticeSubmitting" class="drawer-btn">
            发布
          </el-button>
        </div>
      </div>
    </el-drawer>

    <!-- PC端告警详情对话框 -->
    <el-dialog
      v-model="alertDetailVisible"
      title="告警详情"
      width="700px"
      @closed="closeAlertDetail"
      class="detail-dialog"
      v-if="!isMobileView"
    >
      <div v-if="currentAlertDetail" class="detail-content">
        <div class="detail-header">
          <div class="header-left">
            <el-tag 
              :type="getAlertGrade(currentAlertDetail.grade).type" 
              effect="dark"
              size="large"
              class="detail-tag"
            >
              {{ getAlertGrade(currentAlertDetail.grade).label }}
            </el-tag>
            <span class="detail-type">{{ getAlertTypeName(currentAlertDetail.alert_type) }}</span>
          </div>
          <div class="header-right">
            <el-tag 
              :type="currentAlertDetail.solved ? 'success' : 'danger'"
              effect="light"
              class="status-detail-tag"
            >
              {{ currentAlertDetail.solved ? '已处理' : '未处理' }}
            </el-tag>
          </div>
        </div>
        
        <el-divider content-position="left">基本信息</el-divider>
        
        <div class="info-grid">
          <div class="info-item">
            <div class="info-label">告警ID</div>
            <div class="info-value">#{{ currentAlertDetail.id }}</div>
          </div>
          
          <div class="info-item">
            <div class="info-label">告警区域</div>
            <div class="info-value">
              <el-tag v-if="currentAlertDetail.area_name" size="small" effect="plain" class="area-detail-tag">
                {{ currentAlertDetail.area_name }}
              </el-tag>
              <span v-else class="no-area">未指定区域</span>
            </div>
          </div>
          
          <div class="info-item">
            <div class="info-label">告警时间</div>
            <div class="info-value timestamp-value">{{ formatDate(currentAlertDetail.timestamp) }}</div>
          </div>
          
          <div class="info-item">
            <div class="info-label">公开状态</div>
            <div class="info-value">
              <el-tag 
                :type="currentAlertDetail.publicity ? 'success' : 'info'" 
                effect="light"
                size="small"
              >
                {{ currentAlertDetail.publicity ? '公开' : '内部' }}
              </el-tag>
            </div>
          </div>
        </div>
        
        <el-divider content-position="left">告警详情</el-divider>
        
        <div class="message-container">
          <div class="message-content">{{ currentAlertDetail.message }}</div>
        </div>
        
        <div class="actions-container" v-if="!currentAlertDetail.solved && isStaffOrAdmin">
          <el-button 
            type="success" 
            @click="solveAlert(currentAlertDetail.id)"
            :icon="Check"
            class="detail-action-button"
          >
            标记为已解决
          </el-button>
        </div>
      </div>
    </el-dialog>
    
    <!-- 移动端告警详情抽屉 -->
    <el-drawer
      v-model="alertDetailVisible"
      title="告警详情"
      :direction="drawerDirection"
      :size="drawerSize"
      @closed="closeAlertDetail"
      class="mobile-drawer"
      v-if="isMobileView"
    >
      <div v-if="currentAlertDetail" class="detail-content drawer-content compact-drawer">
        <div class="compact-header">
          <div class="compact-header-row">
            <el-tag 
              :type="getAlertGrade(currentAlertDetail.grade).type" 
              effect="dark"
              size="small"
              class="detail-tag"
            >
              {{ getAlertGrade(currentAlertDetail.grade).label }}
            </el-tag>
            <span class="detail-type compact-type">{{ getAlertTypeName(currentAlertDetail.alert_type) }}</span>
            <el-tag 
              :type="currentAlertDetail.solved ? 'success' : 'danger'"
              effect="light"
              size="small"
              class="status-compact-tag"
            >
              {{ currentAlertDetail.solved ? '已处理' : '未处理' }}
            </el-tag>
          </div>
        </div>
        
        <el-divider content-position="left" class="compact-divider">基本信息</el-divider>
        
        <div class="compact-info-grid">
          <div class="compact-info-item">
            <span class="compact-info-label">告警ID:</span>
            <span class="compact-info-value">#{{ currentAlertDetail.id }}</span>
          </div>
          
          <div class="compact-info-item">
            <span class="compact-info-label">区域:</span>
            <span class="compact-info-value">
              <el-tag v-if="currentAlertDetail.area_name" size="small" effect="plain" class="area-detail-tag">
                {{ currentAlertDetail.area_name }}
              </el-tag>
              <span v-else class="no-area">未指定区域</span>
            </span>
          </div>
          
          <div class="compact-info-item">
            <span class="compact-info-label">时间:</span>
            <span class="compact-info-value timestamp-value">{{ formatDate(currentAlertDetail.timestamp) }}</span>
          </div>
          
          <div class="compact-info-item">
            <span class="compact-info-label">公开性:</span>
            <span class="compact-info-value">
              <el-tag 
                :type="currentAlertDetail.publicity ? 'success' : 'info'" 
                effect="light"
                size="small"
              >
                {{ currentAlertDetail.publicity ? '公开' : '内部' }}
              </el-tag>
            </span>
          </div>
        </div>
        
        <el-divider content-position="left" class="compact-divider">告警详情</el-divider>
        
        <div class="compact-message-container">
          <div class="message-content">{{ currentAlertDetail.message }}</div>
        </div>
        
        <div class="actions-container" v-if="!currentAlertDetail.solved && isStaffOrAdmin">
          <el-button 
            type="success" 
            @click="solveAlert(currentAlertDetail.id)"
            :icon="Check"
            class="detail-action-button mobile-action-button"
          >
            标记为已解决
          </el-button>
        </div>
      </div>
    </el-drawer>

    <!-- PC端通知详情对话框 -->
    <el-dialog
      v-model="noticeDetailVisible"
      title="通知详情"
      width="700px"
      @closed="closeNoticeDetail"
      class="detail-dialog"
      v-if="!isMobileView"
    >
      <div v-if="currentNoticeDetail" class="detail-content">
        <div class="notice-detail-header">
          <h3 class="notice-detail-title">{{ currentNoticeDetail.title }}</h3>
        </div>
        
        <el-divider content-position="left">基本信息</el-divider>
        
        <div class="info-grid">
          <div class="info-item">
            <div class="info-label">通知ID</div>
            <div class="info-value">#{{ currentNoticeDetail.id }}</div>
          </div>
          
          <div class="info-item">
            <div class="info-label">发布时间</div>
            <div class="info-value timestamp-value">{{ formatDate(currentNoticeDetail.timestamp) }}</div>
          </div>
          
          <div class="info-item">
            <div class="info-label">关联区域</div>
            <div class="info-value">
              <div v-if="currentNoticeDetail.related_areas && currentNoticeDetail.related_areas.length" class="area-detail-tags">
                <el-tag 
                  v-for="areaId in currentNoticeDetail.related_areas" 
                  :key="areaId"
                  size="small" 
                  effect="plain"
                  class="area-detail-tag"
                >
                  {{ getAreaName(areaId) }}
                </el-tag>
              </div>
              <span v-else class="no-area">全校范围</span>
            </div>
          </div>
        </div>
        
        <el-divider content-position="left">通知内容</el-divider>
        
        <div class="message-container">
          <div class="message-content">{{ currentNoticeDetail.content }}</div>
        </div>
      </div>
    </el-dialog>
    
    <!-- 移动端通知详情抽屉 -->
    <el-drawer
      v-model="noticeDetailVisible"
      title="通知详情"
      :direction="drawerDirection"
      :size="drawerSize"
      @closed="closeNoticeDetail"
      class="mobile-drawer"
      v-if="isMobileView"
    >
      <div v-if="currentNoticeDetail" class="detail-content drawer-content compact-drawer">
        <h3 class="compact-notice-title">{{ currentNoticeDetail.title }}</h3>
        
        <el-divider content-position="left" class="compact-divider">基本信息</el-divider>
        
        <div class="compact-info-grid">
          <div class="compact-info-item">
            <span class="compact-info-label">通知ID:</span>
            <span class="compact-info-value">#{{ currentNoticeDetail.id }}</span>
          </div>
          
          <div class="compact-info-item">
            <span class="compact-info-label">时间:</span>
            <span class="compact-info-value timestamp-value">{{ formatDate(currentNoticeDetail.timestamp) }}</span>
          </div>
          
          <div class="compact-info-item">
            <span class="compact-info-label">区域:</span>
            <span class="compact-info-value">
              <div v-if="currentNoticeDetail.related_areas && currentNoticeDetail.related_areas.length" class="area-detail-tags">
                <el-tag 
                  v-for="areaId in currentNoticeDetail.related_areas" 
                  :key="areaId"
                  size="small" 
                  effect="plain"
                  class="area-detail-tag"
                >
                  {{ getAreaName(areaId) }}
                </el-tag>
              </div>
              <span v-else class="no-area">全校范围</span>
            </span>
          </div>
        </div>
        
        <el-divider content-position="left" class="compact-divider">通知内容</el-divider>
        
        <div class="compact-message-container">
          <div class="message-content">{{ currentNoticeDetail.content }}</div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>

.alert-notice-container {
  max-width: 1400px;
  margin: 20px auto;
  padding: 0 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px 24px;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
}

.title-section {
  display: flex;
  align-items: center;
}

.page-title {
  margin: 0;
  font-size: 22px;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #333;
  font-weight: 600;
}

.header-icon {
  font-size: 24px;
  color: #409EFF;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.view-mode-button {
  background-color: #f4f6fa;
  border-color: #ebeef5;
}

.main-content {
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.06);
  padding: 24px;
  min-height: 600px;
}

.custom-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
  border-bottom: 1px solid #e8eaec;
}

.custom-tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: transparent;
}

.custom-tabs :deep(.el-tabs__nav) {
  border-radius: 4px;
}

.custom-tabs :deep(.el-tabs__item) {
  font-size: 16px;
  height: 50px;
  line-height: 50px;
  transition: all 0.3s;
  padding: 0 20px;
}

.custom-tabs :deep(.el-tabs__item.is-active) {
  font-weight: 600;
  color: #409EFF;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
  align-items: center;
  background-color: #f8f9fa;
  padding: 15px 20px;
  border-radius: 8px;
}

.left-section, .right-section {
  display: flex;
  gap: 10px;
  align-items: center;
}

.filter-select {
  width: 160px;
}

.search-input {
  width: 280px;
}

.table-container {
  background-color: #fff;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
  min-height: 350px;
}

.data-table {
  width: 100%;
}

.custom-table-header {
  background-color: #f4f6fa !important;
  color: #606266;
  font-weight: 600;
}

.hover-effect-row {
  transition: all 0.2s ease;
  cursor: pointer;
}

.hover-effect-row:hover {
  background-color: #f0f9ff !important;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.alert-message-cell, .notice-title-cell, .notice-content-cell {
  font-size: 14px;
  color: #303133;
  line-height: 1.6;
  padding: 4px 0;
}

.notice-title-cell {
  font-weight: 600;
}

.time-cell {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #909399;
}

.timestamp {
  color: #909399;
  font-size: 13px;
}

.alert-type {
  padding: 4px 8px;
  background-color: #f0f9ff;
  color: #409EFF;
  border-radius: 15px;
  font-weight: 600;
  display: inline-block;
}

.card-tag {
  margin: 2px;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 600;
}

.level-tag {
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-tag {
  padding: 4px 10px;
}

.area-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.area-tag {
  background-color: #f0f7ff;
  color: #4b83d2;
  border-color: #d3e5fc;
}

.no-area {
  color: #909399;
  font-style: italic;
  font-size: 13px;
}

.loading-area {
  color: #909399;
  font-style: italic;
  font-size: 13px;
  display: inline-block;
  padding: 2px 0;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 10px;
}

.action-button {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
}

.action-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.view-button {
  background-color: #ecf5ff;
  border-color: #d9ecff;
  color: #409EFF;
}

.solve-button {
  background-color: #f0f9eb;
  border-color: #e1f3d8;
  color: #67C23A;
}

.cards-container {
  padding: 5px 0;
  min-height: 350px;
}

.alert-cards, .notice-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 15px;
}

.alert-card, .notice-card {
  background: white;
  border-radius: 6px;
  padding: 12px;
  box-shadow: 0 2px 8px 0 rgba(0, 0, 0, 0.06);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  border-left: 3px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.alert-card:hover, .notice-card:hover {
  box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.alert-card[data-grade="3"] {
  border-left-color: #F56C6C;
}

.alert-card[data-grade="2"] {
  border-left-color: #E6A23C;
}

.alert-card[data-grade="1"] {
  border-left-color: #67C23A;
}

.alert-card[data-grade="0"] {
  border-left-color: #909399;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.card-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.card-id {
  font-weight: 600;
  color: #606266;
  font-size: 13px;
}

.card-publisher {
  font-size: 12px;
  color: #909399;
  font-weight: 500;
}

.card-tag {
  margin: 0;
  padding: 0 6px;
  height: 20px;
  line-height: 20px;
  border-radius: 10px;
  font-weight: 500;
  font-size: 11px;
}

.level-tag {
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-tag {
  padding: 0 8px;
}

.alert-type-badge {
  font-size: 12px;
  font-weight: 600;
  color: #409EFF;
  background-color: #ecf5ff;
  padding: 0 6px;
  height: 20px;
  line-height: 20px;
  border-radius: 10px;
  display: inline-block;
}

.card-content {
  color: #303133;
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

.notice-card-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #909399;
  border-top: 1px dashed #ebeef5;
  padding-top: 8px;
}

.card-footer-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-area {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.card-time {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #909399;
}

.card-actions {
  display: flex;
  align-items: center;
}

.solve-button-compact {
  height: 24px;
  padding: 0 10px;
  font-size: 12px;
}

.more-areas {
  font-size: 11px;
  color: #909399;
  background: #f5f7fa;
  padding: 0 4px;
  border-radius: 10px;
}

.area-tag {
  background-color: #f0f7ff;
  color: #4b83d2;
  border-color: #d3e5fc;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin: 20px 0 10px;
}

.empty-placeholder {
  padding: 40px 0;
  display: flex;
  justify-content: center;
  background-color: #fafafa;
  border-radius: 8px;
  margin: 20px 0;
  min-height: 200px;
}

.detail-dialog :deep(.el-dialog__header) {
  background-color: #f4f7fc;
  border-bottom: 1px solid #e4e7ed;
  padding: 15px 20px;
  margin-right: 0;
}

.detail-dialog :deep(.el-dialog__title) {
  font-weight: 600;
  font-size: 18px;
  color: #303133;
}

.detail-dialog :deep(.el-dialog__body) {
  padding: 20px 30px;
}

.detail-content {
  padding: 0;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-tag {
  font-size: 16px;
  padding: 6px 12px;
  border-radius: 15px;
}

.status-detail-tag {
  font-size: 14px;
  padding: 6px 12px;
  border-radius: 15px;
}

.detail-type {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin: 20px 0;
}

.info-item {
  background-color: #f9fafc;
  border-radius: 8px;
  padding: 12px 15px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
}

.info-item:hover {
  background-color: #f5f7fa;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

.info-label {
  color: #606266;
  font-size: 14px;
  margin-bottom: 8px;
  font-weight: 600;
}

.info-value {
  color: #303133;
  font-size: 15px;
}

.timestamp-value {
  color: #606266;
}

.area-detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.area-detail-tag {
  background-color: #f0f7ff;
  border-color: #d3e5fc;
  color: #4b83d2;
}

.message-container {
  background-color: #f9fafc;
  border-radius: 8px;
  padding: 20px;
  margin: 20px 0;
  border-left: 4px solid #409EFF;
  min-height: 100px;
}

.message-content {
  font-size: 15px;
  line-height: 1.8;
  color: #303133;
  white-space: pre-wrap;
}

.notice-detail-header {
  text-align: center;
  margin-bottom: 15px;
}

.notice-detail-title {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  margin: 0;
  padding: 10px 0;
  position: relative;
  display: inline-block;
}

.notice-detail-title::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 10%;
  right: 10%;
  height: 3px;
  background-color: #409EFF;
  border-radius: 3px;
}

.actions-container {
  margin-top: 30px;
  display: flex;
  justify-content: center;
}

.detail-action-button {
  padding: 10px 20px;
  font-size: 15px;
  border-radius: 20px;
  font-weight: 600;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
}

.detail-action-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 12px rgba(0, 0, 0, 0.15);
}

@media (max-width: 768px) {
  .alert-notice-container {
    padding: 0 10px;
    margin: 10px auto;
  }
  
  .page-header {
    padding: 12px 15px;
    margin-bottom: 10px;
  }
  
  .page-title {
    font-size: 18px;
  }
  
  .header-icon {
    font-size: 20px;
  }
  
  .main-content {
    padding: 15px;
    border-radius: 8px;
  }
  
  .filter-bar {
    flex-direction: column;
    gap: 15px;
    padding: 12px;
  }
  
  .left-section, .right-section {
    width: 100%;
  }
  
  .filter-select, .search-input {
    width: 100%;
  }
  
  .custom-tabs :deep(.el-tabs__item) {
    font-size: 14px;
    height: 40px;
    line-height: 40px;
    padding: 0 10px;
  }
  
  .tab-label {
    font-size: 14px;
    gap: 5px;
  }
  
  .detail-dialog :deep(.el-dialog) {
    width: 95% !important;
    margin: 0 auto !important;
  }
  
  .detail-dialog :deep(.el-dialog__body) {
    padding: 15px;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }
  
  .detail-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .header-right {
    align-self: flex-end;
  }
  
  .detail-tag, .status-detail-tag {
    font-size: 12px;
    padding: 4px 8px;
  }
  
  .detail-type {
    font-size: 16px;
  }
  
  .notice-detail-title {
    font-size: 18px;
  }
  
  .message-container {
    padding: 15px;
  }
  
  .message-content {
    font-size: 14px;
    line-height: 1.6;
  }
  
  .pagination-container :deep(.el-pagination) {
    padding: 5px 0;
    justify-content: center;
    flex-wrap: wrap;
  }
}

@media (max-width: 576px) {
  .card-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .card-area {
    max-width: 100%;
  }
  
  .card-time {
    align-items: flex-start;
  }
}

.alert-card, .notice-card {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.cards-container, .table-container {
  transition: opacity 0.3s ease;
}

.mobile-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 10px 15px;
  background-color: #f4f7fc;
  border-bottom: 1px solid #e4e7ed;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.drawer-content {
  padding: 0 15px 15px;
  height: 100%;
  overflow-y: auto;
}

.compact-drawer {
  padding: 0 12px 12px;
}

.compact-form :deep(.el-form-item) {
  margin-bottom: 12px;
}

.compact-header {
  margin-bottom: 10px;
}

.compact-header-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 10px;
}

.compact-type {
  font-size: 16px;
  font-weight: 600;
}

.status-compact-tag {
  font-size: 12px;
  padding: 0 8px;
  margin-left: auto;
}

.compact-divider {
  margin: 10px 0;
  padding: 0 10px;
}

.compact-divider :deep(.el-divider__text) {
  font-size: 14px;
  padding: 0 10px;
  background-color: #fff;
}

.compact-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  padding: 10px;
}

.compact-info-item {
  background-color: #f9fafc;
  border-radius: 6px;
  padding: 8px 10px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.compact-info-label {
  color: #606266;
  font-size: 12px;
  font-weight: 500;
}

.compact-info-value {
  color: #303133;
  font-size: 14px;
}

.compact-message-container {
  background-color: #f9fafc;
  border-radius: 6px;
  padding: 10px 12px;
  margin: 10px;
  border-left: 3px solid #409EFF;
}

.compact-notice-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 8px 0;
  padding-bottom: 6px;
  border-bottom: 2px solid #409EFF;
  display: inline-block;
}

.mobile-detail-header, .mobile-notice-header {
  flex-direction: column;
  gap: 10px;
}

.mobile-detail-header .header-right {
  margin-top: 10px;
  align-self: flex-start;
}

.mobile-action-button {
  width: 100%;
  margin-top: 15px;
  height: 40px;
}

.drawer-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 15px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}

.drawer-btn {
  flex: 1;
  margin: 0 5px;
}

@media (max-width: 768px) {  
  .mobile-drawer :deep(.el-drawer__body) {
    padding: 0;
  }
  
  .compact-info-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 480px) {
  .compact-info-grid {
    grid-template-columns: 1fr;
  }
}
</style>