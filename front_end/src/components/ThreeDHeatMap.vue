<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, reactive } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js'
import type { AreaItem } from '../types'

// 在组件顶部添加帧率控制变量
let lastFrameTime = 0;
const targetFPS = 30; // 目标30帧每秒
const frameInterval = 1000 / targetFPS;


// 聚焦相关（脚本开头部分）
const focusModeActive = ref(false);
const focusedObjectId = ref<string | null>(null);
const showRestoreButton = ref(false);

// 添加摄像头位置相关变量
const originalCameraPosition = ref<THREE.Vector3 | null>(null);
const originalCameraTarget = ref<THREE.Vector3 | null>(null);
const cameraAnimationInProgress = ref(false);

const props = defineProps<{
  areas: AreaItem[]
  mapImage: string
}>()
// 在组件顶部添加（与其他ref变量同级位置）
const autoRotateEnabled = ref(true)
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

// 添加编辑状态管理
const editingItemId = ref<string | null>(null);
const newItemName = ref('');

// 添加坐标显示相关变量
const showCoordinates = ref(false)
const selectedPosition = reactive({
  x: 0,
  y: 0,
  z: 0
})
const raycaster = new THREE.Raycaster()
const mouse = new THREE.Vector2()

// 虚构的热点坐标数据
const heatmapPoints = [
  { x: -4, y: 2, z: -3, intensity: 40 }, // 高强度点
  { x: -3.7, y: 2, z: -2.1, intensity: 35 },
  { x: 3, y: 3, z: 0, intensity: 30 }, // 中心点，最高强度
  { x: -6, y: 1, z: -6, intensity: 0 },
  { x: 6, y: 0.8, z: -5.5, intensity: 0 },
  { x: 5.5, y: 0.2, z: 5, intensity: 0 },
  { x: -1, y: 4, z: 2, intensity: 40 },
  { x: 2.2, y: 1.8, z: 4.1, intensity: 35 },
  { x: 1, y: 1, z: 3.7, intensity: 30 }
]

// 存储点云对象引用，用于动画
const pointCloudObjects: THREE.Points[] = []

// 初始化Three.js场景
const initThreeScene = () => {
  if (!heatmapRef.value) return

  // 创建场景
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x141c2f)

  // 设置相机
  const { clientWidth, clientHeight } = heatmapRef.value
  camera = new THREE.PerspectiveCamera(45, clientWidth / clientHeight, 0.1, 1000)
  camera.position.set(0, 15, 15)
  
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
  controls.autoRotate = autoRotateEnabled.value  // 根据状态设置自动旋转
  controls.autoRotateSpeed = 3.0  // 设置旋转速度，可以根据需要调整
    

  // 添加坐标轴辅助工具
  const axesHelper = new THREE.AxesHelper(5) // 参数是轴线长度
  scene.add(axesHelper)
  

  // 加载OBJ建筑模型
  loadBuildingModel()
  
  // 添加热力点云
  createHeatmapPointCloud()
  
  // 渲染动画
  animate()
  
  // 添加窗口大小调整监听
  window.addEventListener('resize', onWindowResize)
}
// 添加切换自动环视功能的方法
const toggleAutoRotate = () => {
  autoRotateEnabled.value = !autoRotateEnabled.value;
  if (controls) {
    controls.autoRotate = autoRotateEnabled.value;
  }
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
        object.scale.set(0.005, 0.005, 0.005)
        
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
              opacity: 0.2,         // 降低不透明度，使模型更透明
              roughness: 0.5,       // 较低的粗糙度，增加光泽感
              metalness: 0.5,       // 轻微的金属感
              side: THREE.FrontSide, // 双面渲染，确保内部面可见
              depthWrite: true,    // 避免透明物体的排序问题
              wireframe: false,      // 是否显示线框，false为实体
              emissive: 0xffffff,   // 添加自发光颜色 - 白色
              emissiveIntensity: 10// 自发光强度
            })
            
                // 为每个网格添加边缘线，强调轮廓
              const edges = new THREE.EdgesGeometry(child.geometry, 30); // 30度角阈值
              const lineMaterial = new THREE.LineBasicMaterial({
                color: 0x38bdf8,
                opacity: 0.3,
                transparent: true
              });
              const wireframe = new THREE.LineSegments(edges, lineMaterial);
              child.add(wireframe); // 将线框添加为子对象
              
              child.material = transparentMaterial;
              child.castShadow = true;
              child.receiveShadow = true;
              
              // 保存原始材质以便后续高亮
              if (child.geometry) {
                // 为不同深度的面应用不同透明度
                const positionAttribute = child.geometry.getAttribute('position');
                if (positionAttribute) {
                  // 创建颜色缓冲区以调整深度感知
                  const colors = new Float32Array(positionAttribute.count * 3);
                  const color = new THREE.Color();
                  
                  // 根据Y坐标调整颜色明度
                  for (let i = 0; i < positionAttribute.count; i++) {
                    const y = positionAttribute.getY(i);
                    // 根据高度计算颜色因子 (0-1)
                    const factor = Math.min(Math.max((y + 10) / 20, 0), 1);
                    // 调整明度和饱和度
                    color.setRGB(0.4 + factor * 0.2, 0.45 + factor * 0.2, 0.5 + factor * 0.2);
                    colors[i * 3] = color.r;
                    colors[i * 3 + 1] = color.g;
                    colors[i * 3 + 2] = color.b;
                  }
                  
                  child.geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
                  transparentMaterial.vertexColors = true; // 启用顶点颜色
                }
              }
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
    isMesh: object instanceof THREE.Mesh,
    visible: object.visible // 记录初始可见性状态
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
  // 避免与canvas上的悬停检测冲突
  if (hoveredMeshId.value) {
    resetHoveredState();
  }
  highlightObject(id);
}

