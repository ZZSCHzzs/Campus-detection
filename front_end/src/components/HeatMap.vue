<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'
import type { AreaItem } from '../types'

const props = defineProps<{
  areas: AreaItem[]
  mapImage: string
}>()

const heatmapRef = ref<HTMLElement>()
let heatmapChart: echarts.ECharts

// 扩展区域坐标配置，添加更多点位形成更平滑的热力图
const areaCoordinates = {
  '正心12': [1526,1020],
  '正心13': [1526,1420],
  '正心21': [1526,1420],
}

// 生成随机数的辅助函数
const getRandomNumber = (min: number, max: number) => {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

// 生成热力图额外的数据点，使热力图更平滑
const generateExtraPoints = (basePoints) => {
  const extraPoints = []
  
  // 在每个已知点周围生成额外的点
  basePoints.forEach(point => {
    const [x, y, value] = point.value
    
    // 根据人流量值生成周围点的数量
    const pointCount = Math.max(3, Math.floor(value / 10))
    
    // 周围点的值会逐渐衰减
    for (let i = 0; i < pointCount; i++) {
      const distance = 20 + i * 15
      const angle = Math.random() * Math.PI * 2
      const newX = x + Math.cos(angle) * distance
      const newY = y + Math.sin(angle) * distance
      const newValue = value * (0.9 - i * 0.15)
      
      extraPoints.push({
        name: `extra_${point.name}_${i}`,
        value: [newX, newY, newValue]
      })
    }
  })
  return extraPoints
}

const initHeatmap = () => {
  if (!heatmapRef.value) return
  
  heatmapChart = echarts.init(heatmapRef.value)
  
  // 注册自定义地图
  echarts.registerMap('custom', {
    type: 'FeatureCollection',
    features: [{
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [0, 0],
          [2000, 0],
          [2000, 2000],
          [0, 2000],
          [0, 0]
        ]]
      }
    }]
  })
  
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      position: 'item',
      formatter: (params: any) => {
        if (!params.name.startsWith('extra_')) {
          return `${params.name}: ${Math.round(params.value[2])} 人`
        } else {
          return ''
        }
      },
      confine: true
    },
    visualMap: {
      min: 0,
      max: 120,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: '5%',
      show: false,
      inRange: {
        color: [
          'rgba(0, 156, 255, 0.3)',
          'rgba(0, 156, 255, 0.5)',
          'rgba(0, 156, 255, 0.7)',
          'rgba(0, 213, 255, 0.7)',
          'rgba(0, 255, 255, 0.7)',
          'rgba(0, 255, 184, 0.8)',
          'rgba(92, 255, 71, 0.8)',
          'rgba(255, 235, 59, 0.9)',
          'rgba(255, 152, 0, 0.9)',
          'rgba(255, 87, 34, 1)',
          'rgba(255, 0, 0, 1)'
        ]
      }
    },
    geo: {
      map: 'custom',
      roam: false,
      itemStyle: {
        normal: {
          areaColor: 'transparent',
          borderColor: 'transparent'
        },
        emphasis: {
          areaColor: 'transparent'
        }
      },
      silent: true,
      zoom: 1,
      layoutCenter: ['50%', '50%'],
      layoutSize: '100%'
    },
    series: [{
      name: '人流量',
      type: 'heatmap',
      coordinateSystem: 'geo',
      data: [],
      pointSize: 18,
      blurSize: 25,
      minOpacity: 0.4,
      maxOpacity: 0.9,
      animation: true,
      animationDuration: 1000,
      animationEasing: 'cubicOut',
      itemStyle: {
        opacity: 0.8
      },
      emphasis: {
        itemStyle: {
          opacity: 1
        }
      }
    }]
  }

  heatmapChart.setOption(option)
  updateHeatmap()
}

// 更新热力图数据
const updateHeatmap = () => {
  if (!heatmapChart) return
  // 基础数据点 - 从实际区域数据中生成
  const basePoints = props.areas.map(area => {
    const coordinates = areaCoordinates[area.name]
    if (!coordinates) {
      return null
    }
    
    // 使用真实数据或生成随机数据
    const value = area.detected_count ?? getRandomNumber(10, 100)
    
    return {
      name: area.name,
      value: [...coordinates, value]
    }
  }).filter(Boolean)
  
  // 为未在areas中但在坐标配置中的点位添加虚拟数据
  Object.keys(areaCoordinates).forEach(name => {
    if (!name.startsWith('point_')) return
    
    if (!basePoints.some(p => p.name === name)) {
      basePoints.push({
        name,
        value: [...areaCoordinates[name], getRandomNumber(15, 80)]
      })
    }
  })
  
  // 生成额外的数据点来增强热力图效果
  const extraPoints = generateExtraPoints(basePoints)
  
  // 合并所有数据点
  const allPoints = [...basePoints, ...extraPoints]
  
  heatmapChart.setOption({
    series: [{
      data: allPoints
    }]
  })
}

