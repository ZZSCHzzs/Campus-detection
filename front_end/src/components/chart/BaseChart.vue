<script lang="ts" setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { Refresh, Download, FullScreen, Calendar } from '@element-plus/icons-vue'

// Props定义
interface Props {
  title?: string
  height?: string
  width?: string  // 新增width prop
  loading?: boolean
  error?: string | null
  showTimeRange?: boolean
  showRefresh?: boolean
  showExport?: boolean
  showFullscreen?: boolean
  showEmpty?: boolean
  timeRange?: number // 小时数
  timeOptions?: Array<{ label: string; value: number }>
  chartType?: 'line' | 'bar' | 'area'
  theme?: 'light' | 'dark'
  gridConfig?: any
  legendConfig?: any
  // 新增props
  hideTitle?: boolean
  hideControls?: boolean
  // 数据就绪标志 - 新增
  dataReady?: boolean
  // 新增样式配置选项
  styleConfig?: {
    // 网格线配置
    gridLineColor?: string
    gridLineType?: 'solid' | 'dashed' | 'dotted'
    showGridLine?: boolean
    // 坐标轴配置
    axisLineColor?: string
    axisLabelColor?: string
    axisLabelFontSize?: number
    // 曲线/图表颜色
    seriesColors?: string[]
    // 背景配置
    backgroundColor?: string
    // 文字配置
    textColor?: string
    fontSize?: number
    // 新增：线条宽度
    lineWidth?: number
    // 边距配置
    padding?: {
      top?: string
      right?: string
      bottom?: string
      left?: string
    }
    // 图例配置
    legendPosition?: 'top' | 'bottom' | 'left' | 'right'
    showLegend?: boolean
    // 工具提示配置
    tooltipBackgroundColor?: string
    tooltipTextColor?: string
    // 新增：标题样式
    titleStyle?: {
      fontSize?: number
      fontWeight?: string
      color?: string
    }
    // 新增：区域填充样式
    areaStyle?: {
      opacity?: number
      colorStops?: Array<{ offset: number; color: string }>
    }
  }
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  height: '300px',
  width: '100%',
  loading: false,
  error: null,
  showTimeRange: true,
  showRefresh: true,
  showExport: false,
  showFullscreen: false,
  showEmpty: false,
  timeRange: 24,
  timeOptions: () => [
    { label: '最近1小时', value: 1 },
    { label: '最近6小时', value: 6 },
    { label: '最近12小时', value: 12 },
    { label: '最近24小时', value: 24 },
    { label: '最近3天', value: 72 },
    { label: '最近7天', value: 168 }
  ],
  chartType: 'line',
  theme: 'light',
  gridConfig: () => ({
    left: '3%',
    right: '4%',
    bottom: '10%',
    top: '15%',
    containLabel: true
  }),
  legendConfig: () => ({
    top: '5%',
    textStyle: {
      fontSize: 12
    }
  }),
  // 新增默认值
  hideTitle: false,
  hideControls: false,
  dataReady: false  // 新增默认值
})

// Emits定义
const emit = defineEmits<{
  timeRangeChange: [value: number]
  refresh: []
  export: []
  fullscreen: []
  chartReady: [chart: echarts.ECharts]
}>()

// 状态管理
const chartContainer = ref<HTMLElement>()
const chart = ref<echarts.ECharts>()
const currentTimeRange = ref(props.timeRange)
const isFullscreen = ref(false)
const internalLoading = ref(false)

// 计算属性
// 计算属性 - 修改containerStyle
const containerStyle = computed(() => ({
  height: props.height,
  width: props.width,  // 使用props.width
  position: 'relative' as const
}))


