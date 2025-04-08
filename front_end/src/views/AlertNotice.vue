<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import axios from '../axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Bell, Warning, Document, Plus, Check, Delete, Search, Refresh, View, InfoFilled, Clock } from '@element-plus/icons-vue'
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
    const response = await axios.get('/api/areas/')
    if (Array.isArray(response.data)) {
      areas.value = response.data
      console.log('区域数据加载完成，共加载:', areas.value.length, '个区域')
      return true
    }
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
    let url = '/api/alerts/'
    if (alertFilter.value === 'unsolved') {
      url = '/api/alerts/unsolved/'
    }
    
    const response = await axios.get(url)
    if (Array.isArray(response.data)) {

      let alertsData = response.data
      if (alertFilter.value === 'solved') {
        alertsData = alertsData.filter(alert => alert.solved)
      }
      

      console.log(`获取到 ${alertsData.length} 条告警数据`)
      

      processAlertData(alertsData)
    } else {
      alerts.value = []
    }
    

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
    const response = await axios.get('/api/notice/')
    if (Array.isArray(response.data)) {
      processNoticeData(response.data)
    } else {
      notices.value = []
    }
    

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
    
    await axios.post(`/api/alerts/${alertId}/solve/`)
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
    await axios.post('/api/notice/', noticeForm)
    ElMessage.success('通知发布成功')
    noticeDialogVisible.value = false
    

    noticeForm.title = ''
    noticeForm.content = ''
    noticeForm.related_areas = []
    
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
</script>

<template>
  <div class="alert-notice-container">
    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <h2 class="title">
            <el-icon class="header-icon"><Bell /></el-icon>
            告警与通知中心
          </h2>
          <div class="header-actions">
            <el-button type="primary" :icon="Refresh" circle @click="refreshData" />
          </div>
        </div>
      </template>
      
      <el-tabs v-model="activeTab" @tab-change="handleTabChange" class="custom-tabs">

        <el-tab-pane name="alerts" lazy>
          <template #label>
            <span class="tab-label">
              <el-icon><Warning /></el-icon>
              告警管理
            </span>
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
          
          <div class="table-container">
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
          </div>
          
          <div class="empty-placeholder" v-if="paginatedAlerts.length === 0 && !alertsLoading">
            <el-empty description="暂无告警数据" />
          </div>
          
          <div class="pagination-container" v-if="filteredAlerts.length > 0">
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              layout="total, prev, pager, next, jumper"
              :total="filteredAlerts.length"
              @current-change="handlePageChange"
              background
            />
          </div>
        </el-tab-pane>
        

        <el-tab-pane name="notices" lazy>
          <template #label>
            <span class="tab-label">
              <el-icon><Document /></el-icon>
              通知管理
            </span>
          </template>
          
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
          
          <div class="table-container">
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
          </div>
          
          <div class="empty-placeholder" v-if="paginatedNotices.length === 0 && !noticesLoading">
            <el-empty description="暂无通知数据" />
          </div>
          
          <div class="pagination-container" v-if="filteredNotices.length > 0">
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              layout="total, prev, pager, next, jumper"
              :total="filteredNotices.length"
              @current-change="handlePageChange"
              background
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
    

    <el-dialog
      v-model="noticeDialogVisible"
      title="发布新通知"
      width="600px"
      destroy-on-close
      class="detail-dialog"
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
    

    <el-dialog
      v-model="alertDetailVisible"
      title="告警详情"
      width="700px"
      @closed="closeAlertDetail"
      class="detail-dialog"
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
    

    <el-dialog
      v-model="noticeDetailVisible"
      title="通知详情"
      width="700px"
      @closed="closeNoticeDetail"
      class="detail-dialog"
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
  </div>
</template>

<style scoped>
.alert-notice-container {
  max-width: 1400px;
  margin: 20px auto;
  padding: 0 20px;
}

.main-card {
  border-radius: 12px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.07);
  overflow: hidden;
  min-height: 600px; /* 添加最小高度 */
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}

.title {
  margin: 0;
  font-size: 22px;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #333;
  font-weight: 600;
}

.header-icon {
  font-size: 26px;
  color: #409EFF;
}

/* 标签页样式 */
.custom-tabs :deep(.el-tabs__nav) {
  border-radius: 4px;
}

.custom-tabs :deep(.el-tabs__item) {
  font-size: 16px;
  height: 50px;
  line-height: 50px;
  transition: all 0.3s;
}

.custom-tabs :deep(.el-tabs__item.is-active) {
  font-weight: 600;
  transform: translateY(-2px);
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
}

/* 过滤栏样式 */
.filter-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
  align-items: center;
  background-color: #f8f9fa;
  padding: 15px;
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

/* 表格容器样式 */
.table-container {
  background-color: #fff;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  min-height: 350px; /* 添加最小高度 */
}

/* 表格样式 */
.data-table {
  border-radius: 8px;
  overflow: hidden;
}

.custom-table-header {
  background-color: #f4f6fa !important;
  color: #606266;
  font-weight: 600;
}

.hover-effect-row {
  transition: all 0.3s ease;
  cursor: pointer;
}

.hover-effect-row:hover {
  background-color: #f0f9ff !important;
  transform: translateY(-2px);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

/* 表格内容样式 */
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

/* 分页和空状态 */
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
  min-height: 300px; /* 添加最小高度 */
}

/* 详情对话框样式 */
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

/* 信息网格布局 */
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

/* 消息内容容器 */
.message-container {
  background-color: #f9fafc;
  border-radius: 8px;
  padding: 20px;
  margin: 20px 0;
  border-left: 4px solid #409EFF;
  min-height: 100px; /* 添加最小高度 */
}

.message-content {
  font-size: 15px;
  line-height: 1.8;
  color: #303133;
  white-space: pre-wrap;
}

/* 通知详情样式 */
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

/* 滚动条样式 */
.detail-dialog :deep(.el-dialog__body::-webkit-scrollbar) {
  width: 6px;
}

.detail-dialog :deep(.el-dialog__body::-webkit-scrollbar-thumb) {
  background-color: #c0c4cc;
  border-radius: 6px;
}

/* 分割线样式 */
:deep(.el-divider__text) {
  color: #606266;
  font-weight: 600;
  font-size: 16px;
  background-color: #fff;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .filter-bar {
    flex-direction: column;
    gap: 15px;
  }
  
  .left-section, .right-section {
    width: 100%;
  }
  
  .search-input {
    width: 100%;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>