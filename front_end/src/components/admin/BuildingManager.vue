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

    <!-- 新增：类型列显示 -->
    <template #column-category="{ row }">
      <el-tag type="info">{{ categoryLabelMap[row.category] || '其他' }}</el-tag>
    </template>

    <template #form="{ form }">
      <el-form :model="form" label-width="100px">
        <el-form-item label="建筑名称" required>
          <el-input v-model="form.name" placeholder="请输入建筑名称" />
        </el-form-item>

        <!-- 新增：建筑类型选择 -->
        <el-form-item label="建筑类型" required>
          <el-select v-model="form.category" placeholder="请选择建筑类型">
            <el-option
              v-for="opt in CATEGORY_OPTIONS"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
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
      </el-form>
    </template>
  </base-manager>
</template>

<script setup lang="ts">
import BaseManager from './BaseManager.vue'
import View from './View.vue'

// 新增：类型选项与显示映射
const CATEGORY_OPTIONS = [
  { value: 'library', label: '图书馆/阅览室' },
  { value: 'study', label: '自习室/学习空间' },
  { value: 'teaching', label: '教学楼/教室' },
  { value: 'cafeteria', label: '食堂/餐饮' },
  { value: 'dorm', label: '宿舍' },
  { value: 'lab', label: '实验室/科研' },
  { value: 'office', label: '行政/办公' },
  { value: 'sports', label: '体育场馆' },
  { value: 'service', label: '服务/办事大厅' },
  { value: 'other', label: '其他' },
]
const categoryLabelMap = CATEGORY_OPTIONS.reduce((acc, cur) => {
  acc[cur.value] = cur.label
  return acc
}, {} as Record<string, string>)

const columns = [
  { prop: 'name', label: '建筑名称', width: '300', mobileWidth: '150' },
  { prop: 'category', label: '类型', width: '160', mobileWidth: '100', slot: true },
  { prop: 'description', label: '描述', hideOnMobile: true },
  { prop: 'areas_count', label: '区域数量', width: '250', mobileWidth: '120', slot: true },
  { prop: '', label: '' }
]

const defaultFormData = {
  name: '',
  description: '',
  category: 'other'
}
</script>
