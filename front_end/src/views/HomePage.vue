<script lang="ts" setup>
import { ref, onMounted, computed, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import type { AreaItem, Alert, Notice, SummaryData, Building } from '../types'
import { useAuthStore } from '../stores/auth'
import { areaService, noticeService, alertService, summaryService, buildingService } from '../services'
import apiService from '../services'
import AreaList from '../components/data/AreaList.vue'
import EnvironmentalChart from '../components/chart/EnvironmentalChart.vue'
import HistoricalChart from '../components/chart/HistoricalChart.vue'

import {
  User, Monitor, OfficeBuilding, Connection, MapLocation,
  DataAnalysis, Warning, Bell, FirstAidKit, 
  Document, Reading, School, Postcard, Platform, 
  Management, CreditCard, Trophy, Link,
  TrendCharts, HomeFilled, Star, List, Histogram,
  Refresh, LocationInformation, Position, Odometer,
  House, Discount, Promotion, ChatLineRound,
  UserFilled, Avatar, CircleCheckFilled
} from '@element-plus/icons-vue'

const navigationItems = ref([
  { icon: 'Document', link: 'http://today.hit.edu.cn', title: '校内新闻' },
  { icon: 'School', link: 'http://jwts.hit.edu.cn', title: '本科生教务系统' },
  { icon: 'Reading', link: 'http://yjsgl.hit.edu.cn/', title: '研究生管理系统' },
  { icon: 'Platform', link: 'http://i.hit.edu.cn', title: '门户平台' },
  { icon: 'Connection', link: 'http://i-hit-edu-cn.ivpn.hit.edu.cn', title: 'IVPN(校外)' },
  { icon: 'Management', link: 'https://xg.hit.edu.cn/xs/mh', title: '学工系统' },
  { icon: 'CreditCard', link: 'http://xyk.hit.edu.cn', title: '校园卡' },
  { icon: 'Trophy', link: 'http://venue-book.hit.edu.cn:8080/', title: '运动场地预约' },
  { icon: 'Reading', link: 'http://ic.lib.hit.edu.cn/', title: '图书馆预约' }
])

const Hotareas = ref<AreaItem[]>([])
const suggestedAreas = ref<AreaItem[]>([])

const loading = ref(false)
const favoriteAreas = ref<AreaItem[]>([])
const loadingFavorites = ref(false)

// 添加温湿度图表相关状态
const selectedAreaForEnvironmental = ref<number | null>(null)
const allAreas = ref<AreaItem[]>([])
const loadingAllAreas = ref(false)

// 添加新的响应式数据
const selectedBuildingForEnvironmental = ref<number | null>(null)
const buildingAreas = ref<AreaItem[]>([])
const loadingBuildingAreas = ref(false)
const buildings = ref<Building[]>([])

const isFirstLoad = ref(true)

const userStore = useAuthStore()
const isAuthenticated = computed(() => userStore.isAuthenticated)
const favoriteAreaIds = ref<number[]>([])

const STATS_LABELS = {
  nodes_count: '监测节点',
  terminals_count: '接入终端',
  buildings_count: '楼宇数量',
  areas_count: '监测区域',
  historical_data_count: '历史记录',
  people_count: '当前总人数',
  notice_count: '系统通知',
  alerts_count: '安全告警',
  users_count: '注册用户',
  nodes_online_count: '在线节点',
  terminals_online_count: '在线终端'
} as const

const fetchHotAreas = async () => {
  try {

    if (isFirstLoad.value) {
      loading.value = true
    }

    Hotareas.value = await areaService.getPopularAreas(8)

    if (isFirstLoad.value) {
      setTimeout(() => {
        loading.value = false
      }, 100)
    }
  } catch (error) {
    ElMessage.error('热门区域数据获取失败')
    Hotareas.value = []
    if (isFirstLoad.value) {
      loading.value = false
    }
  }
}

const fetchFavoriteAreas = async () => {
  try {

    if (isAuthenticated.value && userStore.user) {
      favoriteAreas.value = await areaService.getFavoriteAreas()
    }
  } catch (error) {
    console.error('获取收藏区域失败:', error)
  }
}

// 获取所有区域用于环境数据图表选择
const fetchAllAreas = async () => {
  try {
    if (isFirstLoad.value) {
      loadingAllAreas.value = true
    }
    
    // 先获取所有建筑
    const buildingsData = await buildingService.getAll()
    const areasList: AreaItem[] = []
    
    // 遍历每个建筑，获取其区域
    for (const building of buildingsData) {
      try {
        const areas = await buildingService.getBuildingAreas(building.id)
        areasList.push(...areas)
      } catch (error) {
        console.error(`获取建筑 ${building.id} 的区域失败`, error)
      }
    }
    
    allAreas.value = areasList
  } catch (error) {
    console.error('获取区域列表失败:', error)
    ElMessage.error('获取区域列表失败')
  } finally {
    if (isFirstLoad.value) {
      loadingAllAreas.value = false
    }
  }
}

// 获取建筑列表
const fetchBuildings = async () => {
  try {
    buildings.value = await buildingService.getBuildingsBasic()
  } catch (error) {
    console.error('获取建筑列表失败:', error)
  }
}

// 建筑选择变化处理
const onBuildingChange = async (buildingId: number | null) => {
  selectedAreaForEnvironmental.value = null
  buildingAreas.value = []
  
  if (!buildingId) return
  
  try {
    loadingBuildingAreas.value = true
    const areas = await buildingService.getBuildingAreas(buildingId)
    buildingAreas.value = areas
  } catch (error) {
    ElMessage.error('获取建筑区域失败')
    buildingAreas.value = []
  } finally {
    loadingBuildingAreas.value = false
  }
}

let intervalTimer1: number | null = null 
let intervalTimer2: number | null = null

// 添加缺失的状态变量
const isMobile = ref(false)
const summary = ref<SummaryData>({
  nodes_count: 0,
  terminals_count: 0,
  buildings_count: 0,
  areas_count: 0,
  historical_data_count: 0,
  people_count: 0,
  notice_count: 0,
  alerts_count: 0,
  users_count: 0,
  nodes_online_count: 0,
  terminals_online_count: 0
})
const loadingSummary = ref(false)
const alerts = ref<Alert[]>([])
const notices = ref<Notice[]>([])
const loadingAlerts = ref(false)
const loadingNotices = ref(false)

// 获取统计数据
const fetchSummary = async () => {
  try {
    if (isFirstLoad.value) {
      loadingSummary.value = true
    }
    const data = await summaryService.getSummary()
    summary.value = data as SummaryData
  } catch (error) {
    ElMessage.error('统计信息获取失败')
  } finally {
    if (isFirstLoad.value) {
      setTimeout(() => {
        loadingSummary.value = false
      }, 100)
    }
  }
}

// 获取公开告警
const fetchPublicAlerts = async () => {
  try {
    if (isFirstLoad.value) {
      loadingAlerts.value = true
    }
    alerts.value = await alertService.getPublicAlerts()
  } catch (error) {
    ElMessage.error('获取告警信息失败')
    alerts.value = []
  } finally {
    if (isFirstLoad.value) {
      setTimeout(() => {
        loadingAlerts.value = false
      }, 100)
    }
  }
}

// 获取最新通知
const fetchLatestNotices = async () => {
  try {
    if (isFirstLoad.value) {
      loadingNotices.value = true
    }
    notices.value = await noticeService.getLatestNotices()
  } catch (error) {
    ElMessage.error('获取通知信息失败')
    notices.value = []
  } finally {
    if (isFirstLoad.value) {
      setTimeout(() => {
        loadingNotices.value = false
      }, 100)
    }
  }
}

const selectedAreaForHistorical = ref<number | null>(null)
const selectedBuildingForHistorical = ref<number | null>(null)
const historicalBuildingAreas = ref<AreaItem[]>([])
const loadingHistoricalBuildingAreas = ref(false)

const onHistoricalBuildingChange = async (buildingId: number | null) => {
  selectedAreaForHistorical.value = null
  historicalBuildingAreas.value = []
  
  if (!buildingId) return
  
  try {
    loadingHistoricalBuildingAreas.value = true
    const areas = await buildingService.getBuildingAreas(buildingId)
    historicalBuildingAreas.value = areas
  } catch (error) {
    ElMessage.error('获取建筑区域失败')
    historicalBuildingAreas.value = []
  } finally {
    loadingHistoricalBuildingAreas.value = false
  }
}
        

// 获取告警类型
const getAlertType = (grade: number) => {
  switch (grade) {
    case 3: return 'error'
    case 2: return 'warning'
    case 1: return 'info'
    default: return 'success'
  }
}

const checkScreenSize = () => {
  isMobile.value = window.innerWidth < 992
}

// 添加推荐区域相关状态
const selectedBuildingForSuggestion = ref<number>(2); // 默认使用id=2的建筑
const loadingSuggested = ref(false);

// 获取推荐区域
const fetchSuggestedAreas = async () => {
  try {
    if (isFirstLoad.value) {
      loadingSuggested.value = true;
    }
    
    suggestedAreas.value = await areaService.getSuggestedAreas(selectedBuildingForSuggestion.value, 8);
    
    if (isFirstLoad.value) {
      setTimeout(() => {
        loadingSuggested.value = false;
      }, 100);
    }
  } catch (error) {
    ElMessage.error('推荐区域数据获取失败');
    suggestedAreas.value = [];
    if (isFirstLoad.value) {
      loadingSuggested.value = false;
    }
  }
}

// 监听建筑选择变化
const onSuggestionBuildingChange = async () => {
  await fetchSuggestedAreas();
}

onMounted(async () => {
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)
  await Promise.all([
    fetchHotAreas(),
    fetchSummary(),
    fetchFavoriteAreas(),
    fetchPublicAlerts(),
    fetchLatestNotices(),
    fetchAllAreas(),
    fetchBuildings(),
    fetchSuggestedAreas() // 添加获取推荐区域
  ]).catch(() => ElMessage.error('数据获取出错'))
  isFirstLoad.value = false
  
  intervalTimer1 = setInterval(() => {
    fetchHotAreas();
    fetchPublicAlerts();
    fetchLatestNotices();
    fetchSummary();
    fetchSuggestedAreas(); // 定时刷新推荐区域
  }, 30000);
  if (isAuthenticated.value) {
    intervalTimer2 = setInterval(async () => {
      await fetchFavoriteAreas()
    }, 30000)
  }
})

