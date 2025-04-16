<script setup lang="ts">
import { ref, onMounted, reactive, watch} from 'vue'
import * as echarts from 'echarts'
import { areaService, alertService, noticeService, summaryService, historicalService, nodeService } from '../services/apiService'
import type { AreaItem, HistoricalData, SummaryData, HardwareNode } from '../types'
import HeatMap from '../components/HeatMap.vue'

// 区域趋势分析模拟数据
const historicalData = [
  { timestamp: '2025-04-16 08:00:00', detected_count: 23 },
  { timestamp: '2025-04-16 08:30:00', detected_count: 45 },
  { timestamp: '2025-04-16 09:00:00', detected_count: 78 },
  { timestamp: '2025-04-16 09:30:00', detected_count: 102 },
  { timestamp: '2025-04-16 10:00:00', detected_count: 95 },
  { timestamp: '2025-04-16 10:30:00', detected_count: 88 },
  { timestamp: '2025-04-16 11:00:00', detected_count: 76 },
  { timestamp: '2025-04-16 11:30:00', detected_count: 92 },
  { timestamp: '2025-04-16 12:00:00', detected_count: 134 },
  { timestamp: '2025-04-16 12:30:00', detected_count: 156 },
  { timestamp: '2025-04-16 13:00:00', detected_count: 121 },
  { timestamp: '2025-04-16 13:30:00', detected_count: 89 },
  { timestamp: '2025-04-16 14:00:00', detected_count: 72 },
  { timestamp: '2025-04-16 14:30:00', detected_count: 68 },
  { timestamp: '2025-04-16 15:00:00', detected_count: 82 },
  { timestamp: '2025-04-16 15:30:00', detected_count: 96 },
  { timestamp: '2025-04-16 16:00:00', detected_count: 115 },
  { timestamp: '2025-04-16 16:30:00', detected_count: 142 },
  { timestamp: '2025-04-16 17:00:00', detected_count: 168 },
  { timestamp: '2025-04-16 17:30:00', detected_count: 153 },
  { timestamp: '2025-04-16 18:00:00', detected_count: 112 },
  { timestamp: '2025-04-16 18:30:00', detected_count: 87 },
  { timestamp: '2025-04-16 19:00:00', detected_count: 64 },
  { timestamp: '2025-04-16 19:30:00', detected_count: 38 }
]
// 添加节点状态相关的状态
const currentAreaNodes = ref<HardwareNode[]>([])
const nodeFetchTimer = ref<number | null>(null)
// 更新获取当前区域节点数据的方法
const fetchCurrentAreaNodes = async () => {
  if (!areas.value || areas.value.length === 0) return
  
  const currentArea = areas.value[currentAreaIndex.value]
  try {
    // 获取当前区域的节点数据
    const nodes = await nodeService.getDatabyAreaId(currentArea.id)
    currentAreaNodes.value = nodes
  } catch (error) {
    console.error('获取节点数据失败:', error)
    currentAreaNodes.value = []
  }
}
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
  // 使用容器中的子元素作为图表渲染区域
  const chartContainer = chartDom.querySelector('.chart-inner-container')
  if (!chartContainer) return null
  
  const chart = echarts.init(chartContainer as HTMLElement)
  
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

    // 使用模拟的历史数据，无需API调用
    // 根据当前区域ID来简单修改数据，使得不同区域有不同的曲线
    const modifier = (currentArea.id % 5) * 0.2 + 0.8 // 0.8到1.8之间的修改系数
    
    const customHistoricalData = historicalData.map(d => ({
      timestamp: d.timestamp,
      detected_count: Math.round(d.detected_count * modifier)
    }))
    
    // 更新图表数据
    areaChart.setOption({
      title: {
        subtext: currentArea.name
      },
      dataset: {
        source: customHistoricalData.map(d => ([
          d.timestamp,
          d.detected_count
        ]))
      }
    })
    
    // 获取节点后立即更新当前区域的节点数据
    fetchCurrentAreaNodes()
  } catch (error) {
    console.error('获取历史数据失败:', error)
  }
}
// 用于卡片移动动画
const cardAnimationState = reactive({
  isMoving: false,
  currentPosition: 0,
  currentIndex: 0,
  cardWidths: [] as number[], // 存储每个卡片的实际宽度
  animationTimer: null as any
})
// 计算并保存所有卡片宽度
const calculateCardWidths = () => {
  const cards = document.querySelectorAll('.area-card')
  
  // 重置宽度数组
  cardAnimationState.cardWidths = []
  
  // 计算每个卡片的宽度（包括外边距/间隔）
  cards.forEach((card, index) => {
    const cardElement = card as HTMLElement
    const cardWidth = cardElement.offsetWidth + 12 // 12px是卡片间隔
    cardAnimationState.cardWidths.push(cardWidth)
  })
  
  console.log('卡片宽度数组:', cardAnimationState.cardWidths)
}
// 控制卡片循环移动
const animateCards = () => {
  const container = document.querySelector('.card-container') as HTMLElement
  if (!container || !areas.value.length) return
  
  const cards = document.querySelectorAll('.area-card')
  const uniqueAreasCount = areas.value.length
  if (cards.length <= 0) return
  
  // 开始移动动画
  cardAnimationState.isMoving = true
  
  // 获取当前卡片的宽度
  const cardWidth = cardAnimationState.cardWidths[cardAnimationState.currentIndex % uniqueAreasCount] || 192
  
  // 应用移动效果
  cardAnimationState.currentPosition -= cardWidth
  container.style.transform = `translateX(${cardAnimationState.currentPosition}px)`
  
  // 更新索引，指向下一个卡片
  cardAnimationState.currentIndex = (cardAnimationState.currentIndex + 1) % cards.length
  
  // 当滚动到第一组的尾部重置位置（实现无缝效果）
  if (cardAnimationState.currentIndex >= uniqueAreasCount) {
    // 重置位置
    setTimeout(() => {
      container.style.transition = 'none'
      cardAnimationState.currentPosition = 0
      cardAnimationState.currentIndex = 0
      container.style.transform = `translateX(0px)`
      
      // 恢复过渡效果
      setTimeout(() => {
        container.style.transition = 'transform 0.5s ease-in-out'
        cardAnimationState.isMoving = false
      }, 50)
    }, 500)
  } else {
    // 移动后停顿
    setTimeout(() => {
      cardAnimationState.isMoving = false
    }, 500)
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
      fetchLatestMessages(),
      fetchCurrentAreaNodes() // 添加节点数据获取
    ])
    // 添加节点状态定时更新
    nodeFetchTimer.value = window.setInterval(fetchCurrentAreaNodes, 5000)

    setTimeout(calculateCardWidths, 500) // 等待卡片完全渲染
    cardAnimationState.animationTimer = setInterval(() => {
      if (!cardAnimationState.isMoving && areas.value.length > 0) {
        animateCards()
      }
    }, 2000) // 每3.5秒移动一次(包含0.5秒的移动时间)
    
    // 监听窗口大小变化，重新计算卡片宽度
    const handleResize = () => {
      cardAnimationState.currentPosition = 0
      cardAnimationState.currentIndex = 0
      const container = document.querySelector('.card-container') as HTMLElement
      if (container) {
        container.style.transition = 'none'
        container.style.transform = `translateX(0px)`
        setTimeout(() => {
          container.style.transition = 'transform 0.5s ease-in-out'
          calculateCardWidths() // 重新计算卡片宽度
        }, 50)
      }
    }
    
    window.addEventListener('resize', handleResize)
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
      clearInterval(cardAnimationState.animationTimer)
      if (nodeFetchTimer.value) clearInterval(nodeFetchTimer.value)
      window.removeEventListener('resize', handleResize)
    }
  } catch (error) {
    console.error('数据加载失败:', error)
    pageState.error = error instanceof Error ? error.message : '未知错误'
    pageState.loading = false
  }
})


