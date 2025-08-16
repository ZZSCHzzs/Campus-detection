<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, reactive, watch, nextTick } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js';
import type { AreaItem } from '../types';

// 在<script setup>部分添加emit定义
const emit = defineEmits(['areaSelected']);

// 聚焦相关
const focusModeActive = ref(false);
const focusedObjectId = ref<string | null>(null);
const focusedModelDescription = ref<string | null>(null);
const showRestoreButton = ref(false);

// 摄像头位置相关变量
const originalCameraPosition = ref<THREE.Vector3 | null>(null);
const originalCameraTarget = ref<THREE.Vector3 | null>(null);
const cameraAnimationInProgress = ref(false);

const props = defineProps<{
  areas: AreaItem[];
  mapImage: string;
}>();

const autoRotateEnabled = ref(true);
const heatmapRef = ref<HTMLElement | null>(null);
const loadingError = ref<string | null>(null);
let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let renderer: THREE.WebGLRenderer;
let controls: OrbitControls;
let animationFrameId: number;

// 调试状态
const showDebugInfo = ref(false);
const modelStructure = ref<{ name: string; type: string; depth: number; id: string; visible: boolean }[]>([]);

// 模型引用映射和高亮状态
const modelObjectsMap = ref<Map<string, THREE.Object3D>>(new Map());
const originalMaterials = ref<Map<string, THREE.Material | THREE.Material[]>>(new Map());
const highlightedObjectId = ref<string | null>(null);

// 编辑状态管理
const editingItemId = ref<string | null>(null);
const newItemName = ref('');

// 坐标显示相关变量
const showCoordinates = ref(false);
const selectedPosition = reactive({ x: 0, y: 0, z: 0 });
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

// 顶点显示相关变量
const vertexDisplayMode = ref(false);
const vertexMarkers = ref<THREE.Points[]>([]);
const selectedVertex = reactive({
  index: -1,
  position: { x: 0, y: 0, z: 0 },
  normal: { x: 0, y: 0, z: 0 },
});
const vertexLabelVisible = ref(false);
const vertexLabelPosition = reactive({ x: 0, y: 0 });

// 判定对象及其父链是否实际可见
const isActuallyVisible = (obj: THREE.Object3D | null): boolean => {
  let cur: THREE.Object3D | null = obj;
  while (cur) {
    if (!cur.visible) return false;
    cur = cur.parent as THREE.Object3D | null;
  }
  return true;
};

// 区域定义移到全局作用域
const areaDefinitions = ref([
  {
    id: 'area1',
    name: '正心13',
    description: '正心1楼',
    position: { x: 5.2, y: 3.8, z: -16.4574 },
    radius: 2 // 球体半径
  },
  {
    id: 'area2',
    name: '正心22',
    description: '正心大教室2楼',
    position: { x: 13.6, y: 7.4, z: -11.6 },
    radius: 2 // 球体半径
  },
  {
    id: 'area3',
    name: '正心11',
    description: '正心1楼',
    position: { x: 17.6, y: 3.8, z: -2.8 },
    radius: 2 // 球体半径
  },
  {
    id: 'area4',
    name: '正心41',
    description: '正心1楼',
    position: { x: 6.1, y: 5, z: 12 },
    radius: 2 // 球体半径
  },
  {
    id: 'area4',
    name: '正心41',
    description: 't',
    position: { x: -12.72, y: 12.192, z: 13.2 },
    radius: 1 // 球体半径
  },
  {
    id: 'area4',
    name: '正心41',
    description: 't',
    position: { x: 4.1, y: 8, z: 13.2 },
    radius: 1 // 球体半径
  },
  {
    id: 'area4',
    name: '正心41',
    description: 't',
    position: { x: 8, y: 17, z: 13 },
    radius: 1 // 球体半径
  },
  {
    id: 'area4',
    name: '正心41',
    description: 't',
    position: { x: -12.72, y: 12.192, z: 13.2 },
    radius: 1 // 球体半径
  },
  {
    id: 'area4',
    name: '正心41',
    description: 't',
    position: { x: -18.72, y: 3.592, z: 6.2 },
    radius: 1 // 球体半径
  },
  {
    id: 'area4',
    name: '正心41',
    description: 't',
    position: { x: -16.72, y: 3.592, z: -12 },
    radius: 1 // 球体半径
  },
  {
    id: 'area4',
    name: '正心41',
    description: 't',
    position: { x: -16.72, y: 20, z: -7 },
    radius: 1 // 球体半径
  },
  {
    id: 'area4',
    name: '正心41',
    description: 't',
    position: { x: -1.672, y: 6, z: 12 },
    radius: 1 // 球体半径
  },
  {
    id: 'area4',
    name: '正心41',
    description: 't',
    position: { x: -1.672, y: 6, z: 12 },
    radius: 1 // 球体半径
  },
  {
    id: 'area4',
    name: '正心41',
    description: 't',
    position: { x: -1.672, y: 6, z: 12 },
    radius: 1 // 球体半径
  },
  {
    id: 'area4',
    name: '正心41',
    description: 't',
    position: { x: -17.672, y: 6, z: 1.2 },
    radius: 1 // 球体半径
  },
  {
    id: 'area4',
    name: '正心41',
    description: 't',
    position: { x: 0.9, y: 6, z: 9.8 },
    radius: 1 // 球体半径
  },
  {
    id: 'area3',
    name: '正心11',
    description: 't',
    position: { x: -16, y: 6, z: -6 },
    radius: 1 // 球体半径
  },
  {
    id: 'area3',
    name: '正心11',
    description: 't',
    position: { x: -16, y: 18, z: -6 },
    radius: 1 // 球体半径
  },
  {
    id: 'area3',
    name: '正心11',
    description: 't',
    position: { x: 17.6, y: 3.8, z: -2.8 },
    radius: 1 // 球体半径
  },
  {
    id: 'area3',
    name: '正心11',
    description: 't',
    position: { x: 17.6, y: 3.8, z: -2.8 },
    radius: 1 // 球体半径
  },
]);

// 替换原有的静态热点数据
// const heatmapPoints = [...] 替换为:
const heatmapPoints = ref([]);

// 存储点云对象引用，用于动画
const pointCloudObjects: THREE.Points[] = []

