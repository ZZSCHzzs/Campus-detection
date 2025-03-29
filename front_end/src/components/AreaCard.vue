<script setup lang="ts">
import { ref, onMounted, defineProps, computed, watch } from 'vue'
import axios from '../axios'
import type { AreaItem, HardwareNode } from '../types'  // 移除 Building 类型

const props = defineProps<{
  area: AreaItem
  buildingName?: string  // 修改 prop 类型为字符串
  displayBuilding?: boolean
  expectStatus?: string
}>()

const nodeData = ref<HardwareNode | null>(null)
const loading = ref(true)
const displayBuilding = ref(props.displayBuilding || false)  // 初始化 displayBuilding 状态


const fetchNodeData = async () => {
  try {
    const { data } = await axios.get(`/api/areas/${props.area.id}/data`)
    nodeData.value = data
  } catch (error) {
    console.error(`节点数据获取失败：区域 ${props.area.id}`, error)
  } finally {
    loading.value = false
  }
}

const displayCard = () => {
  if(props.expectStatus === 'all') return true
  if(props.expectStatus === 'online' && nodeData.value?.status === true) return true
  if(props.expectStatus === 'offline' && nodeData.value?.status === false) return true
  return false
}

const emit = defineEmits(['visible-change'])

// 添加计算属性判断可见性
const isVisible = computed(() => displayCard())

// 当可见性变化时触发事件
watch(isVisible, (newVal) => {
  emit('visible-change', newVal)
}, { immediate: true })

onMounted(() => {
  fetchNodeData()
  setInterval(fetchNodeData, 30000)
})
</script>

<template>
  <el-card class="area-card" v-if="displayCard()">
    <h3>{{ area.name }}</h3>
    <el-skeleton :loading="loading" animated v-loading="loading">
      <template #default>
        <div class="metrics">
          <el-statistic 
            title="当前人数" 
            :value="nodeData?.detected_count || 0" 
          />
          
          <div class="info-item" v-if="displayBuilding">
            <span class="label">所属建筑：</span>
            {{ buildingName || '未知' }} 
          </div>
          
          <div class="info-item">
            <span class="label">节点状态：</span>
            <el-tag :type="nodeData?.status === true ? 'success' : 'danger'">
              {{ nodeData?.status === true ? '在线' : '离线' }}
            </el-tag>
          </div>
          
          <div class="info-item">
            <span class="label">最后更新：</span>
            {{ nodeData ? new Date(nodeData.updated_at).toLocaleString() : '无数据' }}
          </div>
        </div>
      </template>
    </el-skeleton>
  </el-card>
</template>

<style scoped>
.area-card {
  margin-bottom:5px;
  height: 100%;
}

.metrics {
  padding: 10px 0;
}

.info-item {
  margin: 8px 0;
  font-size: 14px;
}

.label {
  color: #666;
  margin-right: 8px;
}
</style>