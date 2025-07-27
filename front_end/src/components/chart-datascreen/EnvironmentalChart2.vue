<script lang="ts" setup>
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import BaseChart from './BaseChart2.vue'
import * as echarts from 'echarts' // 引入echarts以使用渐变色
import { areaService, temperatureHumidityService, co2Service, terminalService } from '../../services'
import type { TemperatureHumidityData, CO2Data } from '../../types.ts'

// Props定义
interface Props {
  areaId?: number
  terminalId?: number
  dataType: 'temperature' | 'humidity' | 'co2' | 'temperature-humidity'
  height?: string
  showControls?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  height: '400px',
  showControls: true
})

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

// 生成CO2图表配置
const generateCO2ChartOption = () => {
  // 检查数据是否有效
  if (!co2Data.value || co2Data.value.length === 0) {
    console.warn('CO2数据为空，无法生成图表');
    return {
      series: [] // 返回空系列以清空图表
    };
  }
  
  // 数据处理和验证
  const validData = co2Data.value.filter(item => 
    item && item.timestamp && item.co2_level !== undefined && item.co2_level !== null
  );
  
  if (validData.length === 0) {
    console.warn('没有有效的CO2数据点');
    return {
      series: []
    };
  }
  
  const times = validData.map(item => new Date(item.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }));
  const values = validData.map(item => item.co2_level);

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      textStyle: { color: '#f0f9ff' }
    },
    xAxis: {
      type: 'category',
      data: times,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.2)' } }, // 降低不透明度
      axisLabel: { color: '#a5f3fc', fontSize: 11 }
    },
    yAxis: {
      name: 'CO2浓度 (ppm)',
      type: 'value',
      nameTextStyle: { color: '#a5f3fc' },
      axisLine: { show: false, lineStyle: { color: 'rgba(255, 255, 255, 0.2)' } }, // 降低不透明度
      axisLabel: { color: '#a5f3fc', fontSize: 11 },
      splitLine: { show: true, lineStyle: { color: 'rgba(255, 255, 255, 0.15)', type: 'dashed' } } // 调整颜色和不透明度
    },
    series: [{
      name: 'CO2浓度',
      type: 'line',
      data: values,
      smooth: true,
      lineStyle: { width: 2, color: '#22d3ee' },
      itemStyle: { color: '#22d3ee' },
      areaStyle: {
        opacity: 0.2,
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(34, 211, 238, 0.6)' }, // 增强渐变
          { offset: 1, color: 'rgba(34, 211, 238, 0)' }
        ])
      }
    }]
  };
};

// 生成温湿度图表配置
const generateTemperatureHumidityChartOption = () => {
  const times = temperatureHumidityData.value.map(item => new Date(item.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }));
  const series: any[] = [];
  const yAxis: any[] = [];

  const baseAxisStyle = {
    type: 'value',
    nameTextStyle: { color: '#a5f3fc', fontSize: 12 },
    axisLine: { show: false, lineStyle: { color: 'rgba(255, 255, 255, 0.2)' } }, // 降低不透明度
    axisLabel: { color: '#a5f3fc', fontSize: 11 },
    splitLine: { show: true, lineStyle: { color: 'rgba(255, 255, 255, 0.15)', type: 'dashed' } } // 调整颜色和不透明度
  };

  if (props.dataType === 'temperature' || props.dataType === 'temperature-humidity') {
    yAxis.push({ ...baseAxisStyle, name: '温度 (°C)', position: 'left', axisLabel: { ...baseAxisStyle.axisLabel, formatter: '{value}°C' } });
    series.push({
      name: '温度',
      type: 'line',
      yAxisIndex: 0,
      data: temperatureHumidityData.value.map(item => item.temperature || null),
      smooth: true,
      lineStyle: { width: 2, color: '#22d3ee' },
      itemStyle: { color: '#22d3ee' },
      areaStyle: { // 添加温度渐变
        opacity: 0.2,
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(34, 211, 238, 0.6)' }, // 增强渐变
          { offset: 1, color: 'rgba(34, 211, 238, 0)' }
        ])
      }
    });
  }

  if (props.dataType === 'humidity' || props.dataType === 'temperature-humidity') {
    const yAxisIndex = props.dataType === 'temperature-humidity' ? 1 : 0;
    yAxis.push({ ...baseAxisStyle, name: '湿度 (%)', position: yAxisIndex === 1 ? 'right' : 'left', axisLabel: { ...baseAxisStyle.axisLabel, formatter: '{value}%' } });
    series.push({
      name: '湿度',
      type: 'line',
      yAxisIndex: yAxisIndex,
      data: temperatureHumidityData.value.map(item => item.humidity || null),
      smooth: true,
      lineStyle: { width: 2, color: '#a78bfa' },
      itemStyle: { color: '#a78bfa' },
      areaStyle: { // 添加湿度渐变
        opacity: 0.2,
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(167, 139, 250, 0.6)' }, // 增强渐变
          { offset: 1, color: 'rgba(167, 139, 250, 0)' }
        ])
      }
    });
  }

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      textStyle: { color: '#f0f9ff' }
    },
    xAxis: {
      type: 'category',
      data: times,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.2)' } }, // 降低不透明度
      axisLabel: { color: '#a5f3fc', fontSize: 11 }
    },
    yAxis: yAxis,
    series: series,
    legend: {
      data: series.map(s => s.name),
      top: 'top',
      textStyle: { color: '#e0f2fe' }
    }
  };
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

// 时间范围变化处理
const handleTimeRangeChange = (hours: number) => {
  currentTimeRange.value = hours
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
    ref="baseChart"
    :title="chartTitle"
    :height="height"
    :loading="loading"
    :error="error"
    :show-time-range="showControls"
    :show-refresh="showControls"
    :show-export="showControls"
    :time-range="currentTimeRange"
    @time-range-change="handleTimeRangeChange"
    @refresh="refreshData"
    @chart-ready="handleChartReady"
  />
</template>

<style scoped>
/* 可以添加特定于环境图表的样式 */
</style>