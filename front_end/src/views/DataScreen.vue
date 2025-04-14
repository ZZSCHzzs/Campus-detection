<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import * as echarts from 'echarts'
import { areaService, alertService, noticeService, summaryService, historicalService } from '../services/apiService'
import type { AreaItem, HistoricalData, SummaryData } from '../types'
import HeatMap from '../components/HeatMap.vue'

// 添加统计数据
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

// 添加页面状态管理
const pageState = reactive({
  loading: true,
  error: null,
  lastUpdated: ''
})

const currentTime = ref('')
const areas = ref<AreaItem[]>([])
const chartRef = ref<HTMLElement>()
let areaChart: echarts.ECharts | null = null

// 在 script setup 中添加类型定义
type MessageType = 'emergency' | 'warning' | 'info'
type Message = {
  id: number
  text: string
  type: MessageType
  timestamp: string
  sourceType: 'alert' | 'notice'
  sourceId: number
}

const messages = ref<Message[]>([])

const isFullscreen = ref(false)

// 计算属性：获取高占比区域
const highOccupancyAreas = computed(() => {
  return areas.value.filter(area => {
    if (area.capacity && area.detected_count) {
      return (area.detected_count / area.capacity) > 0.8
    }
    return false
  })
})

const toggleFullScreen = () => {
  const dashboard = document.querySelector('.dashboard') as HTMLElement
  if (!document.fullscreenElement) {
    dashboard.requestFullscreen()
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}

// 更新时间
const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleString()
  pageState.lastUpdated = now.toLocaleTimeString()
}

// 获取最新告警和通知
const fetchLatestMessages = async () => {
  try {
    const [alerts, notices] = await Promise.all([
      alertService.getUnsolvedAlerts(),
      noticeService.getLatestNotices(5)
    ])
    
    const newMessages: Message[] = [
      ...alerts.map(alert => ({
        id: alert.id,
        text: `🚨 ${alert.message}`,
        type: getAlertType(alert.grade),
        timestamp: alert.timestamp,
        sourceType: 'alert',
        sourceId: alert.id
      })),
      ...notices.map(notice => ({
        id: notice.id,
        text: `ℹ️ ${notice.title}`,
        type: 'info',
        timestamp: notice.timestamp,
        sourceType: 'notice',
        sourceId: notice.id
      }))
    ]
    
    messages.value = newMessages.sort((a, b) => 
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    ).slice(0, 8)
  } catch (error) {
    console.error('获取消息失败:', error)
  }
}

// 告警等级转换为消息类型
const getAlertType = (grade: number): MessageType => {
  const gradeMap: { [key: number]: MessageType } = {
    3: 'emergency', // 严重
    2: 'warning',   // 警告
    1: 'warning',   // 注意
    0: 'info'       // 普通
  }
  return gradeMap[grade] || 'info'
}

