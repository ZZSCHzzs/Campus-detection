<template>
  <base-manager
    title="历史数据管理"
    resource-name="historical"
    item-name="历史数据"
    :columns="columns"
    :default-form-data="defaultFormData"
  >
    <template #form="{ form }">
      <el-form :model="form" label-width="100px">
        <el-form-item label="区域" required>
          <el-select 
            v-model="form.area" 
            placeholder="请选择区域"
            filterable
            remote
            :remote-method="searchAreas"
            :loading="loadingAreas"
          >
            <el-option
              v-for="item in areas"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="检测人数" required>
          <el-input-number v-model="form.detected_count" :min="0" :max="1000" />
        </el-form-item>
        
        <el-form-item label="时间戳" required>
          <el-date-picker
            v-model="form.timestamp"
            type="datetime"
            placeholder="选择日期时间"
            format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>
      </el-form>
    </template>
  </base-manager>
</template>

<script setup>
import { ref } from 'vue'
import BaseManager from './BaseManager.vue'
import { apiService } from '../../services/api'

// 表格列定义
const columns = [
  { prop: 'area_name', label: '区域名称', width: '200' },
  { prop: 'detected_count', label: '检测人数', width: '120' },
  { prop: 'timestamp', label: '时间戳', width: '180',
    formatter: (row) => new Date(row.timestamp).toLocaleString() },
  { prop: 'building_name', label: '所属建筑', width: '200' }
]

// 默认表单数据
const defaultFormData = {
  area: null,
  detected_count: 0,
  timestamp: new Date()
}

// 区域选择相关
const areas = ref([])
const loadingAreas = ref(false)

// 搜索区域
const searchAreas = async (query) => {
  if (query !== '') {
    loadingAreas.value = true
    try {
      const response = await apiService.customGet(`areas?search=${query}`)
      areas.value = response.data.results || response.data
    } catch (error) {
      console.error('获取区域失败:', error)
    } finally {
      loadingAreas.value = false
    }
  } else {
    areas.value = []
  }
}
</script>
