<script setup lang="ts">
import { ref, onMounted, reactive, watch } from 'vue'
import { computed } from 'vue';
import * as echarts from 'echarts'
import { areaService, alertService, noticeService, summaryService, nodeService, buildingService } from '../services'
import type { AreaItem, Building, HistoricalData, SummaryData, HardwareNode } from '../types'
import HistoricalChart2 from '../components/chart-datascreen/HistoricalChart2.vue'
import HardwareNodeStatus from '../components/data/HardwareNodeStatus.vue'
import EnvironmentalChart2 from '../components/chart-datascreen/EnvironmentalChart2.vue'

// 在<script setup>部分添加选中区域的状态
const selectedAreaId = ref(null);
// 添加处理区域选择事件的函数
const handleAreaSelected = (areaId) => {
  console.log('选中区域ID:', areaId);
  selectedAreaId.value = areaId;
  currentAreaIndex.value = areas.value.findIndex(area => area.id === areaId);
  
  // 如果找不到对应区域，设置为第一个区域
  if (currentAreaIndex.value === -1 && areas.value.length > 0) {
    currentAreaIndex.value = 0;
  }
};

// watch监听selectedAreaId变化，更新图表显示
watch(selectedAreaId, (newId) => {
  if (newId) {
    // 如果有新选中的区域，更新currentAreaIndex
    const index = areas.value.findIndex(area => area.id === newId);
    if (index !== -1) {
      currentAreaIndex.value = index;
    }
  }
});
// 添加一个计算属性，将温湿度数据合并到区域数据中
const areasWithEnvironmentData = computed(() => {
  if (!areas.value || !nodes.value) return [];
  
  return areas.value.map(area => {
    // 查找与该区域关联的节点（通过bound_node关联）
    const relatedNode = nodes.value.find(node => node.id === area.bound_node);
    
    // 返回合并后的对象
    return {
      ...area,
      temperature: relatedNode?.temperature,
      humidity: relatedNode?.humidity
    };
  });
});

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
const buildings = ref<Building[]>([])
const nodes = ref<HardwareNode[]>([])
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

    const [areasData, buildingsData, nodesData] = await Promise.all([
      buildingService.getBuildingAreas(2),
      buildingService.getAll(), // 假设存在 getAll 方法
      nodeService.getAll() // 假设存在 getAll 方法
    ]);

    areas.value = areasData;
    buildings.value = buildingsData;
    nodes.value = nodesData;

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
    <!-- 3D Heatmap as background -->
    <ThreeDHeatMap :areas="areasWithEnvironmentData" 
    class="heatmap-container-fullscreen" 
    @areaSelected="handleAreaSelected" />

    <!-- UI Overlay -->
    <div class="ui-overlay">
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
        <!-- Top overview cards -->

        <div class="top-section">
          <div class="overview-container-left">
            <div class="trapezoid-left"></div>
            <div class="overview-left">
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
            </div>
          </div>
          <div class="heatmap-title-trapezoid">
            <span class="heatmap-title-text">数据可视平台</span>
          </div>
          <div class="overview-container-right">
            <div class="trapezoid-right"></div>
            <div class="overview-right">
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
          </div>
        </div>
        <!-- Center Content -->
        <div class="main-content">
          <div class="left-column">
            <CarouselList title="建筑列表" subtitle="Building List" :items="buildings">
              <template #item="{ item }">
                <div class="list-item-custom">
                  <span>{{ item.name }}</span>
                  <span class="item-detail">区域数: {{ item.areas_count }}</span>
                </div>
              </template>
            </CarouselList>

            <CarouselList title="区域列表" subtitle="Area List" :items="areas">
              <template #item="{ item }">
                <div class="list-item-custom">
                  <span>{{ item.name }}</span>
                  <span class="item-detail">{{ item.detected_count }}/{{ item.capacity }} 人</span>
                </div>
              </template>
            </CarouselList>

            <CarouselList title="节点列表" subtitle="Node List" :items="nodes">
              <template #item="{ item }">
                <div class="list-item-custom">
                  <span>{{ item.name }}</span>
                  <div class="node-details">
                    <span class="item-detail">温度：{{ item.temperature?.toFixed(1) }}°C</span>
                    <span class="item-detail">湿度：{{ item.humidity?.toFixed(1) }}%</span>
                    <span class="status-badge" :class="item.status ? 'status-active' : 'status-inactive'">
                      {{ item.status ? '在线' : '离线' }}
                    </span>
                  </div>
                </div>
              </template>
            </CarouselList>
          </div>
          <div class="right-column">
            <div ref="chartRef" class="chart-container">
              <div class="tech-corners"></div>
              <div class="chart-inner-container">
                <EnvironmentalChart2 :areaId="selectedAreaId || (areas.length > 0 ? areas[currentAreaIndex].id : null)"
                  :dataType="'temperature-humidity'" :hideTitle="true" :hideControls="true" :width="'100%'"
                  :height="'100%'" :styleConfig="{
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
                  }" />
              </div>
            </div>
            <div ref="chartRef" class="chart-container">
              <div class="tech-corners"></div>
              <div class="chart-inner-container">
                <HistoricalChart2 :areaId="selectedAreaId || (areas.length > 0 ? areas[currentAreaIndex].id : null)" 
                  :hideTitle="true"
                  :hideControls="true" :width="'100%'" :height="'100%'" :hideDataZoom="true" :hideStatistics="true"
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
                  }" />
              </div>
            </div>
          </div>

    </div>


    <!-- Bottom message river -->
    <div class="message-river">
      <div class="message-container">
        <div v-for="msg in messages" :key="`${msg.sourceType}-${msg.sourceId}`" class="message-bubble"
          :class="[`type-${msg.type}`]">
          <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
          <span class="message-text">{{ msg.text }}</span>
        </div>
      </div>
    </div>

    <!-- Heatmap Title -->

