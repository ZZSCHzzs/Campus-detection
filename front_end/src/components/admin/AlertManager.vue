<template>
  <base-manager
    title="告警管理"
    resource-name="alerts"
    :dataLink="props.dataLink"
    item-name="告警"
    :columns="columns"
    :default-form-data="defaultFormData"
  >
    <template #column-grade="{ row }">
      <el-tag :type="getGradeType(row.grade)">
        {{ getGradeLabel(row.grade) }}
      </el-tag>
    </template>
    
    <template #column-alert_type="{ row }">
      <el-tag :type="getAlertTypeType(row.alert_type)">
        {{ getAlertTypeLabel(row.alert_type) }}
      </el-tag>
    </template>
    
    <template #column-area="{ row }">
      <div style="display: flex; align-items: center;">
        <el-tag>{{ getAreaName(row.area) }}</el-tag>
        <Jump :module="'areas'" :name="getAreaName(row.area)" />
      </div>
    </template>
    
    <template #column-solved="{ row }">
      <el-tag :type="row.solved ? 'success' : 'warning'">
        {{ row.solved ? '已处理' : '未处理' }}
      </el-tag>
    </template>
    
    <template #column-publicity="{ row }">
      <el-tag :type="row.publicity ? 'info' : 'danger'">
        {{ row.publicity ? '公开' : '不公开' }}
      </el-tag>
    </template>
    
    <template #form="{ form }">
      <el-form :model="form" label-width="100px">
        <el-form-item label="所属区域" required>
          <el-select 
            v-model="form.area" 
            placeholder="请选择区域"
            remote
            :remote-method="fetchAreas"
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
        
        <el-form-item label="告警等级" required>
          <el-select v-model="form.grade" placeholder="请选择告警等级">
            <el-option label="普通" :value="0" />
            <el-option label="注意" :value="1" />
            <el-option label="警告" :value="2" />
            <el-option label="严重" :value="3" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="告警类型" required>
          <el-select v-model="form.alert_type" placeholder="请选择告警类型">
            <el-option label="火灾" value="fire" />
            <el-option label="安保" value="guard" />
            <el-option label="人群聚集" value="crowd" />
            <el-option label="生命危急" value="health" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="是否公开">
          <el-switch
            v-model="form.publicity"
            active-text="公开"
            inactive-text="不公开"
          />
        </el-form-item>
        
        <el-form-item label="是否已处理">
          <el-switch
            v-model="form.solved"
            active-text="已处理"
            inactive-text="未处理"
          />
        </el-form-item>
        
        <el-form-item label="告警信息" required>
          <el-input 
            v-model="form.message" 
            type="textarea" 
            placeholder="请输入告警信息" 
            rows="3"
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
import Jump from './Jump.vue'
import { defineProps } from 'vue'

// 引入 props
const props = defineProps({
  dataLink: {
    type: String,
    default: ''
  }
})

// 表格列定义
const columns = [
  { prop: 'area', label: '所属区域', width: '150', slot: true },
  { prop: 'grade', label: '告警等级', width: '120', slot: true },
  { prop: 'alert_type', label: '告警类型', width: '120', slot: true },
  { prop: 'message', label: '告警信息' },
  { prop: 'publicity', label: '是否公开', width: '100', slot: true },
  { prop: 'solved', label: '处理状态', width: '100', slot: true },
  { prop: 'timestamp', label: '告警时间', width: '180',
    formatter: (row) => new Date(row.timestamp).toLocaleString() }
]

// 默认表单数据
const defaultFormData = {
  area: null,
  grade: 0,
  alert_type: 'other',
  publicity: true,
  message: '',
  solved: false
}

// 区域选择相关
const areas = ref([])
const loadingAreas = ref(false)

// 搜索区域
const fetchAreas = async () => {
  loadingAreas.value = true
  try {
    const response = await apiService.customGet('areas')
    areas.value = response.data.results || response.data
  } catch (error) {
    console.error('获取区域失败:', error)
  } finally {
    loadingAreas.value = false
  }
}
fetchAreas()

const getAreaName = (id) => {
  const area = areas.value.find(item => item.id === id)
  return area ? area.name : '未知区域'
}

// 等级标签处理
const getGradeLabel = (grade) => {
  const labels = ['普通', '注意', '警告', '严重']
  return labels[grade] || '未知'
}

const getGradeType = (grade) => {
  const types = ['info', 'success', 'warning', 'danger']
  return types[grade] || 'info'
}

// 告警类型标签处理
const getAlertTypeLabel = (type) => {
  const typeMap = {
    'fire': '火灾',
    'guard': '安保',
    'crowd': '人群聚集',
    'health': '生命危急',
    'other': '其他'
  }
  return typeMap[type] || '未知'
}

const getAlertTypeType = (type) => {
  const typeMap = {
    'fire': 'danger',
    'guard': 'info',
    'crowd': 'warning',
    'health': 'error',
    'other': 'info'
  }
  return typeMap[type] || 'info'
}
</script>
