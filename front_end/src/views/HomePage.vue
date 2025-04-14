<script lang="ts" setup>
import { ref, onMounted, computed, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import type { AreaItem, Alert, Notice, SummaryData } from '../types'
import { useAuthStore } from '../stores/auth'
import { areaService, noticeService, alertService, summaryService } from '../services/apiService'
import apiService from '../services/apiService'
import AreaList from '../components/AreaList.vue'

import {
  User, Monitor, OfficeBuilding, Connection, MapLocation,
  DataAnalysis, Warning, Bell, FirstAidKit
} from '@element-plus/icons-vue'

const Hotareas = ref<AreaItem[]>([])
const loading = ref(false)
const favoriteAreas = ref<AreaItem[]>([])
const loadingFavorites = ref(false)

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
  people_count: '系统总人数',
  notice_count: '系统通知',
  alerts_count: '安全告警'
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
    favoriteAreaIds.value = []
    favoriteAreas.value = []
  }
}

const chartLoading = ref(false)
const chartInitFailed = ref(false)

let chart: echarts.ECharts | null = null
let resizeHandler: (() => void) | null = null
let intervalTimer1: number | null = null 
let intervalTimer2: number | null = null

const initChart = async () => {
  chartLoading.value = false
  chartInitFailed.value = false
  try {
    const chartDom = document.getElementById('trend-chart')
    if (!chartDom) {
      chartInitFailed.value = true
      return
    }

    if (chart) {
      chart.dispose()
    }

    chart = echarts.init(chartDom)
    const option = {
      title: { text: '今日人流趋势' },
      tooltip: { trigger: 'axis' },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: { type: 'category', data: ['6:00', '9:00', '12:00', '15:00', '18:00', '21:00', '24:00'] },
      yAxis: { type: 'value' },
      series: [{
        data: [10, 200, 100, 180, 70, 110, 20],
        type: 'line',
        smooth: true,
        symbolSize: 8,
        lineStyle: {
          width: 3,
          shadowColor: 'rgba(64, 158, 255, 0.2)',
          shadowBlur: 12,
          shadowOffsetY: 6
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.4)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.02)' }
          ])
        },
        label: {
          show: true,
          position: 'top',
          color: '#36b5ff',
          fontSize: 12
        }
      }]
    }

    chart.setOption(option)
    chartLoading.value = false
  } catch (error) {
    chartLoading.value = false
    chartInitFailed.value = true
  }
}

const summary = ref<SummaryData>({
  nodes_count: 0,
  terminals_count: 0,
  buildings_count: 0,
  areas_count: 0,
  historical_data_count: 0,
  people_count: 0,
  notice_count: 0,
  alerts_count: 0
})
const loadingSummary = ref(false)

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

const alerts = ref<Alert[]>([])
const notices = ref<Notice[]>([])
const loadingAlerts = ref(false)
const loadingNotices = ref(false)

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

const getAlertType = (grade: number) => {
  switch (grade) {
    case 3: return 'error'
    case 2: return 'warning'
    case 1: return 'info'
    default: return 'success'
  }
}

const isMobile = ref(false)

const checkScreenSize = () => {
  isMobile.value = window.innerWidth < 992
}

onMounted(async () => {
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)
  await Promise.all([
    fetchHotAreas(),
    fetchSummary(),
    fetchFavoriteAreas(),
    fetchPublicAlerts(),
    fetchLatestNotices()
  ]).catch(() => ElMessage.error('数据获取出错'))
  isFirstLoad.value = false
  setTimeout(async () => {
    await initChart()
    resizeHandler = () => {
      if (chart) {
        try {
          chart.resize()
        } catch (e) {

        }
      }
    }
    window.addEventListener('resize', resizeHandler)
  })
  intervalTimer1 = setInterval(() => {
    fetchHotAreas();
    fetchPublicAlerts();
    fetchLatestNotices();
    fetchSummary();
  }, 30000);
  if (isAuthenticated.value) {
    intervalTimer2 = setInterval(async () => {
      await fetchFavoriteAreas()
    }, 30000)
  }
  onBeforeUnmount(() => {
    clearInterval(intervalTimer1)
    if (isAuthenticated.value) {
      clearInterval(intervalTimer2)
    }
  })
})