// 鼠标离开处理函数
const handleItemMouseLeave = () => {
  // 只在不是canvas悬停时才重置
  if (!hoveredMeshId.value) {
    resetHighlight();
  }
}

// 添加鼠标悬停对象标签相关变量
const hoveredMeshId = ref<string | null>(null);
const meshLabelVisible = ref(false);
const meshLabelPosition = reactive({
  x: 0,
  y: 0
});
const meshLabelContent = ref('');
// 添加射线检测节流
let lastRaycastTime = 0;
const raycastInterval = 100; // 每100毫秒检测一次
// 添加射线检测和悬停高亮功能
const handleCanvasMouseMove = (event) => {
  const now = Date.now();
  if (now - lastRaycastTime < raycastInterval) return;
  lastRaycastTime = now;
  if (!heatmapRef.value || !camera || !scene || !renderer) return;
  
  // 计算鼠标在canvas中的归一化坐标（-1到1之间）
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  
  // 更新射线投射器
  raycaster.setFromCamera(mouse, camera);
  
  // 获取与射线相交的所有物体
  const intersects = raycaster.intersectObjects(scene.children, true);
  
  // 如果有相交的物体
  if (intersects.length > 0) {
    // 寻找第一个是Mesh的对象
    let meshObject = null;
    let i = 0;
    
    while (i < intersects.length && !meshObject) {
      if (intersects[i].object instanceof THREE.Mesh) {
        meshObject = intersects[i].object;
      }
      i++;
    }
    
    if (meshObject) {
      // 找到相交的网格对象
      const id = meshObject.uuid;
      
      // 避免重复处理同一个对象
      if (hoveredMeshId.value !== id) {
        // 重置之前的高亮
        if (hoveredMeshId.value) {
          resetHighlight();
        }
        
        // 高亮新对象
        hoveredMeshId.value = id;
        highlightObject(id);
        
        // 获取对象名称用于显示
        let objectName = meshObject.name || '未命名部分';
        
        // 遍历结构以获取更完整的对象信息
        const structureItem = modelStructure.value.find(item => item.id === id);
        if (structureItem) {
          objectName = structureItem.name || objectName;
        }
        
        // 更新标签内容和位置
        meshLabelContent.value = objectName;
        meshLabelPosition.x = event.clientX;
        meshLabelPosition.y = event.clientY - 25; // 稍微向上偏移
        meshLabelVisible.value = true;
      } else {
        // 即使是同一对象，也要更新标签位置
        meshLabelPosition.x = event.clientX;
        meshLabelPosition.y = event.clientY - 25;
      }
    } else {
      // 没有指向Mesh对象，重置
      resetHoveredState();
    }
  } else {
    // 没有指向任何对象，重置
    resetHoveredState();
  }
}

// 重置悬停状态
const resetHoveredState = () => {
  if (hoveredMeshId.value) {
    resetHighlight();
    hoveredMeshId.value = null;
    meshLabelVisible.value = false;
  }
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
  const now = Date.now();
  const elapsed = now - lastFrameTime;
  
  // 帧率控制 - 确保不超过目标帧率
  if (elapsed < frameInterval) return;
  
  // 更新时间戳，考虑实际消耗的时间
  lastFrameTime = now - (elapsed % frameInterval);
  
  // 更新控制器 - 仅在摄像机动画未进行时允许用户控制
  if (controls && !cameraAnimationInProgress.value) {
    controls.update()
  }
  
  // 为点云添加动画效果
  const time = Date.now() * 0.001
  
  pointCloudObjects.forEach((cloud, cloudIndex) => {
    const geometry = cloud.geometry
    const positionAttribute = geometry.getAttribute('position')
    const velocityAttribute = geometry.getAttribute('velocity')
    const randomnessAttribute = geometry.getAttribute('randomness')
    const phaseAttribute = geometry.getAttribute('phase')
    const originalPositions = geometry.userData.originalPositions
    
    // 选择性粒子更新 - 每帧只更新10%的粒子
    const particleCount = positionAttribute.count;
    const updateCount = Math.ceil(particleCount * 0.1); // 每帧更新10%
    const startIndex = Math.floor(Math.random() * (particleCount - updateCount));
    
    // 仅更新一部分粒子
    for (let i = startIndex; i < startIndex + updateCount; i++) {
      if (i >= particleCount) break;
      
      const index = i * 3
      const phase = phaseAttribute.getX(i)
      
      // 获取速度和随机性参数
      const vx = velocityAttribute.getX(i)
      const vy = velocityAttribute.getY(i)
      const vz = velocityAttribute.getZ(i)
      
      const rx = randomnessAttribute.getX(i)
      const ry = randomnessAttribute.getY(i)
      const rz = randomnessAttribute.getZ(i)
      
      // 原始位置
      const originalX = originalPositions[index]
      const originalY = originalPositions[index + 1]
      const originalZ = originalPositions[index + 2]
      
      // 简化三角函数计算
      const t1 = time * 1.7 + phase
      const t2 = time * 0.7 + i
      
      // 预计算sin值
      const sin1 = Math.sin(t1)
      const sin2 = Math.sin(t2 * 0.5)
      
      // 计算杂乱运动和漂移
      const noiseX = sin1 * rx
      const driftX = vx * sin2
      
      const noiseY = Math.sin(t1 * 1.2) * ry
      const driftY = vy * Math.sin(t2 * 0.9)
      
      const noiseZ = Math.sin(t1 * 0.8) * rz
      const driftZ = vz * sin2
      
      // 更新位置
      positionAttribute.setXYZ(
        i,
        originalX + noiseX + driftX,
        originalY + noiseY + driftY,
        originalZ + noiseZ + driftZ
      )
    }
    
    // 通知 Three.js 更新位置缓冲区
    positionAttribute.needsUpdate = true
  })
  
  // 渲染场景
  if (renderer && scene && camera) {
    renderer.render(scene, camera)
  }
}


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

