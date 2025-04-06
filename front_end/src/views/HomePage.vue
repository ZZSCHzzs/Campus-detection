<script lang="ts" setup>
import {ref, onMounted, computed, nextTick} from 'vue'
import * as echarts from 'echarts'
import {ElMessage} from 'element-plus'
import type {AreaItem} from '../types'
import axios from '../axios'

const Hotareas = ref<AreaItem[]>([])
const loading = ref(false) 

const STATS_LABELS = {
  nodes_count: '监测节点',
  terminals_count: '接入终端',
  buildings_count: '楼宇数量',
  areas_count: '监测区域',
  historical_data_count: '历史记录',
  people_count: '系统总人数'
} as const

const fetchHotAreas = async () => {
  try {
    loading.value = true 
    const response = await axios.get('/api/areas/popular')
    
    
    if (Array.isArray(response.data)) {
      Hotareas.value = response.data
    } else if (response.data && response.data.data && Array.isArray(response.data.data)) {
      
      Hotareas.value = response.data.data
    } else {
      Hotareas.value = []
    }
    
    
    setTimeout(() => {
      loading.value = false
    }, 100)
  } catch (error) {
    ElMessage.error('热门区域数据获取失败')
    Hotareas.value = [] 
  }
}

const chartLoading = ref(false)
const chartInitFailed = ref(false) 

let chart: echarts.ECharts | null = null
const initChart = async () => {
  chartLoading.value = false
  chartInitFailed.value = false
  try {
    const chartDom = document.getElementById('trend-chart')
    if (!chartDom) {
      chartInitFailed.value = true
      return
    }
    
    if (chart) {
      chart.dispose()
    }
    
    chart = echarts.init(chartDom)
    const option = {
      title: {text: '今日人流趋势'},
      tooltip: {trigger: 'axis'},
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {type: 'category', data: ['6:00', '9:00', '12:00', '15:00', '18:00', '21:00', '24:00']},
      yAxis: {type: 'value'},
      series: [{
        data: [10, 200, 100, 180, 70, 110, 20],
        type: 'line',
        smooth: true,
        symbolSize: 8,
        lineStyle: {
          width: 3,
          shadowColor: 'rgba(64, 158, 255, 0.2)',
          shadowBlur: 12,
          shadowOffsetY: 6
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            {offset: 0, color: 'rgba(64, 158, 255, 0.4)'},
            {offset: 1, color: 'rgba(64, 158, 255, 0.02)'}
          ])
        },
        label: {
          show: true,
          position: 'top',
          color: '#36b5ff',
          fontSize: 12
        }
      }]
    }
    
    chart.setOption(option)
    chartLoading.value = false
  } catch (error) {
    chartLoading.value = false
    chartInitFailed.value = true
  }
}

interface SummaryData {
  nodes_count: number
  terminals_count: number
  buildings_count: number
  areas_count: number
  historical_data_count: number
  people_count: number
}

const summary = ref<SummaryData>({
  nodes_count: 0,
  terminals_count: 0,
  buildings_count: 0,
  areas_count: 0,
  historical_data_count: 0,
  people_count: 0
})
const loadingSummary = ref(false)

const fetchSummary = async () => {
  try {
    loadingSummary.value = true
    const response = await axios.get('/api/summary')
    summary.value = response.data as SummaryData 

  } catch (error) {
    ElMessage.error('统计信息获取失败')
  } finally {
    setTimeout(() => {
      loadingSummary.value = false
    }, 100)
  }
}

onMounted(async () => {
  await Promise.all([
    fetchHotAreas(),
    fetchSummary()
  ]).catch(() => ElMessage.error('数据获取出错'))
  
  await nextTick()
  
  setTimeout(async () => {
    
    await nextTick()
    initChart()
    
    
    window.addEventListener('resize', () => {
      if (chart) {
        try {
          chart.resize()
        } catch (e) {
          
        }
      }
    })
  }) 
  
  setInterval(fetchHotAreas, 30000)
})

const getProgressColor = (rate: number) => {
  if (rate > 0.9) return '#F56C6C'
  if (rate > 0.7) return '#E6A23C'
  if (rate > 0.5) return '#409EFF'
  return '#67C23A'
}

const getTagType = (rate: number) => {
  if (rate > 0.9) return 'danger'
  if (rate > 0.7) return 'warning'
  if (rate > 0.5) return 'info'
  return 'success'
}
</script>

