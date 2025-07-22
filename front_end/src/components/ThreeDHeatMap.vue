<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js'
import type { AreaItem } from '../types'

const props = defineProps<{
  areas: AreaItem[]
  mapImage: string
}>()

const heatmapRef = ref<HTMLElement | null>(null)
const loadingError = ref<string | null>(null)
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let controls: OrbitControls
let animationFrameId: number

// 添加调试状态
const showDebugInfo = ref(false)
const modelStructure = ref<{name: string, type: string, depth: number, id: string}[]>([])

// 添加模型引用映射和高亮状态
const modelObjectsMap = ref<Map<string, THREE.Object3D>>(new Map())
const originalMaterials = ref<Map<string, THREE.Material | THREE.Material[]>>(new Map())
const highlightedObjectId = ref<string | null>(null)

// 初始化Three.js场景
const initThreeScene = () => {
  if (!heatmapRef.value) return

  // 创建场景
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x141c2f)

  // 设置相机
  const { clientWidth, clientHeight } = heatmapRef.value
  camera = new THREE.PerspectiveCamera(45, clientWidth / clientHeight, 0.1, 1000)
  camera.position.set(0, 10, 15)
  
  // 创建渲染器
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(clientWidth, clientHeight)
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  heatmapRef.value.appendChild(renderer.domElement)
  
  // 添加轨道控制器
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.minDistance = 5
  controls.maxDistance = 30
  controls.maxPolarAngle = Math.PI / 2
  

  // 加载OBJ建筑模型
  loadBuildingModel()
  
  // 渲染动画
  animate()
  
  // 添加窗口大小调整监听
  window.addEventListener('resize', onWindowResize)
}

// 加载OBJ建筑模型
const loadBuildingModel = () => {
  const mtlLoader = new MTLLoader()
  
  mtlLoader.load('/models/campus.mtl', (materials) => {
    materials.preload()
    
    const objLoader = new OBJLoader()
    objLoader.setMaterials(materials)
    objLoader.load(
      '/models/campus.obj',
      (object) => {
        // 先缩放模型
        object.scale.set(0.1, 0.1, 0.1)
        
        // 计算模型边界盒
        const boundingBox = new THREE.Box3().setFromObject(object)
        // 获取边界盒中心点
        const center = boundingBox.getCenter(new THREE.Vector3())
        // 将模型位置移动，使中心点与原点重合
        object.position.x = -center.x
        object.position.z = -center.z
        // Y轴可以根据需要单独调整，例如使模型底部与地面对齐
        object.position.y = -boundingBox.min.y
        
        // 为模型添加阴影
        object.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.castShadow = true
            child.receiveShadow = true
          }
        })
        
        // 在加载模型成功后的处理函数中
        object.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            // 创建透明材质
            const transparentMaterial = new THREE.MeshPhysicalMaterial({
              color: 0x6b7280,
              transparent: true,
              opacity: 0.1,         // 降低不透明度，使模型更透明
              roughness: 1,       // 较低的粗糙度，增加光泽感
              metalness: 0.0,       // 轻微的金属感
              side: THREE.FrontSide, // 双面渲染，确保内部面可见
              depthWrite: false,    // 避免透明物体的排序问题
              wireframe: false,      // 是否显示线框，false为实体
              emissive: 0xffffff,   // 添加自发光颜色 - 白色
              emissiveIntensity: 1 // 自发光强度
            })
            
            child.material = transparentMaterial
            child.castShadow = true
            child.receiveShadow = true
          }
        })
        
        // 收集并保存模型结构
        modelStructure.value = collectModelStructure(object);
        
        scene.add(object)
        loadingError.value = null
      },
      (xhr) => {
        console.log((xhr.loaded / xhr.total * 100) + '% loaded')
      },
      (error) => {
        console.error('模型加载出错:', error)
        loadingError.value = '建筑模型加载失败，请检查模型文件'
      }
    )
  }, undefined, (error) => {
    console.error('材质加载出错:', error)
    
    // 无材质加载OBJ
    const objLoader = new OBJLoader()
    objLoader.load(
      '/models/campus.obj',
      (object) => {
        // 应用默认材质
        object.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.material = new THREE.MeshPhongMaterial({
              color: 0x6b7280,
              transparent: true,
              opacity: 0.8
            })
            child.castShadow = true
            child.receiveShadow = true
          }
        })
        
        object.scale.set(0.1, 0.1, 0.1)
        scene.add(object)
        loadingError.value = null
      },
      undefined,
      (error) => {
        console.error('模型加载出错:', error)
        loadingError.value = '建筑模型加载失败，请检查模型文件'
      }
    )
  })
}

