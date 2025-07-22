<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, computed, watch, onBeforeMount } from 'vue'
import { useAuthStore } from '../stores/auth'
import { areaService, alertService, noticeService } from '../services'
import apiService from '../services'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Bell, Warning, Document, Plus, Check, Search, Refresh, View, Clock, Grid, List, Location, User } from '@element-plus/icons-vue'
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
  apiService.setCacheDuration('alerts', 30000);
  apiService.setCacheDuration('notice', 30000);
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

    <div class="main-content">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange" class="custom-tabs">
        <!-- 告警信息标签页 -->
        <el-tab-pane name="alerts" lazy>
          <template #label>
            <div class="tab-label">
              <el-icon><Warning /></el-icon>
              <span>告警信息</span>
            </div>
          </template>

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

          <!-- 表格视图 -->
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
              @row-click="showAlertDetail"
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
                    <el-icon><Clock /></el-icon>
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
                      @click.stop="showAlertDetail(scope.row)"
                      title="查看详情"
                      class="action-button view-button"
                    />
                    <el-button 
                      v-if="!scope.row.solved && isStaffOrAdmin"
                      type="success" 
                      :icon="Check" 
                      circle 
                      size="small"
                      @click.stop="solveAlert(scope.row.id)"
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

          <!-- 卡片视图 -->
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
                      <el-icon><Location /></el-icon>
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
                      <el-icon><Check /></el-icon>解决
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
        
        <!-- 通知公告标签页 -->
        <el-tab-pane name="notices" lazy>
          <template #label>
            <div class="tab-label">
              <el-icon><Document /></el-icon>
              <span>通知公告</span>
            </div>
          </template>

          <div class="filter-bar">
            <div class="left-section">
              <el-button 
                v-if="isStaffOrAdmin"
                type="primary" 
                class="action-button publish-button"
                @click="noticeDialogVisible = true"
              >
                <el-icon><Plus /></el-icon>
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

          <!-- 表格视图 -->
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
              @row-click="showNoticeDetail"
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
                      v-for="areaId in scope.row.related_areas.slice(0, 2)" 
                      :key="areaId"
                      size="small" 
                      effect="plain"
                      class="card-tag area-tag"
                    >
                      {{ getAreaName(areaId) }}
                    </el-tag>
                    <el-tag v-if="scope.row.related_areas.length > 2" size="small" type="info" effect="plain">
                      +{{ scope.row.related_areas.length - 2 }}
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
                    @click.stop="showNoticeDetail(scope.row)"
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

          <!-- 卡片视图 -->
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
                      <el-icon><Location /></el-icon>
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
                  <div class="publisher" v-if="notice.publisher_name">
                    <el-icon><User /></el-icon>
                    {{ notice.publisher_name }}
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

    <!-- 发布通知对话框 -->
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
            collapse-tags
            collapse-tags-tooltip
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

    <!-- 移动端抽屉 -->
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
              collapse-tags
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

    <!-- 告警详情对话框 -->
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

    <!-- 通知详情对话框 -->
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
            <div class="info-label">发布者</div>
            <div class="info-value">{{ currentNoticeDetail.publisher_name || '系统' }}</div>
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
            <span class="compact-info-label">发布者:</span>
            <span class="compact-info-value">{{ currentNoticeDetail.publisher_name || '系统' }}</span>
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
  background: #f8f9fb;
  min-height: calc(100vh - 40px);
  border-radius: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 18px 24px;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(26, 58, 145, 0.15);
  border: none;
  color: white;
  position: relative;
  overflow: hidden;
}

.page-header::before {
  content: "";
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 60%);
  opacity: 0.3;
  pointer-events: none;
}

.title-section {
  display: flex;
  align-items: center;
  position: relative;
  z-index: 1;
}

