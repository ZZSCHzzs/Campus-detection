<script setup lang="ts">
import { ref, onMounted, reactive, watch } from 'vue'
import * as echarts from 'echarts'
import { areaService, alertService, noticeService, summaryService, nodeService } from '../services'
import type { AreaItem, HistoricalData, SummaryData, HardwareNode } from '../types'
import HistoricalChart2  from '../components/chart-datascreen/HistoricalChart2.vue'
import HardwareNodeStatus from '../components/data/HardwareNodeStatus.vue'
import EnvironmentalChart2 from '../components/chart-datascreen/EnvironmentalChart2.vue'

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

const pageState = reactive({
  loading: true,
  error: null,
  lastUpdated: ''
})

const currentTime = ref('')
const areas = ref<AreaItem[]>([])
const chartRef = ref<HTMLElement>()
let areaChart: echarts.ECharts | null = null

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

const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleString()
  pageState.lastUpdated = now.toLocaleTimeString()
}

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

const getAlertType = (grade: number): MessageType => {
  const gradeMap: { [key: number]: MessageType } = {
    3: 'emergency',
    2: 'warning',
    1: 'warning',
    0: 'info'
  }
  return gradeMap[grade] || 'info'
}

const updateStats = async () => {
  try {
    const data = await summaryService.getSummary()
    summary.value = data as SummaryData
    const alerts = await alertService.getUnsolvedAlerts()
    const alertsCount = alerts.length
    summary.value.alerts_count = alertsCount
    updateTime()
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

const currentAreaIndex = ref(0)

const cardAnimationState = reactive({
  isMoving: false,
  currentPosition: 0,
  currentIndex: 0,
  cardWidths: [] as number[],
  cardHeights: [] as number[],
  animationTimer: null as any
})

const calculateCardWidths = () => {
  const cards = document.querySelectorAll('.area-card')

  cardAnimationState.cardWidths = []

  cards.forEach((card, index) => {
    const cardElement = card as HTMLElement
    const cardWidth = cardElement.offsetWidth + 12
    cardAnimationState.cardWidths.push(cardWidth)
  })

  console.log('卡片宽度数组:', cardAnimationState.cardWidths)
}

const calculateCardHeights = () => {
  const cards = document.querySelectorAll('.area-card')
  
  cardAnimationState.cardHeights = []

  // 只计算原始区域的卡片，不包括重复的卡片
  const uniqueCards = Array.from(cards).slice(0, areas.value.length)
  
  uniqueCards.forEach((card) => {
    const cardElement = card as HTMLElement
    // 计算卡片高度加上gap值
    const cardHeight = cardElement.offsetHeight + 12
    cardAnimationState.cardHeights.push(cardHeight)
  })

  console.log('卡片高度数组:', cardAnimationState.cardHeights)
}

// const animateCards = () => {
//   const container = document.querySelector('.card-container') as HTMLElement
//   if (!container || !areas.value.length) return

//   const cards = document.querySelectorAll('.area-card')
//   const uniqueAreasCount = areas.value.length
//   if (cards.length <= 0) return

//   cardAnimationState.isMoving = true

//   // 使用固定步长，确保每次滚动精确一个卡片的高度
//   // 计算第一个卡片的实际高度作为固定步长
//   const firstCardHeight = cardAnimationState.cardHeights[0] || 62 // 使用固定步长

//   // 修改为垂直方向移动固定步长
//   cardAnimationState.currentPosition -= firstCardHeight
//   container.style.transform = `translateY(${cardAnimationState.currentPosition}px)`

//   cardAnimationState.currentIndex = (cardAnimationState.currentIndex + 1) % cards.length

//   if (cardAnimationState.currentIndex >= uniqueAreasCount) {
//     setTimeout(() => {
//       container.style.transition = 'none'
//       cardAnimationState.currentPosition = 0
//       cardAnimationState.currentIndex = 0
//       container.style.transform = `translateY(0px)`

//       setTimeout(() => {
//         container.style.transition = 'transform 0.5s ease-in-out'
//         cardAnimationState.isMoving = false
//       }, 50)
//     }, 500)
//   } else {
//     setTimeout(() => {
//       cardAnimationState.isMoving = false
//     }, 500)
//   }
// }

onMounted(async () => {
  try {
    pageState.loading = true

    areas.value = await areaService.getAll()

    await Promise.all([
      updateStats(),
      fetchLatestMessages(),
    ])

    setTimeout(calculateCardWidths, 500)
    setTimeout(calculateCardHeights, 500)
    // cardAnimationState.animationTimer = setInterval(() => {
    //   if (!cardAnimationState.isMoving && areas.value.length > 0) {
    //     animateCards()
    //   }
    // }, 2000)

    const handleResize = () => {
      cardAnimationState.currentPosition = 0
      cardAnimationState.currentIndex = 0
      const container = document.querySelector('.card-container') as HTMLElement
      if (container) {
        container.style.transition = 'none'
        container.style.transform = `translateY(0px)`
        setTimeout(() => {
          container.style.transition = 'transform 0.5s ease-in-out'
          calculateCardWidths()
          calculateCardHeights()
        }, 50)
      }
    }

    window.addEventListener('resize', handleResize)
    pageState.loading = false

    const statsTimer = setInterval(updateStats, 3000)
    const messagesTimer = setInterval(fetchLatestMessages, 30000)
    const timeTimer = setInterval(updateTime, 1000)

    window.addEventListener('resize', () => {
      areaChart?.resize()
    })

    return () => {
      clearInterval(statsTimer)
      clearInterval(messagesTimer)
      clearInterval(timeTimer)
      clearInterval(cardAnimationState.animationTimer)
      window.removeEventListener('resize', handleResize)
    }
  } catch (error) {
    console.error('数据加载失败:', error)
    pageState.error = error instanceof Error ? error.message : '未知错误'
    pageState.loading = false
  }
})

const mapImage = new URL('../assets/map_zx_F1.png', import.meta.url).href

const statusGridRef = ref(null)

function formatTime(value: string) {
  if (!value) return '--:--'

  try {
    const date = new Date(value)

    if (isNaN(date.getTime())) {
      return value
    }

    const today = new Date()
    if (date.toDateString() === today.toDateString()) {
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    } else {

      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      }).replace(/\//g, '-')
    }
  } catch (error) {
    console.error('日期格式化错误:', error)
    return value
  }
}
</script>

<template>
  <div class="dashboard">
    
    <div class="fullscreen-toggle" @click="toggleFullScreen">
      <i class="fullscreen-icon" :class="{ 'is-active': isFullscreen }"></i>
    </div>

    <div v-if="pageState.loading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <div class="loading-text">数据加载中...</div>
    </div>

    <div v-if="pageState.error" class="error-container">
      <div class="error-icon">⚠️</div>
      <div class="error-message">{{ pageState.error }}</div>
    </div>

    <template v-if="!pageState.loading && !pageState.error">
      
      <div class="overview">
        <div class="overview-item">
          <h3>今日总客流</h3>
          <div class="number-container">
            <div class="number">{{ summary.people_count }}</div>
            <div class="trend up">+{{ Math.floor(summary.people_count * 0.12) }}</div>
          </div>
        </div>
        <div class="overview-item">
          <h3>在线节点数</h3>
          <div class="number-container">
            <div class="number">{{ summary.nodes_online_count }}</div>
          <div class="label">总量: {{ summary.nodes_count }}</div>
          </div>  
        </div>
        <div class="overview-item">
          <h3>在线终端数</h3>
          <div class="number-container">
            <div class="number">{{ summary.terminals_online_count }}</div>
            <div class="label">总量: {{ summary.terminals_count }}</div>
          </div>
        </div>    
        <div class="overview-item">
          <h3>告警事件数</h3>
          <div class="number-container">
            <div class="number warning">{{ summary.alerts_count }}</div>
            <div class="label" :class="{ 'warning-text': summary.alerts_count > 0 }">
              {{ summary.alerts_count > 0 ? '需要处理' : '无告警' }}
            </div>
          </div>
        </div>
        <div class="overview-item">
          <h3>通知事件数</h3>
          <div class="number-container">
            <div class="number info">{{ summary.notice_count }}</div>
            <div class="label">今日新增: {{ Math.floor(summary.notice_count * 0.3) }}</div>
          </div>
        </div>
        <div class="overview-item">
          <h3>建筑数量</h3>
          <div class="number-container">
            <div class="number">{{ summary.buildings_count }}</div>
            <div class="label">已覆盖: {{ summary.areas_count }}</div>
          </div>
        </div>
        <div class="overview-item">
          <h3>区域总数</h3>
          <div class="number-container">
            <div class="number">{{ summary.areas_count }}</div>
            <div class="trend up">+{{ Math.max(1, Math.floor(summary.areas_count * 0.05)) }}</div>
          </div>
        </div>
        <div class="overview-item">
          <h3>历史数据量</h3>
          <div class="number-container">
            <div class="number info">{{ summary.historical_data_count }}</div>
          </div>
        </div>
        <div class="overview-item">
          <h3>系统用户数</h3>
          <div class="number-container">
            <div class="number">{{ summary.users_count }}</div>
            <div class="trend up">+{{ Math.max(1, Math.floor(summary.users_count * 0.08)) }}</div>
          </div>
        </div>
        <div class="overview-item">
          <h3>当前时间</h3>
          <div class="time">{{ currentTime }}</div>
        </div>
      </div>

      <div class="main-content">
        <div class="lower-content">
          <ThreeDHeatMap :areas="areas" :mapImage="mapImage" class="heatmap-container absolute-heatmap" />
          <!-- 热力图中央顶部倒梯形标题 -->
          <div class="heatmap-title-trapezoid">
            <span class="heatmap-title-text">实时3D热力图</span>
          </div>
          <!-- 移动区域状态监控到热力图左侧 -->
          <div class="left-column-1 fixed-left"> 
            <div class="areas-container">
              <div class="tech-corners"></div>
              <div class="section-header">
                <h2>区域状态监控</h2>
                <div class="subtitle">Area Status Monitor</div>
              </div>
              <div class="status-grid" ref="statusGridRef">
                <div class="card-container" :class="{ 'moving': cardAnimationState.isMoving }">
                  <el-card v-for="(area, index) in areas" :key="area.id" class="area-card">
                    <!-- 区域卡片内容 -->
                    <div class="area-header">
                      <h4>
                        {{ area.name.length > 6 ? area.name.substring(0, 6) + '...' : area.name }}
                        <span class="status-badge" :class="{ 'status-active': area.status }">
                          {{ area.status ? '正常' : '异常' }}
                        </span>
                      </h4>
                    </div>

                    <div class="area-stats">
                      <div class="stat-item">
                        <div class="stat-top">
                          <span>{{ area.detected_count || 0 }}/{{ area.capacity }}</span>
                          <span v-if="area.updated_at" class="update-time">{{ formatTime(area.updated_at) }}</span>
                        </div>
                        <div class="usage-bar">
                          <div class="usage-fill"
                            :style="{ width: `${Math.min(100, area.detected_count ? (area.detected_count / area.capacity) * 100 : 0)}%` }"
                            :class="{ 'high-usage': area.detected_count && area.capacity && (area.detected_count / area.capacity) > 0.8 }">
                          </div>
                        </div>
                      </div>
                    </div>
                  </el-card>
                </div>
              </div>
            </div>
            <!-- <div class="right-column"> -->
              <div class="node-status-container">
                <div class="tech-corners"></div>
                <div class="section-header">
                  <h2>硬件节点状态</h2>
                  <div class="subtitle">Hardware Node Status</div>
                </div>
                <div class="node-content">
                  <HardwareNodeStatus :areaId="areas.length > 0 ? areas[currentAreaIndex].id : null" />
                </div>
              </div>
            <!-- </div> -->
            </div>
          
          <div class="left-column-2 fixed-right"> 
            <div ref="chartRef" class="chart-container">
              <div class="tech-corners"></div>
              <div class="chart-inner-container">
                <EnvironmentalChart2 
                  :areaId="areas.length > 0 ? areas[currentAreaIndex].id : null" 
                  :dataType="'temperature-humidity'" 
                  :hideTitle="true" 
                  :hideControls="true"
                  :width="'100%'"
                  :height="'100%'"
                  :styleConfig="{
                    gridLineColor: 'rgba(56, 189, 248, 0.1)',
                    gridLineType: 'dashed',
                    showGridLine: true,
                    axisLineColor: 'rgba(56, 189, 248, 0.5)',
                    axisLabelColor: '#a5f3fc',
                    axisLabelFontSize: 11,
                    seriesColors: ['#22d3ee', '#a78bfa'],
                    backgroundColor: 'transparent',
                    textColor: '#e0f2fe',
                    fontSize: 12,
                    lineWidth: 2,
                    padding: {
                      top: '15%',
                      right: '5%',
                      bottom: '10%',
                      left: '12%'
                    },
                    showLegend: true,
                    legendPosition: 'top',
                    tooltipBackgroundColor: 'rgba(15, 23, 42, 0.9)',
                    tooltipTextColor: '#f0f9ff',
                    areaStyle: {
                      opacity: 0.2,
                      colorStops: [
                        { offset: 0, color: 'rgba(34, 211, 238, 0.4)' },
                        { offset: 1, color: 'rgba(34, 211, 238, 0)' }
                      ]
                    }
                  }"
                />
              </div>
            </div>
            <div ref="chartRef" class="chart-container">
              <div class="tech-corners"></div>
              <div class="chart-inner-container">
                <HistoricalChart2 
                  :areaId="areas.length > 0 ? areas[currentAreaIndex].id : null" 
                  :hideTitle="true" 
                  :hideControls="true"
                  :width="'100%'"
                  :height="'100%'"
                  :hideDataZoom="true"
                  :hideStatistics="true"
                  :styleConfig="{
                    gridLineColor: 'rgba(56, 189, 248, 0.1)',
                    gridLineType: 'dashed',
                    showGridLine: true,
                    axisLineColor: 'rgba(56, 189, 248, 0.5)',
                    axisLabelColor: '#a5f3fc',
                    axisLabelFontSize: 11,
                    seriesColors: ['#4ade80'],
                    backgroundColor: 'transparent',
                    textColor: '#e0f2fe',
                    fontSize: 12,
                    lineWidth: 2,
                    padding: {
                      top: '15%',
                      right: '5%',
                      bottom: '10%',
                      left: '12%'
                    },
                    showLegend: false,
                    tooltipBackgroundColor: 'rgba(15, 23, 42, 0.9)',
                    tooltipTextColor: '#f0f9ff',
                    areaStyle: {
                      opacity: 0.2,
                      colorStops: [
                        { offset: 0, color: 'rgba(74, 222, 128, 0.4)' },
                        { offset: 1, color: 'rgba(74, 222, 128, 0)' }
                      ]
                    }
                  }"
                />
              </div>
            </div>
                
          </div> 
        </div>
        
        
      </div>
    </template>
    <div class="message-river">
          <div class="message-container">
            <div v-for="msg in messages" :key="`${msg.sourceType}-${msg.sourceId}`" class="message-bubble"
              :class="[`type-${msg.type}`]">
              <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
              <span class="message-text">{{ msg.text }}</span>
            </div>
          </div>
        </div>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 20px;
  position: relative;
  min-height: 100vh;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  color: #e2e8f0;
  overflow: hidden;
  --scroll-speed: 20s;
}


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
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

