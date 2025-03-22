<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import axios from '../axios'
import type { AreaItem } from '../types'

const areas = ref<AreaItem[]>([])
const chartRef = ref<HTMLElement>()

onMounted(() => {
  const chart = echarts.init(chartRef.value!)
  
  const option = {
    title: { text: '区域人流趋势' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'time' },
    yAxis: { type: 'value' },
    series: [{
      data: [],
      type: 'line',
      smooth: true
    }]
  }

  chart.setOption(option)
  
  // 定时更新数据
  setInterval(async () => {
    const { data } = await axios.get('/api/historical')
    option.series[0].data = data.data
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
        <el-statistic :value="area.current_count" />
        <el-progress 
          :percentage="(area.current_count / area.max_capacity) * 100" 
          :status="area.status" />
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