</template>
</div>
</div>
</template>

<style scoped>
.dashboard {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #0f172a;
}

.heatmap-container-fullscreen {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
}

.ui-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 2;
  pointer-events: none;
  /* Let mouse events pass through */
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 0;
  box-sizing: border-box;
}

.top-section {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  height: 100px;
  flex-shrink: 0;
  position: relative;
}

.fullscreen-toggle,
.overview-container-left,
.overview-container-right,
.main-content,
.message-river,
.heatmap-title-trapezoid {
  pointer-events: auto;
  /* Re-enable pointer events for UI elements */
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
  z-index: 9999;
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


.overview-container-left,
.overview-container-right {
  height: 100%;
  width: 45%;
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(10px);
  box-sizing: border-box;
}

.overview-container-left {
  left: 0;
  margin-right: 20px;
  clip-path: polygon(0 0, 100% 0, 95% 100%, 0% 100%);
}

.overview-container-right {
  right: 0;
  margin-left: 20px;
  clip-path: polygon(0% 0, 100% 0, 100% 100%, 5% 100%);
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  height: 100%;
}

.main-content {
  flex-grow: 1;
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin: 0;
  min-height: 0;
  pointer-events: none;
}

.left-column,
.right-column {
  width: 27%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 10px;
  background: rgba(15, 23, 42, 0.7);
  pointer-events: auto;
}

.right-column {
  background: linear-gradient(to left, rgba(15, 23, 42, 0.9) 85%, rgba(15, 23, 42, 0));
  padding-left: 60px;
}

.left-column {
  background: linear-gradient(to right, rgba(15, 23, 42, 0.9) 85%, rgba(15, 23, 42, 0));
  padding-right: 60px;
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

.overview-item {
  background: rgba(30, 41, 59, 0.7);
  padding: 10px;
  border-radius: 0px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.2);
  transition: all 0.3s;
  backdrop-filter: blur(10px);
  overflow: hidden;
  margin: 10px 0;
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

.overview-item h3 {
  margin: 0;
  font-size: 0.8rem;
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

.heatmap-title-trapezoid {
  background-color: rgba(15, 23, 42, 0.7);
  color: #e0f2fe;
  padding: 8px 30px;
  clip-path: polygon(0 0, 100% 0, 90% 100%, 10% 100%);
  font-size: 1.1rem;
  font-weight: bold;
  border: 1px solid rgba(56, 189, 248, 0.3);
  box-sizing: border-box;
  white-space: nowrap;
  z-index: 10;
}

.trapezoid-left,
.trapezoid-right {
  position: absolute;
  top: 0;
  width: 100%;
  height: 100%;
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(10px);
  z-index: -1;
}

.trapezoid-left {
  clip-path: polygon(0 0, 100% 0, 95% 100%, 0% 100%);
}

.trapezoid-right {
  clip-path: polygon(0% 0, 100% 0, 100% 100%, 5% 100%);
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
  font-size: 1.2rem;
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

.heatmap-title-text {
  position: relative;
  z-index: 1;
  font-size: 1.25rem;
  font-weight: bold;
  color: #e0f2fe;
  letter-spacing: 2px;
  text-shadow: 0 2px 8px rgba(56, 189, 248, 0.25);
  font-family: 'Microsoft YaHei', 'Arial', sans-serif;
  user-select: none;
  padding: 0 12px;
}

.time {
  font-size: 1rem;
  font-weight: bold;
  margin-top: 8px;
  background: linear-gradient(90deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  color: transparent;
  font-family: 'Courier New', monospace;
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

.overview-left,
.overview-right {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 15px;
  height: 100%;
}

.overview-left {
  padding-right: 45px;
  padding-left: 10px;
}

.overview-right {
  padding-left: 45px;
  padding-right: 10px;
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

.message-river {
  bottom: 0;
  left: 0;
  width: 100%;
  height: 60px;
  background: rgba(0, 17, 45, 0.8);
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

.list-item-custom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.item-detail {
  font-size: 12px;
  color: #94a3b8;
}

.node-details {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.status-active {
  background-color: rgba(22, 163, 74, 0.3);
  color: #4ade80;
}

.status-inactive {
  background-color: rgba(239, 68, 68, 0.3);
  color: #f87171;
}

.chart-container,
.info-list-container {
  /* Assuming CarouselList has this class */
  border: 1px solid rgba(56, 189, 248, 0.3);

  backdrop-filter: blur(5px);
  padding: 10px;
  flex-direction: column;
  min-height: 0;
}

.list-item-custom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 10px 5px;
  transition: background-color 0.3s ease;
}

.list-item-custom:hover {
  background-color: rgba(56, 189, 248, 0.1);
}

.list-item-custom>span:first-child {
  color: #e0f2fe;
  font-weight: 500;
}
</style>