// 初始化Three.js场景
const initThreeScene = () => {
  if (!heatmapRef.value) return

  // 创建场景
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x141c2f)
  // ----- 添加自然光照系统 -----
  
  // 1. 添加环境光 - 提供柔和的基础照明
  const ambientLight = new THREE.AmbientLight(0x404040, 2);
  scene.add(ambientLight);

  // 2. 添加半球光 - 模拟天空和地面的反射光
  const hemisphereLight = new THREE.HemisphereLight(
    0x87CEEB,  // 天空色 - 淡蓝色
    0x222222,  // 地面色 - 暗灰色
    1        // 强度
  );
  scene.add(hemisphereLight);

  // 3. 添加方向光 - 模拟太阳光
  const directionalLight = new THREE.DirectionalLight(0xFFFFFF, 7);
  directionalLight.position.set(500, 750, 500);  // 光源位置
  directionalLight.castShadow = true;         // 启用阴影
  directionalLight.shadow.mapSize.width = 4096;
  directionalLight.shadow.mapSize.height = 2048;
  directionalLight.shadow.camera.near = 0.5;
  directionalLight.shadow.camera.far = 5000;
  directionalLight.shadow.camera.left = -1000;
  directionalLight.shadow.camera.right = 1000;
  directionalLight.shadow.camera.top = 1000;
  directionalLight.shadow.camera.bottom = -1000;

  // // 创建太阳光辅助标记(可选)
  // const sunSphere = new THREE.Mesh(
  //   new THREE.SphereGeometry(2, 16, 16),
  //   new THREE.MeshBasicMaterial({ color: 0xB0C4DE, transparent: true, opacity: 0.1 })
  // );
  // sunSphere.position.copy(directionalLight.position);
  // scene.add(sunSphere);
  scene.add(directionalLight);

  // ----- 自然光照系统添加完成 -----
  // 添加环境贴图
  const cubeTextureLoader = new THREE.CubeTextureLoader();
  cubeTextureLoader.setPath('./skybox/');
  const cubeTexture = cubeTextureLoader.load([
    'px.jpg', 'nx.jpg',
    'py.jpg', 'ny.jpg',
    'pz.jpg', 'nz.jpg'
  ]);

  // 设置为场景背景和环境贴图
  scene.background = cubeTexture;
  scene.environment = cubeTexture;
  // 添加地图贴图地面
  const textureLoader = new THREE.TextureLoader();
  textureLoader.load('./ground.png', (texture) => {
    // 设置贴图重复（缩放效果），如2倍缩放
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(27.5, 27.5); // X和Y方向缩放27.5倍

    // 设置贴图旋转（单位为弧度），如旋转45度
    texture.center.set(0.5, 0.5); // 以中心为旋转点
    texture.rotation = Math.PI/4*5 - Math.PI/180*4; // 旋转45度

    // 设置贴图偏移（如需要移动贴图）
    texture.offset.set(0.02, 0.04);

    // 创建平面几何体，大小可根据实际场景调整
    const planeSize = 4000;
    const geometry = new THREE.PlaneGeometry(planeSize, planeSize);
    const material = new THREE.MeshBasicMaterial({
      map: texture,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 1,
      depthWrite: true   // 地面保持深度写入
    });
    const plane = new THREE.Mesh(geometry, material);
    plane.rotation.x = -Math.PI / 2; // 使平面水平
    plane.position.y = -1; // 稍微高于0，避免与模型重叠
    plane.renderOrder = -1;
    scene.add(plane);
  });

  // 设置相机
  const { clientWidth, clientHeight } = heatmapRef.value
  camera = new THREE.PerspectiveCamera(45, clientWidth / clientHeight, 0.1, 1000)
  camera.position.set(0, 60, 80)
  
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
  controls.maxDistance = 300
  controls.maxPolarAngle = Math.PI / 2
  controls.autoRotate = autoRotateEnabled.value  // 根据状态设置自动旋转
  controls.autoRotateSpeed = 1.0  // 设置旋转速度，可以根据需要调整
    

  // // 添加坐标轴辅助工具
  // const axesHelper = new THREE.AxesHelper(5) // 参数是轴线长度
  // scene.add(axesHelper)
  

  // 加载OBJ建筑模型
  loadBuildingModel()
  
  // 添加区域标记平面
  createAreaMarkers()
  
  // 使用nextTick确保数据已更新后再创建热力图
  nextTick(() => {
    // 添加热力点云
    createHeatmapPointCloud()
  })
    
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
        object.scale.set(0.02, 0.02, 0.02)
        
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
            child.renderOrder = 1;
          }
        })
        
        // 在加载模型成功后的处理函数中
        object.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            // 创建透明材质
            const transparentMaterial = new THREE.MeshStandardMaterial({
              color: 0xB0C4DE,       // 淡蓝色调
              transparent: true,
              opacity: 0.3,          // 略微提高不透明度，让光照更明显
              roughness: 0.5,
              metalness: 0.005,
              side: THREE.DoubleSide, 
              depthWrite: true,      // 启用深度写入以正确处理光照
              flatShading: false,
              envMapIntensity: 0.3,  // 减弱环境贴图的影响，让直接光源更明显
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
                    // 使用平方或立方函数创建更平滑的渐变
                    const factor = Math.pow(Math.min(Math.max((y + 10) / 20, 0), 1), 2);
                    // 使用更柔和的颜色变化
                    color.setRGB(0.45 + factor * 0.15, 0.48 + factor * 0.15, 0.52 + factor * 0.15);
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
            // 使用加权法线平滑算法，减少条纹效果
            if (child.geometry) {
              // 清除任何现有法线
              child.geometry.deleteAttribute('normal');
              
              // 使用修改后的法线计算方法
              computeSmoothVertexNormals(child.geometry);
            }
            child.material = new THREE.MeshPhongMaterial({
              color: 0x6b7280,
              transparent: true,
              opacity: 0.8
            })
            child.castShadow = true
            child.receiveShadow = true
          }
        })
        
        // 添加平滑法线计算函数
        const computeSmoothVertexNormals = (geometry) => {
          const positions = geometry.getAttribute('position');
          const normals = new Float32Array(positions.count * 3);
          
          // 创建面法线
          for (let i = 0; i < positions.count; i += 3) {
            const v1 = new THREE.Vector3().fromBufferAttribute(positions, i);
            const v2 = new THREE.Vector3().fromBufferAttribute(positions, i + 1);
            const v3 = new THREE.Vector3().fromBufferAttribute(positions, i + 2);
            
            const cb = new THREE.Vector3().subVectors(v3, v2);
            const ab = new THREE.Vector3().subVectors(v1, v2);
            const normal = new THREE.Vector3().crossVectors(cb, ab).normalize();
            
            normals[i * 3] = normal.x;
            normals[i * 3 + 1] = normal.y;
            normals[i * 3 + 2] = normal.z;
            
            normals[(i + 1) * 3] = normal.x;
            normals[(i + 1) * 3 + 1] = normal.y;
            normals[(i + 1) * 3 + 2] = normal.z;
            
            normals[(i + 2) * 3] = normal.x;
            normals[(i + 2) * 3 + 1] = normal.y;
            normals[(i + 2) * 3 + 2] = normal.z;
          }
          
          // 设置新的法线属性
          geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
        }
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

// 添加鼠标悬停对象标签相关变量
const hoveredMeshId = ref<string | null>(null);
const meshLabelVisible = ref(false);
const meshLabelPosition = reactive({
  x: 0,
  y: 0
});
const meshLabelContent = ref('');

