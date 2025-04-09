<script lang="ts" setup>
import {ref, onMounted, defineProps, computed, watch} from 'vue'
import { areaService } from '../services/apiService'
import type {AreaItem, HardwareNode} from '../types'
import {Star, Timer, Warning} from '@element-plus/icons-vue'

const props = defineProps<{
  area: AreaItem
  buildingName?: string
  displayBuilding?: boolean
  expectStatus?: string
}>()

const nodeData = ref<HardwareNode | null>(null)
const loading = ref(true)
const displayBuilding = ref(props.displayBuilding || false)
const favoriteLoading = ref(false)
const isFavorite = ref(props.area.is_favorite)

const fetchNodeData = async () => {
  try {
    // 使用areaService获取区域数据
    nodeData.value = await areaService.getAreaData(props.area.id)
  } catch (error) {
    console.error(`节点数据获取失败：区域 ${props.area.id}`, error)
  } finally {
    loading.value = false
  }
}

const displayCard = () => {
  if (props.expectStatus === 'all') return true
  if (props.expectStatus === 'online' && nodeData.value?.status === true) return true
  if (props.expectStatus === 'offline' && nodeData.value?.status === false) return true
  if (!props.expectStatus) return true
  return false
}

const emit = defineEmits(['visible-change', 'favorite-change'])

const isVisible = computed(() => displayCard())

watch(isVisible, (newVal) => {
  emit('visible-change', newVal)
}, {immediate: true})

const toggleFavorite = async () => {
  favoriteLoading.value = true
  try {
    // 使用areaService切换收藏状态
    await areaService.toggleFavoriteArea(props.area.id)
    isFavorite.value = !isFavorite.value
    emit('favorite-change', {
      areaId: props.area.id,
      isFavorite: isFavorite.value
    })
  } catch (error) {
    console.error('收藏操作失败:', error)
  } finally {
    favoriteLoading.value = false
  }
}

const loadRatio = computed(() => {
  if (!nodeData.value) return 0
  if (!props.area.capacity) return -1
  return nodeData.value.detected_count / props.area.capacity
})

const loadColor = computed(() => {
  const ratio = loadRatio.value
  if (ratio >= 0.9) return '#F56C6C'
  if (ratio >= 0.7) return '#E6A23C'
  if (ratio >= 0.5) return '#F7BA2A'
  if (ratio == -1) return '#409EFF'
  return '#67C23A'
})

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
  <el-card v-if="displayCard()" :body-style="{ padding: '0px' }" class="area-card">
    <div :style="{ background: `linear-gradient(135deg, ${loadColor}22, ${loadColor}44)` }" class="card-header">
      <h3>{{ area.name }}</h3>
      <div class="card-header-actions">
        <el-button
            :icon="Star"
            :loading="favoriteLoading"
            :title="isFavorite ? '取消收藏' : '添加收藏'"
            :type="isFavorite ? 'warning' : 'info'"
            circle
            class="favorite-btn"
            size="small"
            @click.stop="toggleFavorite"
        ></el-button>
        <el-tag :type="nodeData?.status === true ? 'success' : 'danger'" effect="dark" size="small">
          {{ nodeData?.status === true ? '在线' : '离线' }}
        </el-tag>
      </div>
    </div>

    <el-skeleton v-loading="loading" :loading="loading" animated>
      <template #default>
        <div class="metrics">
          <div class="count-display">
            <el-statistic
                :value="nodeData?.detected_count || 0"
                :value-style="{ color: loadColor }"
                title="当前人数"
            />
            <div v-if="area.capacity" class="capacity-badge">
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
                :color="loadColor"
                :indeterminate="loadRatio == -1"
                :percentage="loadRatio>=0 ? loadRatio * 100 : 30"
                :show-text="false"
                :striped="loadRatio == -1"
                :stroke-width="10"
            />
            <div :style="{ color: loadColor }" class="load-status">
              <el-icon>
                <Warning v-if="loadRatio >= 0.8"/>
              </el-icon>
              <span>{{ loadStatus }}</span>
            </div>
          </div>

          <div v-if="displayBuilding" class="info-item">
            <span class="label">所属建筑：</span>
            {{ buildingName || '未知' }}
          </div>

          <div class="info-item update-time">
            <el-icon>
              <Timer/>
            </el-icon>
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

.card-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.favorite-btn {
  transition: all 0.3s;
}

.favorite-btn:hover {
  transform: scale(1.1);
}
</style>