onBeforeUnmount(() => {

  if (intervalTimer1) clearInterval(intervalTimer1)
  if (intervalTimer2) clearInterval(intervalTimer2)

  window.removeEventListener('resize', checkScreenSize)
})
</script>

<template>
  <div class="home-container">
    <el-card class="header-card">
      <div class="header-wrapper">
        <div class="header-title-container">
          <div class="header-icon-container">
            <el-icon class="header-icon"><House /></el-icon>
          </div>
          <h1 class="header-title">智慧校园<span class="highlight">空间感知调控</span>系统</h1>
        </div>
        <div class="divider">
          <span class="divider-dot"></span>
          <span class="divider-line"></span>
          <span class="divider-dot"></span>
        </div>
        <div class="sub-title">实时监测校园内各区域人员情况与环境数据，保障安全与高效管理</div>
      </div>
    </el-card>
    
    <!-- 统计卡片部分 -->
    <el-card class="stats-card mb-20 mt-20">
      <div v-loading="loadingSummary">
        <el-skeleton :rows="1" animated :loading="loadingSummary">
          <template #default>
            <div v-if="Object.values(summary).some(value => value > 0)">
              <el-row :gutter="20">
                <el-col
                  v-for="(value, key) in summary"
                  :key="key"
                  :span="isMobile ? 12 : 4"
                  :xs="8" :sm="6" :md="4" :lg="3"
                >
                  <el-statistic :title="STATS_LABELS[key]" :value="value" class="stat-item">
                    <template #suffix>
                      <!-- 优化后的多样化图标 -->
                      <el-icon v-if="key === 'people_count'" class="stat-icon">
                        <UserFilled />
                      </el-icon>
                      <el-icon v-else-if="key === 'nodes_count'" class="stat-icon">
                        <Monitor />
                      </el-icon>
                      <el-icon v-else-if="key === 'buildings_count'" class="stat-icon">
                        <OfficeBuilding />
                      </el-icon>
                      <el-icon v-else-if="key === 'terminals_count'" class="stat-icon">
                        <Connection />
                      </el-icon>
                      <el-icon v-else-if="key === 'areas_count'" class="stat-icon">
                        <MapLocation />
                      </el-icon>
                      <el-icon v-else-if="key === 'historical_data_count'" class="stat-icon">
                        <TrendCharts />
                      </el-icon>
                      <el-icon v-else-if="key === 'notice_count'" class="stat-icon">
                        <Bell />
                      </el-icon>
                      <el-icon v-else-if="key === 'alerts_count'" class="stat-icon">
                        <Warning />
                      </el-icon>
                      <el-icon v-else-if="key === 'users_count'" class="stat-icon">
                        <Avatar />
                      </el-icon>
                      <el-icon v-else-if="key === 'nodes_online_count'" class="stat-icon">
                        <CircleCheckFilled />
                      </el-icon>
                      <el-icon v-else-if="key === 'terminals_online_count'" class="stat-icon">
                        <CircleCheckFilled />
                      </el-icon>
                    </template>
                  </el-statistic>
                </el-col>
              </el-row>
            </div>
            <div v-else class="no-data-message">
              <el-empty description="暂无统计数据" />
            </div>
          </template>
        </el-skeleton>
      </div>
    </el-card>

    <el-row :gutter="20" class="mt-20">
      <el-col :span="isMobile ? 24 : 16" :xs="24" :sm="24" :md="16" :lg="16">
        <!-- 热门区域卡片 -->
        <el-card class="dashboard-card">
          <template #header>
            <div class="card-header">
              <el-icon class="card-icon hot-icon"><TrendCharts /></el-icon>
              <span class="card-title">热门区域实时排行</span>
            </div>
          </template>
          <AreaList :areas="Hotareas" :loading="loading" empty-text="暂无热门区域数据"
            :max-height="Hotareas.length > 8 ? '150px' : 'auto'" />
        </el-card>
        
        <!-- 空闲区域推荐卡片 -->
        <el-card class="dashboard-card">
          <template #header>
            <div class="chart-header">
              <div class="card-header">
                <el-icon class="card-icon suggest-icon"><Promotion /></el-icon>
                <span class="card-title">空闲区域推荐</span>
              </div>
              <div class="chart-controls">
                <el-select 
                  v-model="selectedBuildingForSuggestion" 
                  placeholder="选择建筑" 
                  size="small" 
                  style="width: 120px;"
                  @change="onSuggestionBuildingChange"
                >
                  <el-option
                    v-for="building in buildings"
                    :key="building.id"
                    :label="building.name"
                    :value="building.id"
                  />
                </el-select>
              </div>
            </div>
          </template>
          <AreaList :areas="suggestedAreas" :loading="loadingSuggested" empty-text="暂无推荐区域数据"
            :max-height="suggestedAreas.length > 8 ? '150px' : 'auto'" />
        </el-card>
        
        <!-- 收藏区域卡片 -->
        <el-card v-if="isAuthenticated" class="dashboard-card">
          <template #header>
            <div class="card-header">
              <el-icon class="card-icon favorite-icon"><Star /></el-icon>
              <span class="card-title">我的收藏区域</span>
            </div>
          </template>
          <AreaList :areas="favoriteAreas" :loading="loadingFavorites"
            :max-height="favoriteAreas.length > 6 ? '193px' : 'auto'" empty-text="暂无收藏区域" />
        </el-card>
        
        <!-- 人员变化趋势卡片 -->
        <el-card class="dashboard-card">
          <template #header>
            <div class="chart-header">
              <div class="card-header">
                <el-icon class="card-icon trend-icon"><Histogram /></el-icon>
                <span class="card-title">人员变化趋势</span>
              </div>
              <div class="chart-controls">
                <el-select 
                  v-model="selectedBuildingForHistorical" 
                  placeholder="选择建筑" 
                  size="small" 
                  style="width: 120px; margin-right: 8px;"
                  @change="onHistoricalBuildingChange"
                  clearable
                >
                  <el-option
                    v-for="building in buildings"
                    :key="building.id"
                    :label="building.name"
                    :value="building.id"
                  />
                </el-select>
                <el-select 
                  v-model="selectedAreaForHistorical" 
                  placeholder="选择区域" 
                  size="small" 
                  style="width: 180px;"
                  :loading="loadingHistoricalBuildingAreas"
                  :disabled="!selectedBuildingForHistorical"
                >
                  <el-option
                    v-for="area in historicalBuildingAreas"
                    :key="area.id"
                    :label="area.name"
                    :value="area.id"
                  />
                </el-select>
              </div>
            </div>
          </template>
          <HistoricalChart 
            v-if="selectedAreaForHistorical"
            :area-id="selectedAreaForHistorical" 
            height="320px"
            :hide-data-zoom="true"
            :style-config="{
              gridLineColor: 'rgba(0, 0, 0, 0.1)',
              axisLineColor: 'rgba(0, 0, 0, 0.2)',
              axisLabelColor: '#333',
              axisLabelFontSize: 12,
              seriesColors: ['#409EFF'],
              backgroundColor: 'transparent',
              textColor: '#333',
              fontSize: 12,
              showLegend: false,
              tooltipBackgroundColor: 'rgba(15, 23, 42, 0.9)',
              tooltipTextColor: '#ffffff',
              showGridLine: true, // 确保显示网格线
              yAxis: {
                axisLine: { show: true }, // 确保显示Y轴线
                splitLine: { show: true } // 确保显示Y轴分割线
              },
              xAxis: {
                axisLine: { show: true } // 确保显示X轴线
              }
            }"
          />
          <HistoricalChart 
            v-else
            height="320px"
            :hide-data-zoom="true"
            :style-config="{
              gridLineColor: 'rgba(0, 0, 0, 0.1)',
              axisLineColor: 'rgba(0, 0, 0, 0.2)',
              axisLabelColor: '#333',
              axisLabelFontSize: 12,
              seriesColors: ['#409EFF'],
              backgroundColor: 'transparent',
              textColor: '#333',
              fontSize: 12,
              showLegend: false,
              tooltipBackgroundColor: 'rgba(15, 23, 42, 0.9)',
              tooltipTextColor: '#ffffff',
              showGridLine: true, // 确保显示网格线
              yAxis: {
                axisLine: { show: true }, // 确保显示Y轴线
                splitLine: { show: true } // 确保显示Y轴分割线
              },
              xAxis: {
                axisLine: { show: true } // 确保显示X轴线
              }
            }"
          />
        </el-card>
        
        <!-- 环境数据监测卡片 -->
        <el-card class="dashboard-card">
          <template #header>
            <div class="chart-header">
              <div class="card-header">
                <el-icon class="card-icon env-icon"><Odometer /></el-icon>
                <span class="card-title">环境数据监测</span>
              </div>
              <div class="chart-controls">
                <el-select 
                  v-model="selectedBuildingForEnvironmental" 
                  placeholder="选择建筑" 
                  size="small" 
                  style="width: 120px; margin-right: 8px;"
                  @change="onBuildingChange"
                  clearable
                >
                  <el-option
                    v-for="building in buildings"
                    :key="building.id"
                    :label="building.name"
                    :value="building.id"
                  />
                </el-select>
                <el-select 
                  v-model="selectedAreaForEnvironmental" 
                  placeholder="选择区域" 
                  size="small" 
                  style="width: 180px;"
                  :loading="loadingBuildingAreas"
                  :disabled="!selectedBuildingForEnvironmental"
                >
                  <el-option
                    v-for="area in buildingAreas"
                    :key="area.id"
                    :label="area.name"
                    :value="area.id"
                  />
                </el-select>
              </div>
            </div>
          </template>
          <EnvironmentalChart 
            v-if="selectedAreaForEnvironmental"
            :area-id="selectedAreaForEnvironmental" 
            data-type="temperature-humidity" 
            height="280px" 
          />
          <EnvironmentalChart 
            v-else
            data-type="temperature-humidity" 
            height="280px" 
          />
        </el-card>
      </el-col>
      <el-col :span="isMobile ? 24 : 8" :xs="24" :sm="24" :md="8" :lg="8">
        <!-- 公开告警卡片 -->
        <el-card class="dashboard-card">
          <template #header>
            <div class="card-header">
              <el-icon class="card-icon alert-icon"><Warning /></el-icon>
              <span class="card-title">公开告警</span>
            </div>
          </template>
          <div v-loading="loadingAlerts">
            <el-skeleton :rows="2" animated :loading="loadingAlerts">
              <template #default>
                <div v-if="alerts.length > 0">
                  <el-alert v-for="alert in alerts" :key="alert.id" :type="getAlertType(alert.grade)" show-icon
                    class="animated-alert mb-10">
                    <template #icon>
                      <el-icon v-if="alert.alert_type === 'fire'">
                        <Warning />
                      </el-icon>
                      <el-icon v-else-if="alert.alert_type === 'guard'">
                        <Bell />
                      </el-icon>
                      <el-icon v-else-if="alert.alert_type === 'crowd'">
                        <User />
                      </el-icon>
                      <el-icon v-else-if="alert.alert_type === 'health'">
                        <FirstAidKit />
                      </el-icon>
                      <el-icon v-else>
                        <Warning />
                      </el-icon>
                    </template>
                    <template #default>
                      <div class="alert-content">
                        <span class="alert-message">{{ alert.message }}</span>
                        <router-link :to="`/alerts?tab=alerts&alertId=${alert.id}`" class="alert-link">查看详情</router-link>
                      </div>
                    </template>
                  </el-alert>
                </div>
                <div v-else class="no-data-text">
                  暂无安全提醒
                </div>
              </template>
            </el-skeleton>
          </div>
        </el-card>
        
        <!-- 近期通知卡片 -->
        <el-card class="dashboard-card">
          <template #header>
            <div class="card-header">
              <el-icon class="card-icon notice-icon"><ChatLineRound /></el-icon>
              <span class="card-title">近期通知</span>
            </div>
          </template>
          <div v-loading="loadingNotices">
            <el-skeleton :rows="2" animated :loading="loadingNotices">
              <template #default>
                <div v-if="notices.length > 0">
                  <el-alert v-for="notice in notices" :key="notice.id" type="info" show-icon class="animated-alert mt-10">
                    <template #icon>
                      <el-icon>
                        <Bell />
                      </el-icon>
                    </template>
                    <template #default>
                      <div class="alert-content">
                        <span class="alert-message">{{ notice.content }}</span>
                        <router-link :to="`/alerts?tab=notices&noticeId=${notice.id}`"
                          class="alert-link">查看详情</router-link>
                      </div>

                    </template>
                  </el-alert>
                </div>
                <div v-else class="no-data-text">
                  暂无重要通知
                </div>
              </template>
            </el-skeleton>
          </div>
        </el-card>

        <!-- 校园资源导航卡片 -->
        <el-card class="dashboard-card">
          <template #header>
            <div class="card-header">
              <el-icon class="card-icon nav-header-icon"><Link /></el-icon>
              <span class="card-title">校园资源导航</span>
            </div>
          </template>
          <div class="navigation-links">
            <a v-for="item in navigationItems" :key="item.title" :href="item.link" target="_blank" class="nav-link">
              <div class="nav-item">
                <el-icon class="nav-icon">
                  <component :is="item.icon" />
                </el-icon>
                <span class="nav-title">{{ item.title }}</span>
              </div>
            </a>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