.loading-text {
  margin-top: 15px;
  font-size: 18px;
  color: #e2e8f0;
}


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
  transition: all 0.3s ease;
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


.overview {
  display: grid;
  /* 调整为10个卡片，每行显示5个 */
  grid-template-columns: repeat(10, 1fr);
  gap: 15px;
  margin-bottom: 15px;
  position: relative;
  z-index: 1;
}

@media (max-width: 1600px) {
  .overview {
    grid-template-columns: repeat(4, 1fr);
  }
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

@media (max-width: 480px) {
  .overview {
    grid-template-columns: repeat(1, 1fr);
  }
}

.overview-item {
  background: rgba(30, 41, 59, 0.7);
  padding: 15px;
  border-radius: 0px;
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
  0% {
    transform: translateX(-100%);
  }

  100% {
    transform: translateX(100%);
  }
}

.overview-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 25px rgba(56, 189, 248, 0.25);
}

.number-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

/* 调整 number 元素的样式，移除上边距因为现在由容器控制 */
.number-container .number {
  margin-top: 0;
}

/* 调整 trend 元素的样式，不再是绝对定位 */
.number-container .trend {
  position: static;
  margin-left: 10px;
  white-space: nowrap;
}

.number {
  font-size: 2rem;
  font-weight: bold;
  margin-top: 8px;
  margin-left: 8px;
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


.label {
  font-size: 0.8rem;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: 8px;
  white-space: nowrap;
  color: #94a3b8;
}

.warning-text {
  color: #fb7185;
}

.trend {
  
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


.time {
  font-size: 1.2rem;
  font-weight: bold;
  margin-top: 8px;
  background: linear-gradient(90deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  color: transparent;
  font-family: 'Courier New', monospace;
}


.main-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: calc(100vh - 160px - 60px);
  margin-bottom: 0px;
  position: relative;
  z-index: 1;
}

@media (max-width: 1200px) {
  .main-content {
    grid-template-columns: 1fr;
    gap: 15px;
  }
}

.chart-container {
  flex: 1;
  min-width: 300px; /* 设置最小宽度 */
  border-radius: 0px;
  padding: 15px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.2);
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
  background: rgba(30, 41, 59, 0.7);
  min-height: 240px;
  
  display: flex;
  
  flex-direction: column;
  
}

.heatmap-container {
  border-radius: 15px;
  padding: 0 !important;
  box-shadow: none;
  overflow: hidden;
  box-shadow: none;
  background: transparent;
  border: 1px solid rgba(56, 189, 248, 0.2);
  backdrop-filter: blur(10px);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 15px !important;
  
}


.map-image-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}


