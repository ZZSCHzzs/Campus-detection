<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted, reactive } from 'vue'
import * as echarts from 'echarts'
import { areaService } from '../services'
import type { TemperatureHumidityData, CO2Data, AreaItem, ProcessTerminal } from '../types'

const props = defineProps({
  areaId: {
    type: Number,
    default: null
  },
  terminalId: {
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
  areas: {
    type: Array as () => AreaItem[],
    default: () => []
  },
  dataType: {
    type: String as () => 'temperature' | 'humidity' | 'co2' | 'temperature-humidity',
    default: 'temperature-humidity'
  }
})

const chartContainer = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null
const loading = ref(false)
const error = ref<string | null>(null)
const temperatureHumidityData = ref<TemperatureHumidityData[]>([])
const co2Data = ref<CO2Data[]>([])
const currentAreaName = ref(props.areaName || '未知区域')

// 轮换状态管理
const rotationState = reactive({
  currentIndex: 0,
  isRotating: true,
  rotationTimer: null as any,
  isTransitioning: false,
  areaDataCache: new Map<number, TemperatureHumidityData[]>(),
  terminalDataCache: new Map<number, CO2Data[]>()
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
  
  chart.showLoading({
    text: '环境数据加载中',
    maskColor: 'rgba(15, 23, 42, 0.8)',
    textColor: '#e2e8f0',
    spinnerRadius: 6
  })
}

// 更新图表数据
const updateChart = () => {
  if (!chart) return
  
  let timestamps: string[] = []
  let series: any[] = []
  let yAxis: any[] = []
  
  if (props.dataType === 'co2') {
    // 显示CO2数据
    if (co2Data.value.length === 0) return
    
    timestamps = co2Data.value.map(item => formatTimeLabel(item.timestamp))
    const co2Levels = co2Data.value.map(item => item.co2_level)
    
    yAxis = [{
      type: 'value',
      name: 'CO2浓度(ppm)',
      axisLabel: { color: '#94a3b8', fontSize: 10 },
      nameTextStyle: { color: '#34d399' },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } }
    }]
    
    series = [{
      name: 'CO2浓度',
      type: 'line',
      data: co2Levels,
      lineStyle: { width: 3, color: '#34d399' },
      areaStyle: {
        opacity: 0.3,
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#34d39980' },
          { offset: 1, color: '#34d3990d' }
        ])
      },
      itemStyle: { color: '#34d399', borderColor: '#ffffff', borderWidth: 1 },
      smooth: true,
      symbol: 'circle',
      symbolSize: 6
    }]
  } else {
    // 显示温湿度数据
    if (temperatureHumidityData.value.length === 0) return
    
    timestamps = temperatureHumidityData.value.map(item => formatTimeLabel(item.timestamp))
    
    if (props.dataType === 'temperature-humidity') {
      // 显示温度和湿度
      const temperatures = temperatureHumidityData.value.map(item => item.temperature ?? null)
      const humidities = temperatureHumidityData.value.map(item => item.humidity ?? null)
      
      yAxis = [
        {
          type: 'value',
          name: '温度(°C)',
          position: 'left',
          axisLabel: { color: '#94a3b8', fontSize: 10 },
          nameTextStyle: { color: '#f87171' },
          splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } }
        },
        {
          type: 'value',
          name: '湿度(%)',
          position: 'right',
          axisLabel: { color: '#94a3b8', fontSize: 10 },
          nameTextStyle: { color: '#60a5fa' },
          splitLine: { show: false }
        }
      ]
      
      series = [
        {
          name: '温度',
          type: 'line',
          yAxisIndex: 0,
          data: temperatures,
          lineStyle: { width: 3, color: '#f87171' },
          itemStyle: { color: '#f87171' },
          smooth: true
        },
        {
          name: '湿度',
          type: 'line',
          yAxisIndex: 1,
          data: humidities,
          lineStyle: { width: 3, color: '#60a5fa' },
          itemStyle: { color: '#60a5fa' },
          smooth: true
        }
      ]
    } else {
      // 显示单一类型数据
      let data: (number | null)[] = []
      let color = '#38bdf8'
      let name = ''
      let unit = ''
      
      if (props.dataType === 'temperature') {
        data = temperatureHumidityData.value.map(item => item.temperature ?? null)
        color = '#f87171'
        name = '温度'
        unit = '°C'
      } else if (props.dataType === 'humidity') {
        data = temperatureHumidityData.value.map(item => item.humidity ?? null)
        color = '#60a5fa'
        name = '湿度'
        unit = '%'
      }
      
      yAxis = [{
        type: 'value',
        name: `${name}(${unit})`,
        axisLabel: { color: '#94a3b8', fontSize: 10 },
        nameTextStyle: { color },
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } }
      }]
      
      series = [{
        name,
        type: 'line',
        data,
        lineStyle: { width: 3, color },
        areaStyle: {
          opacity: 0.3,
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: color + '80' },
            { offset: 1, color: color + '0d' }
          ])
        },
        itemStyle: { color, borderColor: '#ffffff', borderWidth: 1 },
        smooth: true,
        symbol: 'circle',
        symbolSize: 6
      }]
    }
  }
  
  const option = {
    title: {
      text: currentAreaName.value,
      left: 'center',
      textStyle: { color: '#e2e8f0', fontSize: 18 },
      padding: [0, 0, 10, 0]
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.8)',
      borderColor: 'rgba(56, 189, 248, 0.3)',
      textStyle: { color: '#e2e8f0' },
      formatter: function(params: any) {
        let result = params[0].name + '<br/>'
        params.forEach((param: any) => {
          if (param.value !== null) {
            let unit = ''
            if (param.seriesName === '温度') unit = '°C'
            else if (param.seriesName === '湿度') unit = '%'
            else if (param.seriesName === 'CO2浓度') unit = 'ppm'
            result += `${param.seriesName}: ${param.value}${unit}<br/>`
          }
        })
        return result
      }
    },
    legend: props.dataType === 'temperature-humidity' ? {
      data: ['温度', '湿度'],
      textStyle: { color: '#e2e8f0' },
      top: 30
    } : undefined,
    grid: {
      left: '3%',
      right: props.dataType === 'temperature-humidity' ? '10%' : '4%',
      bottom: '3%',
      top: props.dataType === 'temperature-humidity' ? '20%' : '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: timestamps,
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.3)' } },
      axisLabel: { color: '#94a3b8', fontSize: 10 },
      splitLine: { show: false }
    },
    yAxis,
    series,
    animationDuration: 1000
  }
  
  chart.hideLoading()
  chart.setOption(option)
}