// 初始化图表 - 修复loading状态
const initChart = async () => {
  if (!chartContainer.value) {
    console.warn('图表容器不存在')
    return
  }

  // 检查数据是否准备就绪
  if (!props.dataReady && !props.loading) {
    console.log('数据未准备就绪，等待数据加载完成')
    return
  }

  try {
    // 设置内部加载状态
    internalLoading.value = true

    // 销毁已存在的图表
    if (chart.value) {
      chart.value.dispose()
      chart.value = undefined
    }

    // 强制等待一帧以确保DOM完全渲染
    await new Promise(resolve => requestAnimationFrame(resolve))
    await new Promise(resolve => setTimeout(resolve, 50))

    // 检查容器尺寸
    let containerWidth = chartContainer.value.clientWidth
    let containerHeight = chartContainer.value.clientHeight

    // 如果容器尺寸无效，尝试从props获取
    if (!containerWidth || containerWidth <= 0) {
      containerWidth = parseInt(props.width, 10)
    }
    if (!containerHeight || containerHeight <= 0) {
      containerHeight = parseInt(props.height, 10)
    }

    if (containerWidth <= 0 || containerHeight <= 0) {
      console.error('无法获取有效容器尺寸，图表可能无法正确渲染')
      // 可以在这里设置一个默认的最小尺寸，以防完全无法渲染
      if (chartContainer.value) {
        if (containerWidth <= 0) chartContainer.value.style.width = '100%'
        if (containerHeight <= 0) chartContainer.value.style.height = '300px' // 降级到固定高度
      }
      await nextTick()
      containerWidth = chartContainer.value.clientWidth
      containerHeight = chartContainer.value.clientHeight
    }

    // 创建新图表，使用显式尺寸
    const opts = {
      width: containerWidth || undefined,
      height: containerHeight || undefined,
      renderer: 'canvas' as const
    }
    const existChart = echarts.getInstanceByDom(chartContainer.value)
    if (existChart) {
      existChart.dispose()
    }
    chart.value = echarts.init(chartContainer.value, props.theme, opts)

    // 设置基础配置
    const baseOption = {
      animation: true,
      animationDuration: 1000,
      animationEasing: 'cubicOut',
      backgroundColor: props.styleConfig?.backgroundColor || 'transparent',
      color: props.styleConfig?.seriesColors || ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399'],
      grid: {
        ...props.gridConfig,
        top: props.styleConfig?.padding?.top || props.gridConfig?.top || '15%',
        right: props.styleConfig?.padding?.right || props.gridConfig?.right || '4%',
        bottom: props.styleConfig?.padding?.bottom || props.gridConfig?.bottom || '10%',
        left: props.styleConfig?.padding?.left || props.gridConfig?.left || '3%',
        containLabel: true
      },
      legend: {
        ...props.legendConfig,
        show: props.styleConfig?.showLegend !== false,
        [props.styleConfig?.legendPosition || 'top']: '5%',
        textStyle: {
          fontSize: props.styleConfig?.fontSize || 12,
          color: props.styleConfig?.textColor || '#333'
        }
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: props.styleConfig?.tooltipBackgroundColor || 'rgba(50, 50, 50, 0.9)',
        borderColor: '#333',
        borderWidth: 1,
        textStyle: {
          color: props.styleConfig?.tooltipTextColor || '#fff',
          fontSize: props.styleConfig?.fontSize || 12
        },
        formatter: '{b}<br/>{a}: {c}'
      },
      xAxis: {
        type: 'category',
        boundaryGap: props.chartType === 'bar',
        axisLine: {
          lineStyle: {
            color: props.styleConfig?.axisLineColor || '#e0e0e0'
          }
        },
        axisLabel: {
          color: props.styleConfig?.axisLabelColor || '#666',
          fontSize: props.styleConfig?.axisLabelFontSize || 11
        },
        splitLine: {
          show: false
        }
      },
      yAxis: {
        type: 'value',
        axisLine: {
          show: false
        },
        axisTick: {
          show: false
        },
        axisLabel: {
          color: props.styleConfig?.axisLabelColor || '#666',
          fontSize: props.styleConfig?.axisLabelFontSize || 11
        },
        splitLine: {
          show: props.styleConfig?.showGridLine !== false,
          lineStyle: {
            color: props.styleConfig?.gridLineColor || '#f0f0f0',
            type: props.styleConfig?.gridLineType || 'dashed'
          }
        }
      }
    }

    try {
      // 设置基础配置时添加错误捕获
      try {
        chart.value.setOption(baseOption as any)
      } catch (error) {
        // 静默处理 ECharts 内部错误，避免控制台报错
        if (error instanceof Error && error.message.includes('Cannot read properties of undefined')) {
          // 忽略这个特定错误
          console.warn('ECharts 内部错误已忽略:', error.message)
        } else {
          throw error // 重新抛出其他错误
        }
      }

      // 触发图表就绪事件
      emit('chartReady', chart.value)
      console.log('图表初始化完成')
      
      // 初始化完成后更新加载状态 - 修复点
      internalLoading.value = false

    } catch (error) {
      console.error('图表初始化失败:', error)
      ElMessage.error('图表初始化失败')
      // 出错时也要更新加载状态
      internalLoading.value = false
    }
  } catch (error) {
    console.error('图表初始化失败:', error)
    ElMessage.error('图表初始化失败')
    // 出错时也要更新加载状态
    internalLoading.value = false
  }
}

