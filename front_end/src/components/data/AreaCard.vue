<script lang="ts" setup>
import {ref, onMounted, onBeforeUnmount, defineProps, computed, watch} from 'vue'
import { nodeService,areaService } from '../services'
import apiService from '../services'
import type {AreaItem, HardwareNode} from '../types'
import {Star, Timer, Warning} from '@element-plus/icons-vue'
import HistoricalChart from './chart/HistoricalChart.vue'

const props = defineProps<{
  area: AreaItem
  buildingName?: string
  displayBuilding?: boolean
  expectStatus?: string
  compact?: boolean
}>()

// 添加弹窗状态
const showHistoryDialog = ref(false)

const nodeData = ref<HardwareNode | null>(null)
const loading = ref(true)
const displayBuilding = ref(props.displayBuilding || false)
const favoriteLoading = ref(false)
const isFavorite = ref(props.area.is_favorite)
let intervalId: number | null = null
const isComponentMounted = ref(true)

const fetchNodeData = async () => {
  if (!isComponentMounted.value) return
  
  try {
    const data = await nodeService.getDatabyAreaId(props.area.id)
    if (isComponentMounted.value) {
      nodeData.value = data
    }
  } catch (error) {
    if (isComponentMounted.value) {
      console.error(`节点数据获取失败：区域 ${props.area.id}`, error)
    }
  } finally {
    if (isComponentMounted.value) {
      loading.value = false
    }
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
  if (!isComponentMounted.value) return
  
  favoriteLoading.value = true
  try {
    await areaService.toggleFavoriteArea(props.area.id)
    if (isComponentMounted.value) {
      isFavorite.value = !isFavorite.value
      emit('favorite-change', {
        areaId: props.area.id,
        isFavorite: isFavorite.value
      })
    }
  } catch (error) {
    if (isComponentMounted.value) {
      console.error('收藏操作失败:', error)
    }
  } finally {
    if (isComponentMounted.value) {
      favoriteLoading.value = false
    }
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

const loadPercentage = computed(() => {
  if (loadRatio.value === -1) return '未知'
  return Math.round(loadRatio.value * 100) + '%'
})

onMounted(() => {
  isComponentMounted.value = true
  fetchNodeData()
  intervalId = setInterval(fetchNodeData, 5000)
})

onBeforeUnmount(() => {
  isComponentMounted.value = false
  if (intervalId !== null) {
    clearInterval(intervalId)
    intervalId = null
  }
})

// 点击区域标题显示历史数据
const showHistoryChart = () => {
  showHistoryDialog.value = true
}
</script>

<template>

  <div v-if="compact && displayCard()" class="area-card-compact" :class="{'offline': !nodeData?.status}">

    <div class="card-header-compact">
      <div class="header-main">
        <h4 class="area-name clickable-title" @click="showHistoryChart">{{ area.name }}</h4>
        <div class="status-indicator">
          <el-tag :type="nodeData?.status ? 'success' : 'danger'" effect="light" size="small" round>
            {{ nodeData?.status ? '在线' : '离线' }}
          </el-tag>
        </div>
      </div>
      
      <div class="header-meta">
        <div class="meta-tags">
          <el-tag v-if="area.building" size="small" type="info" effect="plain" class="building-tag">
            {{ area.building }}
          </el-tag>
          <div class="floor-chip">{{ area.floor }}F</div>
          <div class="env-chip">
            <el-tooltip content="温度" placement="top">
              <span><i class="el-icon-temperature"></i>{{ nodeData?.temperature || '--' }}</span>
            </el-tooltip>
            <span class="env-divider">|</span>
            <el-tooltip content="湿度" placement="top">
              <span><i class="el-icon-water-drop"></i>{{ nodeData?.humidity || '--' }}</span>
            </el-tooltip>
          </div>
        </div>
        <el-button
          :icon="Star"
          :loading="favoriteLoading"
          :type="isFavorite ? 'warning' : ''"
          circle
          class="favorite-btn-compact"
          size="small"
          @click.stop="toggleFavorite"
        ></el-button>
      </div>
    </div>

    <div class="card-body-compact">
      <div class="count-display-compact">
        <div class="count-and-capacity">
          <span class="count-number" :style="{ color: loadColor }">{{ nodeData?.detected_count || 0 }}</span>
          <span v-if="area.capacity" class="capacity-text">/ {{ area.capacity }}</span>
        </div>
        <div class="percentage-chip" :style="{ backgroundColor: loadColor }">
          {{ loadPercentage }}
        </div>
      </div>
      
      <div class="load-status-text" :style="{ color: loadColor }">
        {{ loadStatus }}
      </div>
    </div>

    <div v-if="loading" class="compact-loading-overlay">
      <div class="compact-loading-spinner"></div>
    </div>
  </div>

  <el-card v-else-if="displayCard()" :body-style="{ padding: '0px' }" class="area-card">
    <div :style="{ background: `linear-gradient(135deg, ${loadColor}22, ${loadColor}44)` }" class="card-header">
      <h3 class="clickable-title" @click="showHistoryChart">{{ area.name }}</h3>
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

    <el-skeleton :loading="loading" animated>
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
            
            <div class="env-stats">
              <el-statistic
                :value="nodeData?.temperature"
                title="温度"
                :value-style="{ color: '#409EFF' }"
                :suffix="nodeData?.temperature ? '°C' : '-'"
              />
              <el-statistic
                :value="nodeData?.humidity"
                title="湿度"
                :value-style="{ color: '#409EFF' }"
                :suffix="nodeData?.humidity ? '%' : '-'"
              />
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
  
  <!-- 历史数据弹窗 -->
  <el-dialog
    v-model="showHistoryDialog"
    :title="`${area.name} - 历史数据`"
    width="80%"
    :close-on-click-modal="false"
    :append-to-body="true"
    :destroy-on-close="true"
    top="5vh"
    class="history-dialog"
  >
    <div class="history-chart-container">
      <HistoricalChart 
        :area-id="area.id" 
        :area-name="area.name"
        height="400px" 
        chart-type="area"
      />
    </div>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="showHistoryDialog = false">关闭</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.area-card {
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
  margin: 5px 0;
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

.area-card-compact {
  background-color: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  overflow: hidden;
  border: 2px solid #ebeef5;
  margin-bottom: 15px;
  position: relative; 
  cursor: pointer;
  display: flex;
  flex-direction: column;
  height: 120px;
}

.area-card-compact:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 15px rgba(0, 0, 0, 0.08);
  border-color: #dcdfe6;
}

.area-card-compact.offline {
  background-color: #fafafa;
  border-color: #f0f0f0;
  opacity: 0.85;
}

.card-header-compact {
  padding: 12px 15px 8px;
  border-bottom: 1px solid #f0f2f5;
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.area-name {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: calc(100% - 50px);
}

.clickable-title {
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.clickable-title:hover {
  color: #409EFF !important;
  transform: translateX(2px);
}

.clickable-title::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 0;
  height: 2px;
  background: #409EFF;
  transition: width 0.3s ease;
}

.clickable-title:hover::after {
  width: 100%;
}

.status-indicator {
  flex-shrink: 0;
}

.header-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.meta-tags {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}

.building-tag {
  font-size: 10px;
  padding: 0 5px;
  height: 18px;
  line-height: 16px;
}

.floor-chip {
  background-color: #f2f6fc;
  font-size: 10px;
  padding: 0px 6px;
  border-radius: 10px;
  color: #606266;
  height: 18px;
  display: flex;
  align-items: center;
}

.favorite-btn-compact {
  padding: 4px;
  font-size: 12px;
  height: 24px;
  width: 24px;
}

.card-body-compact {
  flex: 1;
  padding: 10px 15px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.count-display-compact {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.count-and-capacity {
  display: flex;
  align-items: baseline;
}

.count-number {
  font-size: 24px;
  font-weight: 400;
  line-height: 1;
}

.capacity-text {
  font-size: 14px;
  color: #909399;
  margin-left: 3px;
}

.percentage-chip {
  color: white;
  font-size: 12px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 12px;
}

.load-status-text {
  font-size: 14px;
  font-weight: 600;
  text-align: right;
  margin-top: 5px;
}

.compact-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
}

.compact-loading-spinner {
  width: 30px;
  height: 30px;
  border: 3px solid #409EFF;
  border-radius: 50%;
  border-top-color: transparent;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .area-card-compact {
    height: 110px;
  }
  
  .card-header-compact {
    padding: 10px 12px 6px;
  }
  
  .area-name {
    font-size: 15px;
  }
  
  .card-body-compact {
    padding: 8px 12px;
  }
  
  .count-number {
    font-size: 24px;
  }
  
  .card-footer-compact {
    padding: 6px 12px;
  }
}

/* 温湿度显示样式 */
.env-stats {
  display: flex;
  margin-left: auto;
  gap: 15px;
  align-items: center;
}

.env-item {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #606266;
  font-size: 14px;
}

.env-label {
  color: #909399;
}

.env-value {
  font-weight: 500;
}

.el-icon-temperature::before {
  content: "🌡️";
  font-size: 12px;
}

.el-icon-water-drop::before {
  content: "💧";
  font-size: 12px;
}

/* 紧凑模式下的温湿度样式 */
.env-chip {
  display: flex;
  align-items: center;
  background-color: #f2f6fc;
  padding: 0 6px;
  border-radius: 10px;
  color: #606266;
  height: 18px;
  font-size: 10px;
  white-space: nowrap;
}

.env-divider {
  margin: 0 3px;
  color: #c0c4cc;
}

/* 调整紧凑模式下的标签容器，让它更好地适应多个标签 */
.meta-tags {
  flex-wrap: wrap;
  row-gap: 4px;
}

/* 弹窗样式 */
.dialog-footer {
  text-align: right;
}

.history-chart-container {
  height: 500px;
  width: 100%;
  position: relative;
  overflow: hidden;
}

:deep(.history-dialog .el-dialog__body) {
  padding: 10px 20px;
}
</style>