<template>
  <div class="home-container">
    <el-card class="header-card">
      <div class="header-wrapper">
        <h1 class="header-title">智慧校园<span class="highlight">人员检测</span>系统</h1>
        <div class="sub-title">实时监测校园内各区域人员情况，保障安全与高效管理</div>
      </div>
    </el-card>
    <el-card class="stats-card mb-20 mt-20">
      <el-skeleton :rows="1" animated :loading="loadingSummary">
        <template #default>
          <div v-if="Object.values(summary).some(value => value > 0)">
            <el-row :gutter="20">
              <el-col v-for="(value, key) in summary" :key="key" :span="4">
                <el-statistic
                    :title="STATS_LABELS[key]"
                    :value="value"
                    class="stat-item"
                >
                  <template #suffix>
                    <el-icon v-if="key === 'people_count'" class="stat-icon"><el-icon-user /></el-icon>
                    <el-icon v-else-if="key === 'nodes_count'" class="stat-icon"><el-icon-monitor /></el-icon>
                    <el-icon v-else-if="key === 'buildings_count'" class="stat-icon"><el-icon-office-building /></el-icon>
                  </template>
                </el-statistic>
              </el-col>
            </el-row>
          </div>
          <div v-else class="no-data-message">
            <el-empty description="暂无统计数据" />
          </div>
        </template>
      </el-skeleton>
    </el-card>

    <el-row :gutter="20" class="mt-20">
      <el-col :span="16">
        <el-card class="dashboard-card">
          <template #header>
            <span class="card-title pulse">🏃 热门区域实时排行</span>
          </template>
          <el-skeleton :rows="5" animated :loading="loading">
            <template #default>
              <div v-if="Hotareas && Hotareas.length > 0">
                <el-table :data="Hotareas" size="small" :highlight-current-row="true">
                  <el-table-column label="区域名称" prop="name"/>
                  <el-table-column label="当前人数">
                    <template #default="{row}">
                      <el-tag :type="row.detected_count > 50 ? 'warning' : 'success'" effect="light" class="animate-tag">
                        {{ row.detected_count || 0 }} 人
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="负载率">
                    <template #default="{row}">
                      <div v-if="row.capacity">
                        <el-progress 
                          :percentage="Math.floor((row.detected_count / row.capacity) * 100)" 
                          :show-text="false" 
                          :color="getProgressColor(row.detected_count / row.capacity)"
                          style="display: inline-block; width: calc(100% - 100px);"/>
                        <el-tag :type="getTagType(row.detected_count / row.capacity)" class="animate-tag">
                          {{ Math.floor((row.detected_count / row.capacity) * 100) }}%
                        </el-tag>
                      </div>
                      <div v-else>
                        <el-tag type="info">暂无负载量数据</el-tag>
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
              <div v-else class="no-data-message">
                <el-empty description="暂无热门区域数据" />
              </div>
            </template>
          </el-skeleton>
        </el-card>
        <el-card class="dashboard-card">
          <template #header>
            <div class="chart-header">
              <span class="card-title">📈 人员变化趋势</span>
              <el-button 
                v-if="chartInitFailed" 
                size="small" 
                type="primary" 
                @click="initChart"
              >
                重新加载图表
              </el-button>
            </div>
          </template>
          <el-skeleton :rows="8" animated :loading="chartLoading">
            <template #default>
              <div v-if="!chartInitFailed" id="trend-chart" style="height:320px; width:100%;"></div>
              <div v-else class="chart-error">
                <el-empty description="图表加载失败" :image-size="100">
                  <template #description>
                    <p>趋势图加载失败，请点击"重新加载图表"按钮重试</p>
                  </template>
                </el-empty>
              </div>
            </template>
          </el-skeleton>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="dashboard-card">
          <template #header>
            <span class="card-title">⚠️ 安全提醒</span>
          </template>
          <el-skeleton :rows="1" animated :loading="loading">
            <template #default>
              <el-alert show-icon title="午间高峰期（11:30-13:00）建议错峰出行" type="error" class="animated-alert"/>
            </template>
          </el-skeleton>
        </el-card>
        <el-card class="dashboard-card">
          <template #header>
            <span class="card-title">📢 今日重要通知</span>
          </template>
          <el-skeleton :rows="2" animated :loading="loading">
            <template #default>
              <el-alert show-icon title="图书馆区域今日15:00-17:00临时关闭" type="info" class="animated-alert"/>
              <el-alert class="mt-10 animated-alert" show-icon title="教学区东侧实施人流管控" type="warning"/>
            </template>
          </el-skeleton>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