// 设置图表事件监听
const setupChartEvents = () => {
  if (!chart.value) return

  // 监听窗口大小变化
  const resizeHandler = () => {
    if (chart.value) {
      chart.value.resize()
    }
  }

  // 添加被动选项
  window.addEventListener('resize', resizeHandler, { passive: true })

  // 组件卸载时移除监听 - 移动到 onUnmounted 钩子中
  return () => {
    window.removeEventListener('resize', resizeHandler)
  }
}

// 更新图表数据
const echartsSeriesTypes = ['line', 'bar', 'pie', 'scatter', 'effectScatter', 'radar', 'tree',
  'treemap', 'sunburst', 'boxplot', 'candlestick', 'heatmap', 'map', 'parallel', 'lines',
  'graph', 'sankey', 'funnel', 'gauge', 'pictorialBar', 'themeRiver', 'custom'];

const updateChart = (option: any) => {
  // 如果图表实例不存在，先初始化图表
  if (!chart.value) {
    console.warn('图表实例不存在，尝试初始化图表')
    initChart().then(() => {
      // 初始化完成后再次调用 updateChart
      if (chart.value && option) {
        updateChart(option)
      }
    })
    return
  }

  // 验证基础配置项
  if (!option || typeof option !== 'object') {
    console.warn('图表配置项无效:', option)
    return
  }

  try {
    // 设置内部加载状态
    internalLoading.value = true

    // 深度克隆选项避免污染原始数据
    const clonedOption = JSON.parse(JSON.stringify(option))

    // **关键修复：合并样式配置**
    // 应用样式配置到图表选项
    if (props.styleConfig) {
      // 合并网格配置
      if (!clonedOption.grid) clonedOption.grid = {}
      clonedOption.grid = {
        ...clonedOption.grid,
        top: props.styleConfig.padding?.top || clonedOption.grid.top || '15%',
        right: props.styleConfig.padding?.right || clonedOption.grid.right || '4%',
        bottom: props.styleConfig.padding?.bottom || clonedOption.grid.bottom || '10%',
        left: props.styleConfig.padding?.left || clonedOption.grid.left || '3%',
        containLabel: true
      }

      // 合并背景色
      if (props.styleConfig.backgroundColor) {
        clonedOption.backgroundColor = props.styleConfig.backgroundColor
      }

      // 合并颜色配置
      if (props.styleConfig.seriesColors) {
        clonedOption.color = props.styleConfig.seriesColors
      }

      // 合并图例配置
      if (!clonedOption.legend) clonedOption.legend = {}
      clonedOption.legend = {
        ...clonedOption.legend,
        show: props.styleConfig.showLegend !== false,
        [props.styleConfig.legendPosition || 'top']: '5%',
        textStyle: {
          fontSize: props.styleConfig.fontSize || 12,
          color: props.styleConfig.textColor || '#333'
        }
      }

      // 合并提示框配置
      if (!clonedOption.tooltip) clonedOption.tooltip = {}
      clonedOption.tooltip = {
        ...clonedOption.tooltip,
        trigger: 'axis',
        backgroundColor: props.styleConfig.tooltipBackgroundColor || 'rgba(50, 50, 50, 0.9)',
        borderColor: '#333',
        borderWidth: 1,
        textStyle: {
          color: props.styleConfig.tooltipTextColor || '#fff',
          fontSize: props.styleConfig.fontSize || 12
        }
      }

      // 合并X轴配置
      if (!clonedOption.xAxis) clonedOption.xAxis = {}
      if (Array.isArray(clonedOption.xAxis)) {
        clonedOption.xAxis.forEach(axis => {
          if (!axis.axisLine) axis.axisLine = {}
          axis.axisLine.lineStyle = {
            color: props.styleConfig.axisLineColor || '#e0e0e0'
          }
          if (!axis.axisLabel) axis.axisLabel = {}
          axis.axisLabel = {
            ...axis.axisLabel,
            color: props.styleConfig.axisLabelColor || '#666',
            fontSize: props.styleConfig.axisLabelFontSize || 11
          }
        })
      } else {
        if (!clonedOption.xAxis.axisLine) clonedOption.xAxis.axisLine = {}
        clonedOption.xAxis.axisLine.lineStyle = {
          color: props.styleConfig.axisLineColor || '#e0e0e0'
        }
        if (!clonedOption.xAxis.axisLabel) clonedOption.xAxis.axisLabel = {}
        clonedOption.xAxis.axisLabel = {
          ...clonedOption.xAxis.axisLabel,
          color: props.styleConfig.axisLabelColor || '#666',
          fontSize: props.styleConfig.axisLabelFontSize || 11
        }
      }

      // 合并Y轴配置
      if (!clonedOption.yAxis) clonedOption.yAxis = {}
      if (Array.isArray(clonedOption.yAxis)) {
        clonedOption.yAxis.forEach(axis => {
          if (!axis.axisLabel) axis.axisLabel = {}
          axis.axisLabel = {
            ...axis.axisLabel,
            color: props.styleConfig.axisLabelColor || '#666',
            fontSize: props.styleConfig.axisLabelFontSize || 11
          }
          if (!axis.splitLine) axis.splitLine = {}
          axis.splitLine = {
            show: props.styleConfig.showGridLine !== false,
            lineStyle: {
              color: props.styleConfig.gridLineColor || '#f0f0f0',
              type: props.styleConfig.gridLineType || 'dashed'
            }
          }
          if (!axis.nameTextStyle) axis.nameTextStyle = {}
          axis.nameTextStyle = {
            color: props.styleConfig.textColor || '#666',
            fontSize: props.styleConfig.fontSize || 12
          }
        })
      } else {
        if (!clonedOption.yAxis.axisLabel) clonedOption.yAxis.axisLabel = {}
        clonedOption.yAxis.axisLabel = {
          ...clonedOption.yAxis.axisLabel,
          color: props.styleConfig.axisLabelColor || '#666',
          fontSize: props.styleConfig.axisLabelFontSize || 11
        }
        if (!clonedOption.yAxis.splitLine) clonedOption.yAxis.splitLine = {}
        clonedOption.yAxis.splitLine = {
          show: props.styleConfig.showGridLine !== false,
          lineStyle: {
            color: props.styleConfig.gridLineColor || '#f0f0f0',
            type: props.styleConfig.gridLineType || 'dashed'
          }
        }
        if (!clonedOption.yAxis.nameTextStyle) clonedOption.yAxis.nameTextStyle = {}
        clonedOption.yAxis.nameTextStyle = {
          color: props.styleConfig.textColor || '#666',
          fontSize: props.styleConfig.fontSize || 12
        }
      }

      // 合并系列配置
      if (clonedOption.series && Array.isArray(clonedOption.series)) {
        clonedOption.series.forEach((series, index) => {
          // 应用线条样式
          if (series.type === 'line') {
            if (!series.lineStyle) series.lineStyle = {}
            series.lineStyle = {
              ...series.lineStyle,
              width: props.styleConfig.lineWidth || 2,
              color: props.styleConfig.seriesColors?.[index] || series.lineStyle.color
            }
            
            // 应用区域填充样式
            if (props.styleConfig.areaStyle) {
              series.areaStyle = {
                opacity: props.styleConfig.areaStyle.opacity || 0.1,
                color: props.styleConfig.areaStyle.colorStops ? {
                  type: 'linear',
                  x: 0, y: 0, x2: 0, y2: 1,
                  colorStops: props.styleConfig.areaStyle.colorStops
                } : undefined
              }
            }
          }
          
          // 应用标题样式
          if (props.styleConfig.titleStyle && clonedOption.title) {
            if (!clonedOption.title.textStyle) clonedOption.title.textStyle = {}
            clonedOption.title.textStyle = {
              ...clonedOption.title.textStyle,
              fontSize: props.styleConfig.titleStyle.fontSize || 16,
              fontWeight: props.styleConfig.titleStyle.fontWeight || 'normal',
              color: props.styleConfig.titleStyle.color || props.styleConfig.textColor || '#333'
            }
          }
        })
      }
    }

    // ... 其余的验证和设置逻辑保持不变
    // 确保基础结构存在
    if (!clonedOption.series) {
      clonedOption.series = []
    }

    // 强化 series 校验 - 只进行一次过滤
    if (Array.isArray(clonedOption.series)) {
      clonedOption.series = clonedOption.series
        .filter(s => {
          // 验证 series 基础结构
          if (!s || typeof s !== 'object') return false
          
          // 验证 type 属性
          if (!s.type || typeof s.type !== 'string') {
            console.warn('Series 缺少有效的 type 属性:', s)
            return false
          }
          
          // 验证 type 是否为支持的类型
          if (!echartsSeriesTypes.includes(s.type)) {
            console.warn('不支持的 series type:', s.type)
            return false
          }
          
          // 验证 data 属性
          if (!Array.isArray(s.data)) {
            console.warn('Series data 不是数组:', s)
            return false
          }
          
          return true
        })
        .map(s => ({
          ...s,
          // 确保 data 格式合法，过滤 null/undefined 值
          data: s.data.filter(d => d !== null && d !== undefined)
        }))
    }

    // 验证是否有有效的 series
    if (!clonedOption.series || clonedOption.series.length === 0) {
      console.warn('没有有效的 series 配置，显示空图表')
      
      // 显示空图表而不是报错
      const emptyOption = {
        title: clonedOption.title || {},
        xAxis: clonedOption.xAxis || { type: 'category', data: [] },
        yAxis: clonedOption.yAxis || { type: 'value' },
        series: []
      }
      
      chart.value.clear()
      chart.value.setOption(emptyOption, { notMerge: true })
      return
    }

    // 确保其他必要配置项存在
    if (!clonedOption.xAxis) {
      clonedOption.xAxis = { type: 'category', data: [] }
    }
    if (!clonedOption.yAxis) {
      clonedOption.yAxis = { type: 'value' }
    }

    // 安全地设置图表选项
    try {
      chart.value.clear()
      chart.value.setOption(clonedOption, { notMerge: true })
      
      // 确保图表正确渲染
      nextTick(() => {
        if (chart.value) {
          // 检查图表容器尺寸并调整
          if (chart.value.getWidth() === 0 || chart.value.getHeight() === 0) {
            console.warn('图表尺寸为0，尝试调整大小')
            chart.value.resize()
          }
          
          // 强制重绘图表
          chart.value.resize()
          
          // 数据渲染成功后更新加载状态
          console.log('图表数据渲染完成')
        }
      })
      internalLoading.value = false
    } catch (setOptionError) {
      console.error('ECharts setOption 失败:', setOptionError)
      
      // 如果是类型错误，尝试使用更安全的配置
      if (setOptionError instanceof TypeError) {
        console.warn('尝试使用安全配置重新渲染图表')
        const safeOption = {
          title: { text: '图表加载失败' },
          xAxis: { type: 'category', data: [] },
          yAxis: { type: 'value' },
          series: []
        }
        chart.value.clear()
        chart.value.setOption(safeOption, { notMerge: true })
      }
      
      // 出错时也要更新加载状态
      internalLoading.value = false
    }
    
  } catch (error) {
    console.error('图表更新失败:', error)
    ElMessage.error('图表更新失败')
    // 出错时也要更新加载状态
    internalLoading.value = false
  }
}

