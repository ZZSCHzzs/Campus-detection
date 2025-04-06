<template>
  <base-manager
    title="终端管理"
    resource-name="terminals"
    item-name="终端"
    :columns="columns"
    :default-form-data="defaultFormData"
  >
    <template #column-status="{ row }">
      <el-tag :type="row.status === 'online' ? 'success' : 'danger'">
        {{ row.status === 'online' ? '在线' : '离线' }}
      </el-tag>
    </template>
    
    <template #column-nodes_count="{ row }">
      <div class="nodes-count-cell">
        {{ row.nodes_count || 0 }}
        <el-button 
          type="primary" 
          size="small" 
          circle 
          @click.stop="viewNodes(row.id)"
          icon="View"
          class="view-nodes-btn"
        ></el-button>
      </div>
    </template>
    
    <template #form="{ form }">
      <el-form :model="form" label-width="100px">
        <el-form-item label="终端名称" required>
          <el-input v-model="form.name" placeholder="请输入终端名称" />
        </el-form-item>
        
        <el-form-item label="状态">
          <el-select v-model="form.status" placeholder="请选择状态">
            <el-option label="在线" value="online" />
            <el-option label="离线" value="offline" />
          </el-select>
        </el-form-item>
      </el-form>
    </template>
  </base-manager>
  
  <!-- 节点列表对话框 -->
  <el-dialog
    v-model="nodesDialogVisible"
    title="终端节点列表"
    width="70%"
  >
    <el-table 
      v-loading="loadingNodes" 
      :data="nodesList" 
      border 
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="节点名称" />
      <el-table-column prop="type" label="类型" />
      <el-table-column prop="status" label="状态">
        <template #default="{ row }">
          <el-tag :type="row.status === 'online' ? 'success' : 'danger'">
            {{ row.status === 'online' ? '在线' : '离线' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="nodesDialogVisible = false">关闭</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import BaseManager from './BaseManager.vue'
import { apiService } from '../../services/api'
import { ElMessage } from 'element-plus'

// 表格列定义
const columns = [
  { prop: 'name', label: '终端名称' },
  { prop: 'status', label: '状态', width: '150', slot: true },
  { prop: 'nodes_count', label: '关联节点数', width: '150', slot: true }
]

// 默认表单数据
const defaultFormData = {
  name: '',
  status: 'online'
}

// 节点列表数据
const nodesList = ref([])
const nodesDialogVisible = ref(false)
const loadingNodes = ref(false)
const currentTerminalId = ref(null)

// 查看节点列表
const viewNodes = async (terminalId) => {
  currentTerminalId.value = terminalId
  nodesDialogVisible.value = true
  await loadNodes(terminalId)
}

// 加载节点列表
const loadNodes = async (terminalId) => {
  if (!terminalId) return
  
  loadingNodes.value = true
  try {
    const response = await apiService.customGet(`terminals/${terminalId}/nodes`)
    nodesList.value = response.data
  } catch (error) {
    console.error('加载节点失败:', error)
    ElMessage.error('加载节点列表失败')
    nodesList.value = []
  } finally {
    loadingNodes.value = false
  }
}
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
