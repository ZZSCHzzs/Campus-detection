<template>
  <base-manager
    title="区域管理"
    resource-name="areas"
    item-name="区域"
    :columns="columns"
    :default-form-data="defaultFormData"
  >
    <template #form="{ form }">
      <el-form :model="form" label-width="100px">
        <el-form-item label="区域名称" required>
          <el-input v-model="form.name" placeholder="请输入区域名称" />
        </el-form-item>
        
        <el-form-item label="所属建筑">
          <el-select 
            v-model="form.building" 
            placeholder="请选择建筑"
            filterable
            remote
            :remote-method="searchBuildings"
            :loading="loadingBuildings"
          >
            <el-option
              v-for="item in buildings"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="绑定节点">
          <el-select 
            v-model="form.bound_node" 
            placeholder="请选择硬件节点"
            filterable
            remote
            :remote-method="searchNodes"
            :loading="loadingNodes"
          >
            <el-option
              v-for="item in nodes"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="区域类型">
          <el-select v-model="form.type" placeholder="请选择区域类型">
            <el-option label="教室" value="classroom" />
            <el-option label="办公室" value="office" />
            <el-option label="实验室" value="lab" />
            <el-option label="走廊" value="hallway" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="楼层">
          <el-input-number v-model="form.floor" :min="1" :max="100" />
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input 
            v-model="form.description" 
            type="textarea" 
            placeholder="请输入描述" 
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

// 表格列定义
const columns = [
  { prop: 'name', label: '区域名称', width: '200' },
  { prop: 'building_name', label: '所属建筑', width: '200' },
  { prop: 'type', label: '区域类型', width: '120',
    formatter: (row) => {
      const typeMap = {
        'classroom': '教室',
        'office': '办公室',
        'lab': '实验室',
        'hallway': '走廊',
        'other': '其他'
      }
      return typeMap[row.type] || row.type
    }
  },
  { prop: 'floor', label: '楼层', width: '80' },
  { prop: 'bound_node_name', label: '绑定节点', width: '180' },
  { prop: 'description', label: '描述' }
]

// 默认表单数据
const defaultFormData = {
  name: '',
  building: null,
  bound_node: null,
  type: 'classroom',
  floor: 1,
  description: ''
}

// 建筑选择相关
const buildings = ref([])
const loadingBuildings = ref(false)

// 搜索建筑
const searchBuildings = async (query) => {
  if (query !== '') {
    loadingBuildings.value = true
    try {
      const response = await apiService.customGet(`buildings?search=${query}`)
      buildings.value = response.data.results || response.data
    } catch (error) {
      console.error('获取建筑失败:', error)
    } finally {
      loadingBuildings.value = false
    }
  } else {
    buildings.value = []
  }
}

// 节点选择相关
const nodes = ref([])
const loadingNodes = ref(false)

// 搜索节点
const searchNodes = async (query) => {
  if (query !== '') {
    loadingNodes.value = true
    try {
      const response = await apiService.customGet(`nodes?search=${query}`)
      nodes.value = response.data.results || response.data
    } catch (error) {
      console.error('获取节点失败:', error)
    } finally {
      loadingNodes.value = false
    }
  } else {
    nodes.value = []
  }
}
</script>