// 处理双击开始编辑名称
const startEditName = (item) => {
  // 只允许编辑一项
  editingItemId.value = item.id;
  newItemName.value = item.name || '';
}

// 应用名称修改
const applyRename = () => {
  if (!editingItemId.value || !newItemName.value.trim()) {
    cancelRename();
    return;
  }

  // 获取正在编辑的对象
  const object = modelObjectsMap.value.get(editingItemId.value);
  if (object) {
    // 更改实际3D对象的名称
    object.name = newItemName.value.trim();
    
    // 更新结构树显示
    const itemIndex = modelStructure.value.findIndex(item => item.id === editingItemId.value);
    if (itemIndex >= 0) {
      modelStructure.value[itemIndex].name = newItemName.value.trim();
    }
  }
  
  // 清除编辑状态
  editingItemId.value = null;
  newItemName.value = '';
}

// 取消重命名操作
const cancelRename = () => {
  editingItemId.value = null;
  newItemName.value = '';
}

// 处理重命名输入框的按键事件
const handleRenameKeydown = (event) => {
  if (event.key === 'Enter') {
    applyRename();
  } else if (event.key === 'Escape') {
    cancelRename();
  }
}

// 添加坐标显示功能
const updateMousePosition = (event) => {
  if (!renderer.value || !camera.value) return;
  
  const rect = renderer.value.domElement.getBoundingClientRect();
  
  // 计算鼠标在场景中的位置
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  
  // 更新射线投射器
  raycaster.setFromCamera(mouse, camera);
  
  // 计算物体与鼠标射线的交点
  const intersects = raycaster.intersectObjects(scene.children, true);
  if (intersects.length > 0) {
    const point = intersects[0].point;
    selectedPosition.x = point.x;
    selectedPosition.y = point.y;
    selectedPosition.z = point.z;
  }
}

// 监听鼠标移动事件
const onDocumentMouseMove = (event) => {
  updateMousePosition(event);
}

// 监听鼠标点击事件
const onDocumentMouseClick = (event) => {
  if (!showCoordinates.value) return;
  
  // 更新坐标
  updateMousePosition(event);
}

// 处理点击事件获取坐标
const handleCanvasClick = (event) => {
  if (!heatmapRef.value || !camera || !scene) return
  
  // 计算鼠标在canvas中的归一化坐标（-1到1之间）
  const rect = renderer.domElement.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
  
  // 设置射线投射器
  raycaster.setFromCamera(mouse, camera)
  
  // 获取与射线相交的所有物体
  const intersects = raycaster.intersectObjects(scene.children, true)
  
  // 如果有相交的物体
  if (intersects.length > 0) {
    // 获取第一个交点的坐标（最近的）
    const point = intersects[0].point
    
    // 更新选中位置
    selectedPosition.x = parseFloat(point.x.toFixed(3))
    selectedPosition.y = parseFloat(point.y.toFixed(3))
    selectedPosition.z = parseFloat(point.z.toFixed(3))
    
    // 显示坐标信息
    showCoordinates.value = true
  }
}

// 切换坐标显示
const toggleCoordinates = () => {
  showCoordinates.value = !showCoordinates.value;
}

// 切换对象可见性
const toggleVisibility = (id) => {
  // 获取目标对象
  const object = modelObjectsMap.value.get(id);
  if (!object) return;
  
  // 切换可见性
  object.visible = !object.visible;
  
  // 更新结构树状态
  const itemIndex = modelStructure.value.findIndex(item => item.id === id);
  if (itemIndex >= 0) {
    modelStructure.value[itemIndex].visible = object.visible;
  }
  
  // 如果之前高亮了这个对象但现在设为不可见，则取消高亮
  if (!object.visible && highlightedObjectId.value === id) {
    resetHighlight();
  }
}