// 添加射线检测和悬停高亮功能
const handleCanvasMouseMove = (event) => {
  if (!heatmapRef.value || !camera || !scene || !renderer) return;
  
  // 计算鼠标在canvas中的归一化坐标（-1到1之间）
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  
  // 更新射线投射器
  raycaster.setFromCamera(mouse, camera);
  
  // 获取与射线相交的所有物体（递归）
  const intersects = raycaster.intersectObjects(scene.children, true);
  // 仅保留"实际可见"的命中结果
  let visibleIntersects = intersects.filter(i => isActuallyVisible(i.object));
  
  // 在聚焦模式下额外过滤区域标记和模型部分
  if (focusModeActive.value && focusedModelDescription.value) {
    const focusedDescription = focusedModelDescription.value.toLowerCase();
    
    visibleIntersects = visibleIntersects.filter(intersect => {
      const obj = intersect.object;
      
      // 如果是区域标记，检查描述是否匹配
      if (obj.userData?.isAreaMarker) {
        const areaDescription = (obj.userData.areaDescription || '').toLowerCase();
        
        // 宽松匹配：只要描述中包含相同的关键字即可
        const isMatching = 
          areaDescription.includes(focusedDescription) ||
          focusedDescription.includes(areaDescription);
        
        return isMatching;
      } 
      // 如果是其他网格对象，检查其名称或父级名称是否与聚焦模型匹配
      else if (obj instanceof THREE.Mesh) {
        // 检查自身名称
        const objName = (obj.name || '').toLowerCase();
        if (objName && (objName.includes(focusedDescription) || focusedDescription.includes(objName))) {
          return true;
        }
        
        // 检查是否与聚焦对象ID直接相关
        if (focusedObjectId.value && (obj.uuid === focusedObjectId.value || obj.parent?.uuid === focusedObjectId.value)) {
          return true;
        }
        
        // 检查父级对象链
        let parent = obj.parent;
        while (parent) {
          const parentName = (parent.name || '').toLowerCase();
          if (parentName && (parentName.includes(focusedDescription) || focusedDescription.includes(parentName))) {
            return true;
          }
          
          if (parent.uuid === focusedObjectId.value) {
            return true;
          }
          
          parent = parent.parent;
        }
        
        // 不匹配，过滤掉
        return false;
      }
      
      // 默认保留非网格对象（如光源等）
      return true;
    });
  }
  
  // 如果有相交的可见物体
  if (visibleIntersects.length > 0) {
    // 首先检查是否是区域标记
    let areaMarker = null;
    let meshObject = null;
    
    // 重置所有区域标记的悬停状态
    modelObjectsMap.value.forEach((object) => {
      if (object.userData?.isAreaMarker) {
        object.userData.isHovered = false;
      }
    });
    
    // 遍历所有可见交点找到区域标记或网格对象
    for (let i = 0; i < visibleIntersects.length; i++) {
      const obj = visibleIntersects[i].object;
      
      // 检查是否是区域标记
      if (obj.userData && obj.userData.isAreaMarker) {
        areaMarker = obj;
        // 设置悬停状态
        obj.userData.isHovered = true;
        break; // 区域标记优先级最高
      }
      
      // 如果还没找到网格对象，检查当前对象是否为网格
      if (!meshObject && obj instanceof THREE.Mesh) {
        meshObject = obj;
      }
    }
    
    // 优先处理区域标记
    if (areaMarker) {
      const id = areaMarker.uuid;
      
      // 避免重复处理同一个对象
      if (hoveredMeshId.value !== id) {
        // 重置之前的高亮
        resetHoveredState();
        
        // 设置当前悬停ID
        hoveredMeshId.value = id;
        
        // 创建区域标签内容 - 添加区域名称、描述和人数信息
        const areaName = areaMarker.userData.areaName || '未命名区域';
        const areaDesc = areaMarker.userData.areaDescription || '';
        
        // 获取匹配的区域数据中的人数和温湿度信息
        let peopleInfo = '';
        let tempHumidInfo = '';
        
        if (areaMarker.userData.matchedAreaData) {
          const data = areaMarker.userData.matchedAreaData;
          const detected = data.detected_count || 0;
          const capacity = data.capacity || '未知';
          peopleInfo = `<div class="area-people">当前人数: ${detected}/${capacity}</div>`;
          tempHumidInfo = `<div class="area-climate">
              ${data.temperature !== undefined ? `温度: ${data.temperature}°C` : ''}
              ${data.temperature !== undefined && data.humidity !== undefined ? ' | ' : ''}
              ${data.humidity !== undefined ? `湿度: ${data.humidity}%` : ''}
          </div>`;
          
        } 
        else {
          // 即使没有匹配的数据也显示默认人数信息
          peopleInfo = `<div class="area-people">当前人数: 0/未知</div>`;
        }
        
        // 更新标签内容和位置
        meshLabelContent.value = `<div class="area-label">
          <div class="area-name">${areaName}</div>
          ${areaDesc ? `<div class="area-desc">位置：${areaDesc}</div>` : ''}
          ${peopleInfo}
          ${tempHumidInfo}
        </div>`;
        
        meshLabelPosition.x = event.clientX;
        meshLabelPosition.y = event.clientY - 25;
        meshLabelVisible.value = true;
      } else {
        meshLabelPosition.x = event.clientX;
        meshLabelPosition.y = event.clientY - 25;
      }
    }
    // 如果不是区域标记但是网格对象
    else if (meshObject) {
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
        const structureItem = modelStructure.value.find(item => item.id === id);
        if (structureItem) {
          objectName = structureItem.name || objectName;
        }
        
        // 更新标签内容和位置
        meshLabelContent.value = objectName;
        meshLabelPosition.x = event.clientX;
        meshLabelPosition.y = event.clientY - 25;
        meshLabelVisible.value = true;
      } else {
        meshLabelPosition.x = event.clientX;
        meshLabelPosition.y = event.clientY - 25;
      }
    } else {
      // 没有指向Mesh对象或区域标记，重置
      resetHoveredState();
    }
  } else {
    // 重置所有区域标记的悬停状态
    modelObjectsMap.value.forEach((object) => {
      if (object.userData?.isAreaMarker) {
        object.userData.isHovered = false;
      }
    });
    
    // 没有指向任何可见对象，重置
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
  animationFrameId = requestAnimationFrame(animate);
  
  // 更新控制器
  if (controls && !cameraAnimationInProgress.value) {
    controls.update();
  }
  
  // 获取当前时间
  const time = Date.now() * 0.001
  
  // 更新区域标记动画效果
  modelObjectsMap.value.forEach((object) => {
    if (object.userData?.isAreaMarker) {
      const material = object.material;
      const phase = object.userData.pulsePhase || 0;
      
      if (object.userData.isSelected) {
        // 选中状态 - 绿色强烈闪烁效果
        material.opacity = 1 + Math.sin(time * 4 + phase) * 0.2;
        material.color.setRGB(
          0.2 + Math.sin(time * 2) * 0.1, 
          1 + Math.sin(time * 3) * 0.1, 
          0.4 + Math.sin(time * 2.5) * 0.1
        );
        
        // 更新光晕效果
        if (object.children[0] && object.children[0].material) {
          object.children[0].material.opacity = 0.8 + Math.sin(time * 3 + phase) * 0.1;
          object.children[0].scale.setScalar(1.2 + Math.sin(time * 2) * 0.1);
        }
      }
      else if (object.userData.isHovered) {
        // 悬停状态 - 明显的闪烁效果
        material.opacity = 1 + Math.sin(time * 5 + phase) * 0.2;
        material.color.setRGB(
          0.6 + Math.sin(time * 3) * 0.4, 
          0.8 + Math.sin(time * 4 + 1) * 0.2, 
          1.0
        );
        
        // 更新光晕效果
        if (object.children[0] && object.children[0].material) {
          object.children[0].material.opacity = 0.8 + Math.sin(time * 3 + phase) * 0.1;
          object.children[0].scale.setScalar(1.1 + Math.sin(time * 2) * 0.05);
        }
      } else {
        // 非悬停状态 - 几乎完全透明
        material.opacity = 0;
        material.color.setRGB(0.22, 0.74, 0.97); // 恢复原始颜色
        
        // 更新光晕效果
        if (object.children[0] && object.children[0].material) {
          object.children[0].material.opacity = 0.0001;
          object.children[0].scale.setScalar(1.1);
        }
      }
    }
  });
  
  // 为点云添加动画效果
  pointCloudObjects.forEach((cloud, cloudIndex) => {
    const geometry = cloud.geometry
    const positionAttribute = geometry.getAttribute('position')
    const velocityAttribute = geometry.getAttribute('velocity')
    const randomnessAttribute = geometry.getAttribute('randomness')
    const phaseAttribute = geometry.getAttribute('phase')
    const originalPositions = geometry.userData.originalPositions
    
    // 更新每个点的位置
    for (let i = 0; i < positionAttribute.count; i++) {
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
      
      // 计算杂乱运动 - 使用不同频率的正弦波叠加
      const noiseX = Math.sin(time * 1.7 + phase) * rx  
      const noiseY = Math.sin(time * 2.3 + phase * 2) * ry 
      const noiseZ = Math.sin(time * 1.5 + phase * 3) * rz 
      
      // 随机漂移运动
      const driftX = vx * Math.sin(time * 0.7 + i * 1) 
      const driftY = vy * Math.sin(time * 0.9 + i * 0.5) 
      const driftZ = vz * Math.sin(time * 0.8 + i * 1.5) 
      
      // 更新位置 - 围绕原始位置进行杂乱运动
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

// 切换顶点显示模式
const toggleVertexDisplay = () => {
  if (vertexDisplayMode.value) {
    // 关闭模式 - 移除所有顶点标记
    removeVertexMarkers();
    vertexDisplayMode.value = false;
  } else {
    // 开启模式 - 显示当前可见模型的顶点
    displayModelVertices();
    vertexDisplayMode.value = true;
  }
}

// 移除所有顶点标记
const removeVertexMarkers = () => {
  vertexMarkers.value.forEach(markers => {
    scene.remove(markers);
    if (markers.geometry) markers.geometry.dispose();
    if (markers.material) markers.material.dispose();
  });
  
  vertexMarkers.value = [];
  vertexLabelVisible.value = false;
}

// 显示模型顶点
const displayModelVertices = () => {
  // 首先移除现有标记
  removeVertexMarkers();
  
  // 查找所有可见的网格
  scene.traverse((object) => {
    if (object instanceof THREE.Mesh && isActuallyVisible(object) && 
        // 忽略面积过大的平面(如地面)
        !(object.geometry instanceof THREE.PlaneGeometry && object.geometry.parameters.width > 10)) {
      
      // 获取顶点位置
      const geometry = object.geometry;
      const positionAttr = geometry.getAttribute('position');
      
      // 创建顶点标记几何体
      const markerGeometry = new THREE.BufferGeometry();
      const positions = new Float32Array(positionAttr.count * 3);
      
      // 存储原始索引以便后续查询
      const indices = new Uint32Array(positionAttr.count);
      
      // 仅显示唯一顶点，避免重复
      const uniqueVertices = new Map();
      
      for (let i = 0; i < positionAttr.count; i++) {
        const x = positionAttr.getX(i);
        const y = positionAttr.getY(i);
        const z = positionAttr.getZ(i);
        
        // 使用顶点位置作为键来检测重复
        const key = `${Math.round(x*1000)},${Math.round(y*1000)},${Math.round(z*1000)}`;
        
        if (!uniqueVertices.has(key)) {
          const index = uniqueVertices.size;
          uniqueVertices.set(key, index);
          
          // 将顶点转换到世界坐标
          const vertex = new THREE.Vector3(x, y, z);
          vertex.applyMatrix4(object.matrixWorld);
          
          positions[index*3] = vertex.x;
          positions[index*3 + 1] = vertex.y;
          positions[index*3 + 2] = vertex.z;
          
          indices[index] = i;
        }
      }
      
      // 裁剪数组到实际大小
      const uniqueCount = uniqueVertices.size;
      markerGeometry.setAttribute('position', 
        new THREE.BufferAttribute(positions.slice(0, uniqueCount * 3), 3));
      markerGeometry.setAttribute('originalIndex', 
        new THREE.BufferAttribute(indices.slice(0, uniqueCount), 1));
      
      // 存储对原始几何体和网格的引用
      markerGeometry.userData = {
        originalGeometry: geometry,
        originalMesh: object
      };
      
      // 创建顶点标记材质
      const markerMaterial = new THREE.PointsMaterial({
        size: 0.05,
        color: 0xffff00,
        sizeAttenuation: true,
        transparent: true,
        opacity: 0.8,
        depthTest: true
      });
      
      // 创建点云对象
      const markers = new THREE.Points(markerGeometry, markerMaterial);
      markers.name = `顶点标记_${object.name || object.uuid}`;
      
      // 添加到场景
      scene.add(markers);
      
      // 存储引用
      vertexMarkers.value.push(markers);
      
      console.log(`为对象 "${object.name || '未命名'}" 添加了 ${uniqueCount} 个顶点标记`);
    }
  });
}

// 处理顶点点击
const handleVertexClick = (event) => {
  if (!vertexDisplayMode.value) return;
  
  // 计算射线检测
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  
  raycaster.setFromCamera(mouse, camera);
  
  // 仅与顶点标记进行交叉检测
  const intersects = raycaster.intersectObjects(vertexMarkers.value, false);
  
  if (intersects.length > 0) {
    const intersection = intersects[0];
    const pointIndex = intersection.index;
    
    // 获取点云和对应的原始几何体
    const pointCloud = intersection.object;
    const markerGeometry = pointCloud.geometry;
    const positionAttr = markerGeometry.getAttribute('position');
    const originalIndexAttr = markerGeometry.getAttribute('originalIndex');
    
    // 确保索引有效且在范围内
    if (pointIndex === undefined || pointIndex < 0 || pointIndex >= positionAttr.count) {
      console.error('无效的点索引:', pointIndex);
      return;
    }
    
    // 重要：强制刷新射线检测结果
    raycaster.params.Points.threshold = 0.1;
    
    // 打印当前点击的索引，帮助调试
    console.log('点击顶点索引:', pointIndex, '点所属点云ID:', pointCloud.uuid);
    
    // 获取原始顶点索引 - 确保索引获取正确
    const originalIndex = originalIndexAttr ? originalIndexAttr.getX(pointIndex) : pointIndex;
    
    // 获取顶点位置 - 直接从当前点云数据中获取
    const vertex = new THREE.Vector3();
    vertex.fromBufferAttribute(positionAttr, pointIndex);
    
    // 获取原始网格和几何体
    const originalGeometry = markerGeometry.userData.originalGeometry;
    const originalMesh = markerGeometry.userData.originalMesh;
    
    // 尝试获取法线信息
    let normal = { x: 0, y: 0, z: 0 };
    if (originalGeometry.getAttribute('normal')) {
      const normalAttr = originalGeometry.getAttribute('normal');
      // 确保原始索引有效
      const validNormalIndex = Math.min(originalIndex, normalAttr.count - 1);
      
      const normalVec = new THREE.Vector3();
      normalVec.fromBufferAttribute(normalAttr, validNormalIndex);
      
      // 应用旋转矩阵转换法线到世界坐标
      normalVec.applyQuaternion(originalMesh.quaternion);
      normal = { 
        x: parseFloat(normalVec.x.toFixed(4)), 
        y: parseFloat(normalVec.y.toFixed(4)), 
        z: parseFloat(normalVec.z.toFixed(4)) 
      };
    }
    
    // 重要：使用Object.assign进行赋值，确保reactive对象更新
    Object.assign(selectedVertex, {
      index: originalIndex,
      position: { 
        x: parseFloat(vertex.x.toFixed(4)), 
        y: parseFloat(vertex.y.toFixed(4)),
        z: parseFloat(vertex.z.toFixed(4)) 
      },
      normal: normal
    });
    
    // 显示顶点标签 - 确保位置正确更新
    vertexLabelPosition.x = event.clientX;
    vertexLabelPosition.y = event.clientY;
    vertexLabelVisible.value = true;
    
    // 高亮显示选中的顶点
    highlightSelectedVertex(pointCloud, pointIndex);
    
    // 强制UI更新
    nextTick(() => {
      console.log('已更新顶点信息:', JSON.stringify(selectedVertex));
    });
  } else {
    // 点击空白处，隐藏标签
    vertexLabelVisible.value = false;
    resetVertexHighlight();
  }
}

// 高亮显示选中顶点
const highlightSelectedVertex = (pointCloud, index) => {
  // 重置之前的高亮
  resetVertexHighlight();
  
  // 记录当前点云和原始颜色
  const material = pointCloud.material as THREE.PointsMaterial;
  
  // 存储原始颜色
  material.userData = material.userData || {};
  material.userData.originalColor = material.color.clone();
  
  // 修改为高亮颜色
  material.color.set(0xff0000); // 红色高亮
  material.size = 0.08; // 增大选中点的尺寸
  
  // 保存点云和索引以便后续重置
  material.userData.highlightedPointCloud = pointCloud;
  material.userData.highlightedIndex = index;
}

// 重置顶点高亮
const resetVertexHighlight = () => {
  vertexMarkers.value.forEach(markers => {
    const material = markers.material as THREE.PointsMaterial;
    if (material.userData?.originalColor) {
      material.color.copy(material.userData.originalColor);
      material.size = 0.05;
    }
  });
}


// 组件卸载前清理资源
onBeforeUnmount(() => {
  window.removeEventListener('resize', onWindowResize)
  
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null;
  }
  
  // 清理点云对象
  pointCloudObjects.forEach(cloud => {
    if (cloud && cloud.parent) {
      cloud.parent.remove(cloud);
    }
    if (cloud && cloud.geometry) cloud.geometry.dispose();
    if (cloud && cloud.material) {
      if (Array.isArray(cloud.material)) {
        cloud.material.forEach(material => material.dispose());
      } else {
        cloud.material.dispose();
      }
    }
  });
  pointCloudObjects.length = 0;
  
  if (renderer) {
    renderer.dispose()
    renderer.forceContextLoss();
    renderer = null;
  }
  
  if (heatmapRef.value && renderer) {
    try {
      heatmapRef.value.removeChild(renderer.domElement)
    } catch (e) {
      console.warn('移除渲染器DOM时出错:', e);
    }
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
    scene = null;
  }
  
  // 清理材质引用
  originalMaterials.value.clear();
  modelObjectsMap.value.clear();
  // 清理顶点标记
  removeVertexMarkers();
  
  // 清理其他引用
  camera = null;
  controls = null;
})

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


// handleCanvasClick函数
const handleCanvasClick = (event) => {
  // 顶点显示模式下调用顶点点击处理函数
  if (vertexDisplayMode.value) {
    handleVertexClick(event);
    return;
  }
  if (!heatmapRef.value || !camera || !scene) return
  
  // 计算鼠标在canvas中的归一化坐标（-1到1之间）
  const rect = renderer.domElement.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
  
  // 设置射线投射器
  raycaster.setFromCamera(mouse, camera)
  
  // 获取与射线相交的所有物体
  const intersects = raycaster.intersectObjects(scene.children, true)
  
  // 检查是否点击了区域标记
  let hitAreaMarker = false;
  
  if (intersects.length > 0) {
    for (let i = 0; i < intersects.length; i++) {
      const obj = intersects[i].object;
      if (obj.userData?.isAreaMarker) {
        hitAreaMarker = true;
        // 如果是区域标记，获取其关联数据
        const areaData = obj.userData.matchedAreaData;
        const areaName = obj.userData.areaName;
        const areaId = areaData?.id;
        
        console.log(`区域 ${areaName} 被点击，ID: ${areaId}`);
        
        // 为点击的区域添加选中效果
        highlightSelectedArea(obj);
        
        // 发送事件通知父组件，传递区域ID
        if (areaId) {
          emit('areaSelected', areaId);
        }
        
        // 已处理区域点击，不需要继续处理坐标显示
        return;
      }
    }
  }
  
  // 如果代码执行到这里，表示没有点击到区域标记
  // 无论是点击了其他物体还是点击了空白区域，都应该重置选中状态
  if (selectedArea.value) {
    resetSelectedArea();
  }
  
  // 处理其他点击逻辑（如果有物体被点击）
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
  // 添加重置选中区域的函数
const resetSelectedArea = () => {
  if (selectedArea.value) {
    // 重置选中区域的效果
    selectedArea.value.material.color.set(0x38bdf8);
    selectedArea.value.userData.isSelected = false;
    
    if (selectedArea.value.children[0]) {
      selectedArea.value.children[0].material.color.set(0x38bdf8);
    }
    
    selectedArea.value = null;
  }
};
// 添加选中区域高亮效果函数
const selectedArea = ref(null);

// 修改highlightSelectedArea函数，确保正确处理区域切换
const highlightSelectedArea = (areaObj) => {
  // 如果点击的是已选中的区域，则不做任何处理
  if (selectedArea.value === areaObj) {
    return;
  }
  
  // 先重置之前选中的区域（如果有）
  if (selectedArea.value) {
    // 重置之前选中区域的效果
    selectedArea.value.material.color.set(0x38bdf8);
    selectedArea.value.userData.isSelected = false;
    
    if (selectedArea.value.children[0]) {
      selectedArea.value.children[0].material.color.set(0x38bdf8);
    }
  }
  
  // 设置新选中的区域
  selectedArea.value = areaObj;
  
  // 添加选中效果 - 使用绿色
  areaObj.material.color.set(0x4ade80);
  areaObj.userData.isSelected = true;
  
  // 如果有光晕效果，也更新其颜色
  if (areaObj.children[0] && areaObj.children[0].material) {
    areaObj.children[0].material.color.set(0x4ade80);
  }
  // 在highlightSelectedArea函数的最后添加:
  console.log('设置区域选中状态:', areaObj.userData.areaName, '已选中');
  console.log('材质信息:', {
    isSelected: areaObj.userData.isSelected,
    color: areaObj.material.color.getHexString(),
    opacity: areaObj.material.opacity
  });
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
const createDensityField = (points, resolution = 48) => { // 降低分辨率提高性能
  if (!points || points.length === 0) {
    console.warn('没有热点数据，使用默认空密度场');
    return { 
      grid: new Array(resolution * resolution * resolution).fill(0),
      bounds: {
        min: new THREE.Vector3(-20, -5, -20),
        max: new THREE.Vector3(20, 15, 20)
      },
      resolution,
      cellSize: new THREE.Vector3(40/resolution, 20/resolution, 40/resolution)
    };
  }
  
  console.log('开始创建密度场，点数:', points.length);
  const grid = new Array(resolution * resolution * resolution).fill(0);
  
  // 使用固定边界而非从场景动态计算
  const bounds = {
    min: new THREE.Vector3(-40, 0, -40),
    max: new THREE.Vector3(40, 30, 40)
  };
  
  // 计算大小
  const size = new THREE.Vector3().subVectors(bounds.max, bounds.min);
  const cellSize = size.clone().divideScalar(resolution);
  // 预先计算一些常量来提高循环性能
  const maxDistanceSquared = 100; // 最大影响距离的平方
  
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
// 生成热力点数据函数
const generateHeatmapPoints = () => {
  console.log('生成热力点数据...');
  const points = [];
  
  // 遍历所有区域定义
  areaDefinitions.value.forEach(area => {
    // 查找匹配的区域数据，获取人数
    const matchedAreaData = props.areas.find(a => a.name === area.name);
    const personCount = matchedAreaData?.detected_count || 0;
    
    console.log(`区域 ${area.name} 匹配人数: ${personCount}`);
    
    // 创建中心热力点 - 直接使用区域定义的坐标
    points.push({
      x: area.position.x,
      y: area.position.y,
      z: area.position.z,
      intensity: personCount * 1.2 // 中心点强度略高
    });
    
    // 根据人数生成周围热力点，越多人生成越多点
    const pointCount = personCount;
    
    // 在中心点周围生成额外的点，形成热力云
    for (let i = 0; i < pointCount; i++) {
      // 使用高斯分布生成更集中的点
      const angle = Math.random() * Math.PI * 2;
      
      // 增强中心集中效果：
      // 1. 使用更小的半径因子 0.05 -> 0.03
      // 2. 使用三次随机平均值而不是二次随机，大幅增强中心集中效果
      
      const radius = area.radius;
      
      // 计算偏移坐标
      const x = area.position.x + Math.cos(angle) * radius;
      const z = area.position.z + Math.sin(angle) * radius;
      const y = area.position.y + (Math.random() - 0.5) * 0.1; // 进一步减小垂直变化
      
      // 距离中心越近强度越高 - 使用4次方增强中心集中效果
      const distFactor = 1.0 - Math.pow(radius / (area.radius), 2);
      const intensity = personCount * (0.15 + distFactor * 0.85); // 增大中心与边缘强度差异
      
      points.push({
        x, y, z,
        intensity
      });
    }
  });
  
  console.log(`共生成 ${points.length} 个热力点`);
  return points;
};
// 热力点云创建函数
const createHeatmapPointCloud = () => {
  try {
    console.log('开始创建热力点云');
    
    // 清理之前可能存在的点云对象
    pointCloudObjects.forEach(cloud => {
      if (cloud && cloud.parent) {
        cloud.parent.remove(cloud);
      }
      if (cloud && cloud.geometry) cloud.geometry.dispose();
      if (cloud && cloud.material) cloud.material.dispose();
    });
    pointCloudObjects.length = 0;
    
    // 生成热力点数据
    heatmapPoints.value = generateHeatmapPoints();
    
    // 确保热点数据存在且有效
    if (!heatmapPoints.value || heatmapPoints.value.length === 0) {
      console.warn('热点数据为空，创建默认热力点');
      // 创建一些默认点以避免渲染错误
      heatmapPoints.value = [
        { x: 0, y: 1, z: 0, intensity: 1 },
        { x: 1, y: 1, z: 1, intensity: 0.5 }
      ];
    }
    
    console.log(`使用 ${heatmapPoints.value.length} 个热力点创建密度场`);
    
    // 创建密度场
    const densityField = createDensityField(heatmapPoints.value);
    
    // 生成粒子几何体
    const particleGeometry = createParticlesFromDensityField(densityField);
    
    // 如果几何体无效，提前返回
    if (!particleGeometry) {
      console.error('创建粒子几何体失败');
      return;
    }
    
    // 创建粒子贴图
    const createParticleTexture = () => {
      const canvas = document.createElement('canvas');
      const size = 64;
      canvas.width = size;
      canvas.height = size;
      const context = canvas.getContext('2d');
      
      // 创建径向渐变
      const gradient = context.createRadialGradient(
        size/2, size/2, 0,
        size/2, size/2, size/2
      );
      
      gradient.addColorStop(0, 'rgba(255, 255, 255, 1.0)');   // 中心完全不透明
      gradient.addColorStop(0.2, 'rgba(255, 255, 255, 0.9)'); // 近中心区域高亮度
      gradient.addColorStop(0.4, 'rgba(255, 255, 255, 0.7)'); // 中间区域增强亮度
      gradient.addColorStop(0.7, 'rgba(255, 255, 255, 0.3)'); // 渐变过渡
      gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');     // 边缘完全透明
      
      context.fillStyle = gradient;
      context.fillRect(0, 0, size, size);
      
      return new THREE.CanvasTexture(canvas);
    }

    // 创建并应用贴图到点云材质
    const particleTexture = createParticleTexture();
    const particleMaterial = new THREE.PointsMaterial({
      size: 0.7,
      vertexColors: true,
      transparent: true,
      opacity: 1,
      blending: THREE.NormalBlending,
      sizeAttenuation: true,
      depthWrite: false,
      map: particleTexture,
      alphaTest: 0.01
    });
    // 创建点云对象并添加到场景
    const particles = new THREE.Points(particleGeometry, particleMaterial);
    particles.renderOrder = 0; // 确保粒子后渲染
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
  const desiredParticleCount = 100000000
  console.log(`目标粒子数量: ${desiredParticleCount}`);
  
  // 预分配数组
  const particlePositions = new Float32Array(desiredParticleCount * 3);
  const particleColors = new Float32Array(desiredParticleCount * 3);
  const particleVelocity = new Float32Array(desiredParticleCount * 3);
  const particleRandomness = new Float32Array(desiredParticleCount * 3);
  const particlePhases = new Float32Array(desiredParticleCount);
  
  let particleIndex = 0;
  
  // 使用接受-拒绝采样法基于密度分布生成粒子
  const attempts = desiredParticleCount ; // 限制尝试次数
  for (let i = 0; i < attempts; i++) {
    // 随机选择一个网格点
    const x = Math.floor(Math.random() * resolution);
    const y = Math.floor(Math.random() * resolution);
    const z = Math.floor(Math.random() * resolution);
    
    const gridIndex = x + y * resolution + z * resolution * resolution;
    const cellDensity = grid[gridIndex];
    
    // 归一化的密度值
    const normalizedDensity = cellDensity / maxDensity;
    
    // 对密度值进行非线性增强，让高密度区域的概率增长更快

    // 添加基础概率确保低密度区域也能生成粒子
    const baseProbability = 0.000005;  // 降低基础概率，让低密度区域更稀疏
    const densityWeight = 0.999995;    // 增加密度权重

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
      const MID_DENSITY_THRESHOLD = 80;  // 中密度阈值

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
      particleVelocity[index] = (Math.random() - 0.5) * 1;
      particleVelocity[index + 1] = (Math.random() - 0.5) * 1;
      particleVelocity[index + 2] = (Math.random() - 0.5) * 1;
      
      particleRandomness[index] = Math.random() * 0.3;
      particleRandomness[index + 1] = Math.random() * 0.3;
      particleRandomness[index + 2] = Math.random() * 0.3;
      
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

// 添加一个新函数，用于在双击区域标记时同步显示相关模型部分
const handleAreaMarkerSelection = (areaMarker) => {
  if (!areaMarker || !areaMarker.userData || !areaMarker.userData.isAreaMarker) {
    return false; // 不是区域标记，返回false
  }
  
  // 获取关联的模型部分IDs
  const relatedModelPartIds = areaMarker.userData.relatedModelPartIds || [];
  
  console.log(`选中区域标记 "${areaMarker.userData.areaName}"，关联 ${relatedModelPartIds.length} 个模型部分`);
  
  // 切换聚焦模式，传入区域标记ID
  toggleFocusMode(areaMarker.uuid);
  
  return true; // 返回true表示已处理区域标记
};
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
  const visibleIntersects = intersects.filter(i => isActuallyVisible(i.object));
  
  // 如果有相交的物体且不是在聚焦模式下，则聚焦该物体
  if (visibleIntersects.length > 0 && !focusModeActive.value) {
    // 首先检查是否命中区域标记
    for (let i = 0; i < visibleIntersects.length; i++) {
      const obj = visibleIntersects[i].object;
      // 检查是否是区域标记
      if (obj.userData && obj.userData.isAreaMarker) {
        // 处理区域标记选择
        if (handleAreaMarkerSelection(obj)) {
          return; // 已处理区域标记，退出函数
        }
      }
    }
    
    // 如果不是区域标记，查找第一个是Mesh的对象
    let meshObject = null;
    let i = 0;
    
    while (i < visibleIntersects.length && !meshObject) {
      if (visibleIntersects[i].object instanceof THREE.Mesh) {
        meshObject = visibleIntersects[i].object;
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
    
    // 找到聚焦的对象
    const focusedObject = modelObjectsMap.value.get(objectId);
    if (!focusedObject) {
      console.error('找不到聚焦对象:', objectId);
      return;
    }
    
    console.log('聚焦对象:', focusedObject.name || 'unnamed');
    
    // 检查是否为区域标记
    const isAreaMarker = focusedObject.userData?.isAreaMarker === true;
    let relatedModelPartIds = [];
    
    // 如果是区域标记，获取并记录其描述信息
    if (isAreaMarker && focusedObject.userData?.areaDescription) {
      focusedModelDescription.value = focusedObject.userData.areaDescription;
      console.log(`记录聚焦区域描述: ${focusedModelDescription.value}`);
    } else {
      // 如果是模型部分，尝试从其名称或属性中获取描述
      focusedModelDescription.value = focusedObject.name || null;
      console.log(`记录聚焦模型描述: ${focusedModelDescription.value}`);
    }
    
    // 首先标记所有对象为不可见
    modelObjectsMap.value.forEach((object, id) => { 
      const isCurrentAreaMarker = object.userData?.isAreaMarker === true;
      const itemIndex = modelStructure.value.findIndex(item => item.id === id); 
      
      // 保持所有区域标记可见
      if (isCurrentAreaMarker) { 
        object.visible = true; 
        if (itemIndex >= 0) modelStructure.value[itemIndex].visible = true; 
        return; 
      } 
      
      // 其他对象默认隐藏
      object.visible = false; 
      if (itemIndex >= 0) modelStructure.value[itemIndex].visible = false; 
    });
    
    // 隐藏所有热力图点云
    pointCloudObjects.forEach(cloud => {
      cloud.visible = false;
    });
    
    // 递归地将聚焦对象及其所有子对象标记为可见
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
    
    // 如果是区域标记，额外处理关联的模型部分
    if (isAreaMarker && relatedModelPartIds.length > 0) {
      // 使所有关联的模型部分可见
      relatedModelPartIds.forEach(id => {
        const modelPart = modelObjectsMap.value.get(id);
        if (modelPart) {
          makeObjectAndChildrenVisible(modelPart);
          
          // 确保模型部分的父链也是可见的
          let parent = modelPart.parent;
          while (parent) {
            parent.visible = true;
            
            // 更新结构树状态
            const itemIndex = modelStructure.value.findIndex(item => item.id === parent.uuid);
            if (itemIndex >= 0) {
              modelStructure.value[itemIndex].visible = true;
            }
            
            parent = parent.parent;
          }
        }
      });
      
      console.log(`已显示区域 "${focusedObject.userData.areaName}" 关联的 ${relatedModelPartIds.length} 个模型部分`);
    }
    
    // 如果不是区域标记，检查对象的父级，确保它们也是可见的
    if (!isAreaMarker) {
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

// # 修改exitFocusMode函数
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
  
  // 恢复所有热力图点云的可见性
  pointCloudObjects.forEach(cloud => {
    cloud.visible = true;
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
  focusedModelDescription.value = null; // 清除聚焦模型描述
  showRestoreButton.value = false;
};

// 添加缓动函数
function easeInOutCubic(t) {
  return t < 0.5 
    ? 4 * t * t * t 
    : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

// 创建区域标记球体
const createAreaMarkers = () => {
  console.log('创建区域标记球体...');
  
  // 使用全局定义的区域信息
  areaDefinitions.value.forEach(area => {
    // 查找匹配的区域数据
    const matchedAreaData = props.areas.find(a => a.name === area.name);
    
    // 创建球体几何体
    const geometry = new THREE.SphereGeometry(area.radius, 32, 32);
    
    // 改用BasicMaterial解决黑色问题，不依赖光照
    const material = new THREE.MeshBasicMaterial({
      color: 0xFF5733, // 红色基调
      transparent: true,
      opacity: 0,  // 不可见
      side: THREE.DoubleSide,
      depthWrite: false, // 禁用深度写入
      depthTest: true,   // 保持深度测试
      blending: THREE.AdditiveBlending, // 改用叠加混合模式
    });
    
    // 创建球体
    const sphere = new THREE.Mesh(geometry, material);
    
    // 设置球体位置
    sphere.position.set(area.position.x, area.position.y, area.position.z);
    
    // 创建光晕效果
    const glowGeometry = new THREE.SphereGeometry(area.radius * 1.1, 32, 32);
    const glowMaterial = new THREE.MeshBasicMaterial({
      color: 0xFF5733,
      transparent: true,
      opacity: 0.7,
      side: THREE.BackSide,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    });
    const glowMesh = new THREE.Mesh(glowGeometry, glowMaterial);
    sphere.add(glowMesh);
    
    // 查找与description匹配的模型部分 - 改进匹配逻辑
    const relatedModelParts = [];
    const areaKeywords = area.description.toLowerCase().split(/\s+/); // 分解为关键词
    
    scene.traverse((object) => {
      if (object instanceof THREE.Mesh && object.name) {
        const objName = object.name.toLowerCase();
        
        // 增强匹配逻辑：
        // 1. 完全匹配
        const exactMatch = objName === area.description.toLowerCase();
        
        // 2. 包含关系
        const containsMatch = objName.includes(area.description.toLowerCase()) || 
                              area.description.toLowerCase().includes(objName);
        
        // 3. 关键词匹配 (如果区域描述包含模型名称中的关键词)
        const keywordMatch = areaKeywords.some(keyword => 
          keyword.length > 2 && objName.includes(keyword));
          
        if (exactMatch || containsMatch || keywordMatch) {
          relatedModelParts.push(object.uuid);
          console.log(`区域 "${area.description}" 匹配到模型部分: "${object.name}"`);
        }
      }
    });
    
    console.log(`区域 ${area.name} (${area.description}) 匹配到 ${relatedModelParts.length} 个模型部分`);
    
    // 保存区域信息到球体对象
    sphere.userData = {
      isAreaMarker: true,
      areaId: area.id,
      areaName: area.name,
      areaDescription: area.description,
      matchedAreaData: matchedAreaData || null,
      pulsePhase: Math.random() * Math.PI * 2,
      isHovered: false,
      relatedModelPartIds: relatedModelParts // 存储关联模型ID
    };
    
    // 为调试目的，设置名称
    sphere.name = `区域标记：${area.name}`;
    
    // 将球体添加到场景
    scene.add(sphere);
    
    // 记录到模型结构中
    const itemId = sphere.uuid;
    modelObjectsMap.value.set(itemId, sphere);
    
    // 添加到结构树中
    modelStructure.value.push({
      name: area.name,
      type: 'AreaMarker',
      depth: 0,
      id: itemId,
      isMesh: true,
      visible: true,
      isAreaMarker: true
    });
  });
  
  console.log(`创建了 ${areaDefinitions.value.length} 个区域标记球体`);
};
// 监听区域数据变化，更新热力图
watch(() => props.areas, (newAreas) => {
  console.log('areas数据更新:', newAreas);
  
  // 确保场景已初始化
  if (!scene) {
    console.warn('场景未初始化，无法更新热力图');
    return;
  }
  
  // 更新区域标记数据
  nextTick(() => {
    updateAreaMarkersData(newAreas);
    
    // 重新生成热力点并更新热力图
    updateHeatmapWithNewData();
  });
}, { deep: true, immediate: false });

// 热力图更新函数
const updateHeatmapWithNewData = () => {
  try {
    console.log('更新热力图数据...');
    
    // 移除现有的热力点云
    pointCloudObjects.forEach(cloud => {
      if (cloud && cloud.parent) {
        cloud.parent.remove(cloud);
      }
      if (cloud && cloud.geometry) cloud.geometry.dispose();
      if (cloud && cloud.material) {
        if (Array.isArray(cloud.material)) {
          cloud.material.forEach(m => m.dispose());
        } else {
          cloud.material.dispose();
        }
      }
    });
    pointCloudObjects.length = 0;
    
    // 重新生成热力点
    heatmapPoints.value = generateHeatmapPoints();
    
    // 重新创建热力点云
    createHeatmapPointCloud();
  } catch (error) {
    console.error('更新热力图失败:', error);
  }
}

// 添加更新区域标记数据的函数
const updateAreaMarkersData = (areasData) => {
  if (!areasData || !areasData.length) return;
  
  console.log('更新区域标记数据...');
  
  // 遍历所有模型对象，找到区域标记
  modelObjectsMap.value.forEach((object, id) => {
    // 只处理区域标记
    if (object.userData?.isAreaMarker) {
      const areaName = object.userData.areaName;
      // 使用宽松匹配查找相应区域数据
      const matchedAreaData = areasData.find(a => 
        a.name === areaName || 
        a.name?.includes(areaName) || 
        areaName?.includes(a.name)
      );
      
      if (matchedAreaData) {
        console.log(`更新区域[${areaName}]数据:`, matchedAreaData);
        // 更新标记中存储的区域数据，包括温湿度
        object.userData.matchedAreaData = matchedAreaData;
      }
    }
  });
}
</script>

<template>
  <div class="three-heatmap-container">
    <div class="map-background"></div>
    <div ref="heatmapRef" class="three-canvas"></div>
    
    <div v-if="loadingError" class="error-message">
      {{ loadingError }}
    </div>
        
    <div class="tech-decoration top-right"></div>
    <div class="tech-decoration bottom-left"></div>
    
    <button @click="toggleAutoRotate" class="auto-rotate-btn">
      {{ autoRotateEnabled ? '停止环视' : '自动环视' }}
    </button>
    <button @click="toggleVertexDisplay" class="vertex-display-btn">
      {{ vertexDisplayMode ? '隐藏顶点' : '显示顶点' }}
    </button>
    
    <!-- 顶点信息面板 -->
    <div 
      v-if="vertexLabelVisible" 
      class="vertex-label"
      :style="{
        left: `${vertexLabelPosition.x}px`,
        top: `${vertexLabelPosition.y}px`
      }"
      :key="`vertex-${selectedVertex.index}-${Date.now()}`"
    >
      <div class="vertex-label-title">顶点信息</div>
      <div class="vertex-info">
        <span class="vertex-info-label">索引:</span> {{ selectedVertex.index }}
      </div>
      <div class="vertex-info">
        <span class="vertex-info-label">位置:</span> 
        ({{ selectedVertex.position.x }}, {{ selectedVertex.position.y }}, {{ selectedVertex.position.z }})
      </div>
      <div class="vertex-info">
        <span class="vertex-info-label">法线:</span> 
        ({{ selectedVertex.normal.x }}, {{ selectedVertex.normal.y }}, {{ selectedVertex.normal.z }})
      </div>
    </div>
    
    <!-- 顶点模式指示器 -->
    <div v-if="vertexDisplayMode" class="vertex-mode-indicator">
      顶点显示模式 - 点击顶点查看详细信息
    </div>
    
    <!-- 坐标显示面板 -->
    <div v-if="showCoordinates" class="coordinates-panel">
      <div class="coordinates-title">点击位置坐标</div>
      <div class="coordinates-value">X: {{ selectedPosition.x }}</div>
      <div class="coordinates-value">Y: {{ selectedPosition.y }}</div>
      <div class="coordinates-value">Z: {{ selectedPosition.z }}</div>
      <button class="close-btn" @click="showCoordinates = false">关闭</button>
    </div>
    
    <!-- 修改悬停标签 -->
    <div 
      v-if="meshLabelVisible" 
      class="mesh-label"
      :style="{
        left: `${meshLabelPosition.x}px`,
        top: `${meshLabelPosition.y}px`
      }"
      v-html="meshLabelContent"
    >
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
  opacity: 0.8;
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
  left: 500px;
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
  bottom: 70px;
  left: 50%;
  transform: translateX(-50%);
  
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

/* 区域标签样式 */
.area-label {
  text-align: center;
}

.area-name {
  font-weight: bold;
  color: #4ade80; /* 绿色标识区域 */
  margin-bottom: 3px;
}

.area-desc {
  font-size: 10px;
  color: #d1fae5;
  opacity: 0.9;
}

.area-people {
  margin-top: 4px;
  font-weight: 500;
  color: #fbbf24; /* 琥珀色显示人数信息 */
  font-size: 12px;
}

/* 修改悬停标签样式，确保可以容纳更多内容 */
.mesh-label {
  position: fixed;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(56, 189, 248, 0.8);
  color: #38bdf8;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  pointer-events: none;
  z-index: 1000;
  box-shadow: 0 0 8px rgba(56, 189, 248, 0.5);
  transform: translate(-50%, -100%);
  white-space: nowrap;
  max-width: 200px;
  line-height: 1.5;
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
  top: 50px;
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

/* 顶点显示按钮样式 */
.vertex-display-btn {
  position: absolute;
  bottom: 70px;
  left: 1100px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(56, 189, 248, 0.5);
  color: #38bdf8;
  padding: 8px 12px;
  border-radius: 4px;
  cursor: pointer;
  z-index: 10;
  transition: all 0.3s;
}

.vertex-display-btn:hover {
  background: rgba(15, 23, 42, 0.9);
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
}

/* 顶点标签样式 */
.vertex-label {
  position: fixed;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(244, 201, 63, 0.8);
  color: #f4c93f;
  padding: 10px 14px;
  border-radius: 4px;
  font-size: 12px;
  pointer-events: none;
  z-index: 1000;
  box-shadow: 0 0 8px rgba(244, 201, 63, 0.5);
  transform: translate(10px, 10px);
  max-width: 300px;
  line-height: 1.5;
}

.vertex-label-title {
  font-weight: bold;
  margin-bottom: 5px;
  border-bottom: 1px solid rgba(244, 201, 63, 0.3);
  padding-bottom: 3px;
}

.vertex-info {
  margin: 3px 0;
  font-family: monospace;
}

.vertex-info-label {
  color: #94a3b8;
  width: 50px;
  display: inline-block;
}

/* 顶点模式指示器 */
.vertex-mode-indicator {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(244, 201, 63, 0.2);
  border: 1px solid rgba(244, 201, 63, 0.5);
  color: #f4c93f;
  padding: 6px 12px;
  border-radius: 4px;
  z-index: 100;
  font-size: 0.8rem;
}
.area-climate {
  margin-top: 4px;
  color: #60a5fa; /* 蓝色显示温湿度信息 */
  font-size: 12px;
  font-weight: 500;
}
</style>