.heatmap-container :deep(canvas),
.heatmap-container :deep(img) {
  border-radius: 8px;
  width: calc(100% - 20px);
  height: calc(100% - 20px);
  object-fit: contain;

  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
  mask-image: radial-gradient(ellipse 90% 90% at center,
      black 60%,
      rgba(0, 0, 0, 0.8) 70%,
      rgba(0, 0, 0, 0.6) 80%,
      rgba(0, 0, 0, 0.3) 90%,
      transparent 100%);
}


.heatmap-container :deep(canvas)::after,
.heatmap-container :deep(img)::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 8px;
  box-shadow: inset 0 0 100px 20px rgba(30, 41, 59, 0.7);
  pointer-events: none;
  z-index: 1;
}


.heatmap-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 30px;
  height: 30px;
  border-top: 2px solid rgba(56, 189, 248, 0.5);
  border-left: 2px solid rgba(56, 189, 248, 0.5);
}


.right-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}


.areas-container {
  flex: 1;
  flex-direction: column;
  display: flex;
  background: rgba(30, 41, 59, 0.7);
  border-radius: 0px;
  padding: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.2);
  overflow: hidden;
  backdrop-filter: blur(8px);
  position: relative;
  display: flex;
  flex-direction: column;;
}

/* 确保status-grid可以在容器内滚动 */
.status-grid {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 3px 0;
}