// 在组件卸载时移除事件监听
onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onDocumentMouseMove);
  window.removeEventListener('click', onDocumentMouseClick);
  
  // 移除点击事件监听
  if (heatmapRef.value) {
    heatmapRef.value.removeEventListener('click', handleCanvasClick)
    heatmapRef.value.removeEventListener('mousemove', handleCanvasMouseMove)
    // 移除双击事件监听
    heatmapRef.value.removeEventListener('dblclick', handleCanvasDoubleClick)
  }
  
  // ...其他清理代码
})

// 创建一个体素网格表示整个空间的密度分布
const createDensityField = (points, resolution = 24) => { // 降低分辨率提高性能
  if (!points || points.length === 0) {
    console.warn('没有热点数据，使用默认空密度场');
    return { 
      grid: new Array(resolution * resolution * resolution).fill(0),
      bounds: calculateBounds([]),
      resolution,
      cellSize: new THREE.Vector3(1, 1, 1)
    };
  }
  
  console.log('开始创建密度场，点数:', points.length);
  const grid = new Array(resolution * resolution * resolution).fill(0);
  const bounds = calculateBounds(points);
  const cellSize = bounds.size.clone().divideScalar(resolution);
  
  // 预先计算一些常量来提高循环性能
  const maxDistanceSquared = 10; // 最大影响距离的平方
  
  // 计算每个体素的密度值
  for (let x = 0; x < resolution; x++) {
    for (let y = 0; y < resolution; y++) {
      for (let z = 0; z < resolution; z++) {
        const voxelPos = new THREE.Vector3(
          bounds.min.x + x * cellSize.x,
          bounds.min.y + y * cellSize.y,
          bounds.min.z + z * cellSize.z
        );
        
        // 累加所有热点对当前体素的影响
        let density = 0;
        for (const point of points) {
          const pointPos = new THREE.Vector3(point.x, point.y, point.z);
          const distanceSquared = voxelPos.distanceToSquared(pointPos);
          
          // 距离截断优化 - 只计算一定距离内的点
          if (distanceSquared < maxDistanceSquared) {
            // 使用距离衰减函数计算影响值
            const influence = point.intensity * Math.exp(-distanceSquared / 1);
            density += influence;
          }
        }
        
        const index = x + y * resolution + z * resolution * resolution;
        grid[index] = density;
      }
    }
  }
  
  console.log('密度场创建完成');
  return { grid, bounds, resolution, cellSize };
}

// 修改后的热力点云创建函数
const createHeatmapPointCloud = () => {
  try {
    console.log('开始创建热力点云');
    
    // 确保热点数据存在
    if (!heatmapPoints || heatmapPoints.length === 0) {
      console.warn('热点数据为空');
      // 添加一些默认热点
    }
    
    // 创建密度场
    const densityField = createDensityField(heatmapPoints);
    
    // 生成粒子几何体
    const particleGeometry = createParticlesFromDensityField(densityField);
    // 创建点云材质
    const particleMaterial = new THREE.PointsMaterial({
      size: 0.01, // 粒子大小
      vertexColors: true,
      transparent: true,
      opacity: 0.6, // 透明度
      blending: THREE.AdditiveBlending,
      sizeAttenuation: true,
    });
    
    // 创建点云对象并添加到场景
    const particles = new THREE.Points(particleGeometry, particleMaterial);
    scene.add(particles);
    
    // 存储点云对象引用，用于动画
    pointCloudObjects.push(particles);
    
    console.log('热力点云创建完成');
  } catch (error) {
    console.error('创建热力点云出错:', error);
    loadingError.value = '热力图加载失败: ' + error.message;
  }
}

