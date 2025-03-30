<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import type { AreaItem } from '../types'
import axios from '../axios'

const areas = ref<AreaItem[]>([])
const loading = ref(false)
// 统计项标签映射
const STATS_LABELS = {
  nodes_count: '监测节点',
  terminals_count: '接入终端',
  buildings_count: '楼宇数量',
  areas_count: '监测区域',
  historical_data_count: '历史记录',
  people_count: '今日人次'
} as const
const fetchAreas = async () => {
  try {
    loading.value = true
    // 第一步：获取基础区域数据
    const { data: baseData } = await axios.get('/api/areas')
    
    // 第二步：为每个区域获取详细数据
    const areasWithData = await Promise.all(
      baseData.map(async (area: AreaItem) => {
        try {
          const { data: hardwareData } = await axios.get(`/api/areas/${area.id}/data`)
          return {
            ...area,
            current_count: hardwareData.current_count,
            status: hardwareData.status,
            update_time: hardwareData.update_time,
          }
        } catch (e) {
          ElMessage.error(`${area.name} 数据获取失败`)
          return area // 返回基础数据保持结构
        }
      })
    )
    
    areas.value = areasWithData
  } catch (error) {
    ElMessage.error('基础数据加载失败')
  } finally {
    loading.value = false
  }
}

// 新增计算属性获取热门区域
const hotAreas = computed(() => {
  return [...areas.value]
    .sort((a, b) => (b.current_count || 0) - (a.current_count || 0))
    .slice(0, 5)
})

// 新增图表初始化
let chart: echarts.ECharts
const initChart = () => {
  chart = echarts.init(document.getElementById('trend-chart')!)
  chart.setOption({
    title: { text: '今日人流趋势' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['6:00', '9:00', '12:00', '15:00', '18:00', '21:00'] },
    yAxis: { type: 'value' },
    series: [{
      data: [120, 200, 150, 80, 70, 110],
      type: 'line',
      smooth: true,
      symbolSize: 8, // 增加数据点标识
      lineStyle: {
        width: 3,
        shadowColor: 'rgba(64, 158, 255, 0.2)', // 添加线条阴影
        shadowBlur: 12,
        shadowOffsetY: 6
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.4)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.02)' }
        ])
      },
      label: {
        show: true,
        position: 'top',
        color: '#36b5ff',
        fontSize: 12
      }
    }]
  })
}

// 新增统计数据结构
interface SummaryData {
  nodes_count: number
  terminals_count: number
  buildings_count: number
  areas_count: number
  historical_data_count: number
  people_count: number
}

// 新增统计相关状态
const summary = ref<SummaryData>({
  nodes_count: 0,
  terminals_count: 0,
  buildings_count: 0,
  areas_count: 0,
  historical_data_count: 0,
  people_count: 0
})
const loadingSummary = ref(false)

// 新增获取统计方法
const fetchSummary = async () => {
  try {
    loadingSummary.value = true
    const { data } = await axios.get('/api/summary')
    summary.value = data
  } catch (error) {
    ElMessage.error('统计信息获取失败')
  } finally {
    loadingSummary.value = false
  }
}

onMounted(() => {
  fetchAreas()
  fetchSummary()  // 新增调用
  initChart()
  // 每30秒自动刷新
  setInterval(fetchAreas, 30000)
})

</script>

<template>
  <div class="home-container">
    <el-card class="header-card">
      <h1 class="header-title">智慧校园人员检测系统</h1>
      <div class="sub-title">实时监测校园内各区域人员情况，保障安全与高效管理</div>
    </el-card>

    <!-- 通知提醒区域移动到上方 -->
    <el-row :gutter="20" class="mt-20">
      <el-col :span="12">
        <el-card class="dashboard-card">
          <template #header>
            <span class="card-title">📢 今日重要通知</span>
          </template>
          <el-alert title="图书馆区域今日15:00-17:00临时关闭" type="info" show-icon />
          <el-alert title="教学区东侧实施人流管控" type="warning" class="mt-10" show-icon />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="dashboard-card">
          <template #header>
            <span class="card-title">⚠️ 安全提醒</span>
          </template>
          <el-alert title="午间高峰期（11:30-13:00）建议错峰出行" type="error" show-icon />
        </el-card>
      </el-col>
    </el-row>

    <!-- 统计卡片保持原位 -->
    <el-card class="stats-card mb-20">
      <el-row :gutter="20" v-loading="loadingSummary">
        <el-col :span="4" v-for="(value, key) in summary" :key="key">
          <el-statistic 
            :title="STATS_LABELS[key]" 
            :value="value"
            class="stat-item"
          />
        </el-col>
      </el-row>
    </el-card>

    <el-row :gutter="20">
      <!-- 热门区域 -->
      <el-col :span="12">
        <el-card class="dashboard-card">
          <template #header>
            <span class="card-title">🏃 热门区域实时排行</span>
          </template>
          <el-table :data="hotAreas" size="small">
            <el-table-column prop="name" label="区域名称" />
            <el-table-column label="当前人数">
              <template #default="{row}">
                <el-tag :type="row.current_count > 50 ? 'danger' : 'success'">
                  {{ row.current_count || 0 }} 人
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 趋势图表 -->
      <el-col :span="12">
        <el-card class="dashboard-card">
          <template #header>
            <span class="card-title">📈 人员变化趋势</span>
          </template>
          <div id="trend-chart" style="height:300px"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
/* 新增标题居中样式 */
.header-card {
  text-align: center !important;
  .header-title {
    font-size: 2.2rem;
    margin-bottom: 12px;
  }
  .sub-title {
    font-size: 1.1rem;
    color: #666;
  }
}

.home-container {
  max-width: 1400px;
  margin: 20px auto;
  padding: 30px; /* 增大容器内边距 */
}

/* 卡片统一样式 */
.el-card {
  border-radius: 12px !important; /* 增加圆角 */
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important; /* 柔和阴影 */
  border: 1px solid #ebeef5;
  transition: all 0.3s;
  
  &:hover {
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12) !important;
  }
}

/* 统计卡片优化 */
.stats-card {
  margin-bottom: 30px; /* 增大间距 */
  
  .stat-item {
    padding: 16px;
    :deep(.el-statistic__content) {
      font-size: 28px !important; /* 加大字号 */
      font-weight: 600;
      background: linear-gradient(45deg, #409eff, #36b5ff);
      -webkit-background-clip: text;
      color: transparent;
    }
    :deep(.el-statistic__title) {
      font-size: 14px;
      color: #888; /* 弱化标题颜色 */
      letter-spacing: 0.5px;
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
  height: 320px !important;
  padding: 15px; /* 增加内边距 */
}

/* 通知区域优化 */
.el-alert {
  margin: 12px 0;
  border-radius: 8px !important;
  &--error {
    background-color: #fff0f0 !important; /* 减淡红色背景 */
    border: 1px solid rgba(245, 108, 108, 0.3);
  }
}

/* 间距系统 */
.mb-20 { margin-bottom: 20px; }
.mb-30 { margin-bottom: 30px; }
.mt-20 { margin-top: 20px; }
.mt-30 { margin-top: 30px; }
</style>
