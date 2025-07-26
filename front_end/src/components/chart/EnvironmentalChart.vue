<script lang="ts" setup>
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import BaseChart from './BaseChart.vue'
import { areaService, temperatureHumidityService, co2Service, terminalService } from '../../services'
import type { TemperatureHumidityData, CO2Data } from '../../types.ts'

// Props定义
interface Props {
  areaId?: number
  terminalId?: number
  dataType: 'temperature' | 'humidity' | 'co2' | 'temperature-humidity'
  height?: string
  width?: string
  showControls?: boolean
  hideTitle?: boolean
  hideControls?: boolean
  // 样式配置 - 完全依赖外部传入
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
    // 新增 areaStyle 类型定义
    areaStyle?: {
      opacity?: number
      colorStops?: Array<{ offset: number; color: string }>
    }
  }
}

const props = withDefaults(defineProps<Props>(), {
  width: '100%',
  showControls: true,
  hideTitle: false,
  hideControls: false,
  areaId: 2,
  styleConfig: () => ({})
})

// 新增emit定义
const emit = defineEmits<{
  timeRangeChange: [value: number]
}>()

// 状态管理
const loading = ref(false)
const error = ref<string | null>(null)
const currentTimeRange = ref(24)
const temperatureHumidityData = ref<TemperatureHumidityData[]>([])
const co2Data = ref<CO2Data[]>([])
const currentAreaName = ref('')