// 添加地图图片路径
const mapImage = new URL('../assets/map_zx_F1.png', import.meta.url).href
// 添加到script setup部分
const statusGridRef = ref(null)
// 将占位函数替换为正确的实现
function formatTime(value: string) {
  if (!value) return '--:--'
  
  try {
    const date = new Date(value)
    
    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      return value // 如果无法解析，则返回原始字符串
    }
    
    // 如果是今天的日期，只显示时间
    const today = new Date()
    if (date.toDateString() === today.toDateString()) {
      return date.toLocaleTimeString('zh-CN', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
      })
    } else {
      // 否则显示日期+时间(简短格式)
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      }).replace(/\//g, '-')
    }
  } catch (error) {
    console.error('日期格式化错误:', error)
    return value // 出错时返回原始值
  }
}

// 监听当前区域索引的变化，更新节点数据
watch(() => currentAreaIndex.value, () => {
  fetchCurrentAreaNodes()
})

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
        </div>
      </div>

      <!-- 主要图表区域 -->
      <div class="main-content">
        <!-- 区域状态容器置于顶部 -->
        <div class="areas-container">
          <div class="tech-corners"></div>
          <div class="section-header">
            <h2>区域状态监控</h2>   
            <div class="subtitle">Area Status Monitor</div>
          </div>
          <div class="status-grid" ref="statusGridRef">
            <div class="card-container":class="{'moving': cardAnimationState.isMoving}">
              <el-card v-for="(area, index) in areas" :key="area.id" 
                      class="area-card">
                <!-- 左侧区域名称与状态 -->
                <div class="area-header">
                  <h4>
                    {{ area.name.length > 6 ? area.name.substring(0, 6) + '...' : area.name }}
                    <span class="status-badge" :class="{'status-active': area.status}">
                      {{ area.status ? '正常' : '异常' }}
                    </span>
                  </h4>
                </div>
                
                <!-- 右侧区域统计信息 -->
                <div class="area-stats">
                  <div class="stat-item">
                    <div class="stat-top">
                      <span>{{ area.detected_count || 0 }}/{{ area.capacity }}</span>
                      <span v-if="area.updated_at" class="update-time">{{ formatTime(area.updated_at) }}</span>
                    </div>
                    <div class="usage-bar">
                      <div class="usage-fill" 
                          :style="{width: `${Math.min(100, area.detected_count ? (area.detected_count / area.capacity) * 100 : 0)}%`}"
                          :class="{'high-usage': area.detected_count && area.capacity && (area.detected_count / area.capacity) > 0.8}"></div>
                    </div>
                  </div>
                </div>
              </el-card>
              <el-card v-for="(area, index) in areas" :key="area.id" 
                      class="area-card">
                <!-- 左侧区域名称与状态 -->
                <div class="area-header">
                  <h4>
                    {{ area.name.length > 6 ? area.name.substring(0, 6) + '...' : area.name }}
                    <span class="status-badge" :class="{'status-active': area.status}">
                      {{ area.status ? '正常' : '异常' }}
                    </span>
                  </h4>
                </div>
                
                <!-- 右侧区域统计信息 -->
                <div class="area-stats">
                  <div class="stat-item">
                    <div class="stat-top">
                      <span>{{ area.detected_count || 0 }}/{{ area.capacity }}</span>
                      <span v-if="area.updated_at" class="update-time">{{ formatTime(area.updated_at) }}</span>
                    </div>
                    <div class="usage-bar">
                      <div class="usage-fill" 
                          :style="{width: `${Math.min(100, area.detected_count ? (area.detected_count / area.capacity) * 100 : 0)}%`}"
                          :class="{'high-usage': area.detected_count && area.capacity && (area.detected_count / area.capacity) > 0.8}"></div>
                    </div>
                  </div>
                </div>
              </el-card>
            </div>
          </div>
        </div>
        
        <!-- 下部内容区域样式 -->
        <div class="lower-content">
          <!-- 热力图容器位于左侧 -->
          <HeatMap :areas="areas" :mapImage="mapImage" class="heatmap-container">
            <template #default="{ mapElement }">
              <div class="map-image-wrapper">
                {{ mapElement }}
              </div>
            </template>
          </HeatMap>

          <!-- 新增右侧列容器，用于垂直排列图表和节点状态 -->
          <div class="right-column">
            <!-- 图表容器位于右侧上方 -->
            <div ref="chartRef" class="chart-container">
              <div class="tech-corners"></div>
              <div class="section-header">
                <h2>区域趋势分析</h2>
                <div class="subtitle">Area Trend Analysis</div>
              </div>
              <div class="chart-inner-container"></div>
            </div>
            
            <!-- 节点状态容器位于右侧下方 -->
            <div class="node-status-container">
              <div class="tech-corners"></div>
              <div class="section-header">
                <h2>硬件节点状态</h2>
                <div class="subtitle">Hardware Node Status</div>
              </div>
              <div class="nodes-grid" v-if="currentAreaNodes.length > 0">
                <div v-for="node in currentAreaNodes" :key="node.id" class="node-card">
                  <div class="node-header">
                    <span class="node-name">{{ node.name }}</span>
                    <span :class="['status-badge', node.status ? 'status-active' : '']">
                      {{ node.status ? '在线' : '离线' }}
                    </span>
                  </div>
                  <div class="node-stats">
                    <div class="stat-item">
                      <span class="stat-title">检测人数</span>
                      <span class="stat-value">{{ node.detected_count }}</span>
                    </div>
                    <div class="stat-item">
                      <span class="stat-title">更新时间</span>
                      <span class="stat-time">{{ formatTime(node.updated_at) }}</span>
                    </div>
                  </div>
                  <div class="tech-indicator" :class="{ 'active': node.status }"></div>
                </div>
              </div>
              <div class="empty-state" v-else>
                <p>当前区域没有活跃的硬件节点</p>
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
  display: flex;
  flex-direction: column;
  gap: 20px;
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
  flex: 1; /* 占据右侧空间的60% */
  border-radius: 15px;
  padding: 15px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.2);
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
  background: rgba(30, 41, 59, 0.7);
  min-height: 240px; /* 确保有足够高度显示图表 */
}

