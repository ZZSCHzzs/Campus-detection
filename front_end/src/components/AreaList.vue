<script setup lang="ts">
import type { AreaItem } from '../types'

const props = defineProps({
  areas: {
    type: Array as () => AreaItem[],
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  },
  emptyText: {
    type: String,
    default: '暂无区域数据'
  },
  maxHeight: {
    type: String,
    default: '400px'
  }
})

const getProgressColor = (rate: number) => {
  if (rate > 0.9) return '#F56C6C'
  if (rate > 0.7) return '#E6A23C'
  if (rate > 0.5) return '#409EFF'
  return '#67C23A'
}

const getTagType = (rate: number) => {
  if (rate > 0.9) return 'danger'
  if (rate > 0.7) return 'warning'
  if (rate > 0.5) return 'info'
  return 'success'
}

const getStatusText = (count: number, capacity: number) => {
  const ratio = count / (capacity || 100);
  if (ratio >= 0.9) return '拥挤';
  if (ratio >= 0.7) return '较拥挤';
  if (ratio >= 0.5) return '适中';
  return '空闲';
}

const getStatusIcon = (count: number, capacity: number) => {
  const ratio = count / (capacity || 100);
  if (ratio >= 0.9) return 'el-icon-warning-filled';
  if (ratio >= 0.7) return 'el-icon-warning';
  if (ratio >= 0.5) return 'el-icon-info-filled';
  return 'el-icon-success-filled';
}
</script>

<template>
  <el-skeleton :rows="4" animated :loading="loading">
    <template #default>

      <div v-if="areas && areas.length > 0" class="area-list-container">
        <el-scrollbar :height="maxHeight === 'auto' ? undefined : maxHeight">
          <div class="area-grid" :style="{ 'grid-template-rows': 'auto' }">
            <div 
              v-for="area in areas" 
              :key="area.id" 
              class="area-card"
            >

              <div class="card-line">

                <div class="area-name-section">
                  <h4 class="area-name">{{ area.name }}</h4>
                  <el-tag v-if="area.building" size="small" type="info" effect="plain" class="area-building-tag">
                    {{ area.building }}
                  </el-tag>
                </div>
                

                <div class="area-data-section">
                  <div class="data-chip">
                    <span class="count-value" :style="{ color: getProgressColor(area.detected_count / (area.capacity || 100)) }">
                      {{ area.detected_count || 0 }}
                    </span>
                    <span v-if="area.capacity" class="capacity-indicator">/ {{ area.capacity }}</span>
                    <span class="stat-badge" :class="getTagType(area.detected_count / (area.capacity || 100))">
                      {{ Math.floor((area.detected_count / (area.capacity || 100)) * 100) }}%
                    </span>
                  </div>
                </div>
              </div>
              

              <div class="progress-border-container">
                <div 
                  class="progress-border" 
                  :style="{
                    width: Math.floor((area.detected_count / (area.capacity || 100)) * 100) + '%',
                    backgroundColor: getProgressColor(area.detected_count / (area.capacity || 100))
                  }"
                ></div>
              </div>
            </div>
          </div>
        </el-scrollbar>
      </div>
      

      <div v-else class="no-data-message">
        <el-empty :description="emptyText" />
      </div>
    </template>
  </el-skeleton>
</template>

<style scoped>
/* 容器样式 */
.area-list-container {
  width: 100%;
  height: 100%;
}

/* 调整网格布局 */
.area-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  grid-auto-rows: min-content;
  gap: 10px;
  padding: 5px;
}

/* 紧凑型卡片 */
.area-card {
  background-color: #ffffff;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  transition: all 0.2s;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 2px solid #ebeef5;
  margin-bottom: 5px;
  position: relative; /* 为进度条设置相对定位 */
}

.area-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.08);
}

/* 卡片主行 - 所有信息在一行内 */
.card-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  min-height: 30px;
}

/* 进度条容器 */
.progress-border-container {
  height: 2px; /* 进度条高度 */
  width: 100%;
  background-color: #f0f0f0;
  position: absolute;
  bottom: 0;
  left: 0;
}

/* 实际进度条 */
.progress-border {
  height: 100%;
  transition: all 0.3s ease;
}

/* 名称部分 */
.area-name-section {
  display: flex;
  align-items: center;
  min-width: 0;
  flex: 1;
}

.area-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0 8px 0 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.area-building-tag {
  font-size: 10px;
  padding: 0 4px;
  height: 18px;
  line-height: 18px;
}

/* 数据部分 */
.area-data-section {
  display: flex;
  align-items: center;
  white-space: nowrap;
}

.data-chip {
  display: flex;
  align-items: center;
}

.count-value {
  font-size: 16px;
  font-weight: bold;
}

.capacity-indicator {
  font-size: 12px;
  opacity: 0.7;
  margin-left: 2px;
  margin-right: 8px;
}

.stat-badge {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 10px;
  color: #fff;
  margin-left: 4px;
}

.stat-badge.success { background-color: #67C23A; }
.stat-badge.info { background-color: #409EFF; }
.stat-badge.warning { background-color: #E6A23C; }
.stat-badge.danger { background-color: #F56C6C; }

.no-data-message {
  padding: 30px 0;
  text-align: center;
}
</style>