/* 改进的标题样式 */
.header-card {
  text-align: center !important;
  background: linear-gradient(135deg, #f6f9ff 0%, #f0f5ff 100%) !important;
  overflow: hidden;
  position: relative;
  border: none !important;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08) !important;
}

.header-wrapper {
  position: relative;
  z-index: 2;
  padding: 20px 0;
}

.header-title-container {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 15px;
}

.header-icon-container {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, #409eff, #007bff);
  border-radius: 50%;
  margin-right: 15px;
  box-shadow: 0 5px 15px rgba(64, 158, 255, 0.3);
}

.header-icon {
  font-size: 28px;
  color: white;
}

.header-wrapper::before,
.header-wrapper::after {
  content: "";
  position: absolute;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  background: rgba(64, 158, 255, 0.05);
  z-index: -1;
}

.header-wrapper::before {
  top: -150px;
  left: -150px;
}

.header-wrapper::after {
  bottom: -150px;
  right: -150px;
}

.header-title {
  font-size: 2.5rem;
  margin: 0;
  background: linear-gradient(90deg, #3352a3, #409EFF);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  letter-spacing: 2px;
  text-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
  transition: all 0.3s ease;
}

.header-title:hover {
  transform: translateY(-2px);
  text-shadow: 0 6px 16px rgba(64, 158, 255, 0.25);
}

.header-title .highlight {
  color: #409EFF;
  background: none;
  position: relative;
  padding: 0 5px;
  font-weight: 700;
}

.header-title .highlight::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 8px;
  background: rgba(64, 158, 255, 0.2);
  z-index: -1;
  border-radius: 4px;
}