.heatmap-container {
  flex: 1.2; /* 热力图占比略大 */
  border-radius: 15px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(56, 189, 248, 0.2);
  backdrop-filter: blur(10px);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 15px !important; /* 修改内边距 */
}

/* 创建渐变遮罩容器 */
.map-image-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 图片样式与边缘模糊效果 */
.heatmap-container :deep(canvas),
.heatmap-container :deep(img) {
  border-radius: 8px;
  width: calc(100% - 20px);
  height: calc(100% - 20px);
  object-fit: contain;

  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
  mask-image: radial-gradient(
    ellipse 90% 90% at center,
    black 60%,
    rgba(0, 0, 0, 0.8) 70%,
    rgba(0, 0, 0, 0.6) 80%,
    rgba(0, 0, 0, 0.3) 90%,
    transparent 100%
  );
  -webkit-mask-image: radial-gradient(
    ellipse 90% 90% at center,
    black 60%,
    rgba(0, 0, 0, 0.8) 70%,
    rgba(0, 0, 0, 0.6) 80%,
    rgba(0, 0, 0, 0.3) 90%,
    transparent 100%
  );
}

/* 可选：添加发光效果增强过渡感 */
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

/* 可选：添加科技感装饰 */
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

/* 右侧容器样式 */
.right-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 区域状态容器样式优化 */
.areas-container {
  flex: 0.35; 
  background: rgba(30, 41, 59, 0.7);
  border-radius: 12px;
  padding: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.2);
  overflow: hidden; /* 隐藏溢出内容 */
  backdrop-filter: blur(8px);
  position: relative;
  min-height: 110px; /* 减小高度 */
  max-height: 130px; /* 减小最大高度 */
  display: flex;
  flex-direction: column;
}