// 更新实时统计数据
const updateStats = async () => {
  try {
    const data = await summaryService.getSummary()
    summary.value = data as SummaryData
    updateTime()
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

// 添加当前显示的区域索引
const currentAreaIndex = ref(0)

// 初始化图表
const initChart = (chartDom: HTMLElement) => {
  if (!chartDom) return null
  
  const chart = echarts.init(chartDom)
  
  const option = {
    dataset: {
      source: [] as Array<[string, number]>
    },
    title: {
      text: '区域实时人流',
      subtext: '', 
      textStyle: {
        color: '#e2e8f0',
        fontSize: 16,
        fontWeight: 600
      },
      subtextStyle: {
        color: '#94a3b8',
        fontSize: 14
      }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.85)',
      borderColor: 'rgba(56, 189, 248, 0.3)',
      textStyle: {
        color: '#e2e8f0'
      },
      axisPointer: {
        type: 'line',
        lineStyle: {
          color: '#3b82f6'
        }
      }
    },
    grid: {
      left: '5%',
      right: '5%',
      top: '15%',
      bottom: '12%',
      containLabel: true
    },
    xAxis: {
      type: 'time',
      name: '时间',
      nameTextStyle: {
        color: '#88ccff'
      },
      axisLabel: {
        color: '#94a3b8',
        formatter: (value: string) => formatTime(value)
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: 'rgba(59, 130, 246, 0.1)'
        }
      },
      scale: true,
      boundaryGap: ['20%', '20%']
    },
    yAxis: {
      type: 'value',
      name: '人数',
      nameTextStyle: {
        color: '#88ccff'
      },
      axisLabel: {
        color: '#94a3b8'
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: 'rgba(59, 130, 246, 0.1)'
        }
      },
      scale: true,
      min: (value: { min: number }) => Math.floor(value.min * 0.8),
      max: (value: { max: number }) => Math.ceil(value.max * 1.2)
    },
    series: [{
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: {
        width: 3,
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#3b82f6' },
          { offset: 1, color: '#60a5fa' }
        ])
      },
      itemStyle: {
        color: '#3b82f6',
        borderWidth: 2,
        borderColor: '#fff'
      },
      areaStyle: {
        opacity: 0.2,
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
          { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
        ])
      }
    }]
  }
  
  chart.setOption(option)
  return chart
}

// 更新图表数据
const updateChart = async () => {
  try {
    if (!areaChart || !areas.value || areas.value.length === 0) return
    
    // 更新当前区域索引
    currentAreaIndex.value = (currentAreaIndex.value + 1) % areas.value.length
    const currentArea = areas.value[currentAreaIndex.value]

    // 获取当前区域的历史数据
    const historicalData = await historicalService.getAreaHistorical(currentArea.id)
    
    // 更新图表数据
    areaChart.setOption({
      title: {
        subtext: currentArea.name
      },
      dataset: {
        source: historicalData.map(d => ([
          d.timestamp,
          d.detected_count
        ]))
      }
    })
  } catch (error) {
    console.error('获取历史数据失败:', error)
  }
}

// 修改 onMounted 中的图表配置和更新逻辑
onMounted(async () => {
  try {
    pageState.loading = true
    
    // 获取区域数据
    areas.value = await areaService.getAll()
    
    // 初始化图表
    if (chartRef.value) {
      areaChart = initChart(chartRef.value)
    }
    
    // 初始获取数据
    await Promise.all([
      updateStats(),
      updateChart(),
      fetchLatestMessages()
    ])
    
    pageState.loading = false

    // 设置定时更新
    const statsTimer = setInterval(updateStats, 3000)
    const chartTimer = setInterval(updateChart, 10000) // 每10秒切换一次区域
    const messagesTimer = setInterval(fetchLatestMessages, 30000)
    const timeTimer = setInterval(updateTime, 1000)

    // 监听窗口大小变化
    window.addEventListener('resize', () => {
      areaChart?.resize()
    })
    
    // 组件卸载时清除定时器
    return () => {
      clearInterval(statsTimer)
      clearInterval(chartTimer)
      clearInterval(messagesTimer)
      clearInterval(timeTimer)
      window.removeEventListener('resize', () => {
        areaChart?.resize()
      })
    }
  } catch (error) {
    console.error('数据加载失败:', error)
    pageState.error = error instanceof Error ? error.message : '未知错误'
    pageState.loading = false
  }
})

const formatTime = (timestamp: string) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  });
}

// 添加地图图片路径
const mapImage = new URL('../assets/map_zx_F1.jpg', import.meta.url).href
</script>

