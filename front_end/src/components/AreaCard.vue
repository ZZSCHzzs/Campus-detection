<script setup lang="ts">
import { ref, onMounted, defineProps, computed, watch } from 'vue'
import axios from '../axios'
import type { AreaItem, HardwareNode } from '../types'

const props = defineProps<{
  area: AreaItem
  buildingName?: string
  displayBuilding?: boolean
  expectStatus?: string
}>()

const nodeData = ref<HardwareNode | null>(null)
const loading = ref(true)
const displayBuilding = ref(props.displayBuilding || false)

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

// 计算负载率
const loadRatio = computed(() => {
  if (!nodeData.value) return 0
  if(!props.area.capacity) return -1
  return nodeData.value.detected_count / props.area.capacity
})

// 根据负载率决定颜色
const loadColor = computed(() => {
  const ratio = loadRatio.value
  if (ratio >= 0.9) return '#F56C6C' // 高负载 - 红色
  if (ratio >= 0.7) return '#E6A23C' // 中高负载 - 橙色
  if (ratio >= 0.5) return '#F7BA2A' // 中负载 - 黄色
  if (ratio == -1) return '#409EFF' // 未知 - 蓝色
  return '#67C23A' // 低负载 - 绿色
})

// 负载状态文本
const loadStatus = computed(() => {
  const ratio = loadRatio.value
  if (ratio >= 0.9) return '拥挤'
  if (ratio >= 0.7) return '较拥挤'
  if (ratio >= 0.5) return '适中'
  if (ratio == -1) return ''
  return '空闲'
})

onMounted(() => {
  fetchNodeData()
  setInterval(fetchNodeData, 30000)
})
</script>

<template>
  <el-card class="area-card" v-if="displayCard()" :body-style="{ padding: '0px' }">
    <div class="card-header" :style="{ background: `linear-gradient(135deg, ${loadColor}22, ${loadColor}44)` }">
      <h3>{{ area.name }}</h3>
      <el-tag size="small" :type="nodeData?.status === true ? 'success' : 'danger'" effect="dark">
        {{ nodeData?.status === true ? '在线' : '离线' }}
      </el-tag>
    </div>
    
    <el-skeleton :loading="loading" animated v-loading="loading">
      <template #default>
        <div class="metrics">
          <div class="count-display">
            <el-statistic 
              title="当前人数" 
              :value="nodeData?.detected_count || 0" 
              :value-style="{ color: loadColor }"
            />
            <div class="capacity-badge" v-if="area.capacity">
              <span>/{{ area.capacity }}</span>
            </div>
          </div>
          
          <div class="load-progress">
            <div class="load-label">
              <span>负载率</span>
              <div v-if="loadRatio == -1" class="load-percentage">未知</div>
              <div v-else>
                <span class="load-percentage">{{ Math.round(loadRatio * 100) }}%</span>
              </div>
              
            </div>
            <el-progress 
              :percentage="loadRatio>=0 ? loadRatio * 100 : 30" 
              :color="loadColor"
              :stroke-width="10"
              :indeterminate="loadRatio == -1"
              :show-text="false"
              :striped="loadRatio == -1"
            />
            <div class="load-status" :style="{ color: loadColor }">
              <el-icon><Warning v-if="loadRatio >= 0.8" /></el-icon>
              <span>{{ loadStatus }}</span>
            </div>
          </div>
          
          <div class="info-item" v-if="displayBuilding">
            <span class="label">所属建筑：</span>
            {{ buildingName || '未知' }} 
          </div>
          
          <div class="info-item update-time">
            <el-icon><Timer /></el-icon>
            <span>{{ nodeData ? new Date(nodeData.updated_at).toLocaleString() : '无数据' }}</span>
          </div>
        </div>
      </template>
    </el-skeleton>
  </el-card>
</template>

<style scoped>
.area-card {
  margin-bottom: 0;
  height: 100%;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.area-card:hover {
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
  transform: translateY(-3px);
}

.card-header {
  padding: 12px 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.metrics {
  padding: 15px;
}

.count-display {
  position: relative;
  display: flex;
  align-items: flex-end;
  margin-bottom: 15px;
}

.capacity-badge {
  margin-left: 5px;
  margin-bottom: 3px;
  color: #909399;
  font-size: 14px;
}

.load-progress {
  margin: 15px 0;
}

.load-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
  font-size: 14px;
  color: #606266;
}

.load-percentage {
  font-weight: bold;
}

.load-status {
  margin-top: 5px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 5px;
  font-size: 14px;
  font-weight: 500;
}

.info-item {
  margin: 10px 0;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.label {
  color: #909399;
}

.update-time {
  margin-top: 15px;
  color: #909399;
  font-size: 12px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 5px;
}
</style>