<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { AreaItem } from '../types'
import axios from '../axios'

const areas = ref<AreaItem[]>([])
const loading = ref(false)

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

onMounted(() => {
  fetchAreas()
  // 每30秒自动刷新
  setInterval(fetchAreas, 30000)
})
</script>

<template>
  <div class="home-container">
    <el-card class="header-card">
      <h2>校园区域实时状态</h2>
      <el-statistic title="当前在线终端" :value="areas.length" />
    </el-card>

    <el-table :data="areas" v-loading="loading" stripe>
      <el-table-column prop="name" label="区域名称" />
      <el-table-column prop="current_count" label="当前人数"/>
      <el-table-column prop="status" label="状态" />
      <el-table-column prop="update_time" label="更新时间" />
      <!-- 保持原有状态列和时间列 -->
    </el-table>
  </div>
</template>

<style scoped>
.home-container {
  max-width: 1200px;
  margin: 20px auto;
  padding: 20px;
}

.header-card {
  margin-bottom: 20px;
  text-align: center;
}
</style>