// 修改粒子创建函数
const createParticlesFromDensityField = (densityField) => {
  console.log('开始生成粒子...');
  const { grid, bounds, resolution, cellSize } = densityField;
  
  // 找到最大密度值，避免除以零
  const maxDensity = Math.max(...grid, 0.001);
  console.log(`最大密度值: ${maxDensity}`);
  
  // 根据总密度估计粒子数量，限制最大数量
  const desiredParticleCount = 10000000 
  console.log(`目标粒子数量: ${desiredParticleCount}`);
  
  // 预分配数组
  const particlePositions = new Float32Array(desiredParticleCount * 3);
  const particleColors = new Float32Array(desiredParticleCount * 3);
  const particleVelocity = new Float32Array(desiredParticleCount * 3);
  const particleRandomness = new Float32Array(desiredParticleCount * 3);
  const particlePhases = new Float32Array(desiredParticleCount);
  
  let particleIndex = 0;
  
  // 使用接受-拒绝采样法基于密度分布生成粒子
  const attempts = desiredParticleCount;
  for (let i = 0; i < attempts; i++) {
    // 随机选择一个网格点
    const x = Math.floor(Math.random() * resolution);
    const y = Math.floor(Math.random() * resolution);
    const z = Math.floor(Math.random() * resolution);
    
    const gridIndex = x + y * resolution + z * resolution * resolution;
    const cellDensity = grid[gridIndex];
    
    // 归一化的密度值
    const normalizedDensity = cellDensity / maxDensity;
    
    // 添加基础概率确保低密度区域也能生成粒子
    const baseProbability = 0.00005;  // 基础概率，即使密度为0也有10%概率生成粒子
    const densityWeight = 0.8;    // 密度权重
    
    // 计算综合概率
    const generationProbability = baseProbability + normalizedDensity * densityWeight;
    
    // 基于综合概率决定是否在此位置生成粒子
    if (Math.random() < generationProbability) {
      const index = particleIndex * 3;
      
      // 在体素内随机位置
      particlePositions[index] = bounds.min.x + (x + Math.random()) * cellSize.x;
      particlePositions[index + 1] = bounds.min.y + (y + Math.random()) * cellSize.y;
      particlePositions[index + 2] = bounds.min.z + (z + Math.random()) * cellSize.z;
    
      // 设置颜色 - 使用原有代码
      // 在粒子创建函数中定义固定的密度阈值常量
      const LOW_DENSITY_THRESHOLD = 20;  // 低密度阈值
      const MID_DENSITY_THRESHOLD = 35;  // 中密度阈值

      // 在颜色设置部分使用原始密度值而非归一化密度值
      // 设置颜色
      if (cellDensity < LOW_DENSITY_THRESHOLD) {
        // 低密度区域 - 蓝色
        particleColors[index] = 0;
        particleColors[index + 1] = 0.2;
        particleColors[index + 2] = 1.0;
      } else if (cellDensity < MID_DENSITY_THRESHOLD) {
        // 中密度区域 - 黄色
        particleColors[index] = 1.0;
        particleColors[index + 1] = 1.0;
        particleColors[index + 2] = 0.0;
      } else {
        // 高密度区域 - 红色
        particleColors[index] = 1.0;
        particleColors[index + 1] = 0.0;
        particleColors[index + 2] = 0.0;
      }
      
      // 设置运动参数 - 使用原有代码
      particleVelocity[index] = (Math.random() - 0.5) * 0.01;
      particleVelocity[index + 1] = (Math.random() - 0.5) * 0.01;
      particleVelocity[index + 2] = (Math.random() - 0.5) * 0.01;
      
      particleRandomness[index] = Math.random() * 0.1;
      particleRandomness[index + 1] = Math.random() * 0.1;
      particleRandomness[index + 2] = Math.random() * 0.1;
      
      particlePhases[particleIndex] = Math.random() * Math.PI * 2;
      
      particleIndex++;
      
      if (particleIndex >= desiredParticleCount) break;
    }
  }
  
  console.log(`实际生成粒子数: ${particleIndex}`);
  
  // 如果没有成功生成粒子，添加一些默认粒子以确保渲染
  if (particleIndex === 0) {
    console.warn('没有生成粒子，添加默认粒子');
    particlePositions[0] = 0;
    particlePositions[1] = 5;
    particlePositions[2] = 0;
    particleColors[0] = 1;
    particleColors[1] = 1;
    particleColors[2] = 1;
    particleVelocity[0] = 0;
    particleVelocity[1] = 0;
    particleVelocity[2] = 0;
    particleRandomness[0] = 0.05;
    particleRandomness[1] = 0.05;
    particleRandomness[2] = 0.05;
    particlePhases[0] = 0;
    particleIndex = 1;
  }
  
  // 构建几何体
  const particleGeometry = new THREE.BufferGeometry();
  particleGeometry.setAttribute('position', new THREE.BufferAttribute(
    particlePositions.slice(0, particleIndex * 3), 3));
  particleGeometry.setAttribute('color', new THREE.BufferAttribute(
    particleColors.slice(0, particleIndex * 3), 3));
  particleGeometry.setAttribute('velocity', new THREE.BufferAttribute(
    particleVelocity.slice(0, particleIndex * 3), 3));
  particleGeometry.setAttribute('randomness', new THREE.BufferAttribute(
    particleRandomness.slice(0, particleIndex * 3), 3));
  particleGeometry.setAttribute('phase', new THREE.BufferAttribute(
    particlePhases.slice(0, particleIndex), 1));
  
  // 存储原始位置
  particleGeometry.userData.originalPositions = particlePositions.slice(0, particleIndex * 3);
  
  return particleGeometry;
}

onMounted(() => {
  initThreeScene()
  
  // 添加点击事件监听
  if (heatmapRef.value) {
    heatmapRef.value.addEventListener('click', handleCanvasClick)
    // 添加鼠标移动事件监听
    heatmapRef.value.addEventListener('mousemove', handleCanvasMouseMove)
    // 添加双击事件监听
    heatmapRef.value.addEventListener('dblclick', handleCanvasDoubleClick)
  }
  
  window.addEventListener('mousemove', onDocumentMouseMove)
  window.addEventListener('click', onDocumentMouseClick)
})

