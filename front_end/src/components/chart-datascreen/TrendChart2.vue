<script lang="ts" setup>
import { ref, computed } from 'vue'
import BaseChart from './BaseChart.vue'

// Props定义
interface Props {
  title?: string
  height?: string
  showControls?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: '人员变化趋势',
  height: '320px',
  showControls: false
})

// 状态管理
const loading = ref(false)
const error = ref<string | null>(null)

// 基础图表组件引用
const baseChart = ref<InstanceType<typeof BaseChart>>()

// 生成模拟趋势数据（这里使用固定的一天趋势数据）
const generateTrendData = () => {
  const hours = Array.from({ length: 18 }, (_, i) => `${i + 6}:00`)
  const peopleData = [
    10,   // 6:00
    20,   // 7:00
    180,  // 8:00 早高峰
    195,  // 9:00
    320,  // 10:00
    325,  // 11:00
    250,  // 12:00 午餐高峰
    180,  // 13:00
    280,  // 14:00
    285,  // 15:00
    160,  // 16:00
    130,  // 17:00 晚餐高峰
    180,  // 18:00
    310,  // 19:00 晚自习高峰
    330,  // 20:00
    340,  // 21:00
    120,  // 22:00
    20    // 23:00
  ]
  
  return { hours, peopleData }
}

// 生成图表配置
const generateChartOption = () => {
  const { hours, peopleData } = generateTrendData()
  
  return {
    title: {
      text: `今日人流趋势`,
      textStyle: {
        fontSize: 16,
        fontWeight: '500',
        color: '#333'
      },
      left: 'center',
      top: '2%'
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const param = params[0]
        return `时间: ${param.name}<br/>人数: ${param.value}人`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '8%',
      top: '20%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: hours,
      axisLabel: {
        color: '#666',
        fontSize: 12
      },
      axisLine: {
        lineStyle: {
          color: '#e0e0e0'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '人数',
      nameTextStyle: {
        color: '#666',
        fontSize: 12
      },
      axisLabel: {
        formatter: '{value}人',
        color: '#666',
        fontSize: 11
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0',
          type: 'dashed'
        }
      }
    },
    series: [{
      name: '人数',
      data: peopleData,
      type: 'line',
      smooth: true,
      symbolSize: 8,
      lineStyle: {
        width: 3,
        color: '#409EFF',
        shadowColor: 'rgba(64, 158, 255, 0.2)',
        shadowBlur: 12,
        shadowOffsetY: 6
      },
      itemStyle: {
        color: '#409EFF',
        borderColor: '#fff',
        borderWidth: 2
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(64, 158, 255, 0.4)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.02)' }
          ]
        }
      },
      label: {
        show: true,
        position: 'top',
        color: '#36b5ff',
        fontSize: 11,
        formatter: '{c}'
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(64, 158, 255, 0.3)'
        }
      }
    }]
  }
}

// 图表就绪事件处理
const handleChartReady = (chart: any) => {
  updateChart()
}

// 更新图表
const updateChart = () => {
  if (baseChart.value) {
    const option = generateChartOption()
    baseChart.value.updateChart(option)
  }
}

// 刷新数据
const refreshData = () => {
  // 重新生成图表，模拟数据刷新
  updateChart()
}
</script>

<template>
  <BaseChart
    ref="baseChart"
    :title="title"
    :height="height"
    :loading="loading"
    :error="error"
    :show-time-range="showControls"
    :show-refresh="showControls"
    :show-export="showControls"
    @refresh="refreshData"
    @chart-ready="handleChartReady"
  />
</template>

<style scoped>
/* 可以添加特定于趋势图表的样式 */
</style> 