.status-grid {
  width: 100%;
  height: 100%;
  overflow-x: hidden;
  padding: 3px 0;
}


.card-container {
  display: flex;
  flex-direction: column; /* 保持纵向排列 */
  flex: 1;
  width: 100%;
  box-sizing: border-box;
  padding: 0 5px;
  position: relative;
  /* 添加持续滚动动画 */
  animation: continuousScroll 200s linear infinite;
}

.status-grid:after {
  content: '';
  position: absolute;
  bottom: 5px;
  left: 10px;
  right: 10px;
  height: 2px;
  background: rgba(56, 189, 248, 0.1);
  border-radius: 1px;
  z-index: 0;
}

@keyframes slideIndicator {
  0% {
    left: 10px;
  }

  100% {
    left: calc(100% - 30px);
  }
}


.area-card {
  /* 修改为适应垂直排列的样式 */
  flex: 0 0 auto; /* 不再使用固定宽度 */
  width: calc(100% - 10px); /* 使卡片宽度填满容器 */
  background: rgba(30, 41, 59, 0.8) !important;
  border: 2px solid rgba(56, 189, 248, 0.2) !important;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.15);
  min-height: 50px;
  padding: 8px 12px !important;
  display: flex !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: space-between !important;
  margin: 0 auto !important; /* 居中显示 */
  box-sizing: border-box;
  height: 80px; /* 根据内容自适应高度 */
  order: 0;
  
  transform-origin: center;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  position: relative;
  
  overflow: visible;
}