// 计算所有点的边界框
const calculateBounds = (points) => {
  if (!points || points.length === 0) {
    // 如果没有点，提供一个默认的边界框
    return {
      min: new THREE.Vector3(-10, -10, -10),
      max: new THREE.Vector3(10, 10, 10),
      size: new THREE.Vector3(20, 20, 20)
    };
  }
  
  // 初始化边界为第一个点的位置
  const min = new THREE.Vector3(points[0].x, points[0].y, points[0].z);
  const max = new THREE.Vector3(points[0].x, points[0].y, points[0].z);
  
  // 遍历所有点找出最小和最大坐标
  for (const point of points) {
    min.x = Math.min(min.x, point.x);
    min.y = Math.min(min.y, point.y);
    min.z = Math.min(min.z, point.z);
    
    max.x = Math.max(max.x, point.x);
    max.y = Math.max(max.y, point.y);
    max.z = Math.max(max.z, point.z);
  }
  
  // 计算边界框大小
  const size = new THREE.Vector3().subVectors(max, min);
  
  // 稍微扩大边界，防止粒子位于边缘
  min.subScalar(2);
  max.addScalar(2);
  size.addScalar(4);
  
  return { min, max, size };
}

// 添加双击事件处理函数
const handleCanvasDoubleClick = (event) => {
  if (!heatmapRef.value || !camera || !scene || !renderer) return;
  
  // 计算鼠标在canvas中的归一化坐标
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  
  // 设置射线投射器
  raycaster.setFromCamera(mouse, camera);
  
  // 获取与射线相交的所有物体
  const intersects = raycaster.intersectObjects(scene.children, true);
  
  // 如果有相交的物体且不是在聚焦模式下，则聚焦该物体
  if (intersects.length > 0 && !focusModeActive.value) {
    // 查找第一个是Mesh的对象
    let meshObject = null;
    let i = 0;
    
    while (i < intersects.length && !meshObject) {
      if (intersects[i].object instanceof THREE.Mesh) {
        meshObject = intersects[i].object;
      }
      i++;
    }
    
    if (meshObject) {
      toggleFocusMode(meshObject.uuid);
    }
  } else {
    // 如果已经在聚焦模式下或没有点击到物体，则退出聚焦模式
    exitFocusMode();
  }
};

// 替换原有的 toggleFocusMode 函数
const toggleFocusMode = (objectId) => {
  console.log('切换聚焦模式，objectId:', objectId);
  
  if (focusModeActive.value && focusedObjectId.value === objectId) {
    // 如果已经聚焦在该物体上，则退出聚焦模式
    exitFocusMode();
  } else {
    // 进入聚焦模式，显示选中物体，隐藏其他物体
    focusModeActive.value = true;
    focusedObjectId.value = objectId;
    
    // 找到聚焦的对象及其所有子对象
    const focusedObject = modelObjectsMap.value.get(objectId);
    if (!focusedObject) {
      console.error('找不到聚焦对象:', objectId);
      return;
    }
    
    console.log('聚焦对象:', focusedObject.name || 'unnamed');
    
    // 首先标记所有对象为不可见
    modelObjectsMap.value.forEach((object, id) => {
      object.visible = false;
      
      // 更新结构树状态
      const itemIndex = modelStructure.value.findIndex(item => item.id === id);
      if (itemIndex >= 0) {
        modelStructure.value[itemIndex].visible = false;
      }
    });
    
    // 然后递归地将聚焦对象及其所有子对象标记为可见
    function makeObjectAndChildrenVisible(obj) {
      if (!obj) return;
      
      obj.visible = true;
      
      // 更新结构树状态
      const itemIndex = modelStructure.value.findIndex(item => item.id === obj.uuid);
      if (itemIndex >= 0) {
        modelStructure.value[itemIndex].visible = true;
      }
      
      // 递归处理所有子对象
      if (obj.children && obj.children.length > 0) {
        obj.children.forEach(child => {
          makeObjectAndChildrenVisible(child);
        });
      }
    }
    
    // 使聚焦对象及其子对象可见
    makeObjectAndChildrenVisible(focusedObject);
    
    // 检查聚焦对象的父级，确保它们也是可见的
    let parent = focusedObject.parent;
    while (parent) {
      parent.visible = true;
      
      // 更新结构树状态
      const itemIndex = modelStructure.value.findIndex(item => item.id === parent.uuid);
      if (itemIndex >= 0) {
        modelStructure.value[itemIndex].visible = true;
      }
      
      parent = parent.parent;
    }
    
    // 计算聚焦对象的边界盒以确定其几何中心
    const boundingBox = new THREE.Box3().setFromObject(focusedObject);
    const center = boundingBox.getCenter(new THREE.Vector3());
    
    // 计算适当的摄像机距离
    const size = new THREE.Vector3();
    boundingBox.getSize(size);
    const maxDimension = Math.max(size.x, size.y, size.z);
    const distance = maxDimension; // 距离调整因子
    
    // 保存原始摄像头位置和目标点
    if (!originalCameraPosition.value) {
      originalCameraPosition.value = camera.position.clone();
      originalCameraTarget.value = controls.target.clone();
    }
    
    // 计算新的摄像机位置 - 从对象中心稍微偏移
    const newPosition = center.clone().add(new THREE.Vector3(distance, distance * 0.8, distance));
    
    // 禁用自动旋转
    const wasAutoRotating = controls.autoRotate;
    controls.autoRotate = false;
    
    // 开始摄像头过渡动画
    cameraAnimationInProgress.value = true;
    
    // 初始化动画参数
    const startPosition = camera.position.clone();
    const startTarget = controls.target.clone();
    const duration = 1500; // 动画持续时间(毫秒)
    const startTime = Date.now();
    
    // 创建动画函数
    function animateCamera() {
      const now = Date.now();
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // 使用缓动函数使动画更自然
      const easeProgress = easeInOutCubic(progress);
      
      // 更新摄像机位置
      camera.position.lerpVectors(startPosition, newPosition, easeProgress);
      
      // 更新控制器目标点 (看向对象中心)
      controls.target.lerpVectors(startTarget, center, easeProgress);
      controls.update();
      
      // 如果动画未完成，继续请求下一帧
      if (progress < 1) {
        requestAnimationFrame(animateCamera);
      } else {
        // 动画完成
        cameraAnimationInProgress.value = false;
        
        // 如果之前是自动旋转的，恢复自动旋转
        controls.autoRotate = wasAutoRotating && autoRotateEnabled.value;
      }
    }
    
    // 启动动画
    animateCamera();
    
    // 显示恢复按钮
    showRestoreButton.value = true;
  }
};

