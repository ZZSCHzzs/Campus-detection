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
type MessageType = 'emergency' | 'warning' | 'info' | 'null'
type Message = {
  id: number
  text: string
  type: MessageType
  timestamp: string
  sourceType: 'alert' | 'notice' | 'null'// 添加来源类型
  sourceId: number // 添加源数据ID
}

const messages = ref<Message[]>([
  {
    id: null,
    text: 'null',
    type: 'null',
    timestamp: new Date().toLocaleTimeString(),
    sourceType: 'null',
    sourceId: null
  },
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
// 添加当前显示的区域索引
const currentAreaIndex = ref(0)

// 修改 onMounted 中的图表配置和更新逻辑
onMounted(async () => {
  try {
    // 获取区域数据
    areas.value = await areaService.getAll()

    // 图表初始化
    const chart = echarts.init(chartRef.value!)
    
    const option = {
      dataset: {
        source: [] as Array<[string, number]>
      },
      title: {
        text: '区域实时人流',
        subtext: '', 
        textStyle: {
          color: '#334155',
          fontSize: 16,
          fontWeight: 600
        },
        subtextStyle: {
          color: '#64748b',
          fontSize: 14
        }
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: 'rgba(59, 130, 246, 0.2)',
        textStyle: {
          color: '#334155'
        },
        axisPointer: {
          type: 'line',
          lineStyle: {
            color: '#3b82f6'
          }
        }
      },
      xAxis: {
        type: 'time',
        name: '时间',
        nameTextStyle: {
          color: '#88ccff'
        },
        axisLabel: {
          color: '#64748b',
          formatter: (value: string) => formatTime(value)
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: 'rgba(59, 130, 246, 0.1)'
          }
        },
        // 添加自适应设置
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
          color: '#64748b'
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: 'rgba(59, 130, 246, 0.1)'
          }
        },
        // 添加自适应设置
        scale: true,
        min: (value: { min: number }) => Math.floor(value.min * 0.8),  // 下限留20%空间
        max: (value: { max: number }) => Math.ceil(value.max * 1.2)    // 上限留20%空间
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

    // 更新图表数据
    const updateChart = async () => {
      try {
        if (areas.value && areas.value.length > 0) {
          // 更新当前区域索引
          currentAreaIndex.value = (currentAreaIndex.value + 1) % areas.value.length
          const currentArea = areas.value[currentAreaIndex.value]

          // 获取当前区域的历史数据
          const historicalData = await historicalService.getAreaHistorical(currentArea.id)
          
          // 更新图表标题
          option.title.subtext = currentArea.name
          
          // 更新数据
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
    setInterval(updateChart, 10000) // 每10秒切换一次区域
    setInterval(fetchLatestMessages, 30000)
    setInterval(updateTime, 1000)

    // 监听窗口大小变化
    window.addEventListener('resize', () => {
      chart.resize()
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
      
      <div class="areas-container">
        <div class="status-grid">
          <el-card v-for="area in areas" :key="area.id" class="area-card">
            <div class="area-header">
              <div class="header-left">
                <h4>{{ area.name }}<span class="status-badge" :class="{'status-active': area.status}">{{ area.status ? '正常' : '异常' }}</span></h4>
              </div>
            </div>
            <div class="area-stats">
              <div class="stat-item">
                <span>{{ area.detected_count || 0 }}/{{ area.capacity }}</span>
              </div>
            </div>
          </el-card>
        </div>
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
  background: linear-gradient(135deg, #f5f7fa 0%, #e4ebf5 100%);
  color: #334155;
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
  background: rgba(255, 255, 255, 0.95);
  padding: 15px; /* 减小内边距 */
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.1);
  transition: all 0.3s;
}

.overview-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 20px rgba(59, 130, 246, 0.15);
}

/* 调整数字大小 */
.number {
  font-size: 2rem; /* 稍微减小字号 */
  font-weight: bold;
  margin-top: 8px;
  color: #3b82f6;
}

/* 调整标题大小 */
.overview-item h3 {
  margin: 0;
  font-size: 0.9rem; /* 稍微减小字号 */
  color: #64748b;
}

/* 时间显示的特殊样式 */
.time {
  font-size: 1.5rem;
  font-weight: bold;
  margin-top: 8px;
  color: #3b82f6;
}

.main-content {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 25px;
  height: calc(100vh - 220px); /* 减去顶部内容、间距和底部消息河流的高度 */
  padding-bottom: 60px;
}

.chart-container {
  background: #ffffff;
  border-radius: 15px;
  padding: 20px;
  height: 100%;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.1);
}

/* 新增区域卡片容器样式 */
.areas-container {
  background: #ffffff;
  border-radius: 15px;
  padding: 15px;
  height: 100%;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.1);
  overflow: hidden; /* 确保内容不会溢出 */
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); /* 自适应列宽 */
  gap: 12px;
  height: 100%;
  overflow-y: auto;
  padding: 5px;
}

/* 自定义滚动条样式 */
.status-grid::-webkit-scrollbar {
  width: 6px;
}

.status-grid::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.status-grid::-webkit-scrollbar-thumb {
  background: #94a3b8;
  border-radius: 3px;
}

.status-grid::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}

.area-card {
  background: #ffffff !important;
  border: 1px solid rgba(59, 130, 246, 0.1) !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  min-height: 100px; /* 进一步减小卡片高度 */
  padding: 12px !important;
  display: flex;
  flex-direction: column;
}

.area-header h4 {
  font-size: 1.2rem;
  margin: 0;
  color: #334155;
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.area-stats {
  margin-top: 15px;
  margin-bottom: 10px;
  flex-grow: 1;
  display: flex;
  align-items: center;
}

.stat-item {
  margin-bottom: 10px;  /* 为最后一个统计项增加底部间距 */
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px;
  background: #f8fafc;
  border: 1px solid rgba(59, 130, 246, 0.1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border-radius: 10px;
  transition: all 0.3s ease;
  width: 100%;
}

.stat-item:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-2px);
}

.stat-item span {
  color: #3b82f6;
  font-size: 1.5rem; /* 调整字体大小 */
  font-weight: bold;
  background: linear-gradient(45deg, #88ccff, #00ff88);
  -webkit-background-clip: text;
  color: transparent;
}

/* 更新消息河流样式 */
.message-river {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 60px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
  border-top: 1px solid rgba(59, 130, 246, 0.2);
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

@keyframes scrollMessages {
  0% {
    transform: translateX(100%);
  }
  100% {
    transform: translateX(-100%);
  }
}

/* 当鼠标悬停时暂停动画 */
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
  background: #f8fafc;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(59, 130, 246, 0.1);
  flex-shrink: 0;
}

.type-emergency {
  border-left: 4px solid #ef4444;
}

.type-warning {
  border-left: 4px solid #f59e0b;
}

.type-info {
  border-left: 4px solid #3b82f6;
}

.message-time {
  color: #64748b;
  font-size: 12px;
}

.message-text {
  color: #334155;
  font-weight: 500;
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