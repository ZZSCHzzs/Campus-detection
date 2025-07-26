<script lang="ts" setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { Refresh, Download, FullScreen, Calendar } from '@element-plus/icons-vue'

// Props定义
interface Props {
  title?: string
  height?: string
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
  }
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  height: '400px',
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
  hideControls: false
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
const containerStyle = computed(() => ({
  height: props.height,
  width: '100%',
  position: 'relative' as const
}))

const loadingState = computed(() => props.loading || internalLoading.value)

// 初始化图表
const initChart = async () => {
  if (!chartContainer.value) {
    console.warn('图表容器不存在')
    return
  }

  try {
    // 销毁已存在的图表
    if (chart.value) {
      chart.value.dispose()
      chart.value = undefined // 显式设为undefined
    }

    // 强制等待一帧以确保DOM完全渲染
    await new Promise(resolve => requestAnimationFrame(resolve))
    // 额外添加一个短暂延迟，确保弹窗完全展开
    await new Promise(resolve => setTimeout(resolve, 50))

    // 检查容器尺寸
    const containerWidth = chartContainer.value.clientWidth
    const containerHeight = chartContainer.value.clientHeight


    if (containerWidth <= 0 || containerHeight <= 0) {
      console.warn('图表容器尺寸异常，尝试修复')
      // 尝试设置明确的尺寸
      chartContainer.value.style.height = props.height
      chartContainer.value.style.width = '100%'
      chartContainer.value.style.minHeight = '300px' // 添加最小高度

      // 再次检查尺寸
      await nextTick()
      const newWidth = chartContainer.value.clientWidth
      const newHeight = chartContainer.value.clientHeight

      if (newWidth <= 0 || newHeight <= 0) {
        console.error('无法修复容器尺寸，图表可能无法正确渲染')
        // 设置固定像素尺寸作为最后尝试
        chartContainer.value.style.height = '400px'
        chartContainer.value.style.width = '100%'
        await nextTick()
      }
    }

    // 创建新图表，使用显式尺寸
    const opts = {
      width: chartContainer.value.clientWidth || undefined,
      height: chartContainer.value.clientHeight || undefined,
      renderer: 'canvas' as const
    }
    const existChart = echarts.getInstanceByDom(chartContainer.value)
    if (existChart) {
      existChart.dispose()
    }
    chart.value = echarts.init(chartContainer.value, props.theme, opts)


    // 设置基础配置 - 应用样式配置
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
    } catch (error) {
      console.error('图表初始化失败:', error)
      ElMessage.error('图表初始化失败')
    }
  }
  catch (error) {
    console.error('图表初始化失败:', error)
    ElMessage.error('图表初始化失败')
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
  if (!chart.value) {
    console.warn('图表实例不存在，跳过更新')
    return
  }

  // 验证基础配置项
  if (!option || typeof option !== 'object') {
    console.warn('图表配置项无效:', option)
    return
  }

  try {
    // 深度克隆选项避免污染原始数据
    const clonedOption = JSON.parse(JSON.stringify(option))

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
      
      // 处理加载状态
      if (loadingState.value) {
        chart.value.showLoading({
          text: '加载中...',
          color: '#409EFF',
          textColor: '#409EFF',
          maskColor: 'rgba(255, 255, 255, 0.8)',
          zlevel: 0,
          fontSize: 12,
          showSpinner: true,
          spinnerRadius: 10,
          lineWidth: 2
        })
      } else {
        chart.value.hideLoading()
      }
      
      // 检查图表容器尺寸并调整
      nextTick(() => {
        if (chart.value && (chart.value.getWidth() === 0 || chart.value.getHeight() === 0)) {
          console.warn('图表尺寸为0，尝试调整大小')
          chart.value.resize()
        }
      })
      
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
    }
    
  } catch (error) {
    console.error('图表更新失败:', error)
    ElMessage.error('图表更新失败')
  }
}

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
  // 移除错误屏蔽相关代码
  // console.error = filteredConsoleError
  // window.addEventListener('error', handleGlobalError, true)
  // window.addEventListener('unhandledrejection', handleUnhandledRejection, true)
  
  // 确保DOM完全渲染
  await nextTick()

  // 使用requestAnimationFrame确保浏览器已完成布局
  requestAnimationFrame(async () => {
    // 添加短暂延迟，进一步确保DOM稳定
    setTimeout(async () => {
      await initChart()
      if (chart.value) {
        const cleanup = setupChartEvents()
        if (cleanup) {
          cleanupChartEvents = cleanup
        }
      }

      // 如果图表初始化后宽度为0，尝试再次初始化
      if (chart.value && chart.value.getWidth() === 0) {
        console.warn('图表宽度为0，尝试重新初始化')
        setTimeout(async () => {
          await initChart()
          if (chart.value && !cleanupChartEvents) {
            const cleanup = setupChartEvents();
            if (cleanup) {
              cleanupChartEvents = cleanup;
            }
          }
        }, 200)
      }
    }, 100)
  })
})

onUnmounted(() => {
  // 移除错误处理恢复相关代码
  // console.error = originalConsoleError
  // window.removeEventListener('error', handleGlobalError, true)
  // window.removeEventListener('unhandledrejection', handleUnhandledRejection, true)
  
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
    <!-- 图表头部 - 修改显示条件 -->
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
          <el-button v-if="showRefresh" size="small" :icon="Refresh" @click="refreshChart" :loading="loadingState" />

          <el-button v-if="showExport" size="small" :icon="Download" @click="exportChart" />

          <el-button v-if="showFullscreen" size="small" :icon="FullScreen" @click="toggleFullscreen" />
        </div>
      </div>
    </div>

    <!-- 图表容器 -->
    <div class="chart-content">
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
      <div v-if="!loading && !error && showEmpty" class="chart-empty">
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