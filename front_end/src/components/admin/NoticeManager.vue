<template>
  <base-manager
    title="公告管理"
    resource-name="notice"
    :dataLink="props.dataLink"
    item-name="公告"
    :columns="columns"
    :default-form-data="defaultFormData"
  >
    <template #column-related_areas="{ row }">
      <div class="area-tags">
        <el-tag v-for="areaId in row.related_areas" :key="areaId" class="area-tag">
          {{ getAreaName(areaId) }}
          <Jump :module="'areas'" :name="getAreaName(areaId)" :no_padding='true' />
        </el-tag>
        
        <el-tag v-if="!row.related_areas || row.related_areas.length === 0" type="info">
          全局公告
        </el-tag>
      </div>
    </template>
    
    <template #form="{ form }">
      <el-form :model="form" label-width="100px">
        <el-form-item label="公告标题" required>
          <el-input v-model="form.title" placeholder="请输入公告标题" />
        </el-form-item>
        
        <el-form-item label="公告内容" required>
          <el-input 
            v-model="form.content" 
            type="textarea" 
            placeholder="请输入公告内容" 
            rows="5"
          />
        </el-form-item>
        
        <el-form-item label="相关区域">
          <el-select 
            v-model="form.related_areas" 
            placeholder="请选择相关区域"
            multiple
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
          <div class="form-tip">不选择任何区域则作为全局公告</div>
        </el-form-item>
      </el-form>
    </template>
  </base-manager>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import BaseManager from './BaseManager.vue'
import { areaService } from '../../services'
import { defineProps } from 'vue'
import Jump from './Jump.vue'

const props = defineProps({
  dataLink: {
    type: String,
    default: ''
  }
})

const columns = [
  { prop: 'title', label: '公告标题', width: '200', mobileWidth: '150' },
  { prop: 'content', label: '公告内容', mobileWidth: '200' },
  { prop: 'related_areas', label: '相关区域', width: '200', mobileWidth: '150', slot: true },
  { prop: 'timestamp', label: '发布时间', width: '180', hideOnMobile: true,
    formatter: (row) => new Date(row.timestamp).toLocaleString() }
]

const defaultFormData = {
  title: '',
  content: '',
  related_areas: []
}

const areas = ref([])
const loadingAreas = ref(false)

const fetchAreas = async () => {
  loadingAreas.value = true
  try {
    areas.value = await areaService.getAll()
  } catch (error) {
    console.error('获取区域失败:', error)
  } finally {
    loadingAreas.value = false
  }
}

const getAreaName = (id) => {
  const area = areas.value.find(item => item.id === id)
  return area ? area.name : '未知区域'
}

onMounted(() => {
  fetchAreas()
})
</script>

<style scoped>
.area-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.area-tag {
  margin-right: 5px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}
</style>
