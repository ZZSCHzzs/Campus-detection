<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, reactive, watch, nextTick } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js';
import type { AreaItem } from '../types';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { FXAAShader } from 'three/examples/jsm/shaders/FXAAShader.js';

let composer;

// 聚焦相关
const focusModeActive = ref(false);
const focusedObjectId = ref<string | null>(null);
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
    position: { x: 1.3, y: 0.95, z: -4.11435 },
    radius: 0.5 // 球体半径
  },
  {
    id: 'area2',
    name: '正心22',
    description: '正心大教室2楼',
    position: { x: 3, y: 1.85, z: -2.7 },
    radius: 0.5 // 球体半径
  },
  {
    id: 'area1',
    name: '正心11',
    description: '正心1楼',
    position: { x: 4.4, y: 0.95, z: -0.7 },
    radius: 0.5 // 球体半径
  },
]);

// 修改虚构热点数据生成函数
const generateHeatmapPoints = () => {
  const points = [];
  
  // 为每个区域创建热点数据
  areaDefinitions.value.forEach(area => {
    // 查找匹配的区域数据获取人数
    const matchedAreaData = props.areas.find(a => a.name === area.name);
    const personCount = matchedAreaData?.detected_count || 0;
    
    // 基础热点 - 区域中心点
    points.push({
      x: area.position.x,
      y: area.position.y,
      z: area.position.z,
      intensity: personCount // 使用实际人数作为强度
    });
    
    // 在区域周围添加几个随机分布点，强度略低
    const randomPoints = 4;
    for (let i = 0; i < randomPoints; i++) {
      // 在区域半径范围内随机生成点
      const angle = Math.random() * Math.PI * 2;
      const distance = Math.random() * area.radius * 0.8;
      const x = area.position.x + Math.cos(angle) * distance;
      const z = area.position.z + Math.sin(angle) * distance * 0.5;
      const y = area.position.y + (Math.random() - 0.5) * 0.3;
      
      // 随机强度，但基于人数
      const intensityFactor = 0.7 + Math.random() * 0.3;
      points.push({
        x, y, z,
        intensity: personCount * intensityFactor
      });
    }
  });
  
  return points;
};

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
  const ambientLight = new THREE.AmbientLight(0x404040, 20);
  scene.add(ambientLight);

  // 2. 添加半球光 - 模拟天空和地面的反射光
  const hemisphereLight = new THREE.HemisphereLight(
    0x87CEEB,  // 天空色 - 淡蓝色
    0x222222,  // 地面色 - 暗灰色
    3        // 强度
  );
  scene.add(hemisphereLight);

  // 3. 添加方向光 - 模拟太阳光
  const directionalLight = new THREE.DirectionalLight(0xFFFFFF, 7);
  directionalLight.position.set(50, 75, 50);  // 光源位置
  directionalLight.castShadow = true;         // 启用阴影
  directionalLight.shadow.mapSize.width = 1024;
  directionalLight.shadow.mapSize.height = 2048;
  directionalLight.shadow.camera.near = 0.5;
  directionalLight.shadow.camera.far = 500;
  directionalLight.shadow.camera.left = -100;
  directionalLight.shadow.camera.right = 100;
  directionalLight.shadow.camera.top = 100;
  directionalLight.shadow.camera.bottom = -100;

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
  cubeTextureLoader.setPath('/textures/skybox/');
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
    texture.repeat.set(5.5, 5.5); // X和Y方向缩放2倍

    // 设置贴图旋转（单位为弧度），如旋转45度
    texture.center.set(0.5, 0.5); // 以中心为旋转点
    texture.rotation = Math.PI/4*5 - Math.PI/180*4; // 旋转45度

    // 设置贴图偏移（如需要移动贴图）
    texture.offset.set(0.02, 0.04);

    // 创建平面几何体，大小可根据实际场景调整
    const planeSize = 200;
    const geometry = new THREE.PlaneGeometry(planeSize, planeSize);
    const material = new THREE.MeshBasicMaterial({
      map: texture,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.6
    });
    const plane = new THREE.Mesh(geometry, material);
    plane.rotation.x = -Math.PI / 2; // 使平面水平
    plane.position.y = 0.01; // 稍微高于0，避免与模型重叠
    scene.add(plane);
  });

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
    

  // // 添加坐标轴辅助工具
  // const axesHelper = new THREE.AxesHelper(5) // 参数是轴线长度
  // scene.add(axesHelper)
  

  // 加载OBJ建筑模型
  loadBuildingModel()
  
  // 添加区域标记平面
  createAreaMarkers()
  
  // 添加热力点云
  createHeatmapPointCloud()
  
  // 添加后期处理
  composer = addPostProcessing();
  
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
            const transparentMaterial = new THREE.MeshStandardMaterial({
              color: 0xB0C4DE,       // 淡蓝色调
              transparent: true,
              opacity: 0.5,          // 略微提高不透明度，让光照更明显
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
  // 新增：仅保留“实际可见”的命中结果
  const visibleIntersects = intersects.filter(i => isActuallyVisible(i.object));
  
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
  // 更新区域标记动画效果
  modelObjectsMap.value.forEach((object) => {
    if (object.userData?.isAreaMarker) {
      const material = object.material;
      const phase = object.userData.pulsePhase || 0;
      
      if (object.userData.isHovered) {
        // 悬停状态 - 明显的闪烁效果
        material.opacity = 0.4 + Math.sin(time * 5 + phase) * 0.2;
        material.color.setRGB(
          0.6 + Math.sin(time * 3) * 0.4, 
          0.8 + Math.sin(time * 4 + 1) * 0.2, 
          1.0
        );
        
        // 更新光晕效果
        if (object.children[0] && object.children[0].material) {
          object.children[0].material.opacity = 0.2 + Math.sin(time * 3 + phase) * 0.1;
          object.children[0].scale.setScalar(1.1 + Math.sin(time * 2) * 0.05);
        }
      } else {
        // 非悬停状态 - 几乎完全透明
        material.opacity = 0.0001;
        material.color.setRGB(0.22, 0.74, 0.97); // 恢复原始颜色
        
        // 更新光晕效果
        if (object.children[0] && object.children[0].material) {
          object.children[0].material.opacity = 0.0001;
          object.children[0].scale.setScalar(1.1);
        }
      }
    }
  });
  
  // 在animate函数中更新点云动画效果
  pointCloudObjects.forEach((cloud, cloudIndex) => {
    if (!cloud.geometry || !cloud.material) return;
    
    const geometry = cloud.geometry;
    const positionAttribute = geometry.getAttribute('position');
    const velocityAttribute = geometry.getAttribute('velocity');
    const randomnessAttribute = geometry.getAttribute('randomness');
    const phaseAttribute = geometry.getAttribute('phase');
    const intensityAttribute = geometry.getAttribute('intensity');
    const originalPositions = geometry.userData.originalPositions;
    
    // 更新材质参数，随时间变化增加云雾效果
    if (cloud.material.type === 'ShaderMaterial') {
      // 脉动效果
      cloud.material.uniforms.pointSize.value = 8.0 + Math.sin(time * 0.3) * 1.0;
      cloud.material.uniforms.softness.value = 0.05 + Math.sin(time * 0.5) * 0.01;
    }
    
    // 更新每个点的位置，使运动更加流畅连续
    for (let i = 0; i < positionAttribute.count; i++) {
      const index = i * 3;
      const phase = phaseAttribute.getX(i);
      const intensity = intensityAttribute ? intensityAttribute.getX(i) : 1.0;
      
      // 获取速度和随机性参数
      const vx = velocityAttribute.getX(i);
      const vy = velocityAttribute.getY(i);
      const vz = velocityAttribute.getZ(i);
      
      const rx = randomnessAttribute.getX(i);
      const ry = randomnessAttribute.getY(i);
      const rz = randomnessAttribute.getZ(i);
      
      // 原始位置
      const originalX = originalPositions[index];
      const originalY = originalPositions[index + 1];
      const originalZ = originalPositions[index + 2];
      
      // 改进运动方程，增加流体感
      const flowFactor = 3 + intensity * 0.9; // 基于强度的流动因子
      
      // 使用柏林噪声或多层正弦波代替简单的正弦波，创造更自然的流体运动
      const noiseX = Math.sin(time * 0.7 + phase) * Math.cos(time * 0.4 + phase * 2) * rx * flowFactor;
      const noiseY = Math.sin(time * 0.9 + phase * 2) * Math.cos(time * 0.5 + phase) * ry * flowFactor;
      const noiseZ = Math.sin(time * 0.5 + phase * 3) * Math.cos(time * 0.6 + phase * 3) * rz * flowFactor;
      
      // 缓慢的漂移运动
      const driftX = vx * Math.sin(time * 0.3 + i * 0.01) * flowFactor;
      const driftY = vy * Math.sin(time * 0.4 + i * 0.005) * flowFactor;
      const driftZ = vz * Math.sin(time * 0.35 + i * 0.015) * flowFactor;
      
      // 更新位置 - 围绕原始位置进行流体运动
      positionAttribute.setXYZ(
        i,
        originalX + noiseX + driftX,
        originalY + noiseY + driftY,
        originalZ + noiseZ + driftZ
      );
    }
    
    // 通知 Three.js 更新位置缓冲区
    positionAttribute.needsUpdate = true;
  });
  // 使用composer替代renderer直接渲染
  if (composer) {
    composer.render();
  } else if (renderer && scene && camera) {
    renderer.render(scene, camera);
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
  // 清理顶点标记
  removeVertexMarkers();
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
const createDensityField = (points, resolution = 48) => { // 降低分辨率提高性能
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
  const maxDistanceSquared = 1.2; // 最大影响距离的平方
  
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
            // 使用距离衰减函数计算影响值 - 基于intensity（人数）
            const influence = 0.4 * point.intensity * Math.exp(-distanceSquared / 1);
            density += influence;
          }
        }
        
        const index = x + y * resolution + z * resolution * resolution;
        grid[index] = density;
      }
    }
  }
  const smoothedGrid = smoothDensityField(grid, resolution);
  console.log('密度场创建完成');
  return { grid, bounds, resolution, cellSize };
}
// 添加密度场平滑函数
const smoothDensityField = (grid, resolution) => {
  const smoothed = new Array(grid.length).fill(0);
  
  // 对每个体素应用高斯平滑
  for (let x = 0; x < resolution; x++) {
    for (let y = 0; y < resolution; y++) {
      for (let z = 0; z < resolution; z++) {
        const index = x + y * resolution + z * resolution * resolution;
        let sum = 0;
        let weight = 0;
        
        // 在3x3x3邻域内进行平滑
        for (let dx = -1; dx <= 1; dx++) {
          for (let dy = -1; dy <= 1; dy++) {
            for (let dz = -1; dz <= 1; dz++) {
              const nx = Math.min(Math.max(x + dx, 0), resolution - 1);
              const ny = Math.min(Math.max(y + dy, 0), resolution - 1);
              const nz = Math.min(Math.max(z + dz, 0), resolution - 1);
              
              const nIndex = nx + ny * resolution + nz * resolution * resolution;
              const dist = Math.sqrt(dx*dx + dy*dy + dz*dz);
              const gaussWeight = Math.exp(-dist * 0.5); // 高斯权重
              
              sum += grid[nIndex] * gaussWeight;
              weight += gaussWeight;
            }
          }
        }
        
        smoothed[index] = sum / weight;
      }
    }
  }
  
  return smoothed;
}
// 创建自定义着色器材质，替换原来的点云材质
const createCloudShaderMaterial = () => {
  return new THREE.ShaderMaterial({
    uniforms: {
      pointSize: { value: 0.008 }, // 更大的点尺寸
      softness: { value: 0.5 }, // 点的柔和度
    },
    vertexShader: `
      attribute vec3 color;
      attribute float intensity;
      varying vec3 vColor;
      varying float vIntensity;
      uniform float pointSize;
      
      void main() {
        vColor = color;
        vIntensity = intensity;
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        // 基于强度和距离调整点大小
        gl_PointSize = pointSize * (300.0 / -mvPosition.z) * (0.3 + vIntensity * 0.7);
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: `
      varying vec3 vColor;
      varying float vIntensity;
      uniform float softness;
      
      void main() {
        // 计算距离中心点的距离
        vec2 center = vec2(0.5, 0.5);
        float dist = distance(gl_PointCoord, center);
        
        // 创建柔和的圆形点
        float strength = 1.0 - smoothstep(0.0, 0.5 - softness, dist);
        
        // 应用渐变的alpha效果
        gl_FragColor = vec4(vColor, strength * vIntensity);
      }
    `,
    transparent: true,
    blending: THREE.NormalBlending,
    opacity: 0.7, // 添加整体不透明度控制
    depthTest: true,
    depthWrite: false
  });
};

// 修改热力点云创建函数
const createHeatmapPointCloud = () => {
  try {
    console.log('开始创建热力点云');
    
    // 根据当前区域数据生成热点
    heatmapPoints.value = generateHeatmapPoints();
    
    // 确保热点数据存在
    if (!heatmapPoints.value || heatmapPoints.value.length === 0) {
      console.warn('热点数据为空');
    }
    
    // 创建密度场
    const densityField = createDensityField(heatmapPoints.value);
    
    // 生成粒子几何体
    const particleGeometry = createParticlesFromDensityField(densityField);
    
    // 创建着色器材质替代简单的点材质
    const particleMaterial = createCloudShaderMaterial();
    
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
// 修改现有的粒子几何体创建函数
const createParticlesFromDensityField = (densityField) => {
  console.log('开始生成粒子...');
  const { grid, bounds, resolution, cellSize } = densityField;
  
  // 找到最大密度值
  const maxDensity = Math.max(...grid, 0.001);
  
  // 增加粒子数量以获得更连续的效果
  const desiredParticleCount = 30000; // 增加粒子数量
  
  // 预分配数组
  const particlePositions = new Float32Array(desiredParticleCount * 3);
  const particleColors = new Float32Array(desiredParticleCount * 3);
  const particleVelocity = new Float32Array(desiredParticleCount * 3);
  const particleRandomness = new Float32Array(desiredParticleCount * 3);
  const particlePhases = new Float32Array(desiredParticleCount);
  const particleIntensities = new Float32Array(desiredParticleCount); // 新增强度属性
  
  let particleIndex = 0;
  
  // 使用更密集的采样
  const attempts = Math.min(desiredParticleCount * 5, 15000000);
  for (let i = 0; i < attempts; i++) {
    // 随机选择一个网格点
    const x = Math.floor(Math.random() * resolution);
    const y = Math.floor(Math.random() * resolution);
    const z = Math.floor(Math.random() * resolution);
    
    const gridIndex = x + y * resolution + z * resolution * resolution;
    const cellDensity = grid[gridIndex];
    
    // 归一化的密度值
    const normalizedDensity = cellDensity / maxDensity;
    
    // 提高低密度区域的粒子生成概率，使云图更连续
    const baseProbability = 0.000000001;  // 增加基础概率
    const densityWeight = 1;
    
    const generationProbability = baseProbability + normalizedDensity * densityWeight;
    
    if (Math.random() < generationProbability) {
      const index = particleIndex * 3;
      
      // 在体素内随机位置
      particlePositions[index] = bounds.min.x + (x + Math.random()) * cellSize.x;
      particlePositions[index + 1] = bounds.min.y + (y + Math.random()) * cellSize.y;
      particlePositions[index + 2] = bounds.min.z + (z + Math.random()) * cellSize.z;
    
      // 设置颜色 - 使用原有密度阈值
      const LOW_DENSITY_THRESHOLD = 25;
      const MID_DENSITY_THRESHOLD = 45;

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
      
      // 设置粒子强度，用于着色器
      particleIntensities[particleIndex] = normalizedDensity * 0.8 + 0.2;
      
      // 其他设置保持不变
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
  particleGeometry.setAttribute('intensity', new THREE.BufferAttribute(
    particleIntensities.slice(0, particleIndex), 1)); // 添加强度属性
  
  // 存储原始位置
  particleGeometry.userData.originalPositions = particlePositions.slice(0, particleIndex * 3);
  
  return particleGeometry;
}
// 添加后期处理效果，使热力云图更加连续平滑
const addPostProcessing = () => {
  // 创建渲染合成器 - 直接使用导入的模块名
  const composer = new EffectComposer(renderer);
  
  // 添加渲染通道
  const renderPass = new RenderPass(scene, camera);
  composer.addPass(renderPass);
  
  // 添加模糊通道使点云更加柔和连续
  const blurPass = new UnrealBloomPass(
    new THREE.Vector2(window.innerWidth, window.innerHeight),
    0.4,  // 强度
    0.9,  // 半径
    0.55   // 阈值
  );
  composer.addPass(blurPass);
  
  // 添加FXAA抗锯齿通道改善边缘
  const fxaaPass = new ShaderPass(FXAAShader);
  fxaaPass.uniforms['resolution'].value.set(
    1 / window.innerWidth, 
    1 / window.innerHeight
  );
  composer.addPass(fxaaPass);
  
  return composer;
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
    
    // 如果是区域标记，获取关联模型部分ID列表
    if (isAreaMarker && focusedObject.userData?.relatedModelPartIds) {
      relatedModelPartIds = focusedObject.userData.relatedModelPartIds;
      console.log(`区域标记关联了${relatedModelPartIds.length}个模型部分`);
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
      color: 0x38bdf8, // 蓝色基调
      transparent: true,
      opacity: 0,  // 几乎不可见但不为0
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
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.0001,
      side: THREE.BackSide,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    });
    const glowMesh = new THREE.Mesh(glowGeometry, glowMaterial);
    sphere.add(glowMesh);
    
    // 查找与description匹配的模型部分
    const relatedModelParts = [];
    scene.traverse((object) => {
      if (object instanceof THREE.Mesh && object.name) {
        // 使用宽松匹配规则，只要模型名称包含区域描述的关键部分或反之即可
        if (object.name.toLowerCase().includes(area.description.toLowerCase()) || 
            area.description.toLowerCase().includes(object.name.toLowerCase())) {
          relatedModelParts.push(object.uuid);
        }
      }
    });
    
    console.log(`区域 ${area.name} (${area.description}) 匹配到 ${relatedModelParts.length} 个模型部分`);
    
    // 保存区域信息到球体对象，增加关联模型部分IDs
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
  
  // 更新区域标记数据
  updateAreaMarkersData(newAreas);
  
  // 重新生成热力点并更新热力图
  updateHeatmapWithNewData();
}, { deep: true });

// 添加热力图更新函数
const updateHeatmapWithNewData = () => {
  // 移除现有的热力点云
  pointCloudObjects.forEach(cloud => {
    scene.remove(cloud);
    if (cloud.geometry) cloud.geometry.dispose();
    if (cloud.material) cloud.material.dispose();
  });
  pointCloudObjects.length = 0;
  
  // 重新生成热力点
  heatmapPoints.value = generateHeatmapPoints();
  
  // 重新创建热力点云
  createHeatmapPointCloud();
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
    
    <!-- <div class="heatmap-title">
      <h2 class="title-text">3D热力分布图</h2>
      <div class="subtitle-text">3D Heat Distribution</div>
    </div> -->
    
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
    <!-- 调试按钮
    <button @click="showDebugInfo = !showDebugInfo" class="debug-toggle">
      {{ showDebugInfo ? '隐藏结构' : '查看模型结构' }}
    </button>
    
    调试面板 -->
    <!-- <div v-if="showDebugInfo" class="debug-panel">
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
        > -->
          <!-- 可见性切换按钮
          <button 
            class="visibility-toggle"
            @click.stop="toggleVisibility(item.id)"
            :title="item.visible ? '隐藏' : '显示'"
          >
            <span v-if="item.visible">👁️</span>
            <span v-else>👁️‍🗨️</span>
          </button>
          
          编辑状态
          <div v-if="item.id === editingItemId" class="edit-name-container" @click.stop>
            <input 
              v-model="newItemName" 
              class="edit-name-input"
              @keydown="handleRenameKeydown"
              @blur="applyRename"
              v-focus
            />
          </div>
           -->
          <!-- 显示状态 -->
          <!-- <template v-else>
            <span class="item-name">{{ item.name || '未命名' }}</span>
            <span class="item-type">{{ item.type }}</span>
          </template>
        </div>
      </div>
    </div> -->
    
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