/* 新增标题居中样式 */
.header-card {
  text-align: center !important;
  background: linear-gradient(135deg, #f6f9ff 0%, #f0f5ff 100%) !important;
  overflow: hidden;
  position: relative;
}

.header-wrapper {
  position: relative;
  z-index: 2;
  padding: 20px 0;
}

.header-wrapper::before,
.header-wrapper::after {
  content: "";
  position: absolute;
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: rgba(64, 158, 255, 0.1);
  z-index: -1;
}

.header-wrapper::before {
  top: -50px;
  left: -50px;
}

.header-wrapper::after {
  bottom: -50px;
  right: -50px;
}

.header-title {
  font-size: 2.5rem;
  margin-bottom: 16px;
  background: linear-gradient(90deg, #3352a3, #409EFF);
  -webkit-background-clip: text;
  color: transparent;
  letter-spacing: 2px;
  text-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
  transition: all 0.3s ease;
}

.header-title:hover {
  transform: translateY(-2px);
  text-shadow: 0 6px 16px rgba(64, 158, 255, 0.25);
}

.header-title .highlight {
  color: #409EFF;
  background: none;
  position: relative;
  padding: 0 5px;
  font-weight: 700;
}

.header-title .highlight::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 8px;
  background: rgba(64, 158, 255, 0.2);
  z-index: -1;
  border-radius: 4px;
}

.sub-title {
  font-size: 1.15rem;
  color: #666;
  max-width: 700px;
  margin: 0 auto;
  letter-spacing: 0.5px;
  animation: fadeIn 1s ease-in-out;
}

/* 动画 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.8; }
  100% { opacity: 1; }
}

.pulse {
  animation: pulse 2s infinite;
}

.animate-tag {
  transition: all 0.3s ease;
}

.animate-tag:hover {
  transform: scale(1.05);
}

.animated-alert {
  transition: all 0.3s ease;
  animation: fadeIn 0.5s ease-in-out;
}

.animated-alert:hover {
  transform: translateX(5px);
}

/* 卡片统一样式 */
.el-card {
  border-radius: 12px !important; /* 增加圆角 */
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important; /* 柔和阴影 */
  border: 1px solid #ebeef5;
  transition: all 0.3s;

  &:hover {
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12) !important;
    transform: translateY(-2px);
  }
}

/* 统计卡片优化 */
.stats-card {
  margin-bottom: 30px; /* 增大间距 */

  .stat-item {
    padding: 16px;
    position: relative;
    overflow: hidden;
    
    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      width: 100%;
      height: 3px;
      background: linear-gradient(90deg, #409eff, #36b5ff);
      transform: scaleX(0);
      transform-origin: left;
      transition: transform 0.3s ease;
    }
    
    &:hover::after {
      transform: scaleX(1);
    }

    :deep(.el-statistic__content) {
      font-size: 28px !important; /* 加大字号 */
      font-weight: 600;
      background: linear-gradient(45deg, #409eff, #36b5ff);
      -webkit-background-clip: text;
      color: transparent;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    :deep(.el-statistic__title) {
      font-size: 14px;
      color: #888; /* 弱化标题颜色 */
      letter-spacing: 0.5px;
    }
    
    .stat-icon {
      margin-left: 5px;
      font-size: 18px;
      color: #409eff;
    }
  }
}

/* 仪表盘卡片 */
.dashboard-card {
  margin-bottom: 25px;

  :deep(.el-card__header) {
    padding: 18px 24px;
    background: linear-gradient(45deg, #fafafa, #f6f9ff) !important;
    border-bottom: 1px solid #e4e7ed;
  }

  .card-title {
    font-size: 18px !important; /* 加大标题 */
    color: #333;
    letter-spacing: 0.5px;
  }
}

/* 表格优化 */
.el-table {
  :deep(th) {
    background-color: #f8f9fa !important;
  }

  :deep(td) {
    padding: 12px 0 !important; /* 增加行高 */
  }

  :deep(.cell) {
    line-height: 1.6;
  }

  &::before { /* 移除默认分隔线 */
    display: none;
  }
}

/* 图表容器 */
#trend-chart {
  width: 100%;
  height: 320px !important;
  padding: 15px; /* 增加内边距 */
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background-color: #fdfdfd;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-error {
  height: 320px;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f9f9f9;
  border-radius: 8px;
  border: 1px dashed #dcdfe6;
}

/* 修正CSS语法错误 */
.el-alert--error {
  background-color: #fff0f0 !important; /* 修正为!important */
  border: 1px solid rgba(245, 108, 108, 0.3);
}

/* 间距系统 */
.mb-20 {
  margin-bottom: 20px;
}

.mb-30 {
  margin-bottom: 30px;
}

.mt-20 {
  margin-top: 20px;
}

.mt-30 {
  margin-top: 30px;
}

.home-container {
  max-width: 1400px; /* 调整容器宽度为1400px */
  margin: 20px auto;
  padding: 30px;
}

/* 新增空数据提示样式 */
.no-data-message {
  padding: 30px 0;
  text-align: center;
}
</style>