// 获取区域名称
const fetchAreaName = async (areaId: number) => {
  if (!areaId) return '未知区域'
  
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

// 创建模拟温湿度数据
const createMockTemperatureHumidityData = (areaId: number) => {
  if (rotationState.areaDataCache.has(areaId)) {
    return rotationState.areaDataCache.get(areaId)
  }
  
  console.log(`为区域ID ${areaId} 创建模拟温湿度数据`)
  const mockData: TemperatureHumidityData[] = []
  const now = new Date()
  
  // 为不同区域生成不同特征的环境数据
  const areaFactor = areaId % 5 + 1
  
  // 生成24小时的数据点，每30分钟一个
  for (let i = 48; i >= 0; i--) {
    const timestamp = new Date(now)
    timestamp.setMinutes(now.getMinutes() - i * 30)
    
    // 温度：20-30°C，有日间变化
    const hour = timestamp.getHours()
    let baseTemp = 22 + (areaFactor - 1) * 0.5
    if (hour >= 10 && hour <= 16) {
      baseTemp += 3 + Math.random() * 2 // 白天较热
    } else if (hour >= 18 || hour <= 6) {
      baseTemp -= 1 + Math.random() * 1 // 夜间较凉
    }
    const temperature = baseTemp + (Math.random() - 0.5) * 2
    
    // 湿度：40-70%，与温度反相关
    const humidity = 65 - (temperature - 22) * 2 + (Math.random() - 0.5) * 10
    
    mockData.push({
      id: i,
      area: areaId,
      temperature: Math.round(temperature * 10) / 10,
      humidity: Math.round(Math.max(30, Math.min(80, humidity)) * 10) / 10,
      timestamp: timestamp.toISOString()
    })
  }
  
  rotationState.areaDataCache.set(areaId, mockData)
  return mockData
}

// 创建模拟CO2数据
const createMockCO2Data = (terminalId: number) => {
  if (rotationState.terminalDataCache.has(terminalId)) {
    return rotationState.terminalDataCache.get(terminalId)
  }
  
  console.log(`为终端ID ${terminalId} 创建模拟CO2数据`)
  const mockData: CO2Data[] = []
  const now = new Date()
  
  const terminalFactor = terminalId % 3 + 1
  
  // 生成24小时的数据点，每30分钟一个
  for (let i = 48; i >= 0; i--) {
    const timestamp = new Date(now)
    timestamp.setMinutes(now.getMinutes() - i * 30)
    
    // CO2：400-1200ppm，人员活动高峰期较高
    const hour = timestamp.getHours()
    let baseCO2 = 400 + terminalFactor * 50
    if ((hour >= 8 && hour <= 10) || (hour >= 17 && hour <= 19)) {
      baseCO2 += 300 + Math.random() * 200 // 高峰期
    } else if (hour >= 12 && hour <= 14) {
      baseCO2 += 150 + Math.random() * 100 // 午休期
    }
    const co2_level = Math.max(350, Math.floor(baseCO2 + (Math.random() - 0.5) * 100))
    
    mockData.push({
      id: i,
      terminal: terminalId,
      co2_level,
      timestamp: timestamp.toISOString()
    })
  }
  
  rotationState.terminalDataCache.set(terminalId, mockData)
  return mockData
}

// 获取环境数据
const fetchEnvironmentalData = async (areaId?: number, terminalId?: number) => {
  try {
    loading.value = true
    error.value = null
    
    if (areaId) {
      currentAreaName.value = await fetchAreaName(areaId)
    }
    
    // TODO: 当后端API准备好时，取消注释以下代码
    /*
    if (props.dataType === 'co2' && terminalId) {
      try {
        const response = await fetch(`http://smarthit.top/api/terminals/${terminalId}/co2_data/?hours=24`)
        if (response.ok) {
          const data = await response.json()
          if (data && data.length > 0) {
            co2Data.value = data.sort((a, b) => 
              new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
            )
            updateChart()
            return
          }
        }
      } catch (apiError) {
        console.log('CO2 API数据获取失败，使用模拟数据', apiError)
      }
    } else if (areaId) {
      try {
        const response = await fetch(`http://smarthit.top/api/areas/${areaId}/temperature_humidity/?hours=24`)
        if (response.ok) {
          const data = await response.json()
          if (data && data.length > 0) {
            temperatureHumidityData.value = data.sort((a, b) => 
              new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
            )
            updateChart()
            return
          }
        }
      } catch (apiError) {
        console.log('温湿度API数据获取失败，使用模拟数据', apiError)
      }
    }
    */
    
    // 使用模拟数据
    if (props.dataType === 'co2' && terminalId) {
      const mockData = createMockCO2Data(terminalId)
      co2Data.value = mockData
    } else if (areaId) {
      const mockData = createMockTemperatureHumidityData(areaId)
      temperatureHumidityData.value = mockData
    }
    
    updateChart()
    
  } catch (err) {
    error.value = '获取环境数据失败'
    console.error('获取环境数据失败:', err)
    if (chart) {
      chart.hideLoading()
    }
  } finally {
    loading.value = false
  }
}

// 监听窗口大小变化
const handleResize = () => {
  chart?.resize()
}

onMounted(() => {
  initChart()
  
  if (props.dataType === 'co2' && props.terminalId) {
    fetchEnvironmentalData(undefined, props.terminalId)
  } else if (props.areaId) {
    fetchEnvironmentalData(props.areaId)
  }
  
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})

// 监听属性变化
watch(() => props.areaId, (newId) => {
  if (newId && props.dataType !== 'co2') {
    fetchEnvironmentalData(newId)
  }
})

watch(() => props.terminalId, (newId) => {
  if (newId && props.dataType === 'co2') {
    fetchEnvironmentalData(undefined, newId)
  }
})

watch(() => props.dataType, () => {
  if (props.dataType === 'co2' && props.terminalId) {
    fetchEnvironmentalData(undefined, props.terminalId)
  } else if (props.areaId) {
    fetchEnvironmentalData(props.areaId)
  }
})
</script>

<template>
  <div class="environmental-chart" :style="{ height }">
    <div v-if="error" class="chart-error">
      <span>{{ error }}</span>
      <button @click="fetchEnvironmentalData(props.areaId, props.terminalId)" class="retry-btn">重试</button>
    </div>
    
    <!-- 数据类型指示器 -->
    <div class="data-type-indicator">
      <span v-if="props.dataType === 'temperature'" class="indicator temp">温度</span>
      <span v-else-if="props.dataType === 'humidity'" class="indicator humid">湿度</span>
      <span v-else-if="props.dataType === 'co2'" class="indicator co2">CO2</span>
      <span v-else class="indicator temp-humid">温湿度</span>
    </div>
    
    <div ref="chartContainer" class="chart-inner"></div>
  </div>
</template>

<style scoped>
.environmental-chart {
  width: 100%;
  height: 100%;
  position: relative;
}

.chart-inner {
  width: 100%;
  height: 100%;
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

.data-type-indicator {
  position: absolute;
  left: 15px;
  top: 15px;
  z-index: 5;
}

.indicator {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid;
}

.indicator.temp {
  color: #f87171;
  border-color: rgba(248, 113, 113, 0.3);
}

.indicator.humid {
  color: #60a5fa;
  border-color: rgba(96, 165, 250, 0.3);
}

.indicator.co2 {
  color: #34d399;
  border-color: rgba(52, 211, 153, 0.3);
}

.indicator.temp-humid {
  color: #e2e8f0;
  border-color: rgba(226, 232, 240, 0.3);
}
</style> 