// 监听数据就绪状态 - 修改逻辑
watch(() => props.dataReady, (newVal) => {
  if (newVal && !chart.value) {
    console.log('数据准备就绪，开始初始化图表')
    nextTick(() => {
      initChart()
    })
  } else if (newVal && chart.value) {
    // 如果图表已存在且数据准备就绪，更新加载状态
    internalLoading.value = false
  }
})

// 监听loading状态变化 - 修改逻辑
watch(() => props.loading, (newVal, oldVal) => {
  if (chart.value) {
    if (newVal) {
      chart.value.showLoading()
    } else {
      chart.value.hideLoading()
      nextTick(() => {
        if (chart.value) {
          chart.value.resize()
          // 外部loading结束时，如果数据已准备就绪，更新内部loading状态
          if (props.dataReady) {
            internalLoading.value = false
          }
        }
      })
    }
  }
})

// 导出图表
const exportChart = () => {
  if (!chart.value) return

  try {
    const url = chart.value.getDataURL({
      type: 'png',
      backgroundColor: '#fff',
      pixelRatio: 2
    })

    const link = document.createElement('a')
    link.download = `${props.title || 'chart'}-${new Date().getTime()}.png`
    link.href = url
    link.click()

    emit('export')
  } catch (error) {
    console.error('图表导出失败:', error)
    ElMessage.error('图表导出失败')
  }
}