// 计算属性
const chartTitle = computed(() => {
  const typeLabels = {
    'temperature': '温度趋势',
    'humidity': '湿度趋势', 
    'co2': 'CO2浓度',
    'temperature-humidity': '温湿度数据'
  }
  
  const baseTitle = typeLabels[props.dataType] || '环境数据'
  
  if (props.dataType === 'co2' && props.terminalId) {
    return `终端${props.terminalId} - ${baseTitle}`
  } else if (currentAreaName.value) {
    return `${currentAreaName.value} - ${baseTitle}`
  }
  
  return baseTitle
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

// 获取环境数据
const fetchEnvironmentalData = async (areaId?: number, terminalId?: number, hours = 24) => {
  try {
    loading.value = true;
    error.value = null;
    
    if (areaId) {
      currentAreaName.value = await fetchAreaName(areaId);
    }

    if (props.dataType === 'co2' && terminalId) {
      try {
        const data = await terminalService.getTerminalCO2Data(terminalId, hours);
        if (data && data.length > 0) {
          const validData = data.filter(item => 
            item && item.timestamp && item.co2_level !== undefined && item.co2_level !== null
          );
          
          if (validData.length > 0) {
            co2Data.value = validData.sort((a, b) => 
              new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
            );
            // 移除成功日志
            updateChart();
            return;
          }
        }
      } catch (apiError) {
        // 保留错误日志
        console.error('终端CO2 API失败:', apiError);
        // 尝试使用通用CO2服务
        try {
          const data = await co2Service.getByTerminal(terminalId, hours);
          if (data && data.length > 0) {
            // 验证数据格式
            const validData = data.filter(item => 
              item && item.timestamp && item.co2_level !== undefined && item.co2_level !== null
            );
            
            if (validData.length > 0) {
              co2Data.value = validData.sort((a, b) => 
                new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
              );
             // 立即更新图表
              updateChart();
              return;
            } else {
              console.warn('备用API获取到的CO2数据没有有效记录');
              throw new Error('CO2数据格式无效');
            }
          }
        } catch (fallbackError) {
          console.error('所有CO2数据获取方式均失败:', fallbackError);
          throw new Error('CO2数据获取失败');
        }
      }
    }
    
    if (areaId) {
      try {
        // 尝试使用区域API获取温湿度数据
        const data = await areaService.getAreaTemperatureHumidity(areaId, hours)
        if (data && data.length > 0) {
          temperatureHumidityData.value = data.sort((a, b) => 
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          )
          // 立即更新图表
          updateChart()
          return
        }
      } catch (apiError) {

        // 尝试使用通用温湿度服务
        try {
          const data = await temperatureHumidityService.getByArea(areaId, hours)
          if (data && data.length > 0) {
            temperatureHumidityData.value = data.sort((a, b) => 
              new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
            )
           // 立即更新图表
            updateChart()
            return
          }
        } catch (fallbackError) {
          throw new Error('温湿度数据获取失败')
        }
      }
    }
    
    // 如果没有数据，清空数组但不报错
    if (props.dataType === 'co2') {
      co2Data.value = []
      // 如果是CO2数据且没有获取到任何数据，设置提示信息
      if (terminalId) {
        error.value = '暂无CO2数据，传感器可能未连接或配置未启用'
      }
    } else {
      temperatureHumidityData.value = []
      // 如果是温湿度数据且没有获取到任何数据，设置提示信息
      if (areaId) {
        error.value = '暂无温湿度数据'
      }
    }
    console.log('没有获取到数据，使用空数组')
    
  } catch (err: any) {
    error.value = err.message || '获取环境数据失败';
    console.error('获取环境数据失败:', err);
  } finally {
    loading.value = false;
  }
}

// 生成图表配置
const generateChartOption = () => {
  if (props.dataType === 'co2') {
    return generateCO2ChartOption()
  } else {
    return generateTemperatureHumidityChartOption()
  }
}

// 生成CO2图表配置 - 纯数据结构，无样式
const generateCO2ChartOption = () => {
  // 检查数据是否有效
  if (!co2Data.value || co2Data.value.length === 0) {
    return {
      title: {
        text: '当前浓度：-- ppm',
        right: '5%',
        top: '2%'
      },
      xAxis: {
        type: 'category',
        data: []
      },
      yAxis: {
        name: 'CO2浓度 (ppm)'
      },
      series: [{
        name: 'CO2浓度',
        type: 'line',
        data: [],
        smooth: true
      }]
    }
  }
  
  // 数据处理和验证
  const validData = co2Data.value.filter(item => 
    item && item.timestamp && item.co2_level !== undefined && item.co2_level !== null
  )
  
  if (validData.length === 0) {
    return {
      title: {
        text: '当前浓度：-- ppm',
        right: '5%',
        top: '2%'
      },
      xAxis: {
        type: 'category',
        data: []
      },
      yAxis: {
        name: 'CO2浓度 (ppm)'
      },
      series: [{
        name: 'CO2浓度',
        type: 'line',
        data: [],
        smooth: true
      }]
    }
  }
  
  const times = validData.map(item => 
    new Date(item.timestamp).toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  )
  
  const values = validData.map(item => item.co2_level)
  
  // 检查最后一个值是否有效
  const lastValue = values[values.length - 1]
  const currentValue = lastValue !== undefined && lastValue !== null ? lastValue : '--'

  // 纯数据结构，不包含任何样式
  return {
    title: {
      text: '当前浓度：' + currentValue + ' ppm',
      right: '5%',
      top: '2%'
    },
    xAxis: {
      type: 'category',
      data: times
    },
    yAxis: {
      name: 'CO2浓度 (ppm)'
    },
    series: [{
      name: 'CO2浓度',
      type: 'line',
      data: values,
      smooth: true
    }]
  }
}

// 生成温湿度图表配置 - 纯数据结构，无样式
const generateTemperatureHumidityChartOption = () => {
  const times = temperatureHumidityData.value.map(item =>
    new Date(item.timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    })
  )
  
  const series: any[] = []
  const yAxis: any[] = []

  if (props.dataType === 'temperature' || props.dataType === 'temperature-humidity') {
    const temperatures = temperatureHumidityData.value.map(item => item.temperature || null)

    yAxis.push({
      type: 'value',
      name: '温度 (°C)',
      position: 'left',
      axisLabel: {
        formatter: '{value}°C'
      }
    })

    series.push({
      name: '温度',
      type: 'line',
      yAxisIndex: 0,
      data: temperatures,
      smooth: true
    })
  }

  if (props.dataType === 'humidity' || props.dataType === 'temperature-humidity') {
    const humidities = temperatureHumidityData.value.map(item => item.humidity || null)
    const yAxisIndex = props.dataType === 'temperature-humidity' ? 1 : 0

    if (props.dataType === 'temperature-humidity') {
      yAxis.push({
        type: 'value',
        name: '湿度 (%)',
        position: 'right',
        axisLabel: {
          formatter: '{value}%'
        }
      })
    } else {
      yAxis.push({
        type: 'value',
        name: '湿度 (%)',
        axisLabel: {
          formatter: '{value}%'
        }
      })
    }

    series.push({
      name: '湿度',
      type: 'line',
      yAxisIndex: yAxisIndex,
      data: humidities,
      smooth: true
    })
  }

  return {
    xAxis: {
      data: times
    },
    yAxis: yAxis,
    series: series,
    legend: {
      data: series.map(s => s.name)
    }
  }
}

// 图表就绪事件处理
const handleChartReady = (chart: any) => {
  // 图表准备好后，如果已有数据则立即更新
  if (temperatureHumidityData.value.length > 0 || co2Data.value.length > 0) {
    updateChart()
  }
}

// 基础图表组件引用
const baseChart = ref<InstanceType<typeof BaseChart>>()

// 更新图表
const updateChart = () => {
  // 确保图表组件已准备好且有数据
  if (baseChart.value && (
    (props.dataType === 'co2' && co2Data.value.length > 0) ||
    (props.dataType !== 'co2' && temperatureHumidityData.value.length > 0)
  )) {
    const option = generateChartOption();
    
    baseChart.value.updateChart(option);
  } else {
    console.warn('图表更新条件不满足:', {
      baseChartReady: !!baseChart.value,
      dataType: props.dataType,
      co2DataLength: co2Data.value.length,
      tempHumidityDataLength: temperatureHumidityData.value.length
    });
  }
};

// 时间范围变化处理 - 修改为同时触发内部逻辑和向父组件传递
const handleTimeRangeChange = (hours: number) => {
  currentTimeRange.value = hours
  // 向父组件传递时间范围变化事件
  emit('timeRangeChange', hours)
  // 刷新当前组件数据
  refreshData()
}

// 刷新数据
const refreshData = () => {
  if (props.dataType === 'co2' && props.terminalId) {
    fetchEnvironmentalData(undefined, props.terminalId, currentTimeRange.value)
  } else if (props.areaId) {
    fetchEnvironmentalData(props.areaId, undefined, currentTimeRange.value)
  }
}

// 监听props变化
watch(
  () => [props.areaId, props.terminalId, props.dataType],
  () => {
    refreshData()
  },
  { immediate: true }
)
</script>

<template>
  <BaseChart
    :title="chartTitle"
    :height="height"
    :width="width"
    :loading="loading"
    :error="error"
    :show-time-range="showControls"
    :show-refresh="showControls"
    :hide-title="hideTitle"
    :hide-controls="hideControls"
    :style-config="styleConfig"
    @time-range-change="handleTimeRangeChange"
    @refresh="refreshData"
    ref="baseChart"
  />
</template>

<style scoped>
/* 移除所有样式硬编码 */
</style>