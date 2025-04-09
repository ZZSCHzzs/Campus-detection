<template>
  <base-manager title="区域管理" resource-name="areas" item-name="区域" :columns="columns"
    :default-form-data="defaultFormData">
    <template #column-type="{ row }">
      <div style="display: flex; align-items: center;">
        <el-tag>{{ getBuildingName(row.type) }}</el-tag>
        <Jump :module="'buildings'" :name="getBuildingName(row.type)" />
      </div>
    </template>
    <template #column-status="{ row }">
      <el-tag :type="row ? 'success' : 'danger'">
        {{ row ? '在线' : '离线' }}
      </el-tag>
    </template>
    <template #column-bound_node="{ row }">
      <div style="display: flex; align-items: center;">
        <el-tag>{{ getNodeName(row.bound_node) }}</el-tag>
        <Jump :module="'nodes'" :name="getNodeName(row.bound_node)" />
      </div>
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
import { nodeService,buildingService } from '../../services/apiService'
import Jump from "./Jump.vue";

const columns = [
  { prop: 'name', label: '区域名称', width: '150' },
  { prop: 'type', label: '所属建筑', width: '200', slot: true },
  { prop: 'floor', label: '楼层', width: '60' },
  { prop: 'bound_node', label: '绑定节点', width: '120',slot: true},
  { prop: "detected_count", label: "检测结果", width: "100",
    formatter: (row) => row.detected_count || 0
  },
  {  prop: 'status', label: '状态', width: '100', slot: true,
    formatter: (row) => {
      const node = nodes.value.find(n => n.id === row.bound_node)
      return (node && node.status)
    }
  },
  {
    prop: 'updated_at', label: '更新时间', width: '160',
    formatter: (row) => {
      const node = nodes.value.find(n => n.id === row.bound_node)
      return node ? new Date(node.updated_at).toLocaleString() : '未知'
    }
  },
  { prop: 'capacity', label: '最大容量', width:100},
  { prop: 'description', label: '描述' }
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

const nodes = ref([])
const loadingNodes = ref(false)

const fetchNodes = async (query) => {
  loadingNodes.value = true
  try {
    nodes.value = await nodeService.getAll()
  } catch (error) {
    console.error('获取节点失败:', error)
  } finally {
    loadingNodes.value = false
  }
}

const getBuildingName = (buildingId) => {
  const building = buildings.value.find(b => b.id === buildingId)
  return building ? building.name : '未知'
}
const getNodeName = (nodeId) => {
  const node = nodes.value.find(n => n.id === nodeId)
  return node ? node.name : '未知'
}

onMounted(() => {
  fetchBuildings()
  fetchNodes()
})
</script>