/* 修改状态网格样式，移除原有的动画 */
.status-grid {
  width: 100%;
  height: 100%;
  overflow-x: hidden;
  padding: 3px 0;
}

/* 添加卡片容器样式 */
.card-container {
  display: flex;
  gap: 12px; /* 增加间距使移动更明显 */
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  padding: 0 5px; /* 减少内边距 */
  transition: transform 0.5s ease-in-out; /* 整体容器的移动动画 */
  min-width: max-content; /* 确保所有卡片都能显示 */
  position: relative; /* 为绝对定位提供参考 */
}

/* 添加滚动轨迹 */
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
  0% { left: 10px; }
  100% { left: calc(100% - 30px); }
}

/* 区域卡片样式 - 修复溢出问题并美化 */
.area-card {
  flex: 0 0 180px;
  background: rgba(30, 41, 59, 0.8) !important;
  border: 2px solid rgba(56, 189, 248, 0.2) !important;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.15);
  min-height: 50px;
  padding: 8px 12px !important;
  display: flex !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: space-between !important;
  margin: 0 !important;
  box-sizing: border-box;
  height: calc(100% - 2px);
  order: 0; /* 默认顺序属性 */
  transform-origin: center;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  position: relative;
  /* 修复冲突的overflow属性 */
  overflow: visible;
}

