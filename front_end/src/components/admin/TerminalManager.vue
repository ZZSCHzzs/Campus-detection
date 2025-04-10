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
      </el-form>
    </template>
    
  </base-manager>
</template>

<script setup>
import { ref } from 'vue'
import BaseManager from './BaseManager.vue'
import View from './View.vue'

const columns = [
  { prop: 'name', label: '终端名称', width: '200', mobileWidth: '130' },
  { prop: 'status', label: '状态', width: '250', mobileWidth: '100', slot: true },
  { prop: 'nodes_count', label: '关联节点数', width: '250', mobileWidth: '120', slot: true },
  { prop:'',label:''}
]

const defaultFormData = {
  name: '',
  status: 'online'
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
</style>
