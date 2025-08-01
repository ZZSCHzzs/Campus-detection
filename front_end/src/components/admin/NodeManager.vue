<template>
  <base-manager
    title="硬件节点管理"
    resource-name="nodes"
    :dataLink="props.dataLink"
    item-name="硬件节点"
    :columns="columns"
    :default-form-data="defaultFormData"
  >
    <template #column-status="{ row }">
      <el-tag :type="row.status === true ? 'success' : 'danger'">
        {{ row.status === true ? '在线' : '离线' }}
      </el-tag>
    </template>
    <template #column-terminal="{ row }">
    <div style="display: flex; align-items: center;">
      <el-tag>{{ getTerminalName(row.terminal) }}</el-tag>
      <Jump :module="'terminals'" :name="getTerminalName(row.terminal)" />
    </div>
    </template>
    
    <template #column-temperature="{ row }">
      <span v-if="row.temperature !== undefined && row.temperature !== null">
        {{ row.temperature.toFixed(1) }}°C
      </span>
      <span v-else>-</span>
    </template>
    
    <template #column-humidity="{ row }">
      <span v-if="row.humidity !== undefined && row.humidity !== null">
        {{ row.humidity.toFixed(0) }}%
      </span>
      <span v-else>-</span>
    </template>
    
    <template #form="{ form }">
      <el-form :model="form" label-width="100px">
        <el-form-item label="节点名称" required>
          <el-input v-model="form.name" placeholder="请输入节点名称" />
        </el-form-item>
        
        <el-form-item label="状态">
          <el-select v-model="form.status" placeholder="请选择状态">
            <el-option label="在线" value="true" />
            <el-option label="离线" value="false" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="检测人数">
          <el-input v-model="form.detected_count" placeholder="请输入人数" />
        </el-form-item>
        
        <el-form-item label="所属终端">
          <el-select 
            v-model="form.terminal" 
            placeholder="请选择终端"

            remote
            :remote-method="fetchTerminals"
            :loading="loadingTerminals"
          >
            <el-option
              v-for="item in terminals"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input 
            v-model="form.description" 
            type="textarea" 
            placeholder="请输入描述" 
            rows="3"
          />
        </el-form-item>
        
        <el-form-item label="温度">
          <el-input-number 
            v-model="form.temperature" 
            :precision="1" 
            :step="0.1"
            :min="0"
            :max="50"
            placeholder="请输入温度值"
          />
          <span class="form-input-suffix">°C</span>
        </el-form-item>
        
        <el-form-item label="湿度">
          <el-input-number 
            v-model="form.humidity" 
            :precision="0" 
            :step="1"
            :min="0"
            :max="100"
            placeholder="请输入湿度值"
          />
          <span class="form-input-suffix">%</span>
        </el-form-item>
      </el-form>
    </template>
  </base-manager>
</template>

<script setup>
import { ref } from 'vue'
import BaseManager from './BaseManager.vue'
import { terminalService } from '../../services'
import Jump from './Jump.vue'
import {defineProps}  from 'vue'

const props = defineProps({
  dataLink: {
    type: String,
    default: ''
  }
})
const dataLink = ref()

const columns = [
  { prop: 'name', label: '节点名称', width: '180', mobileWidth: '130' },
  { prop: 'detected_count', label: '检测人数', width: '120', mobileWidth: '80' },
  { prop: 'terminal', label: '所属终端', width: '150', mobileWidth: '150', slot: true },
  { prop: 'status', label: '状态', width: '100', mobileWidth: '65', slot: true },
  { prop: 'temperature', label: '温度', width: '100', mobileWidth: '80', slot: true },
  { prop: 'humidity', label: '湿度', width: '100', mobileWidth: '80', slot: true },
  { prop: 'updated_at', label: '更新时间', width: '180', 
    formatter: (row) => new Date(row.updated_at).toLocaleString() },
  { prop: 'description', label: '描述', hideOnMobile: true }
]

const defaultFormData = {
  name: '',
  status: 'online',
  terminal: null,
  description: '',
  detected_count: 0,
  temperature: undefined,
  humidity: undefined
}

const terminals = ref([])
const loadingTerminals = ref(false)

const fetchTerminals = async () => {
    loadingTerminals.value = true
    try {
      terminals.value = await terminalService.getAll()
    } catch (error) {
      console.error('获取终端失败:', error)
    } finally {
      loadingTerminals.value = false
    }
}
fetchTerminals()

const getTerminalName = (id) => {
  const terminal = terminals.value.find(item => item.id === id)
  return terminal ? terminal.name : '未知'
}

</script>

<style scoped>
.form-input-suffix {
  margin-left: 8px;
  color: #606266;
}
</style>
