<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { AreaItem } from '../types'
import axios from '../axios'

const areas = ref<AreaItem[]>([])
const loading = ref(false)

// 获取区域数据
const fetchAreas = async () => {
  try {
    loading.value = true
    const { data } = await axios.get('/api/areas')
    areas.value = data.data
  } catch (error) {
    ElMessage.error('数据加载失败')
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
      <el-table-column label="当前人数">
        <template #default="{ row }">
          {{ row.current_count || 0 }}
        </template>
      </el-table-column>
      <el-table-column label="状态">
        <template #default="{ row }">
          <el-tag :type="row.status === 'normal' ? 'success' : 'danger'">
            {{ row.status === 'normal' ? '正常' : '异常' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最后更新时间">
        <template #default="{ row }">
          {{ new Date(row.update_time).toLocaleTimeString() }}
        </template>
      </el-table-column>
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