.card-container.moving .area-card {
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
}


.area-header {
  flex: 0 0 60px;
  
  margin-right: 8px;
  overflow: hidden;
  
}

.area-header h4 {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  color: #d1d5db;
}


.area-stats {
  flex: 1;
  min-width: 0;
  
  display: flex;
  flex-direction: column;
}

.stat-item {
  display:flex;
  flex-direction: row;
  width: 100%;
}


.stat-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
}


.stat-top span:first-child {
  font-size: 1.1rem;
  font-weight: bold;
  background: linear-gradient(45deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  color: transparent;
  text-shadow: 0 0 8px rgba(56, 189, 248, 0.4);
}


.update-time {
  font-size: 0.6rem !important;
  color: #94a3b8 !important;
  opacity: 0.8;
  background: none !important;
  text-shadow: none !important;
  text-align: right;
  max-width: 50px;
  
  overflow: hidden;
  text-overflow: ellipsis;
}


.status-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 0.5rem;
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  margin-left: 4px;
  white-space: nowrap;
  vertical-align: middle;
  line-height: 1;
}


.usage-bar {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 2px;
}

.usage-fill {
  height: 100%;
  background: linear-gradient(90deg, #38bdf8, #818cf8);
  border-radius: 3px;
  transition: width 0.5s ease-out;
  box-shadow: 0 0 8px rgba(56, 189, 248, 0.4);
}


.area-card:after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.5), transparent);
  opacity: 0.5;
}


