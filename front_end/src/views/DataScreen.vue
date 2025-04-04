<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import axios from '../axios'
import type { AreaItem, HistoricalData } from '../types'

const areas = ref<AreaItem[]>([])
const chartRef = ref<HTMLElement>()

// 初始化时获取区域数据
onMounted(async () => {
  // 获取区域基本信息
  const { data: areaData } = await axios.get('/api/areas')
  areas.value = areaData.data.map((a: AreaItem) => ({
    ...a,
    max_capacity: 50 // 根据实际业务需求设置或从API获取
  }))

  // 图表初始化及历史数据获取
  const chart = echarts.init(chartRef.value!)
  
  const option = {
    dataset: {
      source: [] as Array<[string, number]>
    },
    title: { text: '区域人流趋势' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'time' },
    yAxis: { type: 'value' },
    series: [{
      type: 'line',
      encode: {
        x: 'timestamp',
        y: 'detected_count'
      },
      smooth: true
    }]
  }

  // 定时更新图表数据
  setInterval(async () => {
    const { data } = await axios.get<HistoricalData[]>('/api/historical')
    // 修改为直接使用 data 数组，因为 HistoricalData[] 上不存在属性 data
    option.dataset.source = data.map(d => ([
      d.timestamp,
      d.detected_count
    ]))
    chart.setOption(option)
  }, 5000)
})
</script>

<template>


  <div class="dashboard">
    <div ref="chartRef" class="chart-container"></div>
    
    <div class="status-grid">
      <el-card v-for="area in areas" :key="area.id">
        <h4>{{ area.name }}</h4>

      </el-card>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 20px;
}

.chart-container {
  width: 100%;
  height: 500px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 20px;
}
</style>