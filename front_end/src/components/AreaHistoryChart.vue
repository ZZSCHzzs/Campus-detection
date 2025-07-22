<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted, reactive } from 'vue'
import * as echarts from 'echarts'
import { historicalService, areaService } from '../services'
import type { HistoricalData, AreaItem } from '../types'

const props = defineProps({
  areaId: {
    type: Number,
    default: null
  },
  height: {
    type: String,
    default: '100%'
  },
  areaName: {
    type: String,
    default: ''
  },
  // 添加新属性接收所有区域数据，用于轮换
  areas: {
    type: Array as () => AreaItem[],
    default: () => []
  }
})

const chartContainer = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null
const loading = ref(false)
const error = ref<string | null>(null)
const historicalData = ref<HistoricalData[]>([])
const currentAreaName = ref(props.areaName || '未知区域')

// 添加轮换状态管理
const rotationState = reactive({
  currentIndex: 0,
  isRotating: true,
  rotationTimer: null as any,
  isTransitioning: false,
  // 为每个区域缓存生成的数据
  areaDataCache: new Map<number, HistoricalData[]>()
})

// 格式化时间显示
const formatTimeLabel = (timestamp: string) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 初始化图表
const initChart = () => {
  if (!chartContainer.value) return
  
  chart = echarts.init(chartContainer.value)
  
  // 设置图表加载状态
  chart.showLoading({
    text: '数据加载中',
    maskColor: 'rgba(15, 23, 42, 0.8)',
    textColor: '#e2e8f0',
    spinnerRadius: 6
  })
}

// 更新图表数据
const updateChart = () => {
  if (!chart || historicalData.value.length === 0) return
  
  // 准备数据
  const timestamps = historicalData.value.map(item => formatTimeLabel(item.timestamp))
  const counts = historicalData.value.map(item => item.detected_count)
  
  // 配置图表选项
  const option = {
    title: {
      text: currentAreaName.value,
      left: 'center',
      textStyle: {
        color: '#e2e8f0',
        fontSize: 18,
        fontWeight: 'normal',
        overflow: 'truncate', // 添加溢出处理
      },
      padding: [0, 0, 10, 0] // 添加内边距
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.8)',
      borderColor: 'rgba(56, 189, 248, 0.3)',
      textStyle: { color: '#e2e8f0' },
      formatter: '{b}<br/>检测人数: {c}'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%', // 增加顶部空间以容纳标题
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: timestamps,
      axisLine: {
        lineStyle: { color: 'rgba(148, 163, 184, 0.3)' }
      },
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10
      },
      splitLine: {
        show: false
      }
    },
    yAxis: {
      type: 'value',
      splitLine: {
        lineStyle: { color: 'rgba(148, 163, 184, 0.1)' }
      },
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10
      }
    },
    series: [{
      name: '检测人数',
      type: 'line',
      smooth: true,
      data: counts,
      lineStyle: {
        width: 3,
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#38bdf8' },
          { offset: 1, color: '#818cf8' }
        ])
      },
      areaStyle: {
        opacity: 0.3,
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(56, 189, 248, 0.5)' },
          { offset: 1, color: 'rgba(56, 189, 248, 0.05)' }
        ])
      },
      symbol: 'circle',
      symbolSize: 6,
      itemStyle: {
        color: '#38bdf8',
        borderColor: '#ffffff',
        borderWidth: 1
      },
      emphasis: {
        itemStyle: {
          color: '#38bdf8',
          borderColor: '#ffffff',
          borderWidth: 2,
          shadowColor: 'rgba(56, 189, 248, 0.5)',
          shadowBlur: 10
        }
      }
    }],
    animationDuration: 1000
  }
  
  chart.hideLoading()
  chart.setOption(option)
}

// 获取区域名称
const fetchAreaName = async (areaId: number) => {
  if (!areaId) return '未知区域'
  
  // 如果传入了区域数组，先从中查找
  if (props.areas && props.areas.length > 0) {
    const area = props.areas.find(a => a.id === areaId)
    if (area && area.name) {
      return area.name
    }
  }
  
  try {
    const area = await areaService.getById(areaId)
    if (area && area.name) {
      return area.name
    }
  } catch (error) {
    console.error('获取区域名称失败:', error)
  }
  
  return '未知区域'
}