// 替换原有的 exitFocusMode 函数
const exitFocusMode = () => {
  if (!focusModeActive.value) return;
  
  // 恢复所有物体的可见性
  modelObjectsMap.value.forEach((object, id) => {
    object.visible = true;
    
    // 更新结构树的可见状态
    const itemIndex = modelStructure.value.findIndex(item => item.id === id);
    if (itemIndex >= 0) {
      modelStructure.value[itemIndex].visible = true;
    }
  });
  
  // 如果有保存的原始摄像头位置和目标点，则执行返回动画
  if (originalCameraPosition.value && originalCameraTarget.value) {
    // 禁用自动旋转
    const wasAutoRotating = controls.autoRotate;
    controls.autoRotate = false;
    
    // 开始摄像头返回动画
    cameraAnimationInProgress.value = true;
    
    // 初始化动画参数
    const startPosition = camera.position.clone();
    const startTarget = controls.target.clone();
    const endPosition = originalCameraPosition.value;
    const endTarget = originalCameraTarget.value;
    const duration = 1500; // 动画持续时间(毫秒)
    const startTime = Date.now();
    
    // 创建动画函数
    function animateCamera() {
      const now = Date.now();
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // 使用缓动函数使动画更自然
      const easeProgress = easeInOutCubic(progress);
      
      // 更新摄像机位置
      camera.position.lerpVectors(startPosition, endPosition, easeProgress);
      
      // 更新控制器目标点
      controls.target.lerpVectors(startTarget, endTarget, easeProgress);
      controls.update();
      
      // 如果动画未完成，继续请求下一帧
      if (progress < 1) {
        requestAnimationFrame(animateCamera);
      } else {
        // 动画完成
        cameraAnimationInProgress.value = false;
        
        // 重置保存的摄像头位置
        originalCameraPosition.value = null;
        originalCameraTarget.value = null;
        
        // 如果之前是自动旋转的，恢复自动旋转
        controls.autoRotate = wasAutoRotating && autoRotateEnabled.value;
      }
    }
    
    // 启动动画
    animateCamera();
  }
  
  // 重置聚焦状态
  focusModeActive.value = false;
  focusedObjectId.value = null;
  showRestoreButton.value = false;
};

