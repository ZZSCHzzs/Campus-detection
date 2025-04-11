<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import { areaService, alertService, noticeService, summaryService, historicalService } from '../services/apiService'
import type { AreaItem, HistoricalData,SummaryData } from '../types'

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

const currentTime = ref('')
const areas = ref<AreaItem[]>([])
const chartRef = ref<HTMLElement>()

// 在 script setup 中添加类型定义
type MessageType = 'emergency' | 'warning' | 'info'
type Message = {
  id: number
  text: string
  type: MessageType
  timestamp: string
  sourceType: 'alert' | 'notice' // 添加来源类型
  sourceId: number // 添加源数据ID
}

const messages = ref<Message[]>([
  {
    id: 1,
    text: '🚨 图书馆东区人流量超过预警值',
    type: 'emergency',
    timestamp: new Date().toLocaleTimeString(),
    sourceType: 'alert',
    sourceId: 1
  },
  {
    id: 2,
    text: '⚠️ 食堂即将进入午餐高峰期',
    type: 'warning',
    timestamp: new Date().toLocaleTimeString(),
    sourceType: 'notice',
    sourceId: 2
  },
  {
    id: 3,
    text: 'ℹ️ 教学楼检测设备例行维护中',
    type: 'info',
    timestamp: new Date().toLocaleTimeString(),
    sourceType: 'notice',
    sourceId: 3
  }
])

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

// 更新时间
const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleString()
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
    // 获取统计数据
    const data = await summaryService.getSummary()
    summary.value = data as SummaryData
    updateTime()
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}
// 修改 onMounted 中的区域获取逻辑
onMounted(async () => {
  try {
    // 获取区域数据
    areas.value = await areaService.getAll()

    // 图表初始化及历史数据获取
    const chart = echarts.init(chartRef.value!)
    
    const option = {
      dataset: {
        source: [] as Array<[string, number]>
      },
      title: { text: '区域人流趋势' },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'time' },
      yAxis: { type: 'value' },
      series: [{
        type: 'line',
        encode: {
          x: 'timestamp',
          y: 'detected_count'
        },
        smooth: true
      }]
    }

    // 更新图表数据
    const updateChart = async () => {
      try {
        if (areas.value && areas.value.length > 0) {
          const historicalData = await historicalService.getAreaHistorical(areas.value[0].id)
          option.dataset.source = historicalData.map(d => ([
            d.timestamp,
            d.detected_count
          ]))
          chart.setOption(option)
        }
      } catch (error) {
        console.error('获取历史数据失败:', error)
      }
    }

    // 初始获取数据
    await Promise.all([
      updateStats(),
      updateChart(),
      fetchLatestMessages()
    ])

    // 设置定时更新
    setInterval(updateStats, 3000)
    setInterval(updateChart, 5000)
    setInterval(fetchLatestMessages, 5000)
    setInterval(updateTime, 1000)

    // 监听全屏变化
    document.addEventListener('fullscreenchange', () => {
      isFullscreen.value = !!document.fullscreenElement
    })

  } catch (error) {
    console.error('数据加载失败:', error)
  }
})

const formatTime = (timestamp: string) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}
</script>

<template>
  <div class="dashboard">
    <!-- 添加全屏切换按钮 -->
    <div class="fullscreen-toggle" @click="toggleFullScreen">
      <i class="fullscreen-icon" :class="{ 'is-active': isFullscreen }"></i>
    </div>
    
    <!-- 添加顶部数据总览 -->
    <div class="overview">
      <div class="overview-item">
        <h3>今日总客流</h3>
        <div class="number">{{ summary.people_count }}</div>
      </div>
      <div class="overview-item">
        <h3>在线节点数</h3>
        <div class="number">{{ summary.nodes_count }}</div>
      </div>
      <div class="overview-item">
        <h3>告警事件数</h3>
        <div class="number warning">{{ summary.alerts_count }}</div>
      </div>
      <div class="overview-item">
        <h3>通知事件数</h3>
        <div class="number warning">{{ summary.notice_count }}</div>
      </div>
      <div class="overview-item">
        <h3>当前时间</h3>
        <div class="time">{{ currentTime }}</div>
      </div>
    </div>

    <!-- 主要图表区域使用网格布局 -->
    <div class="main-content">
      <div ref="chartRef" class="chart-container"></div>
      
      <div class="status-grid">
        <el-card v-for="area in areas" :key="area.id" class="area-card">
          <div class="area-header">
            <h4>{{ area.name }}</h4>
            <span class="status-badge" :class="{'status-active': area.status}">
              {{ area.status ? '正常' : '告警' }}
            </span>
          </div>
          <div class="area-stats">
            <div class="stat-item">
              <span>当前人数</span>
              <span>{{ area.detected_count || 0 }}</span>
            </div>
            <div class="stat-item">
              <span>容量上限</span>
              <span>{{ area.capacity }}</span>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 在 template 中更新消息河流组件 -->
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
  </div>
