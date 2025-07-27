<script lang="ts" setup>
import { ref, watch, computed} from 'vue'
import { ElMessage } from 'element-plus'
import BaseChart from './BaseChart.vue'
import { areaService, historicalService } from '../../services'
import type { HistoricalData } from '../../types.ts'

// Props定义
interface Props {
  areaId?: number  // 修改为可选，支持默认值
  areaName?: string
  height?: string
  width?: string  // 新增：宽度支持
  showControls?: boolean
  hideTitle?: boolean
  hideControls?: boolean
  chartType?: 'line' | 'bar' | 'area'
  hideDataZoom?: boolean  // 新增：隐藏下方范围选择条
  hideStatistics?: boolean // 新增：隐藏统计信息
  // 新增样式配置支持
  styleConfig?: {
    gridLineColor?: string
    gridLineType?: 'solid' | 'dashed' | 'dotted'
    showGridLine?: boolean
    axisLineColor?: string
    axisLabelColor?: string
    axisLabelFontSize?: number
    seriesColors?: string[]
    backgroundColor?: string
    textColor?: string
    fontSize?: number
    lineWidth?: number
    padding?: {
      top?: string
      right?: string
      bottom?: string
      left?: string
    }
    legendPosition?: 'top' | 'bottom' | 'left' | 'right'
    showLegend?: boolean
    tooltipBackgroundColor?: string
    tooltipTextColor?: string
    titleStyle?: {
      fontSize?: number
      fontWeight?: string
      color?: string
    }
    yAxis?: {
    }
    xAxis?: {
    }
    areaStyle?: {
      opacity?: number
      colorStops?: Array<{ offset: number; color: string }>
    }
  }
}

const props = withDefaults(defineProps<Props>(), {
  areaId: 2,  // 默认 areaId = 2
  height: '100%',
  width: '100%',  // 新增：默认宽度
  showControls: true,
  hideTitle: false,
  hideControls: false,
  chartType: 'line',
  hideDataZoom: false,  // 默认显示 dataZoom
  hideStatistics: false, // 默认显示统计信息
  styleConfig: () => ({})
})

// 状态管理
const loading = ref(false)
const error = ref<string | null>(null)
const currentTimeRange = ref(24)
const historicalData = ref<HistoricalData[]>([])
const currentAreaName = ref(props.areaName || '')

// 计算属性
const chartTitle = computed(() => {
  return currentAreaName.value ? `${currentAreaName.value} - 人数检测记录` : '人数检测记录'
})

// 获取区域名称
const fetchAreaName = async (areaId: number): Promise<string> => {
  try {
    const area = await areaService.getById(areaId)
    return area.name || `区域${areaId}`
  } catch (error) {
    console.warn('获取区域名称失败:', error)
    return `区域${areaId}`
  }
}

// 获取历史数据
// 获取历史数据
const fetchHistoricalData = async (areaId: number, hours: number) => {
  if (!areaId) return
  
  loading.value = true
  error.value = ''
  
  try {
    // 获取区域名称
    currentAreaName.value = await fetchAreaName(areaId)
    
    // 计算时间范围
    const endTime = new Date()
    const startTime = new Date(endTime.getTime() - hours * 60 * 60 * 1000)
    
    try {
      // 尝试使用区域API获取历史数据
      const data = await areaService.getAreaHistorical(areaId, {
        start_date: startTime.toISOString(),
        end_date: endTime.toISOString()
      })
      
      if (data && data.length > 0) {
        // 前端筛选：只保留当前时间范围内的数据
        const filteredData = data.filter(item => {
          const itemTime = new Date(item.timestamp).getTime()
          return itemTime >= startTime.getTime() && itemTime <= endTime.getTime()
        })
        
        historicalData.value = filteredData.sort((a, b) => 
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        )
        updateChart()
        return
      }
    } catch (apiError) {
      console.error('区域历史数据API失败:', apiError)
      
      // 尝试使用通用历史数据服务
      try {
        const data = await historicalService.getHistoricalByDateRange(
          startTime.toISOString().split('T')[0],
          endTime.toISOString().split('T')[0],
          { area_id: areaId }
        )
        
        if (data && data.length > 0) {
          // 前端筛选：只保留当前时间范围内的数据
          const filteredData = data.filter(item => {
            const itemTime = new Date(item.timestamp).getTime()
            return itemTime >= startTime.getTime() && itemTime <= endTime.getTime()
          })
          
          historicalData.value = filteredData.sort((a, b) => 
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          )
          updateChart()
          return
        }
      } catch (fallbackError) {
        throw new Error('历史数据获取失败')
      }
    }
    
    // 如果没有数据，清空数组并设置提示信息
    historicalData.value = []
    error.value = '暂无历史数据'
    updateChart() // 确保图表更新显示空状态
    
  } catch (err: any) {
    error.value = err.message || '获取历史数据失败'
    console.error('获取历史数据失败:', err)
  } finally {
    loading.value = false
  }
}