<template>
  <div class="dashboard">
    <!-- 全屏切换按钮 -->
    <div class="fullscreen-toggle" @click="toggleFullScreen">
      <i class="fullscreen-icon" :class="{ 'is-active': isFullscreen }"></i>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="pageState.loading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <div class="loading-text">数据加载中...</div>
    </div>
    
    <!-- 错误信息 -->
    <div v-if="pageState.error" class="error-container">
      <div class="error-icon">⚠️</div>
      <div class="error-message">{{ pageState.error }}</div>
      <button class="retry-button" @click="location.reload()">重试</button>
    </div>
    
    <template v-if="!pageState.loading && !pageState.error">
      <!-- 顶部数据总览 -->
      <div class="overview">
        <div class="overview-item">
          <h3>今日总客流</h3>
          <div class="number">{{ summary.people_count }}</div>
          <div class="trend up">+{{ Math.floor(summary.people_count * 0.12) }}</div>
        </div>
        <div class="overview-item">
          <h3>在线节点数</h3>
          <div class="number">{{ summary.nodes_count }}</div>
          <div class="label">总量: {{ summary.terminals_count }}</div>
        </div>
        <div class="overview-item">
          <h3>告警事件数</h3>
          <div class="number warning">{{ summary.alerts_count }}</div>
          <div class="label" :class="{'warning-text': summary.alerts_count > 0}">
            {{ summary.alerts_count > 0 ? '需要处理' : '无告警' }}
          </div>
        </div>
        <div class="overview-item">
          <h3>通知事件数</h3>
          <div class="number info">{{ summary.notice_count }}</div>
          <div class="label">今日新增: {{ Math.floor(summary.notice_count * 0.3) }}</div>
        </div>
        <div class="overview-item">
          <h3>当前时间</h3>
          <div class="time">{{ currentTime }}</div>
          <div class="label">更新于: {{ pageState.lastUpdated }}</div>
        </div>
      </div>

      <!-- 主要图表区域 -->
      <div class="main-content">
        <div  class="charts-container">
          <div v-if="false" ref="chartRef" class="chart-container">
            <div class="tech-corners"></div>
          </div>
          <HeatMap :areas="areas" :mapImage="mapImage" class="heatmap-container" />
        </div>
        
        <div class="right-container">
          <!-- 区域状态容器 -->
          <div class="areas-container">
            <div class="tech-corners"></div>
            <div class="section-header">
              <h2>区域状态监控</h2>
              <div class="subtitle">Area Status Monitor</div>
            </div>
            <div class="status-grid">
              <el-card v-for="area in areas" :key="area.id" class="area-card">
                <div class="area-header">
                  <div class="header-left">
                    <h4>{{ area.name }}
                      <span class="status-badge" :class="{'status-active': area.status}">
                        {{ area.status ? '正常' : '异常' }}
                      </span>
                    </h4>
                  </div>
                </div>
                <div class="area-stats">
                  <div class="stat-item">
                    <span>{{ area.detected_count || 0 }}/{{ area.capacity }}</span>
                    <div class="usage-bar">
                      <div class="usage-fill" 
                           :style="{width: `${Math.min(100, area.detected_count ? (area.detected_count / area.capacity) * 100 : 0)}%`}"
                           :class="{'high-usage': area.detected_count && area.capacity && (area.detected_count / area.capacity) > 0.8}"></div>
                    </div>
                    <div class="area-meta">
                      <span>楼层: {{ area.floor }}F</span>
                      <span v-if="area.updated_at">{{ formatTime(area.updated_at) }}</span>
                    </div>
                  </div>
                </div>
              </el-card>
            </div>
          </div>

          <!-- 新增高占用区域提醒 -->
          <div v-if="highOccupancyAreas.length > 0" class="high-occupancy-alert">
            <div class="alert-header">
              <span class="alert-icon">⚠️</span>
              <span class="alert-title">高占用区域</span>
            </div>
            <div class="alert-content">
              <div v-for="area in highOccupancyAreas" :key="area.id" class="alert-item">
                {{ area.name }}: {{ area.detected_count }}/{{ area.capacity }} 
                ({{ Math.round((area.detected_count / area.capacity) * 100) }}%)
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 消息河流组件 -->
      <div class="message-river">
        <div class="message-container">
          <div 
            v-for="msg in messages" 
            :key="`${msg.sourceType}-${msg.sourceId}`"
            class="message-bubble"
            :class="[`type-${msg.type}`]"
          >
            <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
            <span class="message-text">{{ msg.text }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 20px;
  position: relative;
  min-height: 100vh;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  color: #e2e8f0;
}