</template>

<style scoped>
.dashboard {
  padding: 20px;
  position: relative;
  min-height: 100vh;
  background: #1a1a1a;
  color: #fff;
  transition: all 0.3s ease-in-out;
}

/* 添加全屏样式 */
.dashboard:fullscreen {
  padding: 40px;
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
.dashboard:-webkit-full-screen {
  padding: 40px;
  width: 100vw;
  height: 100vh;
  overflow: auto;
}

.dashboard:-moz-full-screen {
  padding: 40px;
  width: 100vw;
  height: 100vh;
  overflow: auto;
}

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
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  z-index: 1000;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.fullscreen-toggle:hover {
  background: rgba(255, 255, 255, 0.2);
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
  border: 2px solid #88ccff;
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

/* 修改 overview 的样式 */
.overview {
  display: grid;
  grid-template-columns: repeat(5, 1fr); /* 修改为5列 */
  gap: 15px; /* 适当减小间距 */
  margin-bottom: 30px;
}

/* 调整卡片内部样式使其更紧凑 */
.overview-item {
  background: rgba(255, 255, 255, 0.1);
  padding: 15px; /* 减小内边距 */
  border-radius: 10px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: transform 0.3s;
}

/* 调整数字大小 */
.number {
  font-size: 2rem; /* 稍微减小字号 */
  font-weight: bold;
  margin-top: 8px;
  background: linear-gradient(45deg, #88ccff, #00ff88);
  -webkit-background-clip: text;
  color: transparent;
}

/* 调整标题大小 */
.overview-item h3 {
  margin: 0;
  font-size: 0.9rem; /* 稍微减小字号 */
  color: #88ccff;
}

/* 时间显示的特殊样式 */
.time {
  font-size: 1.5rem;
  font-weight: bold;
  margin-top: 8px;
  color: #88ccff;
}

.main-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}

.chart-container {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 20px;
  height: 500px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 20px;
  max-height: 500px;
  overflow-y: auto;
}

.area-card {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  backdrop-filter: blur(10px);
}

.area-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.8rem;
  background: rgba(255, 0, 0, 0.2);
  color: #ff5555;
}

.status-badge.status-active {
  background: rgba(0, 255, 0, 0.2);
  color: #55ff55;
}

.area-stats {
  margin-top: 15px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

/* 更新消息河流样式 */
.message-river {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 60px;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
  z-index: 1000;
}

.message-container {
  display: flex;
  gap: 20px;
  padding: 10px;
  animation: scrollMessages 20s linear infinite;
  white-space: nowrap;
}

.message-bubble {
  padding: 8px 15px;
  border-radius: 20px;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(5px);
  flex-shrink: 0;
  transition: transform 0.3s;
}

.message-bubble:hover {
  transform: translateY(-2px);
}

@keyframes scrollMessages {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(-100%);
  }
}

/* 当鼠标悬停时暂停动画 */
.message-container:hover {
  animation-play-state: paused;
}

/* 更新消息类型样式 */
.type-emergency {
  border-left: 4px solid #ff4444;
}

.type-warning {
  border-left: 4px solid #ffaa00;
}

.type-info {
  border-left: 4px solid #00aaff;
}

/* 更新消息样式 */
.message-time {
  color: #888;
  font-size: 12px;
  white-space: nowrap;
}

.message-text {
  color: #fff;
  white-space: nowrap;
}

/* 确保全屏时消息河流位置正确 */
.dashboard:fullscreen .message-river {
  width: 100vw;
  left: 0;
  bottom: 0;
}

.timestamp {
  display: block;
  font-size: 0.8rem;
  color: #aaa;
  margin-top: 5px;
}

::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}
</style>