// 全屏切换
const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
  emit('fullscreen')

  nextTick(() => {
    if (chart.value) {
      chart.value.resize()
    }
  })
}

// 刷新图表
const refreshChart = () => {
  internalLoading.value = true
  emit('refresh')

  setTimeout(() => {
    internalLoading.value = false
  }, 500)
}

// 时间范围变化
const handleTimeRangeChange = (value: number) => {
  currentTimeRange.value = value
  emit('timeRangeChange', value)
}

// 获取图表实例（供外部使用）
const getChartInstance = () => chart.value

// 暴露方法给父组件
defineExpose({
  updateChart,
  getChartInstance,
  refreshChart,
  exportChart,
  toggleFullscreen
})

// 监听props变化
watch(() => props.loading, (newVal) => {
  if (chart.value) {
    if (newVal) {
      chart.value.showLoading()
    } else {
      chart.value.hideLoading()
    }
  }
})

watch(() => props.error, (newVal) => {
  if (newVal && chart.value) {
    chart.value.hideLoading()
  }
})

let cleanupChartEvents: (() => void) | null = null

// 生命周期
onMounted(async () => {
  // 确保DOM完全渲染
  await nextTick()

  // 只有在数据准备就绪时才初始化图表
  if (props.dataReady) {
    requestAnimationFrame(async () => {
      setTimeout(async () => {
        await initChart()
        if (chart.value) {
          const cleanup = setupChartEvents()
          if (cleanup) {
            cleanupChartEvents = cleanup
          }
        }
      }, 100)
    })
  } else {
    console.log('组件已挂载，等待数据准备就绪')
  }
})