// 修改收集模型结构函数，同时保存对象引用
const collectModelStructure = (object, depth = 0, result = []) => {
  const typeName = object.type || '未知类型';
  const objectName = object.name || '未命名';
  
  // 存储对象引用，以便后续通过UUID查找
  modelObjectsMap.value.set(object.uuid, object);
  
  result.push({
    name: objectName,
    type: typeName,
    depth: depth,
    id: object.uuid,
    isMesh: object instanceof THREE.Mesh
  });
  
  if (object.children && object.children.length > 0) {
    object.children.forEach(child => {
      collectModelStructure(child, depth + 1, result);
    });
  }
  
  return result;
}

// 添加高亮功能
const highlightObject = (id: string) => {
  // 取消之前的高亮
  if (highlightedObjectId.value && highlightedObjectId.value !== id) {
    resetHighlight();
  }
  
  // 设置当前高亮对象ID
  highlightedObjectId.value = id;
  
  // 获取要高亮的对象
  const object = modelObjectsMap.value.get(id);
  if (!object) return;
  
  // 只高亮网格对象
  if (object instanceof THREE.Mesh) {
    // 保存原始材质
    if (!originalMaterials.value.has(id)) {
      originalMaterials.value.set(id, object.material);
    }
    
    // 创建高亮材质
    const highlightMaterial = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,  // 蓝色高亮
      emissive: 0x38bdf8,
      emissiveIntensity: 0.5,
      transparent: true,
      opacity: 0.8,
      metalness: 0.8,
      roughness: 0.2,
      wireframe: false
    });
    
    // 应用高亮材质
    object.material = highlightMaterial;
  }
}

// 重置高亮状态
const resetHighlight = () => {
  if (!highlightedObjectId.value) return;
  
  const object = modelObjectsMap.value.get(highlightedObjectId.value);
  if (object instanceof THREE.Mesh) {
    // 恢复原始材质
    const originalMaterial = originalMaterials.value.get(highlightedObjectId.value);
    if (originalMaterial) {
      object.material = originalMaterial;
    }
  }
  
  highlightedObjectId.value = null;
}

// 悬停处理函数
const handleItemMouseEnter = (id: string) => {
  highlightObject(id);
}

// 鼠标离开处理函数
const handleItemMouseLeave = () => {
  resetHighlight();
}

// 窗口大小变化处理
const onWindowResize = () => {
  if (!heatmapRef.value || !camera || !renderer) return
  
  const { clientWidth, clientHeight } = heatmapRef.value
  
  camera.aspect = clientWidth / clientHeight
  camera.updateProjectionMatrix()
  
  renderer.setSize(clientWidth, clientHeight)
}

// 更新动画
const animate = () => {
  animationFrameId = requestAnimationFrame(animate)
  
  // 更新控制器
  if (controls) {
    controls.update()
  }
  
  // 渲染场景
  if (renderer && scene && camera) {
    renderer.render(scene, camera)
  }
}

// 组件挂载时初始化
onMounted(() => {
  initThreeScene()
})

// 组件卸载前清理资源
onBeforeUnmount(() => {
  window.removeEventListener('resize', onWindowResize)
  
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
  
  if (renderer) {
    renderer.dispose()
  }
  
  if (heatmapRef.value && renderer) {
    heatmapRef.value.removeChild(renderer.domElement)
  }
  
  // 释放场景资源
  if (scene) {
    scene.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        if (object.geometry) {
          object.geometry.dispose()
        }
        
        if (Array.isArray(object.material)) {
          object.material.forEach(material => material.dispose())
        } else if (object.material) {
          object.material.dispose()
        }
      }
    })
  }
  
  // 清理材质引用
  originalMaterials.value.clear();
  modelObjectsMap.value.clear();
})
</script>