.area-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(59, 130, 246, 0.03);
  opacity: 0;
  transition: opacity 0.5s ease;
  border-radius: inherit;
  z-index: -1;
}

.card-moving::before {
  opacity: 1;
}


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
  0% {
    opacity: 0.7;
  }

  50% {
    opacity: 1;
  }

  100% {
    opacity: 0.7;
  }
}

.stat-item span {
  font-size: 1.5rem;
  font-weight: bold;
  background: linear-gradient(45deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  color: transparent;
  text-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
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


.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.5rem;
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  margin-left: 8px;
}

.status-badge.status-active {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}


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
  0% {
    transform: translateX(100%);
  }

  100% {
    transform: translateX(-100%);
  }
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
}

@keyframes shine {
  0% {
    transform: translateX(-200%) skewX(-15deg);
  }

  100% {
    transform: translateX(200%) skewX(-15deg);
  }
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


.lower-content {
  position: relative;
  display: flex;
  gap: 15px;
  flex: 1;
  min-height: 0;
  margin-top: 10px;
  margin-bottom: 35px;
  z-index: 1;
}

@media (max-width: 1200px) {
  .lower-content {
    flex-direction: column;
  }
}


.right-column {
  display: flex;
  flex-direction: column;
  gap: 15px;
  flex: 0.4;
  min-height: 0;
  
}
.left-column-1 {
  display: flex;
  flex-direction: column;
  flex: 0.4;
  min-height: 0;
  max-width: 300px;
}
.left-column-2 .chart-container {
  height: 50%; /* 设置为父容器的一半高度 */
}

.section-header {
  margin-bottom: 6px;
  flex-shrink: 0;
  display: flex;
  
  align-items: center;
  
  gap: 10px;
  
}

.section-header h2 {
  font-size: 0.95rem;
  margin: 0;
  white-space: nowrap;
  
}

.subtitle {
  font-size: 0.7rem;
  color: #94a3b8;
  position: relative;
  padding-left: 10px;
  
}


.subtitle::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  height: 12px;
  width: 1px;
  background: rgba(56, 189, 248, 0.5);
}

.stat-item {
  display: flex;
  flex-direction: column;
}

.stat-title {
  font-size: 12px;
  color: #94a3b8;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
  margin-top: 2px;
  background: linear-gradient(45deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  color: transparent;
}

.stat-time {
  font-size: 14px;
  font-weight: 500;
  margin-top: 2px;
  color: #94a3b8;
}


.tech-indicator {
  position: absolute;
  right: 0;
  top: 0;
  width: 8px;
  height: 100%;
  background: rgba(239, 68, 68, 0.3);
}

.tech-indicator.active {
  background: rgba(34, 197, 94, 0.3);
  animation: pulse-active 2s infinite;
}

@keyframes pulse-active {
  0% {
    opacity: 0.7;
  }

  50% {
    opacity: 1;
  }

  100% {
    opacity: 0.7;
  }
}


.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100px;
  color: #94a3b8;
  font-style: italic;
}


.nodes-grid::-webkit-scrollbar {
  width: 5px;
}

.nodes-grid::-webkit-scrollbar-track {
  background: rgba(148, 163, 184, 0.1);
  border-radius: 3px;
}

.nodes-grid::-webkit-scrollbar-thumb {
  background: rgba(56, 189, 248, 0.3);
  border-radius: 3px;
}

.nodes-grid::-webkit-scrollbar-thumb:hover {
  background: rgba(56, 189, 248, 0.5);
}