// 生成图表配置 - 纯数据结构，无样式
const generateChartOption = () => {
  const times = historicalData.value.map(item => 
    new Date(item.timestamp).toLocaleTimeString('zh-CN', { 
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit', 
      minute: '2-digit' 
    })
  )
  
  const counts = historicalData.value.map(item => item.detected_count || 0)
  
  // 计算统计信息
  const maxCount = Math.max(...counts, 0)
  const avgCount = counts.length > 0 ? Math.round(counts.reduce((a, b) => a + b, 0) / counts.length) : 0
  const currentCount = counts[counts.length - 1] || 0

  // 基础系列配置 - 不包含样式
  const baseSeriesConfig = {
    name: '检测人数',
    data: counts,
    smooth: true
  }

  let series
  if (props.chartType === 'area') {
    series = {
      ...baseSeriesConfig,
      type: 'line'
      // areaStyle 由 BaseChart 根据 styleConfig 处理
    }
  } else if (props.chartType === 'bar') {
    series = {
      ...baseSeriesConfig,
      type: 'bar'
      // barWidth, itemStyle 由 BaseChart 根据 styleConfig 处理
    }
  } else {
    series = {
      ...baseSeriesConfig,
      type: 'line'
    }
  }

  return {
    title: {
      text: props.hideStatistics ? '' : `当前:${currentCount} | 峰值:${maxCount} | 平均:${avgCount}`,
      right: '5%',
      top: '0%'
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const param = params[0]
        return `时间: ${param.name}<br/>检测人数: ${param.value}人`
      }
    },
    xAxis: {
      data: times,
      axisLabel: {
        rotate: 0, // 取消旋转
        formatter: (value: string) => {
          const date = new Date(value)
          // 格式化为 HH:mm
          const hours = date.getHours().toString().padStart(2, '0')
          const minutes = date.getMinutes().toString().padStart(2, '0')
          const formattedTime = `${hours}:${minutes}`

          // 根据数据量决定显示频率
          const total = times.length
          const index = times.indexOf(value)
          if (total > 24) { // 如果数据点多于24个
            // 每隔 (total / 8) 个点显示一个标签，保证最多显示约8个标签
            const interval = Math.floor(total / 3)
            return index % interval === 0 ? formattedTime : ''
          } else if (total > 10) { // 如果数据点在10到24个之间
            return index % 2 === 0 ? formattedTime : '' // 每隔一个显示
          }
          return formattedTime // 数据点少于10个时全部显示
        }
      }
    },
    yAxis: {
      name: '人数',
      axisLabel: {
        formatter: '{value}人'
      },
      min: 0
    },
    series: [series],
    dataZoom: props.hideDataZoom ? [] : [
      {
        type: 'slider',
        show: historicalData.value.length > 20,
        start: 0,
        end: 100,
        height: 20,
        bottom: 10
      }
    ]
  }
}

// 图表就绪事件处理
const handleChartReady = (chart: any) => {
  // 添加 dataZoom 事件监听
  chart.on('dataZoom', (params: any) => {
    handleDataZoomChange(params)
  })
  
  // 图表准备好后，如果已有数据则立即更新
  if (historicalData.value.length > 0) {
    updateChart()
  }
}

// 处理 dataZoom 滑块变化
const handleDataZoomChange = (params: any) => {
  if (!historicalData.value.length) return
  
  // 获取滑块的开始和结束百分比
  const startPercent = params.start || 0
  const endPercent = params.end || 100
  
  // 计算对应的数据索引范围
  const totalCount = historicalData.value.length
  const startIndex = Math.floor((startPercent / 100) * totalCount)
  const endIndex = Math.ceil((endPercent / 100) * totalCount)
  
  // 获取对应时间范围的数据
  const visibleData = historicalData.value.slice(startIndex, endIndex)
  
  if (visibleData.length > 0) {
    // 计算实际的时间范围（小时数）
    const firstTime = new Date(visibleData[0].timestamp)
    const lastTime = new Date(visibleData[visibleData.length - 1].timestamp)
    const timeDiffHours = (lastTime.getTime() - firstTime.getTime()) / (1000 * 60 * 60)
    
    // 更新当前时间范围（但不触发数据重新获取）
    currentTimeRange.value = Math.max(1, Math.ceil(timeDiffHours))
    
    // 可选：向父组件发送滑块时间范围变化事件
    const emit = defineEmits(['dataZoomChange'])
    emit('dataZoomChange', {
      timeRange: currentTimeRange.value,
      startPercent,
      endPercent,
      visibleData
    })
  }
}

// 基础图表组件引用
const baseChart = ref<InstanceType<typeof BaseChart>>()

// 更新图表
const updateChart = () => {
  // 确保图表组件已准备好且有数据
  if (baseChart.value && historicalData.value.length > 0) {
    const option = generateChartOption()
    baseChart.value.updateChart(option)
  }
}

// 时间范围变化处理（来自下拉选择器）
const handleTimeRangeChange = (hours: number) => {
  currentTimeRange.value = hours
  refreshData() // 重新获取数据
}

// 刷新数据
const refreshData = () => {
  fetchHistoricalData(props.areaId, currentTimeRange.value)
}

// 监听props变化 - 修改为支持可选 areaId
watch(
  () => [props.areaId],
  () => {
    if (props.areaId) {  // 只有当 areaId 存在时才刷新数据
      refreshData()
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="historical-chart-wrapper">
    <BaseChart
      ref="baseChart"
      :title="chartTitle"
      :height="height"
      :width="width"
      :loading="loading"
      :error="error"
      :show-time-range="showControls && !hideControls"
      :show-refresh="showControls && !hideControls"
      :show-export="showControls && !hideControls"
      :hide-title="hideTitle"
      :hide-controls="hideControls"
      :time-range="currentTimeRange"
      :chart-type="chartType"
      :style-config="styleConfig"
      @time-range-change="handleTimeRangeChange"
      @refresh="refreshData"
      @chart-ready="handleChartReady"
    />
  </div>
</template>

<style scoped>
.historical-chart-wrapper {
  height: 100%;
  width: 100%;
  position: relative;
}

:deep(.chart-container) {
  flex: 1;
  min-height: 0;
}

:deep(.echarts-container) {
  height: 100% !important;
}
</style>