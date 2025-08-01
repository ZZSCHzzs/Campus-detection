<script setup lang="ts">
import type { AreaItem } from '../../types.ts'
import { computed } from 'vue'

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

const calculateRatio = (count: number | undefined | null, capacity: number | undefined | null) => {

  if (!capacity) return -1;
  return (count || 0) / capacity;
}

const getProgressColor = (rate: number) => {

  if (rate >= 0.9) return '#F56C6C'
  if (rate >= 0.7) return '#E6A23C'
  if (rate >= 0.3) return '#67C23A'
  if (rate == -1) return '#409EFF'
  return '#409EFF'
}

const getTagType = (rate: number) => {

  if (rate === -1) return 'info'
  if (rate > 0.9) return 'danger'
  if (rate > 0.7) return 'warning'
  if (rate > 0.3) return 'success'
  return 'info'
}

const getStatusText = (rate: number) => {

  if (rate === -1) return '未设置容量';
  if (rate >= 0.9) return '拥挤';
  if (rate >= 0.7) return '较拥挤';
  if (rate >= 0.3) return '适中';
  return '空闲';
}

const getStatusIcon = (rate: number) => {

  if (rate === -1) return 'el-icon-info';
  if (rate >= 0.9) return 'el-icon-warning-filled';
  if (rate >= 0.7) return 'el-icon-warning';
  if (rate >= 0.3) return 'el-icon-success-filled';
  return 'el-icon-info-filled';
}

const processedAreas = computed(() => {
  return props.areas.map(area => {
    const ratio = calculateRatio(area.detected_count, area.capacity);
    return {
      ...area,
      ratio,
      progressColor: getProgressColor(ratio),
      tagType: getTagType(ratio),
      statusText: getStatusText(ratio),
      statusIcon: getStatusIcon(ratio),
      percentDisplay: ratio === -1 ? '未知' : `${Math.floor(ratio * 100)}%`
    };
  });
});
</script>

<template>
  <el-skeleton :rows="4" animated :loading="loading">
    <template #default>

      <div v-if="areas && areas.length > 0" class="area-list-container">
        <el-scrollbar :height="maxHeight === 'auto' ? undefined : maxHeight" class="no-horizontal-scroll">
          <div class="row-container">
            <el-row :gutter="10">
              <el-col 
                v-for="area in processedAreas" 
                :key="area.id"
                :xs="24" 
                :sm="12" 
                :md="8" 
                :lg="6" 
                :xl="6"
                class="area-col"
              >
                <div class="area-card">
                  <div class="card-line">

                  <div class="area-name-section">
                    <h4 class="area-name">{{ area.name }}</h4>
                    <el-tag v-if="area.building" size="small" type="info" effect="plain" class="area-building-tag">
                      {{ area.building }}
                    </el-tag>
                  </div>
                  
                  <div class="area-data-section">
                    <div class="data-chip">
                      <span class="count-value" :style="{ color: area.progressColor }">
                        {{ area.detected_count || 0 }}
                      </span>
                      <span v-if="area.capacity" class="capacity-indicator">/ {{ area.capacity }}</span>
                      <span class="stat-badge" :class="area.tagType">
                        {{ area.percentDisplay }}
                      </span>
                    </div>
                  </div>
                </div>
                
                <div class="progress-border-container">
                  <div 
                    class="progress-border" 
                    :style="{
                      width: area.ratio === -1 ? '0%' : Math.floor(area.ratio * 100) + '%',
                      backgroundColor: area.progressColor
                    }"
                  ></div>
                </div>
                </div>
              </el-col>
            </el-row>
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

.area-list-container {
  width: 100%;
  height: 100%;
}

.row-container {
  width: 100%;
  padding: 0 5px;
  box-sizing: border-box;
}

.no-horizontal-scroll {
  overflow-x: hidden !important;
}

.area-col {
  margin-bottom: 10px;
}

.area-card {
  background-color: #ffffff;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  transition: all 0.2s;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 2px solid #ebeef5;
  position: relative;
  height: 100%;
}

.card-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  min-height: 30px;
}

.progress-border-container {
  height: 2px;
  width: 100%;
  background-color: #f0f0f0;
  position: absolute;
  bottom: 0;
  left: 0;
}

.progress-border {
  height: 100%;
  transition: all 0.3s ease;
}

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