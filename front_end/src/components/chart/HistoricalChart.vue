<script lang="ts" setup>
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import BaseChart from './BaseChart.vue'
import { areaService, historicalService } from '../../services'
import type { HistoricalData } from '../../types.ts'

// Props定义
interface Props {
  areaId: number
  areaName?: string
  height?: string
  showControls?: boolean
  chartType?: 'line' | 'bar' | 'area'
}

const props = withDefaults(defineProps<Props>(), {
  height: '400px',
  showControls: true,
  chartType: 'line'
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
const fetchHistoricalData = async (areaId: number, hours = 24) => {
  try {
    loading.value = true
    error.value = null
    
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
        historicalData.value = data.sort((a, b) => 
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );
        // 移除成功日志
        updateChart();
        return;
      }
    } catch (apiError) {
      // 保留错误日志
      console.error('区域历史数据API失败:', apiError);

      
      // 尝试使用通用历史数据服务
      try {
        const data = await historicalService.getHistoricalByDateRange(
          startTime.toISOString().split('T')[0],
          endTime.toISOString().split('T')[0],
          { area_id: areaId }
        )
        
        if (data && data.length > 0) {
          historicalData.value = data.sort((a, b) => 
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          )

          // 立即更新图表
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

    
  } catch (err: any) {
    error.value = err.message || '获取历史数据失败'
    console.error('获取历史数据失败:', err)
  } finally {
    loading.value = false
  }
}

// 生成图表配置
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

  const baseSeriesConfig = {
    name: '检测人数',
    data: counts,
    smooth: true,
    lineStyle: {
      width: 3,
      color: '#409EFF'
    },
    itemStyle: {
      color: '#409EFF',
      borderColor: '#fff',
      borderWidth: 2
    },
    emphasis: {
      itemStyle: {
        shadowBlur: 10,
        shadowColor: 'rgba(64, 158, 255, 0.3)'
      }
    }
  }

  let series
  if (props.chartType === 'area') {
    series = {
      ...baseSeriesConfig,
      type: 'line',
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
          ]
        }
      }
    }
  } else if (props.chartType === 'bar') {
    series = {
      ...baseSeriesConfig,
      type: 'bar',
      barWidth: '60%',
      itemStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: '#409EFF' },
            { offset: 1, color: '#79bbff' }
          ]
        },
        borderRadius: [4, 4, 0, 0]
      }
    }
  } else {
    series = {
      ...baseSeriesConfig,
      type: 'line'
    }
  }

  return {
    title: {
      text: `当前: ${currentCount}人 | 峰值: ${maxCount}人 | 平均: ${avgCount}人`,
      textStyle: {
        fontSize: 14,
        fontWeight: 'normal',
        color: '#666'
      },
      right: '5%',
      top: '2%'
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
        rotate: 45,
        formatter: (value: string) => {
          // 如果数据点太多，只显示部分标签
          if (times.length > 20) {
            const index = times.indexOf(value)
            return index % 3 === 0 ? value : ''
          }
          return value
        }
      }
    },
    yAxis: {
      name: '人数',
      nameTextStyle: {
        color: '#666',
        fontSize: 12
      },
      axisLabel: {
        formatter: '{value}人'
      },
      min: 0
    },
    series: [series],
    dataZoom: [
      {
        type: 'slider',
        show: historicalData.value.length > 20,
        start: historicalData.value.length > 20 ? 70 : 0,
        end: 100,
        height: 20,
        bottom: 10
      }
    ]
  }
}

// 图表就绪事件处理
const handleChartReady = (chart: any) => {
  // 图表准备好后，如果已有数据则立即更新
  if (historicalData.value.length > 0) {
    updateChart()
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

// 时间范围变化处理
const handleTimeRangeChange = (hours: number) => {
  currentTimeRange.value = hours
  refreshData()
}

// 刷新数据
const refreshData = () => {
  fetchHistoricalData(props.areaId, currentTimeRange.value)
}

// 监听props变化
watch(
  () => [props.areaId],
  () => {
    refreshData()
  },
  { immediate: true }
)
</script>

<template>
  <BaseChart
    ref="baseChart"
    :title="chartTitle"
    :height="height"
    :loading="loading"
    :error="error"
    :show-time-range="showControls"
    :show-refresh="showControls"
    :show-export="showControls"
    :time-range="currentTimeRange"
    :chart-type="chartType"
    @time-range-change="handleTimeRangeChange"
    @refresh="refreshData"
    @chart-ready="handleChartReady"
  />
</template>

<style scoped>

</style>