.divider {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 15px 0;
}

.divider-line {
  width: 100px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(64, 158, 255, 0.5), transparent);
}

.divider-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #409EFF;
  margin: 0 8px;
}

.sub-title {
  font-size: 1.15rem;
  color: #666;
  max-width: 700px;
  margin: 0 auto;
  letter-spacing: 1px;
  animation: fadeIn 1s ease-in-out;
}

/* 卡片标题优化 */
.card-header {
  display: flex;
  align-items: center;
}

.card-icon {
  margin-right: 8px;
  font-size: 20px;
  padding: 3px;
  border-radius: 8px;
  color: white;
}

.hot-icon {
  background-color: #f56c6c;
}

.suggest-icon {
  background-color: #67c23a;
}

.favorite-icon {
  background-color: #e6a23c;
}

.trend-icon {
  background-color: #409eff;
}

.env-icon {
  background-color: #17a2b8;
}

.alert-icon {
  background-color: #dc3545;
}

.notice-icon {
  background-color: #6610f2;
}

.nav-header-icon {
  background-color: #fd7e14;
}

.card-title {
  font-size: 17px !important;
  font-weight: 600;
  color: #333;
  letter-spacing: 0.5px;
}

/* 改进的卡片样式 */
.dashboard-card {
  margin-bottom: 25px;
  display: flex;
  flex-direction: column;
  border: none;
  transition: all 0.3s;
}

