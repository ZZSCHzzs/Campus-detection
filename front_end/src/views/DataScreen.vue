<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import axios from '../axios'
import type { AreaItem, HistoricalData } from '../types'

// 添加新的响应式数据
const totalFlow = ref(0)
const onlineNodes = ref(0)
const warningCount = ref(0)
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
}

// 模拟消息数据
const messages = ref<Message[]>([
  {
    id: 1,
    text: '🚨 图书馆东区人流量超过预警值',
    type: 'emergency',
    timestamp: new Date().toLocaleTimeString()
  },
  {
    id: 2,
    text: '⚠️ 食堂即将进入午餐高峰期',
    type: 'warning',
    timestamp: new Date().toLocaleTimeString()
  },
  {
    id: 3,
    text: 'ℹ️ 教学楼检测设备例行维护中',
    type: 'info',
    timestamp: new Date().toLocaleTimeString()
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

// 更新消息处理逻辑
const updateMessages = () => {
  const types: MessageType[] = ['emergency', 'warning', 'info']
  const newMessages = [
    '🚨 实验楼B区人流量已达上限',
    '⚠️ 体育馆东门临时关闭',
    'ℹ️ 图书馆阅览室余座更新',
    '🚨 教学楼电梯检修通知',
    '⚠️ 食堂就餐高峰预警'
  ]
  
  const newMessage: Message = {
    id: Date.now(),
    text: newMessages[Math.floor(Math.random() * newMessages.length)],
    type: types[Math.floor(Math.random() * types.length)],
    timestamp: new Date().toLocaleTimeString()
  }
  
  // 保持最多8条消息
  if (messages.value.length >= 8) {
    messages.value.shift()
  }
  messages.value.push(newMessage)
}

// 初始化时获取区域数据
onMounted(async () => {
  // 获取区域基本信息
  const { data: areaData } = await axios.get('/api/areas')
  areas.value = areaData.data.map((a: AreaItem) => ({
    ...a,
    max_capacity: 50 // 根据实际业务需求设置或从API获取
  }))

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

  // 定时更新图表数据
  setInterval(async () => {
    const { data } = await axios.get<HistoricalData[]>('/api/historical')
    // 修改为直接使用 data 数组，因为 HistoricalData[] 上不存在属性 data
    option.dataset.source = data.map(d => ([
      d.timestamp,
      d.detected_count
    ]))
    chart.setOption(option)
  }, 5000)

  // 每5秒更新一次消息
  setInterval(updateMessages, 5000)

  // 添加数字滚动效果
  setInterval(() => {
    totalFlow.value = Math.floor(Math.random() * 10000)
    onlineNodes.value = Math.floor(Math.random() * 50)
    warningCount.value = Math.floor(Math.random() * 20)
    updateTime()
  }, 3000)

  // 监听全屏变化
  document.addEventListener('fullscreenchange', () => {
    isFullscreen.value = !!document.fullscreenElement
  })
})
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
        <div class="number">{{ totalFlow }}</div>
      </div>
      <div class="overview-item">
        <h3>在线节点数</h3>
        <div class="number">{{ onlineNodes }}</div>
      </div>
      <div class="overview-item">
        <h3>告警事件数</h3>
        <div class="number warning">{{ warningCount }}</div>
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
            <span class="status-badge" :class="{'status-active': Math.random() > 0.5}">
              {{ Math.random() > 0.5 ? '正常' : '告警' }}
            </span>
          </div>
          <div class="area-stats">
            <div class="stat-item">
              <span>当前人数</span>
              <span>{{ Math.floor(Math.random() * 100) }}</span>
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
          :key="msg.id"
          class="message-bubble"
          :class="[`type-${msg.type}`]"
        >
          <span class="message-time">{{ msg.timestamp }}</span>
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

.overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.overview-item {
  background: rgba(255, 255, 255, 0.1);
  padding: 20px;
  border-radius: 10px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: transform 0.3s;
}

.overview-item:hover {
  transform: translateY(-5px);
}

.overview-item h3 {
  margin: 0;
  font-size: 1rem;
  color: #88ccff;
}

.number {
  font-size: 2.5rem;
  font-weight: bold;
  margin-top: 10px;
  background: linear-gradient(45deg, #88ccff, #00ff88);
  -webkit-background-clip: text;
  color: transparent;
}

.number.warning {
  background: linear-gradient(45deg, #ff8888, #ffaa00);
  -webkit-background-clip: text;
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