<template>
  <div class="three-heatmap-container">
    <div class="map-background"></div>
    <div ref="heatmapRef" class="three-canvas"></div>
    
    <div v-if="loadingError" class="error-message">
      {{ loadingError }}
    </div>
    
    <div class="heatmap-title">
      <h2 class="title-text">3D热力分布图</h2>
      <div class="subtitle-text">3D Heat Distribution</div>
    </div>
    
    <div class="tech-decoration top-right"></div>
    <div class="tech-decoration bottom-left"></div>
    
    <div class="controls-hint">
      <div class="hint-item"><span class="hint-key">鼠标拖动</span> 旋转视角</div>
      <div class="hint-item"><span class="hint-key">滚轮</span> 缩放</div>
      <div class="hint-item"><span class="hint-key">右键拖动</span> 平移</div>
    </div>
    
    <!-- 调试按钮 -->
    <button @click="showDebugInfo = !showDebugInfo" class="debug-toggle">
      {{ showDebugInfo ? '隐藏结构' : '查看模型结构' }}
    </button>
    
    <!-- 调试面板 -->
    <div v-if="showDebugInfo" class="debug-panel">
      <h3>模型结构</h3>
      <div class="structure-tree">
        <div 
          v-for="item in modelStructure" 
          :key="item.id" 
          class="structure-item" 
          :class="{ 'is-mesh': item.isMesh, 'is-highlighted': item.id === highlightedObjectId }"
          :style="{paddingLeft: `${item.depth * 16}px`}"
          @mouseenter="item.isMesh ? handleItemMouseEnter(item.id) : null"
          @mouseleave="handleItemMouseLeave"
        >
          <span class="item-name">{{ item.name || '未命名' }}</span>
          <span class="item-type">{{ item.type }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.three-heatmap-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
  padding: 20px;
  background-color: rgba(20, 28, 47, 1.0);
  border-radius: 12px;
  overflow: hidden;
}

.error-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #fecaca;
  padding: 10px 20px;
  border-radius: 8px;
  z-index: 10;
  text-align: center;
  font-size: 0.9rem;
}

.map-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0.2;
  background-image: radial-gradient(circle at center, 
    rgba(56, 189, 248, 0.15) 0%, 
    rgba(20, 28, 47, 0) 70%);
}

.three-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
}

.heatmap-title {
  position: absolute;
  top: 15px;
  left: 20px;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
  flex-shrink: 0;
}

.title-text {
  font-size: 0.95rem;
  font-weight: 500;
  color: #fff;
  margin: 0;
  white-space: nowrap;
}

.subtitle-text {
  font-size: 0.7rem;
  color: #94a3b8;
  position: relative;
  padding-left: 10px;
}

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

.controls-hint {
  position: absolute;
  bottom: 20px;
  right: 20px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(56, 189, 248, 0.3);
  border-radius: 8px;
  padding: 10px;
  z-index: 10;
  color: #e2e8f0;
  font-size: 0.8rem;
  display: flex;
  flex-direction: column;
  gap: 5px;
  transition: opacity 0.3s;
  opacity: 0.7;
}

.controls-hint:hover {
  opacity: 1;
}

.hint-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hint-key {
  background: rgba(56, 189, 248, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.3);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 0.75rem;
  color: #38bdf8;
}

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

.three-heatmap-container {
  animation: pulse 4s infinite;
}

.debug-toggle {
  position: absolute;
  top: 15px;
  right: 20px;
  z-index: 100;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(56, 189, 248, 0.5);
  color: #38bdf8;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
}

.debug-panel {
  position: absolute;
  top: 60px;
  right: 20px;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(56, 189, 248, 0.5);
  border-radius: 8px;
  padding: 12px;
  z-index: 100;
  width: 300px;
  max-height: 70%;
  overflow-y: auto;
  color: #e2e8f0;
}

.debug-panel h3 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #38bdf8;
  border-bottom: 1px solid rgba(56, 189, 248, 0.3);
  padding-bottom: 8px;
}

.structure-tree {
  font-family: monospace;
  font-size: 12px;
}

.structure-item {
  padding: 3px 0;
  display: flex;
  justify-content: space-between;
}

.structure-item.is-mesh {
  cursor: pointer;
}

.structure-item:hover {
  background-color: rgba(56, 189, 248, 0.1);
}

.structure-item.is-highlighted,
.structure-item:hover {
  background-color: rgba(56, 189, 248, 0.2);
  border-radius: 3px;
}

.item-name {
  color: #e2e8f0;
}

.structure-item.is-mesh .item-name {
  color: #38bdf8; /* 可高亮的网格对象使用蓝色 */
}

.item-type {
  color: #94a3b8;
  font-size: 10px;
}

/* 添加悬停提示 */
.structure-item.is-mesh::after {
  content: "👆 悬停可高亮";
  position: absolute;
  right: 10px;
  font-size: 10px;
  color: #38bdf8;
  opacity: 0;
  transition: opacity 0.3s;
}

.structure-item.is-mesh:hover::after {
  opacity: 0.7;
}
</style>