// 创建模拟数据
const createMockData = (areaId: number) => {
  // 如果已有缓存数据，直接返回
  if (rotationState.areaDataCache.has(areaId)) {
    return rotationState.areaDataCache.get(areaId)
  }
  
  console.log(`为区域ID ${areaId} 创建模拟数据`)
  const mockData: HistoricalData[] = []
  const now = new Date()
  
  // 为不同区域生成不同特征的数据
  const areaFactor = areaId % 5 + 1 // 根据区域ID生成随机因子
  
  // 生成24小时的数据点，每30分钟一个
  for (let i = 48; i >= 0; i--) {
    const timestamp = new Date(now)
    timestamp.setMinutes(now.getMinutes() - i * 30) // 每30分钟一个数据点
    
    // 根据区域特性调整基础客流量（10-50之间）
    let baseCount = (10 + Math.floor(Math.random() * 40)) * areaFactor * 0.5
    
    // 早晨和傍晚的高峰期(8-10点，17-19点)增加客流量
    const hour = timestamp.getHours()
    if ((hour >= 8 && hour <= 10) || (hour >= 17 && hour <= 19)) {
      baseCount += (20 + Math.floor(Math.random() * 30)) * (areaFactor * 0.3)
    }
    
    // 午休时间(12-14点)稍高客流量
    if (hour >= 12 && hour <= 14) {
      baseCount += (10 + Math.floor(Math.random() * 19)) * (areaFactor * 0.2)
    }
    
    // 深夜(23-6点)减少客流量
    if (hour >= 23 || hour <= 6) {
      baseCount = Math.max(5, Math.floor(baseCount * 0.3))
    }
    
    // 添加一些随机波动
    const randomFactor = 0.85 + Math.random() * 0.3
    const finalCount = Math.floor(baseCount * randomFactor)
    
    mockData.push({
      id: i,
      area: areaId,
      detected_count: finalCount,
      timestamp: timestamp.toISOString()
    })
  }
  
  // 缓存生成的数据
  rotationState.areaDataCache.set(areaId, mockData)
  return mockData
}

// 获取历史数据
const fetchHistoricalData = async (areaId: number) => {
  if (!areaId) return
  
  try {
    loading.value = true
    error.value = null
    
    // 获取区域名称
    currentAreaName.value = await fetchAreaName(areaId)
    
    // // 尝试从API获取历史数据
    // try {
    //   // 使用日期范围参数获取历史数据
    //   const data = await historicalService.getAreaHistorical(areaId, {
    //     limit: 50
    //   })
      
    //   // 如果API返回了数据，则使用该数据
    //   if (data && data.length > 0) {
    //     historicalData.value = data.sort((a, b) => 
    //       new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    //     )
    //     updateChart()
    //     return
    //   }
    // } catch (apiError) {
    //   console.log('API数据获取失败，使用模拟数据', apiError)
    // }
    
    // 创建模拟历史数据（当API调用失败或返回空数据时）
    const mockData = createMockData(areaId)
    historicalData.value = mockData
    updateChart()
    
  } catch (err) {
    error.value = '获取历史数据失败'
    console.error('获取历史数据失败:', err)
    if (chart) {
      chart.hideLoading()
    }
  } finally {
    loading.value = false
  }
}

// 初始化区域轮换
const initRotation = () => {
  // 如果没有区域数据，或者只有一个区域，不需要轮换
  if (!props.areas || props.areas.length <= 1) {
    if (props.areaId) {
      fetchHistoricalData(props.areaId)
    }
    return
  }
  
  // 清除现有定时器
  if (rotationState.rotationTimer) {
    clearInterval(rotationState.rotationTimer)
  }
  
  // 加载当前区域数据
  const currentAreaId = props.areas[rotationState.currentIndex].id
  fetchHistoricalData(currentAreaId)
  
  // 设置轮换定时器
  rotationState.rotationTimer = setInterval(() => {
    if (!rotationState.isRotating) return
    
    // 标记为正在过渡
    rotationState.isTransitioning = true
    
    // 0.5秒后切换到下一个区域
    setTimeout(() => {
      // 更新到下一个区域索引
      rotationState.currentIndex = (rotationState.currentIndex + 1) % props.areas.length
      const nextAreaId = props.areas[rotationState.currentIndex].id
      
      // 加载下一个区域的数据
      fetchHistoricalData(nextAreaId)
      
      // 0.5秒后完成过渡
      setTimeout(() => {
        rotationState.isTransitioning = false
      }, 500)
      
    }, 500) // 停顿0.5秒
    
  }, 2000) // 每2秒轮换一次
}