.chart-inner-container {
  width: 100%;
  height: 100%; 
}
/* 确保环境图表组件占满容器 */
.chart-inner-container :deep(.base-chart) {
  width: 100%;
  height: 100%;
  flex: 1;
}
.node-status-container {
  flex: 0.55;
  top: 1px;
  background: rgba(30, 41, 59, 0.7);
  border-radius: 0px;
  padding: 15px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.2);
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.node-content {
  flex: 1;
  overflow: hidden;
  margin-top: 8px;
}

::-webkit-scrollbar {
  display: none !important;
  width: 0 !important;
  height: 0 !important;
}

* {
  scrollbar-width: none !important;
  -ms-overflow-style: none !important;
}

.status-grid::-webkit-scrollbar,
.nodes-grid::-webkit-scrollbar,
.mobile-side-menu::-webkit-scrollbar {
  display: none !important;
  width: 0 !important;
}

.status-grid::-webkit-scrollbar,
.status-grid::-webkit-scrollbar-track,
.status-grid::-webkit-scrollbar-thumb,
.nodes-grid::-webkit-scrollbar,
nodes-grid::-webkit-scrollbar-track,
nodes-grid::-webkit-scrollbar-thumb {
  width: 0 !important;
  height: 0 !important;
  display: none !important;
  background: transparent !important;
}
/* 添加持续滚动的关键帧动画 */
@keyframes continuousScroll {
  0% {
    transform: translateY(0);
  }
  100% {
    transform: translateY(-50%); /* 滚动一半高度，与重复卡片高度相匹配 */
  }
}

/* 鼠标悬停时暂停动画 */
.status-grid:hover .card-container {
  animation-play-state: paused;
}
/* 新增：让热力图绝对定位并拉伸 */
.absolute-heatmap {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: auto; /* 保持可交互性 */
  /* 可选：如果需要透明度可调整 */
  opacity: 1;
}
/* 新增：渐变暗效果 */
.absolute-heatmap::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 1;
  /* 渐变从中心亮到四周更暗，中心区域缩小 */
  background: radial-gradient(
    ellipse at 50% 50%,
    rgba(30,41,59,0) 30%,
    rgba(30,41,59,0.4) 60%,
    rgba(30,41,59,0.85) 100%
  );
}
/* 其它内容提升层级，显示在热力图之上 */
.content-on-heatmap {
  position: relative;
  z-index: 2;
  /* 可选：加点阴影让内容更清晰 */
  box-shadow: 0 2px 20px rgba(0,0,0,0.12);
  background: rgba(30,41,59,0.85); /* 可选：略微加深背景 */
  border-radius: 12px;
}
/* 固定left-column-1在lower-content最左侧 */
.fixed-left {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 300px; /* 可根据实际内容调整宽度 */
  z-index: 2;
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* 固定left-column-2在lower-content最右侧 */
.fixed-right {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 360px; /* 可根据实际内容调整宽度 */
  z-index: 2;
  display: flex;
  flex-direction: column;
  height: 100%;
}
/* 兼容移动端，自动恢复为纵向排列 */
@media (max-width: 1200px) {
  .fixed-left,
  .fixed-right {
    position: static;
    width: 100%;
    height: auto;
  }
  .lower-content {
    height: auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
}
/* 热力图中央顶部倒梯形标题样式 */
.heatmap-title-trapezoid {
  position: absolute;
  top: 0px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  width: 220px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.heatmap-title-trapezoid::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 0;
  /* 正梯形效果 */
  clip-path: polygon(0% 0, 100% 0, 90% 100%, 10% 100%);
  background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
  opacity: 0.92;
  /* 多层光效，蓝色和浅蓝色外发光 */
  box-shadow:
    0 0 16px 4px rgba(56,189,248,0.35),
    0 0 32px 8px rgba(56,189,248,0.18),
    0 4px 18px rgba(30,41,59,0.28);
  border: 1.5px solid rgba(56,189,248,0.25);
}

.heatmap-title-text {
  position: relative;
  z-index: 1;
  font-size: 1.25rem;
  font-weight: bold;
  color: #e0f2fe;
  letter-spacing: 2px;
  text-shadow: 0 2px 8px rgba(56,189,248,0.25);
  font-family: 'Microsoft YaHei', 'Arial', sans-serif;
  user-select: none;
  padding: 0 12px;
}

@media (max-width: 600px) {
  .heatmap-title-trapezoid {
    width: 140px;
    height: 32px;
  }
  .heatmap-title-text {
    font-size: 1rem;
    padding: 0 6px;
  }
}
</style>