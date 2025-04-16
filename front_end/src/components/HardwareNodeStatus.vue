<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import { nodeService } from '../services/apiService'
import type { HardwareNode } from '../types'

const props = defineProps<{
  areaId: number | null
}>()

const nodes = ref<HardwareNode[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
let updateInterval: number | null = null

// 获取节点数据
const fetchNodeData = async () => {
  if (!props.areaId) return
  
  loading.value = true
  error.value = null
  
  try {
    nodes.value = await nodeService.getAll()
  } catch (err) {
    error.value = '获取节点数据失败'
    console.error('获取节点数据失败:', err)
  } finally {
    loading.value = false
  }
}

// 格式化时间
const formatTime = (value: string) => {
  if (!value) return '--:--'
  
  try {
    const date = new Date(value)
    
    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      return value
    }
    
    // 如果是今天的日期，只显示时间
    const today = new Date()
    if (date.toDateString() === today.toDateString()) {
      return date.toLocaleTimeString('zh-CN', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
      })
    } else {
      // 否则显示日期+时间(简短格式)
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      }).replace(/\//g, '-')
    }
  } catch (error) {
    console.error('日期格式化错误:', error)
    return value
  }
}

// 当areaId变化时获取新数据
watch(() => props.areaId, (newAreaId) => {
  if (newAreaId) {
    fetchNodeData()
  } else {
    nodes.value = []
  }
})

// 组件挂载时获取数据并设置定时刷新
onMounted(() => {
  fetchNodeData()
  
  // 每10秒刷新一次数据
  updateInterval = window.setInterval(fetchNodeData, 10000)
})

// 组件卸载时清除定时器
onUnmounted(() => {
  if (updateInterval) {
    clearInterval(updateInterval)
  }
})
</script>

<template>
  <div class="hardware-nodes-container">
    <!-- 加载状态 -->
    <div v-if="loading && nodes.length === 0" class="nodes-loading">
      <div class="nodes-loading-spinner"></div>
      <span>加载节点数据中...</span>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="error" class="nodes-error">
      <div class="error-icon">⚠️</div>
      <span>{{ error }}</span>
      <button @click="fetchNodeData" class="retry-button">重试</button>
    </div>
    
    <!-- 没有节点数据 -->
    <div v-else-if="nodes.length === 0" class="nodes-empty">
      <span>暂无节点数据</span>
    </div>
    
    <!-- 节点卡片群 -->
    <div v-else class="nodes-grid">
      <div 
        v-for="node in nodes" 
        :key="node.id" 
        class="node-card"
        :class="{ 'node-active': node.status, 'node-inactive': !node.status }"
      >
        <div class="node-header">
          <span class="node-name">{{ node.name }}</span>
          <span class="node-status-badge" :class="{ 'status-active': node.status }">
            {{ node.status ? '在线' : '离线' }}
          </span>
        </div>
        
        <div class="node-body">
          <div class="node-stat">
            <div class="stat-label">检测人数</div>
            <div class="stat-value">{{ node.detected_count }}</div>
          </div>
          
          <div class="node-stat">
            <div class="stat-label">更新时间</div>
            <div class="stat-time">{{ formatTime(node.updated_at) }}</div>
          </div>
        </div>
        
        <!-- 状态指示器 -->
        <div class="tech-indicator" :class="{ 'active': node.status }"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hardware-nodes-container {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.nodes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  padding: 5px;
  overflow-y: auto;
  max-height: 100%;
}

.node-card {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 8px;
  padding: 12px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
}

.node-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 15px rgba(0, 0, 0, 0.25);
}

.node-active {
  border-left: 3px solid #22c55e;
}

.node-inactive {
  border-left: 3px solid #ef4444;
  opacity: 0.8;
}

.node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.node-name {
  font-weight: 500;
  color: #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.node-status-badge {
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 0.6rem;
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.node-status-badge.status-active {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.node-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.node-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  font-size: 0.7rem;
  color: #94a3b8;
}

.stat-value {
  font-size: 1.1rem;
  font-weight: bold;
  background: linear-gradient(45deg, #38bdf8, #818cf8);
  -webkit-background-clip: text;
  color: transparent;
}

.stat-time {
  font-size: 0.8rem;
  color: #94a3b8;
}

/* 技术感指示器 */
.tech-indicator {
  position: absolute;
  top: 0;
  right: 0;
  width: 8px;
  height: 100%;
  background: rgba(239, 68, 68, 0.3);
}

.tech-indicator.active {
  background: rgba(34, 197, 94, 0.3);
  animation: pulse-active 2s infinite;
}

@keyframes pulse-active {
  0% { opacity: 0.7; }
  50% { opacity: 1; }
  100% { opacity: 0.7; }
}

/* 加载状态样式 */
.nodes-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
  gap: 12px;
}

.nodes-loading-spinner {
  width: 30px;
  height: 30px;
  border: 3px solid rgba(56, 189, 248, 0.3);
  border-top: 3px solid #38bdf8;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 错误状态样式 */
.nodes-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #f87171;
  gap: 10px;
}

.error-icon {
  font-size: 24px;
}

.retry-button {
  margin-top: 8px;
  background: rgba(244, 63, 94, 0.2);
  color: #f43f5e;
  border: 1px solid rgba(244, 63, 94, 0.5);
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.retry-button:hover {
  background: rgba(244, 63, 94, 0.3);
  transform: translateY(-2px);
}

/* 空状态样式 */
.nodes-empty {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #94a3b8;
  font-style: italic;
}
</style>