onBeforeUnmount(() => {

  if (intervalTimer1) clearInterval(intervalTimer1)
  if (intervalTimer2) clearInterval(intervalTimer2)

  window.removeEventListener('resize', checkScreenSize)
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)

  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<template>
  <div class="home-container">
    <el-card class="header-card">
      <div class="header-wrapper">
        <h1 class="header-title">智慧校园<span class="highlight">人员检测</span>系统</h1>
        <div class="sub-title">实时监测校园内各区域人员情况，保障安全与高效管理</div>
      </div>
    </el-card>
    <el-card class="stats-card mb-20 mt-20">
      <el-skeleton :rows="1" animated :loading="loadingSummary">
        <template #default>
          <div v-if="Object.values(summary).some(value => value > 0)">
            <el-row :gutter="20">
              <el-col v-for="(value, key) in summary" :key="key" :span="isMobile ? 12 : 4" :xs="8" :sm="6" :md="4"
                :lg="3">
                <el-statistic :title="STATS_LABELS[key]" :value="value" class="stat-item">
                  <template #suffix>
                    <el-icon v-if="key === 'people_count'" class="stat-icon">
                      <User />
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
                      <DataAnalysis />
                    </el-icon>
                    <el-icon v-else-if="key === 'notice_count'" class="stat-icon">
                      <Bell />
                    </el-icon>
                    <el-icon v-else-if="key === 'alerts_count'" class="stat-icon">
                      <Warning />
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
    </el-card>

    <el-row :gutter="20" class="mt-20">
      <el-col :span="isMobile ? 24 : 16" :xs="24" :sm="24" :md="16" :lg="16">
        <el-card class="dashboard-card">
          <template #header>
            <span class="card-title pulse">🏃 热门区域实时排行</span>
          </template>
          <AreaList :areas="Hotareas" :loading="loading" empty-text="暂无热门区域数据"
            :max-height="Hotareas.length > 8 ? '150px' : 'auto'" />
        </el-card>
        <el-card v-if="isAuthenticated" class="dashboard-card">
          <template #header>
            <span class="card-title">⭐ 我的收藏区域</span>
          </template>
          <AreaList :areas="favoriteAreas" :loading="loadingFavorites"
            :max-height="favoriteAreas.length > 6 ? '193px' : 'auto'" empty-text="暂无收藏区域" />
        </el-card>
        <el-card class="dashboard-card">
          <template #header>
            <div class="chart-header">
              <span class="card-title">📈 人员变化趋势</span>
              <el-button v-if="chartInitFailed" size="small" type="primary" @click="initChart">
                重新加载图表
              </el-button>
            </div>
          </template>
          <el-skeleton :rows="8" animated :loading="chartLoading">
            <template #default>
              <div v-if="!chartInitFailed" id="trend-chart" style="height:320px; width:100%;"></div>
              <div v-else class="chart-error">
                <el-empty description="图表加载失败" :image-size="100">
                  <template #description>
                    <p>趋势图加载失败，请点击"重新加载图表"按钮重试</p>
                  </template>
                </el-empty>
              </div>
            </template>
          </el-skeleton>
        </el-card>
      </el-col>
      <el-col :span="isMobile ? 24 : 8" :xs="24" :sm="24" :md="8" :lg="8">
        <el-card class="dashboard-card">
          <template #header>
            <span class="card-title">⚠️ 公开告警</span>
          </template>
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
        </el-card>
        <el-card class="dashboard-card">
          <template #header>
            <span class="card-title">📢 近期通知</span>
          </template>
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
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>

.header-card {
  text-align: center !important;
  background: linear-gradient(135deg, #f6f9ff 0%, #f0f5ff 100%) !important;
  overflow: hidden;
  position: relative;
}

.header-wrapper {
  position: relative;
  z-index: 2;
  padding: 20px 0;
}

.header-wrapper::before,
.header-wrapper::after {
  content: "";
  position: absolute;
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: rgba(64, 158, 255, 0.1);
  z-index: -1;
}

.header-wrapper::before {
  top: -50px;
  left: -50px;
}

.header-wrapper::after {
  bottom: -50px;
  right: -50px;
}

.header-title {
  font-size: 2.5rem;
  margin-bottom: 16px;
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

.sub-title {
  font-size: 1.15rem;
  color: #666;
  max-width: 700px;
  margin: 0 auto;
  letter-spacing: 1px;
  animation: fadeIn 1s ease-in-out;
}

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
  max-width: 1400px;

  margin: 20px auto;
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

@media (max-width: 768px) {
  .home-container {
    padding: 15px;
    max-width: 100%;
  }

  .header-title {
    font-size: 1.8rem;
    margin-bottom: 10px;
  }

  .sub-title {
    font-size: 1rem;
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
}

@media (max-width: 480px) {
  .header-title {
    font-size: 1.5rem;
  }

  .sub-title {
    font-size: 0.9rem;
  }

  #trend-chart {
    height: 200px !important;
  }
}
</style>