/* 背景网格效果 */
.dashboard::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(rgba(59, 130, 246, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59, 130, 246, 0.05) 1px, transparent 1px);
  background-size: 20px 20px;
  z-index: 0;
}

/* 加载状态样式 */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(15, 23, 42, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.loading-spinner {
  width: 60px;
  height: 60px;
  border: 5px solid rgba(56, 189, 248, 0.3);
  border-top: 5px solid #38bdf8;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 15px;
  font-size: 18px;
  color: #e2e8f0;
}

/* 错误信息样式 */
.error-container {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(30, 41, 59, 0.9);
  padding: 30px;
  border-radius: 15px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(244, 63, 94, 0.3);
  text-align: center;
  z-index: 2000;
  max-width: 400px;
  width: 90%;
}

.error-icon {
  font-size: 40px;
  margin-bottom: 15px;
}

.error-message {
  color: #e2e8f0;
  margin-bottom: 20px;
  line-height: 1.5;
}

.retry-button {
  background: rgba(244, 63, 94, 0.2);
  color: #f43f5e;
  border: 1px solid rgba(244, 63, 94, 0.5);
  padding: 8px 20px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.retry-button:hover {
  background: rgba(244, 63, 94, 0.3);
  transform: translateY(-2px);
}

/* 全屏相关样式 */
.dashboard:fullscreen {
  padding: 30px;
  width: 100vw;
  height: 100vh;
  overflow: auto;
}

.dashboard:fullscreen .overview,
.dashboard:fullscreen .main-content {
  opacity: 0;
  animation: fadeIn 0.5s ease-in-out forwards;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 适配不同浏览器的全屏选择器 */
.dashboard:-webkit-full-screen,
.dashboard:-moz-full-screen,
.dashboard:-ms-fullscreen {
  padding: 40px;
  width: 100vw;
  height: 100vh;
  overflow: auto;
}

.fullscreen-toggle {
  position: fixed;
  right: 20px;
  top: 20px;
  width: 40px;
  height: 40px;
  background: rgba(30, 41, 59, 0.7);
  backdrop-filter: blur(10px);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0 .3s ease;
  z-index: 1000;
  border: 1px solid rgba(56, 189, 248, 0.3);
  box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
}

.fullscreen-toggle:hover {
  background: rgba(56, 189, 248, 0.2);
  transform: scale(1.1);
}

.fullscreen-icon {
  width: 16px;
  height: 16px;
  position: relative;
  transition: all 0.3s ease;
}

.fullscreen-icon::before,
.fullscreen-icon::after {
  content: '';
  position: absolute;
  border: 2px solid #38bdf8;
}

.fullscreen-icon::before {
  width: 6px;
  height: 6px;
  border-width: 2px 0 0 2px;
  left: 0;
  top: 0;
}

.fullscreen-icon::after {
  width: 6px;
  height: 6px;
  border-width: 0 2px 2px 0;
  right: 0;
  bottom: 0;
}

.fullscreen-icon.is-active::before {
  transform: rotate(-45deg);
  left: 2px;
  top: 2px;
}

.fullscreen-icon.is-active::after {
  transform: rotate(-45deg);
  right: 2px;
  bottom: 2px;
}

/* 数据总览样式 */
.overview {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 15px;
  margin-bottom: 30px;
  position: relative;
  z-index: 1;
}

@media (max-width: 1200px) {
  .overview {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .overview {
    grid-template-columns: repeat(2, 1fr);
  }
}

.overview-item {
  background: rgba(30, 41, 59, 0.7);
  padding: 15px;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.2);
  transition: all 0.3s;
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
}

.overview-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #38bdf8, transparent);
  animation: scanline 3s linear infinite;
}

@keyframes scanline {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.overview-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 25px rgba(56, 189, 248, 0.25);
}

/* 数字样式 */
.number {
  font-size: 2rem;
  font-weight: bold;
  margin-top: 8px;
  background: linear-gradient(90deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  color: transparent;
  text-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
}

.number.warning {
  background: linear-gradient(90deg, #f43f5e, #fb7185);
  -webkit-background-clip: text;
  color: transparent;
  text-shadow: 0 0 10px rgba(244, 63, 94, 0.5);
}

.number.info {
  background: linear-gradient(90deg, #38bdf8, #22d3ee);
  -webkit-background-clip: text;
  color: transparent;
  text-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
}

/* 标题样式 */
.overview-item h3 {
  margin: 0;
  font-size: 0.9rem;
  color: #94a3b8;
  position: relative;
  padding-left: 12px;
}

.overview-item h3::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 4px;
  background: #38bdf8;
  border-radius: 50%;
}

/* 标签和趋势指标 */
.label {
  margin-top: 6px;
  font-size: 0.8rem;
  color: #94a3b8;
}

.warning-text {
  color: #fb7185;
}

.trend {
  position: absolute;
  right: 15px;
  bottom: 15px;
  font-size: 0.8rem;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: 8px;
}

.trend.up {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.trend.down {
  background: rgba(244, 63, 94, 0.1);
  color: #f43f5e;
}

/* 时间显示样式 */
.time {
  font-size: 1.5rem;
  font-weight: bold;
  margin-top: 8px;
  background: linear-gradient(90deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  color: transparent;
  font-family: 'Courier New', monospace;
}

/* 主内容样式 */
.main-content {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 25px;
  height: calc(100vh - 160px - 60px);
  margin-bottom: 60px;
  position: relative;
  z-index: 1;
}

@media (max-width: 1200px) {
  .main-content {
    grid-template-columns: 1fr;
    gap: 15px;
  }
}

.charts-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chart-container {
  flex: 1;
  background: rgba(30, 41, 59, 0.7);
  border-radius: 15px;
  padding: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.2);
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
}

.heatmap-container {
  flex: 1;
  border-radius: 15px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

/* 右侧容器样式 */
.right-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 区域状态容器样式 */
.areas-container {
  flex: 1;
  background: rgba(30, 41, 59, 0.7);
  border-radius: 15px;
  padding: 15px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.2);
  overflow: hidden;
  backdrop-filter: blur(10px);
  position: relative;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 8px;
  height: calc(100% - 40px);
  overflow-y: auto;
  padding: 5px;
}

.area-card {
  background: rgba(30, 41, 59, 0.8) !important;
  border: 1px solid rgba(56, 189, 248, 0.2) !important;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  min-height: 80px;
  padding: 8px 10px !important;
  display: flex;
  flex-direction: column;
  transition: all 0.3s;
}

.area-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(56, 189, 248, 0.25);
}

.area-header h4 {
  font-size: 0.9rem;
  margin: 0;
  color: #e2e8f0;
  display: flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-left {
  width: 100%;
}

.area-stats {
  margin-top: 8px;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 5px 8px;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(56, 189, 248, 0.15);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  transition: all 0.3s ease;
  width: 100%;
  position: relative;
  overflow: hidden;
}

.stat-item span {
  font-size: 1.2rem;
  font-weight: bold;
  background: linear-gradient(45deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  color: transparent;
}

.usage-bar {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 2px;
}

.area-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.7rem;
  color: #94a3b8;
  margin-top: 3px;
}

.status-badge {
  padding: 2px 5px;
  border-radius: 10px;
  font-size: 0.7rem;
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  margin-left: 4px;
}

/* 科技感边角装饰 */
.tech-corners::before,
.tech-corners::after {
  content: '';
  position: absolute;
  width: 40px;
  height: 40px;
}

.tech-corners::before {
  top: 0;
  left: 0;
  border-top: 2px solid rgba(56, 189, 248, 0.5);
  border-left: 2px solid rgba(56, 189, 248, 0.5);
}

.tech-corners::after {
  bottom: 0;
  right: 0;
  border-bottom: 2px solid rgba(56, 189, 248, 0.5);
  border-right: 2px solid rgba(56, 189, 248, 0.5);
}

/* 自定义滚动条样式 */
.status-grid::-webkit-scrollbar {
  width: 5px;
}

.status-grid::-webkit-scrollbar-track {
  background: rgba(148, 163, 184, 0.1);
  border-radius: 3px;
}

.status-grid::-webkit-scrollbar-thumb {
  background: rgba(56, 189, 248, 0.3);
  border-radius: 3px;
}

.status-grid::-webkit-scrollbar-thumb:hover {
  background: rgba(56, 189, 248, 0.5);
}

/* 使用进度条替代旧的样式 */
.usage-bar {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
  margin-top: 5px;
}

.usage-fill {
  height: 100%;
  background: linear-gradient(90deg, #38bdf8, #818cf8);
  border-radius: 4px;
  transition: width 0.5s ease-out;
}

.usage-fill.high-usage {
  background: linear-gradient(90deg, #fb923c, #f43f5e);
  animation: pulse-warning 2s infinite;
}

@keyframes pulse-warning {
  0% { opacity: 0.7; }
  50% { opacity: 1; }
  100% { opacity: 0.7; }
}

.stat-item span {
  font-size: 1.5rem;
  font-weight: bold;
  background: linear-gradient(45deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  color: transparent;
  text-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
}

/* 高占用区域提醒 */
.high-occupancy-alert {
  background: rgba(30, 41, 59, 0.7);
  border-radius: 15px;
  padding: 15px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(251, 146, 60, 0.3);
  backdrop-filter: blur(10px);
  animation: pulse-border 2s infinite;
}

@keyframes pulse-border {
  0% { border-color: rgba(251, 146, 60, 0.3); }
  50% { border-color: rgba(251, 146, 60, 0.7); }
  100% { border-color: rgba(251, 146, 60, 0.3); }
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.alert-icon {
  font-size: 18px;
}

.alert-title {
  font-size: 16px;
  font-weight: 500;
  color: #fb923c;
}

.alert-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alert-item {
  padding: 8px 12px;
  background: rgba(251, 146, 60, 0.1);
  border-radius: 8px;
  font-size: 14px;
  color: #fed7aa;
}

/* 状态徽章样式 */
.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.8rem;
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  margin-left: 8px;
}

.status-badge.status-active {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

/* 消息河流样式 */
.message-river {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 60px;
  background: rgba(30, 41, 59, 0.8);
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.2);
  border-top: 1px solid rgba(56, 189, 248, 0.2);
  overflow: hidden;
  z-index: 1000;
  backdrop-filter: blur(10px);
}

.message-container {
  display: flex;
  gap: 20px;
  padding: 10px;
  animation: scrollMessages 30s linear infinite;
  white-space: nowrap;
}

@keyframes scrollMessages {
  0% { transform: translateX(100%); }
  100% { transform: translateX(-100%); }
}

.message-container:hover {
  animation-play-state: paused;
}

.message-bubble {
  padding: 8px 15px;
  border-radius: 8px;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: rgba(15, 23, 42, 0.7);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.15);
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
}

.message-bubble::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 30%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.1), transparent);
  transform: skewX(-15deg);
  animation: shine 3s infinite;
  animation-delay: calc(var(--index, 0) * 0.5s);
}

@keyframes shine {
  0% { transform: translateX(-200%) skewX(-15deg); }
  100% { transform: translateX(200%) skewX(-15deg); }
}

.type-emergency {
  border-left: 4px solid #f43f5e;
  box-shadow: 0 0 15px rgba(244, 63, 94, 0.3);
}

.type-warning {
  border-left: 4px solid #fb923c;
  box-shadow: 0 0 15px rgba(251, 146, 60, 0.3);
}

.type-info {
  border-left: 4px solid #38bdf8;
  box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
}

.message-time {
  color: #94a3b8;
  font-size: 12px;
  font-family: 'Courier New', monospace;
}

.message-text {
  color: #e2e8f0;
  font-weight: 500;
}
</style>