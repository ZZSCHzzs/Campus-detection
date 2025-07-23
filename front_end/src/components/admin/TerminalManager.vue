<template>
  <base-manager
    title="终端管理"
    resource-name="terminals"
    item-name="终端"
    :columns="columns"
    :default-form-data="defaultFormData"
  >
    <template #column-status="{ row }">
      <el-tag :type="row.status === true ? 'success' : 'danger'">
        {{ row.status === true ? '在线' : '离线' }}
      </el-tag>
    </template>
    
    <template #column-nodes_count="{ row }">
      <div class="nodes-count-cell">
        {{ row.nodes_count || 0 }}
        <View resource="nodes" data="terminals" :id="row.id"/>
      </div>
    </template>
    
    <template #column-co2_level="{ row }">
      <div v-if="row.co2_level !== undefined" class="co2-level-cell">
        {{ row.co2_level }} <span class="unit-text">ppm</span>
        <el-tag :type="getCO2LevelType(row.co2_level)" size="small" class="co2-tag">
          {{ getCO2LevelStatus(row.co2_level) }}
        </el-tag>
      </div>
      <span v-else>-</span>
    </template>
    
    <template #form="{ form }">
      <el-form :model="form" label-width="100px">
        <el-form-item label="终端名称" required>
          <el-input v-model="form.name" placeholder="请输入终端名称" />
        </el-form-item>
        
        <el-form-item label="状态">
          <el-select v-model="form.status" placeholder="请选择状态">
            <el-option label="在线" value="true" />
            <el-option label="离线" value="false" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="CO₂浓度">
          <el-input-number 
            v-model="form.co2_level" 
            :precision="0" 
            :step="10"
            :min="0"
            :max="5000"
            placeholder="请输入CO₂浓度" 
          />
          <span class="unit-label">ppm</span>
        </el-form-item>
      </el-form>
    </template>
    
  </base-manager>
</template>

<script setup>
import { ref } from 'vue'
import BaseManager from './BaseManager.vue'
import View from './View.vue'

const columns = [
  { prop: 'name', label: '终端名称', width: '180', mobileWidth: '130' },
  { prop: 'status', label: '状态', width: '120', mobileWidth: '100', slot: true },
  { prop: 'nodes_count', label: '关联节点数', width: '120', mobileWidth: '120', slot: true },
  { prop: 'co2_level', label: 'CO₂浓度', width: '150', mobileWidth: '120', slot: true },
  { prop: 'last_active', label: '最后活动', width: '180', hideOnMobile: true, 
    formatter: (row) => row.last_active ? new Date(row.last_active).toLocaleString() : '-' },
  { prop:'',label:''}
]

const defaultFormData = {
  name: '',
  status: 'online',
  co2_level: undefined
}

// 判断CO2浓度等级
const getCO2LevelType = (level) => {
  if (level === undefined) return 'info';
  if (level < 800) return 'success';
  if (level < 1200) return 'warning';
  return 'danger';
}

// 获取CO2浓度状态描述
const getCO2LevelStatus = (level) => {
  if (level === undefined) return '未知';
  if (level < 800) return '良好';
  if (level < 1200) return '一般';
  if (level < 2000) return '较差';
  return '差';
}

const nodesList = ref([])
const nodesDialogVisible = ref(false)
const loadingNodes = ref(false)
const currentTerminalId = ref(null)

</script>

<style scoped>
.nodes-count-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.view-nodes-btn {
  padding: 2px;
  font-size: 12px;
}

.co2-level-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.unit-text {
  color: #909399;
  font-size: 12px;
}

.co2-tag {
  margin-left: 5px;
}

.unit-label {
  margin-left: 8px;
  color: #606266;
}
</style>