// 监听areas数据变化
watch(() => props.areas, updateHeatmap, { deep: true })

// 监听窗口大小变化
window.addEventListener('resize', () => {
  heatmapChart?.resize()
})

onMounted(() => {
  initHeatmap()
  // 定期更新热力图数据
  setInterval(updateHeatmap, 1000)
})
</script>

<template>
  <div class="heatmap-container">
    <div class="map-background" :style="{ backgroundImage: `url(${mapImage})` }"></div>
    <div ref="heatmapRef" class="heatmap-canvas"></div>
    <div class="heatmap-title">
      <h2 class="title-text">实时热力分布图</h2>
      <div class="subtitle-text">Campus Heat Distribution</div>
    </div>
    <div class="tech-decoration top-right"></div>
    <div class="tech-decoration bottom-left"></div>
  </div>
</template>

<style scoped>
.heatmap-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
  padding: 20px;
  background-color: rgba(20, 28, 47, 1.0);
  border-radius: 12px;
  overflow: hidden;
}

.map-background {
  position: absolute;
  top: 5%;
  left: 5%;
  width: 90%;
  height: 90%;
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  opacity: 1;
  filter: brightness(0.9) contrast(1.1);
  border-radius: 8px;
  mask-image: radial-gradient(
    ellipse 80% 80% at center,
    black 40%,
    rgba(0, 0, 0, 0.9) 50%,
    rgba(0, 0, 0, 0.7) 65%,
    rgba(0, 0, 0, 0.4) 80%,
    transparent 100%
  );
  -webkit-mask-image: radial-gradient(
    ellipse 80% 80% at center,
    black 40%,
    rgba(0, 0, 0, 0.9) 50%,
    rgba(0, 0, 0, 0.7) 65%,
    rgba(0, 0, 0, 0.4) 80%,
    transparent 100%
  );
}

.heatmap-canvas {
  position: absolute;
  top: 5%;
  left: 5%;
  width: 90%;
  height: 90%;
  z-index: 1;
}

.heatmap-title {
  position: absolute;
  top: 15px;
  left: 20px;
  z-index: 2;
  display: flex;
  align-items: center; /* 垂直居中对齐 */
  gap: 10px; /* 标题与副标题间距 */
  margin-bottom: 6px;
  flex-shrink: 0;
}

.title-text {
  font-size: 0.95rem;
  font-weight: 500;
  color: #fff;
  margin: 0;
  white-space: nowrap; /* 防止标题换行 */
}

.subtitle-text {
  font-size: 0.7rem;
  color: #94a3b8;
  position: relative;
  padding-left: 10px; /* 为分隔线留出空间 */
}

/* 添加垂直分隔线 */
.subtitle-text::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  height: 12px;
  width: 1px;
  background: rgba(56, 189, 248, 0.5);
}
.tech-decoration {
  position: absolute;
  width: 80px;
  height: 80px;
  z-index: 2;
  pointer-events: none;
}

.tech-decoration.top-right {
  top: 10px;
  right: 10px;
  border-top: 2px solid rgba(0, 195, 255, 0.7);
  border-right: 2px solid rgba(0, 195, 255, 0.7);
}

.tech-decoration.bottom-left {
  bottom: 10px;
  left: 10px;
  border-bottom: 2px solid rgba(0, 195, 255, 0.7);
  border-left: 2px solid rgba(0, 195, 255, 0.7);
}

/* 添加闪烁动画效果 */
@keyframes pulse {
  0% {
    box-shadow: 0 0 8px rgba(0, 195, 255, 0.5);
  }
  50% {
    box-shadow: 0 0 15px rgba(0, 195, 255, 0.8);
  }
  100% {
    box-shadow: 0 0 8px rgba(0, 195, 255, 0.5);
  }
}

.heatmap-container {
  animation: pulse 4s infinite;
}

/* 添加外发光效果增强过渡感 */
.heatmap-container::after {
  content: '';
  position: absolute;
  top: 5%;
  left: 5%;
  width: 90%;
  height: 90%;
  border-radius: 8px;
  box-shadow: inset 0 0 60px 40px rgba(20, 28, 47, 0.7);
  pointer-events: none;
  z-index: 2;
}
</style>