.card-container.moving .area-card {
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
}

/* 修复区域标题溢出问题 */
.area-header {
  flex: 0 0 60px; /* 固定宽度 */
  margin-right: 8px;
  overflow: hidden; /* 确保内容不会溢出 */
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

/* 优化区域统计信息布局 */
.area-stats {
  flex: 1;
  min-width: 0; /* 防止弹性项目溢出 */
  display: flex;
  flex-direction: column;
}

.stat-item {
  width: 100%;
}

/* 优化统计信息顶部布局 */
.stat-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
}

/* 数值比例显示 */
.stat-top span:first-child {
  font-size: 1.1rem;
  font-weight: bold;
  background: linear-gradient(45deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  color: transparent;
  text-shadow: 0 0 8px rgba(56, 189, 248, 0.4);
}

/* 更新时间显示 */
.update-time {
  font-size: 0.6rem !important;
  color: #94a3b8 !important;
  opacity: 0.8;
  background: none !important;
  text-shadow: none !important;
  text-align: right;
  max-width: 50px; /* 限制宽度 */
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 优化状态徽章样式 */
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

/* 优化使用率进度条 */
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
/* 添加科技感光效 */
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

/* 添加卡片内容的过渡效果 */
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
  font-size: 0.5rem;
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

/* 下部内容区域样式 */
.lower-content {
  display: flex;
  gap: 15px;
  flex: 1;
  min-height: 0; /* 允许内容压缩 */
  margin-top: 10px;
}

@media (max-width: 1200px) {
  .lower-content {
    flex-direction: column;
  }
}
/* 新增右侧列容器样式 */
.right-column {
  display: flex;
  flex-direction: column;
  gap: 15px;
  flex: 0.9;
  min-height: 0; /* 允许内容压缩 */
}
.heatmap-container {
  flex: 1.1; /* 热力图占比略大 */
  border-radius: 15px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(56, 189, 248, 0.2);
  backdrop-filter: blur(10px);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 15px !important; /* 修改内边距 */
}

.section-header {
  margin-bottom: 6px;
  flex-shrink: 0;
  display: flex; /* 使用flex布局让标题和副标题在同一行 */
  align-items: center; /* 垂直居中对齐 */
  gap: 10px; /* 标题与副标题间距 */
}

.section-header h2 {
  font-size: 0.95rem;
  margin: 0;
  white-space: nowrap; /* 防止标题换行 */
}

.subtitle {
  font-size: 0.7rem;
  color: #94a3b8;
  position: relative;
  padding-left: 10px; /* 为分隔线留出空间 */
}

/* 添加垂直分隔线 */
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
.node-status-container {
  flex: 0.8; /* 占据右侧空间的40% */
  background: rgba(30, 41, 59, 0.7);
  border-radius: 15px;
  padding: 15px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.2);
  backdrop-filter: blur(10px);
  position: relative;
  overflow: hidden;
  margin-top: 0; /* 移除上边距，因为已经在容器中设置了间距 */
}
/* 节点卡片网格布局 */
.nodes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
  margin-top: 10px;
  max-height: 160px; /* 减小最大高度 */
  overflow-y: auto;
}

/* 节点卡片样式 */
.node-card {
  background: rgba(15, 23, 42, 0.6);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid rgba(56, 189, 248, 0.15);
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}

.node-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
  border-color: rgba(56, 189, 248, 0.3);
}

/* 节点卡片头部样式 */
.node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.node-name {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
}

/* 节点统计信息样式 */
.node-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
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

/* 节点状态指示器 */
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
  0% { opacity: 0.7; }
  50% { opacity: 1; }
  100% { opacity: 0.7; }
}

/* 空状态样式 */
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100px;
  color: #94a3b8;
  font-style: italic;
}

/* 自定义滚动条样式 */
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
  height: calc(100% - 40px); /* 减去标题区域的高度 */
  margin-top: 10px;
}
</style>