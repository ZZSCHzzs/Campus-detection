<template>
  <base-manager title="区域管理" resource-name="areas" item-name="区域" :columns="columns"
    :default-form-data="defaultFormData" @row-click="handleRowClick">
    <template #column-type="{ row }">
      <div style="display: flex; align-items: center;">
        <el-tag>{{ getBuildingName(row.type) }}</el-tag>
        <Jump :module="'buildings'" :name="getBuildingName(row.type)" />
      </div>
    </template>
    <template #column-status="{ row }">
      <el-tag :type="getNodeStatus(row.bound_node) ? 'success' : 'danger'">
        {{ getNodeStatus(row.bound_node) ? '在线' : '离线' }}
      </el-tag>
    </template>
    <template #column-bound_node="{ row }">
      <div style="display: flex; align-items: center;">
        <el-tag>{{ getNodeName(row.bound_node) }}</el-tag>
        <Jump :module="'nodes'" :name="getNodeName(row.bound_node)" />
      </div>
    </template>
    <template #column-detected_count="{ row }">
      <span>{{ row.detected_count || 0 }}</span>
    </template>
    <template #column-updated_at="{ row }">
      <span>{{ getNodeUpdateTime(row.bound_node) }}</span>
    </template>
    <template #form="{ form }">
      <el-form :model="form" label-width="100px">
        <el-form-item label="区域名称" required>
          <el-input v-model="form.name" placeholder="请输入区域名称" />
        </el-form-item>

        <el-form-item label="绑定节点">
          <el-select v-model="form.bound_node" placeholder="请选择硬件节点" filterable remote :loading="loadingNodes">
            <el-option v-for="item in nodes" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="所属建筑">
          <el-select v-model="form.type" placeholder="请选择建筑" remote :loading="loadingBuildings">
            <el-option v-for="item in buildings" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="楼层">
          <el-input-number v-model="form.floor" :min="1" :max="100" />
        </el-form-item>

        <el-form-item label="最大容量">
          <el-input-number v-model="form.capacity" :min="0" :max="1000" />
        </el-form-item>

        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" placeholder="请输入描述" rows="3" />
        </el-form-item>
      </el-form>
    </template>
  </base-manager>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import BaseManager from './BaseManager.vue'
import { buildingService, areaService } from '../../services/apiService'
import Jump from "./Jump.vue";

const columns = [
  { prop: 'name', label: '区域名称', width: '150', mobileWidth: '120' },
  { prop: 'type', label: '所属建筑', width: '200', mobileWidth: '130', slot: true },
  { prop: 'floor', label: '楼层', width: '60', mobileWidth: '60' },
  { prop: 'bound_node', label: '绑定节点', width: '120', mobileWidth: '100', slot: true },
  { prop: "detected_count", label: "检测结果", width: "100", mobileWidth: '80', slot: true },
  { prop: 'status', label: '状态', width: '100', mobileWidth: '80', slot: true },
  { prop: 'updated_at', label: '更新时间', width: '160', hideOnMobile: true, slot: true },
  { prop: 'capacity', label: '最大容量', width: 100, hideOnMobile: true },
  { prop: 'description', label: '描述', hideOnMobile: true }
]

const defaultFormData = {
  name: '',
  type: null,
  bound_node: null,
  floor: 1,
  description: '',
  capacity: 0,
}

const buildings = ref([])
const loadingBuildings = ref(false)

// 存储区域绑定的节点数据
const areaNodesMap = ref(new Map())
const loadingAreaData = ref(false)

const fetchBuildings = async (query) => {
  loadingBuildings.value = true
  try {
    buildings.value = await buildingService.getAll()
  } catch (error) {
    console.error('获取建筑失败:', error)
  } finally {
    loadingBuildings.value = false
  }
}

// 获取指定区域的节点数据
const fetchAreaData = async (areaId) => {
  if (!areaId || areaNodesMap.value.has(areaId)) return
  
  loadingAreaData.value = true
  try {
    const nodeData = await areaService.getAreaData(areaId)
    if (nodeData) {
      areaNodesMap.value.set(areaId, nodeData)
    }
  } catch (error) {
    console.error('获取区域节点数据失败:', error)
  } finally {
    loadingAreaData.value = false
  }
}

// 处理行点击事件，获取对应区域的节点数据
const handleRowClick = (row) => {
  if (row && row.bound_node) {
    fetchAreaData(row.bound_node)
  }
}

const getBuildingName = (buildingId) => {
  const building = buildings.value.find(b => b.id === buildingId)
  return building ? building.name : '未知'
}

const getNodeName = (nodeId) => {
  if (!nodeId) return '未绑定'
  
  const nodeData = areaNodesMap.value.get(nodeId)
  if (nodeData) return nodeData.name
  
  // 如果还没有获取数据，触发获取
  fetchAreaData(nodeId)
  return '加载中...'
}

const getNodeStatus = (nodeId) => {
  if (!nodeId) return false
  
  const nodeData = areaNodesMap.value.get(nodeId)
  return nodeData ? nodeData.status : false
}

const getNodeUpdateTime = (nodeId) => {
  if (!nodeId) return '未知'
  
  const nodeData = areaNodesMap.value.get(nodeId)
  return nodeData && nodeData.updated_at 
    ? new Date(nodeData.updated_at).toLocaleString() 
    : '未知'
}

onMounted(() => {
  fetchBuildings()
  fetchNodes() // 仍然需要获取所有节点用于表单选择
})

// 表单仍需要节点列表数据用于选择节点
const nodes = ref([])
const loadingNodes = ref(false)

const fetchNodes = async () => {
  loadingNodes.value = true
  try {
    // 这里假设有一个获取所有节点的API
    const response = await areaService.getAllNodes()
    nodes.value = response || []
  } catch (error) {
    console.error('获取节点列表失败:', error)
  } finally {
    loadingNodes.value = false
  }
}
</script>