.page-title {
  margin: 0;
  font-size: 24px;
  display: flex;
  align-items: center;
  gap: 14px;
  color: white;
  font-weight: 600;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.header-icon {
  font-size: 28px;
  color: #ffd54f;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

.header-actions {
  display: flex;
  gap: 12px;
  position: relative;
  z-index: 1;
}

.view-mode-button {
  background-color: rgba(255, 255, 255, 0.15);
  border-color: transparent;
  color: white;
  transition: all 0.3s;
}

.view-mode-button:hover {
  background-color: rgba(255, 255, 255, 0.25);
  transform: translateY(-2px);
}

.main-content {
  background-color: #fff;
  border-radius: 14px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
  padding: 24px 28px;
  min-height: 600px;
  border: 1px solid #e6e9ed;
  position: relative;
  overflow: hidden;
}

.main-content::after {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
  z-index: 1;
}

.custom-tabs :deep(.el-tabs__header) {
  margin-bottom: 25px;
  border-bottom: 1px solid #e8eaec;
  position: relative;
}

.custom-tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: transparent;
}

.custom-tabs :deep(.el-tabs__active-bar) {
  background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
  height: 3px;
  border-radius: 3px;
}

.custom-tabs :deep(.el-tabs__nav) {
  border-radius: 6px;
}

.custom-tabs :deep(.el-tabs__item) {
  font-size: 16px;
  height: 54px;
  line-height: 54px;
  transition: all 0.3s;
  padding: 0 25px;
  color: #606266;
}

.custom-tabs :deep(.el-tabs__item.is-active) {
  font-weight: 600;
  color: #4facfe;
}

.custom-tabs :deep(.el-tabs__item:hover) {
  color: #4facfe;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 24px;
  align-items: center;
  background: linear-gradient(to right, #f0f5ff, #eef7fe);
  padding: 16px 24px;
  border-radius: 12px;
  border: 1px solid #e1eaff;
  box-shadow: 0 4px 12px rgba(100, 150, 255, 0.05);
}

.left-section, .right-section {
  display: flex;
  gap: 12px;
  align-items: center;
}

.filter-select {
  width: 160px;
}

.filter-select :deep(.el-input__inner) {
  border-radius: 8px;
  border: 1px solid #c0d8ff;
}

.search-input {
  width: 300px;
}

.search-input :deep(.el-input__inner) {
  border-radius: 8px;
  border: 1px solid #c0d8ff;
  padding-left: 40px;
  background-color: rgba(255, 255, 255, 0.8);
  transition: all 0.3s;
}

.search-input :deep(.el-input__inner:focus) {
  border-color: #4facfe;
  box-shadow: 0 0 0 2px rgba(79, 172, 254, 0.2);
  background-color: white;
}

.search-input :deep(.el-input__prefix) {
  left: 12px;
  color: #4facfe;
}

.table-container {
  background-color: #fff;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  min-height: 350px;
  border: 1px solid #ebeef5;
  transition: transform 0.3s, box-shadow 0.3s;
}

.table-container:hover {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.data-table {
  width: 100%;
}

.data-table :deep(th.el-table__cell) {
  background: linear-gradient(to right, #f4f7fc, #e9f0fd) !important;
  color: #334466;
  font-weight: 600;
  padding: 14px 0;
  border-bottom: 2px solid #e0e9ff;
}

.data-table :deep(.el-table__row) {
  transition: all 0.2s ease;
}

.hover-effect-row {
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
  padding: 6px 0;
}

.notice-title-cell {
  font-weight: 600;
  color: #4168b4;
}

.time-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #7a8baa;
}

.timestamp {
  color: #7a8baa;
  font-size: 13px;
}

.alert-type {
  padding: 5px 10px;
  background: linear-gradient(135deg, #e0f2ff, #d4eeff);
  color: #0077cc;
  border-radius: 20px;
  font-weight: 600;
  display: inline-block;
  box-shadow: 0 2px 4px rgba(0, 119, 204, 0.1);
}

.card-tag {
  margin: 2px;
  padding: 2px 10px;
  border-radius: 12px;
  font-weight: 600;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.level-tag {
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-tag {
  padding: 4px 12px;
}

.area-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.area-tag {
  background: linear-gradient(135deg, #f0f7ff, #e6f2ff);
  color: #4b83d2;
  border-color: #d3e5fc;
}

.no-area {
  color: #909399;
  font-style: italic;
  font-size: 13px;
  opacity: 0.8;
}

.loading-area {
  color: #7a8baa;
  font-style: italic;
  font-size: 13px;
  display: inline-block;
  padding: 2px 0;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.action-button {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
  transition: all 0.3s;
}

.action-button:hover {
  transform: translateY(-3px) rotate(5deg);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.12);
}

.view-button {
  background: linear-gradient(135deg, #4facfe, #00f2fe);
  border-color: transparent;
  color: white;
}

.solve-button {
  background: linear-gradient(135deg, #67ce8e, #13c276);
  border-color: transparent;
  color: white;
}

.publish-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: linear-gradient(135deg, #4facfe, #00f2fe);
  border-color: transparent;
  color: white;
  box-shadow: 0 4px 10px rgba(79, 172, 254, 0.3);
  border-radius: 8px;
  transition: all 0.3s;
}

.publish-button:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 15px rgba(79, 172, 254, 0.4);
}

.cards-container {
  padding: 8px 0;
  min-height: 350px;
}

.alert-cards, .notice-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
  padding: 6px;
}

.alert-card, .notice-card {
  background: white;
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.06);
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.4s ease;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  border-left: 5px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.alert-card::before, .notice-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 6px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  z-index: 1;
}

.alert-card:hover, .notice-card:hover {
  box-shadow: 0 15px 30px rgba(0, 0, 0, 0.1);
  transform: translateY(-8px);
}

.alert-card[data-grade="3"] {
  border-left-color: #F56C6C;
  background: linear-gradient(to bottom right, #fff, #fff5f5);
}

.alert-card[data-grade="3"]::after {
  content: "";
  position: absolute;
  top: 0;
  right: 0;
  border-style: solid;
  border-width: 0 40px 40px 0;
  border-color: transparent #ff9999 transparent transparent;
  z-index: 1;
}

.alert-card[data-grade="2"] {
  border-left-color: #E6A23C;
  background: linear-gradient(to bottom right, #fff, #fffbf5);
}

.alert-card[data-grade="1"] {
  border-left-color: #67C23A;
  background: linear-gradient(to bottom right, #fff, #f7fcf5);
}

.alert-card[data-grade="0"] {
  border-left-color: #909399;
  background: linear-gradient(to bottom right, #fff, #f9fafc);
}

.notice-card {
  border-left-color: #4facfe;
  background: linear-gradient(to bottom right, #fff, #f5faff);
}

.notice-card::after {
  content: "";
  position: absolute;
  top: -20px;
  right: -20px;
  width: 100px;
  height: 100px;
  background: radial-gradient(circle, rgba(79, 172, 254, 0.1) 0%, rgba(79, 172, 254, 0) 70%);
  border-radius: 50%;
  z-index: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
}

.card-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.card-id {
  font-weight: 700;
  color: #5a6a8a;
  font-size: 14px;
  background: rgba(90, 106, 138, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
}

.card-publisher {
  font-size: 12px;
  color: #909399;
  font-weight: 500;
}

.alert-type-badge {
  font-size: 12px;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #4facfe, #00f2fe);
  padding: 3px 10px;
  height: 22px;
  line-height: 16px;
  border-radius: 11px;
  display: inline-block;
  box-shadow: 0 2px 5px rgba(79, 172, 254, 0.3);
}

.card-content {
  color: #334466;
  font-size: 14px;
  line-height: 1.7;
  margin-bottom: 16px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  position: relative;
  z-index: 1;
}

.notice-card-title {
  font-size: 17px;
  font-weight: 600;
  margin: 0;
  color: #2c3e50;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-bottom: 8px;
  border-bottom: 1px dashed #d8e2ff;
  position: relative;
}

.notice-card-title::after {
  content: "";
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 60px;
  height: 3px;
  background: linear-gradient(90deg, #4facfe, #00f2fe);
  border-radius: 3px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #7a8baa;
  border-top: 1px dashed #d8e2ff;
  padding-top: 12px;
  position: relative;
  z-index: 1;
}

.card-footer-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-area {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.card-time {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #7a8baa;
}

.publisher {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #5a6a8a;
  background: linear-gradient(135deg, #f0f5ff, #e9f2ff);
  padding: 4px 10px;
  border-radius: 12px;
  box-shadow: 0 2px 5px rgba(90, 106, 138, 0.1);
}

.card-actions {
  display: flex;
  align-items: center;
}

.solve-button-compact {
  height: 32px;
  padding: 0 16px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  border-radius: 16px;
  background: linear-gradient(135deg, #67ce8e, #13c276);
  border-color: transparent;
  color: white;
  box-shadow: 0 4px 8px rgba(19, 194, 118, 0.2);
  transition: all 0.3s;
}

.solve-button-compact:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(19, 194, 118, 0.3);
}

.more-areas {
  font-size: 11px;
  color: #7a8baa;
  background: linear-gradient(135deg, #f0f5ff, #e9f2ff);
  padding: 1px 6px;
  border-radius: 10px;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin: 28px 0 16px;
}

.pagination-container :deep(.el-pagination.is-background .el-pager li:not(.is-disabled).is-active) {
  background: linear-gradient(135deg, #4facfe, #00f2fe);
  color: white;
  font-weight: 600;
  box-shadow: 0 4px 8px rgba(79, 172, 254, 0.3);
}

.pagination-container :deep(.el-pagination.is-background .el-pager li:not(.is-disabled):hover) {
  color: #4facfe;
}

.pagination-container :deep(.btn-prev),
.pagination-container :deep(.btn-next) {
  background: white;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
}

.pagination-container :deep(.btn-prev:hover),
.pagination-container :deep(.btn-next:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
}

.empty-placeholder {
  padding: 60px 0;
  display: flex;
  justify-content: center;
  background: linear-gradient(to bottom, #fff, #f5faff);
  border-radius: 14px;
  margin: 24px 0;
  min-height: 250px;
  border: 1px dashed #c0d8ff;
}

.empty-placeholder :deep(.el-empty__image) {
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.1));
}

.empty-placeholder :deep(.el-empty__description) {
  color: #7a8baa;
}

.detail-dialog :deep(.el-dialog__header) {
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  border-bottom: none;
  padding: 20px 24px;
  margin-right: 0;
  border-radius: 12px 12px 0 0;
}

.detail-dialog :deep(.el-dialog__title) {
  font-weight: 600;
  font-size: 18px;
  color: white;
}

.detail-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: rgba(255, 255, 255, 0.8);
}

.detail-dialog :deep(.el-dialog__headerbtn .el-dialog__close:hover) {
  color: white;
}

.detail-dialog :deep(.el-dialog__body) {
  padding: 24px 30px;
  position: relative;
}

.detail-dialog :deep(.el-dialog__body::before) {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 80px;
  background: linear-gradient(to bottom, rgba(30, 60, 114, 0.05), transparent);
  pointer-events: none;
}

.detail-content {
  padding: 0;
  position: relative;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  background: linear-gradient(to right, #f0f5ff, #f5faff);
  padding: 16px 20px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.detail-tag {
  font-size: 16px;
  padding: 6px 14px;
  border-radius: 20px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.status-detail-tag {
  font-size: 14px;
  padding: 6px 14px;
  border-radius: 20px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
}

.detail-type {
  font-size: 20px;
  font-weight: 600;
  color: #2c3e50;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin: 24px 0;
}

.info-item {
  background: linear-gradient(to bottom right, #f9fafc, #f5faff);
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
  transition: all 0.3s;
  border: 1px solid #e9f2ff;
}

.info-item:hover {
  background: linear-gradient(to bottom right, #f5faff, #f0f7ff);
  box-shadow: 0 6px 15px rgba(0, 0, 0, 0.05);
  transform: translateY(-2px);
}

.info-label {
  color: #5a6a8a;
  font-size: 14px;
  margin-bottom: 10px;
  font-weight: 600;
}

.info-value {
  color: #334466;
  font-size: 16px;
  font-weight: 500;
}

.timestamp-value {
  color: #5a6a8a;
}

.area-detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.area-detail-tag {
  background: linear-gradient(135deg, #f0f7ff, #e6f2ff);
  border-color: #d3e5fc;
  color: #4b83d2;
  box-shadow: 0 2px 5px rgba(75, 131, 210, 0.1);
}

.message-container {
  background: linear-gradient(to bottom right, #f9fafc, #f5faff);
  border-radius: 12px;
  padding: 24px;
  margin: 24px 0;
  border-left: 4px solid #4facfe;
  min-height: 120px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
  position: relative;
  overflow: hidden;
}

.message-container::after {
  content: "";
  position: absolute;
  bottom: -10px;
  right: -10px;
  width: 120px;
  height: 120px;
  background: radial-gradient(circle, rgba(79, 172, 254, 0.05) 0%, transparent 70%);
  border-radius: 50%;
}

.message-content {
  font-size: 15px;
  line-height: 1.8;
  color: #334466;
  white-space: pre-wrap;
  position: relative;
  z-index: 1;
}

.notice-detail-header {
  text-align: center;
  margin-bottom: 20px;
}

.notice-detail-title {
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
  padding: 14px 0;
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
  background: linear-gradient(90deg, #4facfe, #00f2fe);
  border-radius: 3px;
}

.actions-container {
  margin-top: 30px;
  display: flex;
  justify-content: center;
}

.detail-action-button {
  padding: 12px 28px;
  font-size: 16px;
  border-radius: 30px;
  font-weight: 600;
  background: linear-gradient(135deg, #67ce8e, #13c276);
  border-color: transparent;
  color: white;
  box-shadow: 0 6px 15px rgba(19, 194, 118, 0.2);
  transition: all 0.3s;
}

.detail-action-button:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(19, 194, 118, 0.3);
}

/* 移动端样式增强 */
@media (max-width: 768px) {
  .alert-notice-container {
    padding: 0 12px;
    margin: 10px auto;
  }
  
  .page-header {
    padding: 14px 16px;
    margin-bottom: 16px;
  }
  
  .page-title {
    font-size: 20px;
  }
  
  .header-icon {
    font-size: 22px;
  }
  
  .main-content {
    padding: 16px;
    border-radius: 10px;
  }
  
  .filter-bar {
    flex-direction: column;
    gap: 16px;
    padding: 14px;
  }
  
  .left-section, .right-section {
    width: 100%;
  }
  
  .filter-select, .search-input {
    width: 100%;
  }
  
  .custom-tabs :deep(.el-tabs__item) {
    font-size: 14px;
    height: 44px;
    line-height: 44px;
    padding: 0 12px;
  }
  
  .tab-label {
    font-size: 14px;
    gap: 6px;
  }
  
  .detail-dialog :deep(.el-dialog) {
    width: 95% !important;
    margin: 0 auto !important;
  }
  
  .detail-dialog :deep(.el-dialog__body) {
    padding: 16px;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .detail-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .header-right {
    align-self: flex-end;
  }
  
  .detail-tag, .status-detail-tag {
    font-size: 12px;
    padding: 4px 10px;
  }
  
  .detail-type {
    font-size: 16px;
  }
  
  .notice-detail-title {
    font-size: 20px;
  }
  
  .message-container {
    padding: 16px;
  }
  
  .message-content {
    font-size: 14px;
    line-height: 1.6;
  }
  
  .pagination-container :deep(.el-pagination) {
    padding: 8px 0;
    justify-content: center;
    flex-wrap: wrap;
  }

  .alert-cards, .notice-cards {
    grid-template-columns: 1fr;
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
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.4s ease;
}

.cards-container, .table-container {
  transition: opacity 0.4s ease;
}

.mobile-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 16px;
  background: linear-gradient(135deg, #1e3c72, #2a5298);
  border-bottom: none;
  font-size: 18px;
  font-weight: 600;
  color: white;
}

.drawer-content {
  padding: 0 16px 16px;
  height: 100%;
  overflow-y: auto;
}

.compact-drawer {
  padding: 0 16px 16px;
}

.compact-form :deep(.el-form-item) {
  margin-bottom: 16px;
 }

.compact-header {
  margin-bottom: 12px;
}

.compact-header-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 12px;
  background: linear-gradient(to right, #f0f5ff, #f5faff);
  border-radius: 10px;
}

.compact-type {
  font-size: 16px;
  font-weight: 600;
}

.status-compact-tag {
  font-size: 12px;
  padding: 2px 10px;
  margin-left: auto;
}

.compact-divider {
  margin: 16px 0;
  padding: 0 12px;
}

.compact-divider :deep(.el-divider__text) {
  font-size: 15px;
  padding: 0 12px;
  background-color: #fff;
  font-weight: 600;
  color: #4168b4;
}

.compact-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  padding: 6px;
}

.compact-info-item {
  background: linear-gradient(to bottom right, #f9fafc, #f5faff);
  border-radius: 8px;
  padding: 10px 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  display: flex;
  flex-direction: column;
  gap: 5px;
  border: 1px solid #e9f2ff;
}

.compact-info-label {
  color: #5a6a8a;
  font-size: 12px;
  font-weight: 500;
}

.compact-info-value {
  color: #334466;
  font-size: 14px;
}

.compact-message-container {
  background: linear-gradient(to bottom right, #f9fafc, #f5faff);
  border-radius: 8px;
  padding: 12px 14px;
  margin: 12px 6px;
  border-left: 3px solid #4facfe;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}

.compact-notice-title {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  margin: 10px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid #4facfe;
  display: inline-block;
}

.mobile-detail-header, .mobile-notice-header {
  flex-direction: column;
  gap: 12px;
}

.mobile-detail-header .header-right {
  margin-top: 12px;
  align-self: flex-start;
}

.mobile-action-button {
  width: 100%;
  margin-top: 16px;
  height: 44px;
  border-radius: 22px;
}

.drawer-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #e1eaff;
}

.drawer-btn {
  flex: 1;
  margin: 0 6px;
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

@keyframes float {
  0% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
  100% { transform: translateY(0px); }
}

@keyframes slideIn {
  from { transform: translateX(-20px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 添加一些动画效果 */
.alert-card, .notice-card {
  animation: fadeIn 0.5s ease-out;
}

.alert-card[data-grade="3"] {
  animation: fadeIn 0.3s ease-out, pulse 2s infinite;
}

@keyframes pulse {
  0% { box-shadow: 0 8px 16px rgba(245, 108, 108, 0.1); }
  50% { box-shadow: 0 8px 20px rgba(245, 108, 108, 0.2); }
  100% { box-shadow: 0 8px 16px rgba(245, 108, 108, 0.1); }
}

.detail-tag, .status-detail-tag {
  animation: slideIn 0.3s ease-out;
}

.card-area, .card-time, .card-footer-left {
  animation: fadeIn 0.5s ease-out;
}

.message-container {
  animation: fadeIn 0.6s ease-out;
}
</style>