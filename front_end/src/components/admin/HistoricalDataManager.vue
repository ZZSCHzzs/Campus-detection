<template>
  <base-manager
    title="历史数据管理"
    resource-name="historical"
    item-name="历史数据"
    :columns="columns"
    :default-form-data="defaultFormData"
  >
    <template #column-area_name="{ row }">
      <el-tag>{{ getAreaName(row) }}</el-tag>
      <Jump module="areas" :name="getAreaName(row)"/>
    </template>
    <template #form="{ form }">
      <el-form :model="form" label-width="100px">
        <el-form-item label="区域" required>
          <el-select 
            v-model="form.area" 
            placeholder="请选择区域"
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
import { onMounted, ref } from 'vue'
import BaseManager from './BaseManager.vue'
import { areaService } from '../../services/apiService'
import Jump from "./Jump.vue";

const columns = [
  { prop: 'area_name', label: '区域名称', width: '250', slot:true },
  { prop: 'detected_count', label: '检测人数', width: '200' },
  { prop: 'timestamp', label: '时间戳',
    formatter: (row) => new Date(row.timestamp).toLocaleString() },
]
const getAreaName = (row) => {
  const area = areas.value.find(a => a.id === row.area)
  return area ? area.name : '未知'
}

const defaultFormData = {
  area: null,
  detected_count: 0,
  timestamp: new Date()
}

const areas = ref([])
const loadingAreas = ref(false)

const fetchAreas = async () => {
    loadingAreas.value = true
    try {
      areas.value = await areaService.getAll()
    } catch (error) {
      console.error('获取区域失败:', error)
    } finally {
      loadingAreas.value = false
    }
}

onMounted(() => {
  fetchAreas()
})
</script>
