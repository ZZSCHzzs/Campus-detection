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
  <div class="areas-container">
    <div class="search-bar">
      <el-input placeholder="搜索区域名称..." />
      <el-select placeholder="状态筛选">
        <el-option label="全部" value="" />
        <el-option label="正常" value="normal" />
        <el-option label="异常" value="abnormal" />
      </el-select>
    </div>

    <el-row :gutter="20">
      <el-col :span="8" v-for="area in areas" :key="area.id">
        <el-card class="area-card">
          <h3>{{ area.name }}</h3>
          <div class="metrics">
            <el-statistic title="当前人数" :value="area.current_count" />
            <el-progress 
              :percentage="(area.current_count / area.max_capacity) * 100" 
              :status="area.status" />
          </div>
          <el-button type="primary" @click="$router.push(`/areas/${area.id}`)">
            查看详情
          </el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.areas-container {
  max-width: 1400px;
  margin: 20px auto;
}

.search-bar {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.area-card {
  margin-bottom: 20px;
}
</style>