.dashboard-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1) !important;
}

.dashboard-card :deep(.el-card__header) {
  padding: 16px 20px;
  background: #ffffff !important;
  border-bottom: 1px solid #f0f0f0;
}

.dashboard-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 15px 20px;
}

/* 保留现有其他样式 */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0% {
    opacity: 1;
  }

  50% {
    opacity: 0.8;
  }

  100% {
    opacity: 1;
  }
}

.pulse {
  animation: pulse 2s infinite;
}

.animate-tag {
  transition: all 0.3s ease;
}

.animate-tag:hover {
  transform: scale(1.05);
}

.animated-alert {
  transition: all 0.3s ease;
  animation: fadeIn 0.5s ease-in-out;
}

.animated-alert:hover {
  transform: translateX(5px);
}

.el-card {
  border-radius: 12px !important;

  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;

  border: 1px solid #ebeef5;
  transition: all 0.3s;

  &:hover {
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12) !important;
    transform: translateY(-2px);
  }
}

.stats-card {
  margin-bottom: 30px;

  .stat-item {
    padding: 16px;
    position: relative;
    overflow: hidden;

    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      width: 100%;
      height: 3px;
      background: linear-gradient(90deg, #409eff, #36b5ff);
      transform: scaleX(0);
      transform-origin: left;
      transition: transform 0.3s ease;
    }

    &:hover::after {
      transform: scaleX(1);
    }

    :deep(.el-statistic__content) {
      font-size: 28px !important;

      font-weight: 600;
      background: linear-gradient(45deg, #409eff, #36b5ff);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    :deep(.el-statistic__title) {
      font-size: 14px;
      color: #888;

      letter-spacing: 1px;
    }

    .stat-icon {
      margin-left: 5px;
      font-size: 18px;
      color: #409eff;
    }
  }
}

.dashboard-card {
  margin-bottom: 25px;
  display: flex;
  flex-direction: column;

  :deep(.el-card__header) {
    padding: 18px 24px;
    background: linear-gradient(45deg, #fafafa, #f6f9ff) !important;
    border-bottom: 1px solid #e4e7ed;
  }

  :deep(.el-card__body) {
    flex: 1;
    display: flex;
    flex-direction: column;
  }

  .card-title {
    font-size: 18px !important;

    color: #333;
    letter-spacing: 1px;
  }
}

.el-table {
  :deep(th) {
    background-color: #f8f9fa !important;
  }

  :deep(td) {
    padding: 12px 0 !important;

  }

  :deep(.cell) {
    line-height: 1.6;
  }

  &::before {

    display: none;
  }
}

#trend-chart {
  width: 100%;
  height: 320px !important;
  padding: 15px;

  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background-color: #fdfdfd;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.chart-controls {
  display: flex;
  align-items: center;
}

.empty-chart {
  height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-error {
  height: 320px;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f9f9f9;
  border-radius: 8px;
  border: 1px dashed #dcdfe6;
}

.el-alert--error {
  background-color: #fff0f0 !important;

  border: 1px solid rgba(245, 108, 108, 0.3);
}

.mb-20 {
  margin-bottom: 20px;
}

.tag-40 {
  width: 40px;
}

.mb-30 {
  margin-bottom: 30px;
}

.mr-20 {
  margin-right: 20px;
}

.mt-20 {
  margin-top: 20px;
}

.mt-30 {
  margin-top: 30px;
}

.mb-10 {
  margin-bottom: 10px;
}

.home-container {
  max-width: 1300px;
  margin: 0 auto;
  padding: 30px;
}

.no-data-message {
  padding: 30px 0;
  text-align: center;
}

.alert-link {
  margin-left: 10px;
  font-size: 12px;
  color: #409EFF;
  text-decoration: none;
}

.alert-link:hover {
  text-decoration: underline;
}

.no-data-text {
  padding: 20px;
  text-align: center;
  color: #909399;
  font-size: 14px;
}

.navigation-links {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.nav-link {
  text-decoration: none;
  color: inherit;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  border-radius: 8px;
  background-color: #f5f7fa;
  transition: all 0.3s;
  text-align: center;
}

.nav-item:hover {
  background-color: #ecf5ff;
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.nav-icon {
  font-size: 24px;
  margin-bottom: 8px;
  color: #409EFF;
}

.nav-title {
  font-size: 12px;
  color: #606266;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  width: 100%;
}

@media (max-width: 768px) {
  .home-container {
    padding: 15px;
    max-width: 100%;
  }

  .header-title {
    font-size: 1.8rem;
  }
  
  .header-icon-container {
    width: 40px;
    height: 40px;
  }
  
  .header-icon {
    font-size: 22px;
  }

  .sub-title {
    font-size: 1rem;
  }

  .divider-line {
    width: 60px;
  }

  .stats-card {
    margin-bottom: 15px;
  }

  .stats-card .stat-item :deep(.el-statistic__content) {
    font-size: 20px !important;
  }

  .stats-card .stat-item :deep(.el-statistic__title) {
    font-size: 12px;
  }

  .dashboard-card {
    margin-bottom: 15px;
  }

  .dashboard-card :deep(.el-card__header) {
    padding: 12px 15px;
  }

  .card-title {
    font-size: 16px !important;
  }

  #trend-chart {
    height: 250px !important;
  }

  .mb-20 {
    margin-bottom: 15px;
  }

  .mt-20 {
    margin-top: 15px;
  }

  .navigation-links {
    grid-template-columns: repeat(3, 1fr);
  }
  
  .chart-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .chart-controls {
    width: 100%;
    justify-content: flex-end;
  }
}

@media (max-width: 480px) {
  .header-title {
    font-size: 1.5rem;
  }
  
  .header-icon-container {
    width: 35px;
    height: 35px;
  }
  
  .header-icon {
    font-size: 18px;
  }

  .sub-title {
    font-size: 0.9rem;
  }

  .divider-line {
    width: 40px;
  }

  #trend-chart {
    height: 200px !important;
  }

  .navigation-links {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