onUnmounted(() => {
  if (cleanupChartEvents) {
    cleanupChartEvents()
  }
  if (chart.value) {
    chart.value.dispose()
  }
})
</script>

<template>
  <div class="base-chart" :class="{ 'fullscreen': isFullscreen }">
    <!-- 图表头部 -->
    <div v-if="!hideTitle && !hideControls && (title || showTimeRange || showRefresh || showExport || showFullscreen)" class="chart-header">
      <div class="chart-title">
        <span v-if="!hideTitle && title">{{ title }}</span>
      </div>

      <div v-if="!hideControls" class="chart-controls">
        <!-- 时间范围选择 -->
        <el-select v-if="showTimeRange" v-model="currentTimeRange" size="small" style="width: 120px;"
          @change="handleTimeRangeChange">
          <el-option v-for="option in timeOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>

        <!-- 控制按钮 -->
        <div class="chart-buttons">
          <el-button v-if="showRefresh" size="small" :icon="Refresh" @click="refreshChart" :loading="internalLoading" />
          <el-button v-if="showExport" size="small" :icon="Download" @click="exportChart" />
          <el-button v-if="showFullscreen" size="small" :icon="FullScreen" @click="toggleFullscreen" />
        </div>
      </div>
    </div>

    <!-- 图表容器 -->
    <div 
      class="chart-content" 
      v-loading="internalLoading"
    >
      <div ref="chartContainer" :style="containerStyle" class="chart-container" />

      <!-- 错误状态 -->
      <div v-if="error" class="chart-error">
        <el-empty :description="error" :image-size="100">
          <el-button type="primary" @click="refreshChart">
            <el-icon>
              <Refresh />
            </el-icon>
            重试
          </el-button>
        </el-empty>
      </div>

      <!-- 无数据状态 -->
      <div v-if="!loading && !error && showEmpty && dataReady" class="chart-empty">
        <el-empty description="暂无数据" :image-size="100" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.base-chart {
  background: transparent;
  border-radius: 0;
  box-shadow: none;
  overflow: hidden;
  transition: all 0.3s ease;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  /* 增加左右内边距 */
  border-bottom: none;
  background: transparent;
}

.chart-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px 12px;
  /* 增加下边距 */
  padding-left: 4px;
  border-left: 4px solid var(--el-color-primary);
}

.chart-header {
  padding: 16px 20px 16px 28px;
  /* 增大左侧内边距 */
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: none;
  background: transparent;
}

.chart-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chart-buttons {
  display: flex;
  gap: 8px;
}

.chart-content {
  position: relative;
}

.chart-container {
  width: 100%;
}

.chart-error,
.chart-empty {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  z-index: 10;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chart-header {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .chart-controls {
    justify-content: space-between;
  }

  .chart-buttons {
    flex-shrink: 0;
  }
}
</style>