// 添加缓动函数
function easeInOutCubic(t) {
  return t < 0.5 
    ? 4 * t * t * t 
    : 1 - Math.pow(-2 * t + 2, 3) / 2;
}
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
    
    <!-- <div class="controls-hint">
      <div class="hint-item"><span class="hint-key">鼠标拖动</span> 旋转视角</div>
      <div class="hint-item"><span class="hint-key">滚轮</span> 缩放</div>
      <div class="hint-item"><span class="hint-key">右键拖动</span> 平移</div>
    </div> -->
    <!-- 在controls-hint div旁边添加 -->
    <button @click="toggleAutoRotate" class="auto-rotate-btn">
      {{ autoRotateEnabled ? '停止环视' : '自动环视' }}
    </button>
    <!-- 调试按钮 -->
    <button @click="showDebugInfo = !showDebugInfo" class="debug-toggle">
      {{ showDebugInfo ? '隐藏结构' : '查看模型结构' }}
    </button>
    
    <!-- 调试面板 -->
    <div v-if="showDebugInfo" class="debug-panel">
      <h3>模型结构</h3>
      <div class="structure-tree">
        <div 
          v-for="item in modelStructure.filter(item => item.isMesh)" 
          :key="item.id" 
          class="structure-item" 
          :class="{ 
            'is-mesh': item.isMesh, 
            'is-highlighted': item.id === highlightedObjectId,
            'is-editing': item.id === editingItemId,
            'is-hidden': !item.visible
          }"
          :style="{paddingLeft: `${item.depth * 16}px`}"
          @mouseenter="handleItemMouseEnter(item.id)"
          @mouseleave="handleItemMouseLeave"
          @dblclick.stop="startEditName(item)"
        >
          <!-- 可见性切换按钮 -->
          <button 
            class="visibility-toggle"
            @click.stop="toggleVisibility(item.id)"
            :title="item.visible ? '隐藏' : '显示'"
          >
            <span v-if="item.visible">👁️</span>
            <span v-else>👁️‍🗨️</span>
          </button>
          
          <!-- 编辑状态 -->
          <div v-if="item.id === editingItemId" class="edit-name-container" @click.stop>
            <input 
              v-model="newItemName" 
              class="edit-name-input"
              @keydown="handleRenameKeydown"
              @blur="applyRename"
              v-focus
            />
          </div>
          
          <!-- 显示状态 -->
          <template v-else>
            <span class="item-name">{{ item.name || '未命名' }}</span>
            <span class="item-type">{{ item.type }}</span>
          </template>
        </div>
      </div>
    </div>
    
    <!-- 坐标显示面板 -->
    <div v-if="showCoordinates" class="coordinates-panel">
      <div class="coordinates-title">点击位置坐标</div>
      <div class="coordinates-value">X: {{ selectedPosition.x }}</div>
      <div class="coordinates-value">Y: {{ selectedPosition.y }}</div>
      <div class="coordinates-value">Z: {{ selectedPosition.z }}</div>
      <button class="close-btn" @click="showCoordinates = false">关闭</button>
    </div>
    
    <!-- 添加悬停标签 -->
    <div 
      v-if="meshLabelVisible" 
      class="mesh-label"
      :style="{
        left: `${meshLabelPosition.x}px`,
        top: `${meshLabelPosition.y}px`
      }"
    >
      {{ meshLabelContent }}
    </div>
    
    <!-- 在template中添加恢复按钮 -->
    <button 
      v-if="showRestoreButton" 
      @click="exitFocusMode" 
      class="restore-view-btn"
    >
      恢复所有模型
    </button>

    <!-- 在template中添加聚焦模式提示 -->
    <div v-if="focusModeActive" class="focus-mode-indicator">
      聚焦模式 - 双击空白区域或点击恢复按钮退出
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

/* 添加可见性切换按钮样式 */
.visibility-toggle {
  background: none;
  border: none;
  padding: 2px;
  margin-right: 4px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.7;
  transition: opacity 0.2s;
  color: #e2e8f0;
}

.visibility-toggle:hover {
  opacity: 1;
}

.structure-item {
  padding: 3px 0;
  display: flex;
  align-items: center;
}

/* 隐藏项目样式 */
.structure-item.is-hidden {
  opacity: 0.5;
}

.structure-item.is-hidden .item-name {
  text-decoration: line-through;
  color: #94a3b8;
}

.item-name {
  flex-grow: 1;
}

.item-type {
  margin-left: auto;
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

/* 添加重命名相关样式 */
.structure-item.is-editing {
  background-color: rgba(56, 189, 248, 0.15);
  padding: 6px 0;
}

.edit-name-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.edit-name-input {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(56, 189, 248, 0.5);
  border-radius: 3px;
  padding: 4px 8px;
  color: #ffffff;
  width: calc(100% - 16px);
  font-family: monospace;
  font-size: 12px;
}

/* 添加悬停提示 - 包含双击重命名信息 */
.structure-item.is-mesh::after {
  content: "👆 悬停高亮 | 双击重命名";
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

/* 坐标显示样式 */
.coordinates-panel {
  position: absolute;
  top: 100px;
  left: 20px;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(56, 189, 248, 0.5);
  border-radius: 8px;
  padding: 12px;
  z-index: 100;
  color: #e2e8f0;
}

.coordinates-title {
  font-weight: bold;
  color: #38bdf8;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(56, 189, 248, 0.3);
  padding-bottom: 4px;
}

.coordinates-value {
  font-family: monospace;
  margin: 4px 0;
}

.close-btn {
  margin-top: 8px;
  background: rgba(56, 189, 248, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.5);
  color: #38bdf8;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
}
/* 在<style>部分添加 */
.auto-rotate-btn {
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(56, 189, 248, 0.5);
  color: #38bdf8;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  z-index: 10;
  transition: all 0.3s;
}

.auto-rotate-btn:hover {
  background: rgba(15, 23, 42, 0.9);
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
}

/* 添加悬停标签样式 */
.mesh-label {
  position: fixed;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(56, 189, 248, 0.8);
  color: #38bdf8;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 12px;
  pointer-events: none;
  z-index: 1000;
  box-shadow: 0 0 8px rgba(56, 189, 248, 0.5);
  transform: translate(-50%, -100%);
  white-space: nowrap;
}

/* 恢复视图按钮样式 */
.restore-view-btn {
  position: absolute;
  top: 60px;
  right: 20px;
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #fca5a5;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  z-index: 101;
  transition: all 0.3s;
}

.restore-view-btn:hover {
  background: rgba(239, 68, 68, 0.3);
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.4);
}

/* 聚焦模式提示样式 */
.focus-mode-indicator {
  position: absolute;
  top: 15px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(56, 189, 248, 0.2);
  border: 1px solid rgba(56, 189, 248, 0.5);
  color: #38bdf8;
  padding: 6px 12px;
  border-radius: 4px;
  z-index: 100;
  font-size: 0.8rem;
}
</style>