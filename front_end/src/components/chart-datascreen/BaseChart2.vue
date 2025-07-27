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
    top: '15%',
    right: '5%',
    bottom: '10%',
    left: '12%',
    containLabel: true
  }),
  legendConfig: () => ({
    show: true,
    top: 'top',
    textStyle: {
      fontSize: 12,
      color: '#e0f2fe'
    }
  })
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
  width: '100%',
  height: '100%',
  minHeight: '250px', // 与 chart-inner-container 保持一致
  position: 'relative'
}));

const loadingState = computed(() => props.loading || internalLoading.value)

// 初始化图表
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


    // 设置基础配置
    const baseOption = {
      backgroundColor: 'transparent',
      color: ['#22d3ee', '#a78bfa'],
      animation: true,
      animationDuration: 1000,
      animationEasing: 'cubicOut',
      grid: props.gridConfig,
      legend: props.legendConfig,
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        borderColor: '#333',
        borderWidth: 1,
        textStyle: {
          color: '#f0f9ff',
          fontSize: 12
        },
        formatter: '{b}<br/>{a}: {c}'
      },
      xAxis: {
        type: 'category',
        boundaryGap: props.chartType === 'bar',
        axisLine: {
          lineStyle: {
            color: 'rgba(56, 189, 248, 0.5)'
          }
        },
        axisLabel: {
          color: '#a5f3fc',
          fontSize: 11
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: 'rgba(56, 189, 248, 0.1)',
            type: 'dashed'
          }
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
          color: '#a5f3fc',
          fontSize: 11
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: 'rgba(56, 189, 248, 0.1)',
            type: 'dashed'
          }
        }
      },
      series: [] // 将 series 的默认配置移到 setOption 中
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
  if (!chart.value) return;

  try {
    // 深度克隆选项避免污染原始数据
    const clonedOption = JSON.parse(JSON.stringify(option));

    // 强化series校验
    if (clonedOption?.series) {
      clonedOption.series = clonedOption.series
        .filter(s =>
          s &&
          typeof s.type === 'string' &&
          echartsSeriesTypes.includes(s.type) &&
          Array.isArray(s.data) &&
          s.data.length > 0
        )
        .map(s => ({
          ...s,
          // 确保data格式合法
          data: s.data.filter(d => d !== null && d !== undefined)
        }));

      if (clonedOption.series.length === 0) {
        throw new Error('无效图表数据：无有效series配置');
      }
    }

    // 先清除旧配置再渲染时添加错误捕获
    try {
      chart.value.clear();
      chart.value.setOption(clonedOption, { notMerge: true });
    } catch (error) {
      // 静默处理 ECharts 内部错误
      if (error instanceof Error && error.message.includes('Cannot read properties of undefined')) {
        console.warn('ECharts setOption 错误已忽略:', error.message)
        return // 直接返回，不继续执行
      } else {
        throw error
      }
    }

    // 检查图表容器尺寸
    if (chart.value.getWidth() === 0 || chart.value.getHeight() === 0) {
      console.warn('图表尺寸为0，尝试调整大小')
      chart.value.resize()
    }

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
      // 检查选项是否包含必要的数据
      if (option && option.series && Array.isArray(option.series) && option.series.length > 0 &&
        option.series.some(s => s && Array.isArray(s.data) && s.data.length > 0)) {

        // 确保图表可见
        if (chartContainer.value) {
          chartContainer.value.style.visibility = 'visible'
        }
        // 过滤无效的 series 项，增加对 type 的检查
        if (Array.isArray(option.series)) {
          option.series = option.series.filter(s => s && typeof s.type === 'string' && Array.isArray(s.data))
        }

        // 使用notMerge: true确保完全重新渲染
        chart.value.setOption(option, { notMerge: true })

        // 强制重绘
        setTimeout(() => {
          if (chart.value) {
            chart.value.resize()
          }
        }, 50)
      } else {
        console.warn('图表选项缺少有效数据:', option)
        // 显示无数据提示
        if (props.showEmpty) {
          const emptyOption: any = {
            title: option?.title || {},
            xAxis: option?.xAxis || { type: 'category', data: [] },
            yAxis: option?.yAxis || { type: 'value' },
            series: []
          }
          chart.value.setOption(emptyOption, true)
        }
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
    <!-- 图表头部 -->
    <div v-if="title || showTimeRange || showRefresh || showExport || showFullscreen" class="section-header">
      <div class="subtitle">
        <span v-if="title">{{ title }}</span>
      </div>
      <div class="chart-buttons">
        <!-- 时间范围选择 -->
        <el-select v-if="showTimeRange" v-model="currentTimeRange" size="small" style="width: 120px;"
          @change="handleTimeRangeChange">
          <el-option v-for="option in timeOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
        <el-button v-if="showRefresh" size="small" :icon="Refresh" type="primary" @click="refreshChart" :loading="loadingState" />

      </div>
    </div>
    <!-- 控制按钮 -->

    <!-- 图表容器 -->
    <div class="chart-content">
      <div ref="chartContainer" :style="{
        width: '100%',
        height: '100%',
        minHeight: '300px',
        position: 'relative' as const
      }" class="chart-container"></div>

      <!-- 错误状态 -->
      <div v-if="error" class="chart-error">
        <el-empty :description="error || '未知错误'" :image-size="100">
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
  padding: 10px 15px;
  /* 减小内边距 */
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: none;
  background: transparent;
  flex-wrap: wrap;
  /* 允许在小屏幕上换行 */
}

.chart-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 0px 0px;
  /* 增加下边距 */
  padding-left: 4px;
  border-left: 4px solid var(--el-color-primary);
}

.chart-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-buttons {
  display: flex;
  gap: 4px;
}

.chart-content {
  position: relative;
  width: 100%;
  height: 100%;
  /* 确保内容填满容器 */
  display: flex;
  flex-direction: column;
  /* 垂直布局 */
  justify-content: center;
  /* 垂直居中内容 */
  align-items: center;
  /* 水平居中内容 */
  box-sizing: border-box;
  /* 包含内边距 */
}

.chart-container {
  width: 100%;
  height: 100%;
  /* 确保图表容器填满内容区域 */
  display: flex;
  flex: 1;
  /* 使图表容器扩展到父容器的剩余空间 */
  overflow: hidden;
  /* 防止内容溢出 */
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

.section-header {
  margin-bottom: 6px;
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;

  gap: 10px;

}

.section-header h2 {
  font-size: 0.95rem;
  margin: 0;
  white-space: nowrap;

}

.subtitle {
  font-size: 1rem;
  color: #94a3b8;
  position: relative;
  padding-left: 10px;

}


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
</style>