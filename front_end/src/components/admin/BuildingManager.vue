<template>
  <base-manager
    title="建筑管理"
    resource-name="buildings"
    item-name="建筑"
    :columns="columns"
    :default-form-data="defaultFormData"
  >
    <template #column-areas_count="{ row }">
      <el-tag>{{ row.areas_count || 0 }}</el-tag>
      <View resource="areas" data="buildings" :id="row.id" />
    </template>
    <template #form="{ form }">
      <el-form :model="form" label-width="100px">
        <el-form-item label="建筑名称" required>
          <el-input v-model="form.name" placeholder="请输入建筑名称" />
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
import BaseManager from './BaseManager.vue'
import View from './View.vue'

const columns = [
  { prop: 'name', label: '建筑名称', width: '300', mobileWidth: '150' },
  { prop: 'description', label: '描述', hideOnMobile: true },
  { prop: 'areas_count', label: '区域数量', width: '250', mobileWidth: '120', slot: true },
  { prop: '', label: '', }
]

const defaultFormData = {
  name: '',
  description: ''
}
</script>