// 手动切换到指定区域
const switchToArea = (index: number) => {
  if (index < 0 || index >= props.areas.length) return
  
  // 暂停自动轮换
  rotationState.isRotating = false
  rotationState.currentIndex = index
  
  // 加载选定区域的数据
  const areaId = props.areas[index].id
  fetchHistoricalData(areaId)
  
  // 10秒后恢复自动轮换
  setTimeout(() => {
    rotationState.isRotating = true
  }, 10000)
}

// 监听窗口大小变化，调整图表大小
const handleResize = () => {
  chart?.resize()
}

onMounted(() => {
  initChart()
  
  // 如果提供了区域数组，启动轮换
  if (props.areas && props.areas.length > 0) {
    initRotation()
  }
  // 否则使用单一区域ID
  else if (props.areaId) {
    fetchHistoricalData(props.areaId)
  }
  
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  // 清除定时器
  if (rotationState.rotationTimer) {
    clearInterval(rotationState.rotationTimer)
  }
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})

// 监听区域ID或名称变化
watch(() => props.areaId, (newId) => {
  // 如果没有区域数组但有新的区域ID，则加载该区域数据
  if (!props.areas || props.areas.length === 0) {
    if (newId) {
      fetchHistoricalData(newId)
    }
  }
})

watch(() => props.areaName, (newName) => {
  if (newName) {
    currentAreaName.value = newName
    updateChart()
  }
})

// 监听区域数组变化
watch(() => props.areas, (newAreas) => {
  if (newAreas && newAreas.length > 0) {
    // 重新初始化轮换
    initRotation()
  }
}, { deep: true })
</script>

<template>
  <div class="area-history-chart" :style="{ height }">
    <div v-if="error" class="chart-error">
      <span>{{ error }}</span>
      <button @click="fetchHistoricalData(props.areaId)" class="retry-btn">重试</button>
    </div>
    
    <!-- 添加区域选择器 -->
    <div v-if="props.areas && props.areas.length > 1" class="area-selector">
      <span 
        v-for="(area, index) in props.areas" 
        :key="area.id"
        :class="['selector-dot', { active: rotationState.currentIndex === index }]"
        @click="switchToArea(index)"
      ></span>
    </div>
    
    <!-- 添加过渡效果 -->
    <div 
      ref="chartContainer" 
      class="chart-inner"
      :class="{ 'chart-transitioning': rotationState.isTransitioning }"
    ></div>
  </div>
</template>

<style scoped>
.area-history-chart {
  width: 100%;
  height: 100%;
  position: relative;
}

.chart-inner {
  width: 100%;
  height: 100%;
  transition: opacity 0.5s ease;
}

.chart-transitioning {
  opacity: 0.5;
}

.chart-error {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.5);
  color: #fb7185;
  gap: 10px;
  z-index: 10;
}

.retry-btn {
  background: rgba(56, 189, 248, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.3);
  color: #38bdf8;
  padding: 5px 15px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 12px;
}

.retry-btn:hover {
  background: rgba(56, 189, 248, 0.3);
  transform: translateY(-2px);
}

/* 区域选择器样式 */
.area-selector {
  position: absolute;
  right: 15px;
  top: 15px;
  display: flex;
  gap: 6px;
  z-index: 5;
}

.selector-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(148, 163, 184, 0.3);
  cursor: pointer;
  transition: all 0.3s ease;
}

.selector-dot.active {
  background: #38bdf8;
  transform: scale(1.2);
}

.selector-dot:hover {
  background: rgba(56, 189, 248, 0.6);
}
</style>