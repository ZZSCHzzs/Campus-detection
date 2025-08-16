<script lang="ts" setup>
import {ref, onMounted, onBeforeUnmount, computed, watch, nextTick} from 'vue'
import {ElMessage} from 'element-plus'
import {Search, HomeFilled, OfficeBuilding, Grid, List, Loading} from '@element-plus/icons-vue'
import type {AreaItem, Building} from '../types'
import {buildingService} from '../services'
import {buildingCustomMethods} from '../services/ResourceServiceDefinitions'
import AreaCard from '../components/data/AreaCard.vue'

// 新增：建筑类型显示映射
const categoryLabelMap: Record<string, string> = {
  library: '图书馆/阅览室',
  study: '自习室/学习空间',
  teaching: '教学楼/教室',
  cafeteria: '食堂/餐饮',
  dorm: '宿舍',
  lab: '实验室/科研',
  office: '行政/办公',
  sports: '体育场馆',
  service: '服务/办事大厅',
  other: '其他'
}

// 建筑数据管理类
class BuildingDataManager {
  private buildingAreas = new Map<number, {
    areas: AreaItem[];
    loaded: boolean;
    loading: boolean;
    hasMore: boolean;
    page: number;
  }>()
  
  private loadedBuildingIds = new Set<number>()
  
  // 初始化建筑数据
  initBuilding(buildingId: number) {
    this.buildingAreas.set(buildingId, {
      areas: [],
      loaded: false,
      loading: false,
      hasMore: true,
      page: 1
    })
  }
  
  // 获取建筑数据
  getBuildingData(buildingId: number) {
    return this.buildingAreas.get(buildingId)
  }
  
  // 更新建筑数据
  updateBuildingData(buildingId: number, data: Partial<{
    areas: AreaItem[];
    loaded: boolean;
    loading: boolean;
    hasMore: boolean;
    page: number;
  }>) {
    const existing = this.getBuildingData(buildingId)
    if (existing) {
      this.buildingAreas.set(buildingId, { ...existing, ...data })
    }
  }
  
  // 检查建筑状态
  isLoaded(buildingId: number): boolean {
    return this.getBuildingData(buildingId)?.loaded || false
  }
  
  isLoading(buildingId: number): boolean {
    return this.getBuildingData(buildingId)?.loading || false
  }
  
  getAreas(buildingId: number): AreaItem[] {
    return this.getBuildingData(buildingId)?.areas || []
  }
  
  markAsLoaded(buildingId: number) {
    this.loadedBuildingIds.add(buildingId)
  }
  
  isMarkedAsLoaded(buildingId: number): boolean {
    return this.loadedBuildingIds.has(buildingId)
  }
  
  getAllData() {
    return this.buildingAreas
  }
  
  getLoadedIds() {
    return Array.from(this.loadedBuildingIds)
  }
}

// 可见性管理类
class VisibilityManager {
  private cardVisibilities = ref<Record<number, boolean>>({})
  
  // 设置区域可见性
  setAreaVisibility(areaId: number, visible: boolean) {
    this.cardVisibilities.value[areaId] = visible
  }
  
  // 获取区域可见性
  getAreaVisibility(areaId: number): boolean {
    return this.cardVisibilities.value[areaId] !== false
  }
  
  // 检查是否有可见性设置
  hasVisibilitySettings(areaIds: number[]): boolean {
    return areaIds.some(id => this.cardVisibilities.value.hasOwnProperty(id))
  }
  
  // 初始化区域可见性
  initAreasVisibility(areas: AreaItem[]) {
    areas.forEach(area => {
      if (!this.cardVisibilities.value.hasOwnProperty(area.id)) {
        this.cardVisibilities.value[area.id] = true
      }
    })
  }
  
  // 检查楼层是否可见
  isFloorVisible(areas: AreaItem[], floor: number): boolean {
    const areasInFloor = areas.filter(a => a.floor === floor)
    
    if (!this.hasVisibilitySettings(areasInFloor.map(a => a.id))) {
      return areasInFloor.length > 0
    }
    
    return areasInFloor.some(area => this.getAreaVisibility(area.id))
  }
  
  // 检查建筑是否可见
  isBuildingVisible(areas: AreaItem[]): boolean {
    if (!areas || areas.length === 0) return false
    
    if (!this.hasVisibilitySettings(areas.map(a => a.id))) {
      return true
    }
    
    const floors = [...new Set(areas.map(a => a.floor))]
    return floors.some(floor => this.isFloorVisible(areas, floor))
  }
  
  getCardVisibilities() {
    return this.cardVisibilities
  }
}

// 数据加载管理类
class DataLoadManager {
  private isComponentMounted = ref(true)
  
  constructor(
    private buildingManager: BuildingDataManager,
    private visibilityManager: VisibilityManager
  ) {}
  
  // 通用加载方法
  async loadWithErrorHandling<T>(
    loadFn: () => Promise<T>,
    errorMessage: string,
    onSuccess?: (data: T) => void
  ): Promise<T | null> {
    if (!this.isComponentMounted.value) return null
    
    try {
      const result = await loadFn()
      if (this.isComponentMounted.value && onSuccess) {
        onSuccess(result)
      }
      return result
    } catch (error) {
      if (this.isComponentMounted.value) {
        console.error(errorMessage, error)
        ElMessage.error('数据加载失败')
      }
      return null
    }
  }
  
  // 加载建筑区域
  async loadBuildingAreas(buildingId: number, loadMore = false) {
    const buildingData = this.buildingManager.getBuildingData(buildingId)
    if (!buildingData) return
    
    // 防止重复加载
    if (buildingData.loading || (buildingData.loaded && !loadMore)) return
    
    this.buildingManager.updateBuildingData(buildingId, { loading: true })
    
    const page = loadMore ? buildingData.page + 1 : 1
    
    const response = await this.loadWithErrorHandling(
      () => buildingCustomMethods.getBuildingAreasPaginated(buildingId, page, PAGE_SIZE),
      `加载建筑 ${buildingId} 的区域失败`,
      (data) => {
        const updatedData = {
          areas: loadMore ? [...buildingData.areas, ...data.areas] : data.areas,
          loaded: true,
          loading: false,
          hasMore: data.has_next,
          page: page
        }
        
        this.buildingManager.updateBuildingData(buildingId, updatedData)
        this.buildingManager.markAsLoaded(buildingId)
        this.visibilityManager.initAreasVisibility(data.areas)
      }
    )
    
    if (!response) {
      this.buildingManager.updateBuildingData(buildingId, { loading: false })
    }
  }
  
  setMountedStatus(mounted: boolean) {
    this.isComponentMounted.value = mounted
  }
}

// 实例化管理器
const buildingManager = new BuildingDataManager()
const visibilityManager = new VisibilityManager()
const loadManager = new DataLoadManager(buildingManager, visibilityManager)

// 原有的响应式数据
const buildings = ref<Building[]>([])
const loading = ref(false)
const expectStatus = ref<string | "all">("all")
const buildingFilter = ref<number | "all">("all")
const searchKeyword = ref("")

const isFirstLoad = ref(true)
const isComponentMounted = ref(true)
let fetchInterval: number | null = null

// 懒加载相关
const INITIAL_LOAD_COUNT = 4 // 初始加载前4个建筑
const PAGE_SIZE = 20 // 每页区域数量

// 使用管理器的计算属性
const buildingAreas = computed(() => buildingManager.getAllData())
const cardVisibilities = computed(() => visibilityManager.getCardVisibilities().value)
const loadedBuildingIds = computed(() => new Set(buildingManager.getLoadedIds()))

watch(searchKeyword, (newVal) => {
  if (newVal) {
    buildingFilter.value = "all"
    expectStatus.value = "all"
  }
})

// 获取已加载的区域（用于搜索）
const loadedAreas = computed(() => {
  const areas: AreaItem[] = []
  buildingAreas.value.forEach((buildingData) => {
    areas.push(...buildingData.areas)
  })
  return areas
})

const filteredAreas = computed(() => {
  return loadedAreas.value.filter(a => a.name.includes(searchKeyword.value))
})

const filteredBuildings = computed(() => {
  if (buildingFilter.value === "all") return buildings.value
  return buildings.value.filter(b => b.id === buildingFilter.value)
})

const getFloors = (areas: AreaItem[] | undefined) => {
  return [...new Set(areas?.map(a => a.floor))].sort()
}

const getAreasByFloor = (areas: AreaItem[] | undefined, floor: number) => {
  return areas?.filter(a => a.floor === floor)
}

// 简化的辅助函数
const getBuildingAreas = (buildingId: number) => buildingManager.getAreas(buildingId)
const isBuildingLoaded = (buildingId: number) => buildingManager.isLoaded(buildingId)
const isBuildingLoading = (buildingId: number) => buildingManager.isLoading(buildingId)

// 初始化建筑基本信息
const fetchBuildingsBasic = async () => {
  loading.value = true
  
  const buildingsData = await loadManager.loadWithErrorHandling(
    () => buildingCustomMethods.getBuildingsBasic(),
    '建筑数据加载失败',
    (data) => {
      buildings.value = data
      data.forEach(building => buildingManager.initBuilding(building.id))
    }
  )
  
  if (buildingsData) {
    await loadInitialBuildings()
  }
  
  loading.value = false
}

// 加载初始建筑区域
const loadInitialBuildings = async () => {
  const initialBuildings = buildings.value.slice(0, INITIAL_LOAD_COUNT)
  await Promise.all(
    initialBuildings.map(building => loadManager.loadBuildingAreas(building.id))
  )
}

// 简化的可见性函数
const handleCardVisibility = (areaId: number, visible: boolean) => {
  visibilityManager.setAreaVisibility(areaId, visible)
}

const isFloorVisible = (buildingId: number, floor: number) => {
  const areas = getBuildingAreas(buildingId)
  return visibilityManager.isFloorVisible(areas, floor)
}

const isBuildingVisible = computed(() => (buildingId: number) => {
  const building = filteredBuildings.value.find(b => b.id === buildingId)
  if (!building) return false
  
  const areas = getBuildingAreas(buildingId)
  return visibilityManager.isBuildingVisible(areas)
})

// 简化的加载函数
const loadBuildingAreas = (buildingId: number, loadMore = false) => {
  return loadManager.loadBuildingAreas(buildingId, loadMore)
}

const handleBuildingVisible = async (buildingId: number) => {
  if (!buildingManager.isMarkedAsLoaded(buildingId)) {
    await loadBuildingAreas(buildingId)
  }
}

const loadMoreAreas = async (buildingId: number) => {
  await loadBuildingAreas(buildingId, true)
}

const isMobile = ref(false)

const checkScreenSize = () => {
  isMobile.value = window.innerWidth < 992
  
  if (isFirstLoad.value) {
    isCompactView.value = isMobile.value
  }
}

const isCompactView = ref(false)

const toggleLayoutMode = () => {
  isCompactView.value = !isCompactView.value
}

// 定期刷新已加载的建筑数据
const refreshLoadedBuildings = async () => {
  if (!isComponentMounted.value) return
  
  const loadedIds = buildingManager.getLoadedIds()
  await Promise.all(
    loadedIds.map(id => {
      // 重置页码，重新加载第一页
      buildingManager.updateBuildingData(id, {
        page: 1,
        loaded: false
      })
      return loadBuildingAreas(id)
    })
  )
}

// 添加 Intersection Observer 相关代码
const observer = ref<IntersectionObserver | null>(null)
const buildingRefs = ref<Map<number, HTMLElement>>(new Map())

// 设置建筑元素引用
const setBuildingRef = (el: HTMLElement | null, buildingId: number) => {
  if (el) {
    buildingRefs.value.set(buildingId, el)
  } else {
    buildingRefs.value.delete(buildingId)
  }
}

// 初始化 Intersection Observer
const initIntersectionObserver = () => {
  if (observer.value) {
    observer.value.disconnect()
  }
  
  observer.value = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const buildingId = parseInt(entry.target.getAttribute('data-building-id') || '0')
          if (buildingId && !buildingManager.isMarkedAsLoaded(buildingId)) {
            handleBuildingVisible(buildingId)
          }
        }
      })
    },
    {
      root: null,
      rootMargin: '100px',
      threshold: 0.1
    }
  )
}

// 观察建筑元素
const observeBuildings = () => {
  if (!observer.value) return
  
  buildingRefs.value.forEach((el, buildingId) => {
    if (!buildingManager.isMarkedAsLoaded(buildingId)) {
      observer.value!.observe(el)
    }
  })
}

onMounted(() => {
  isComponentMounted.value = true
  loadManager.setMountedStatus(true)
  
  // 初始化 Intersection Observer
  initIntersectionObserver()
  
  fetchBuildingsBasic()
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)
  
  // 设置定期刷新数据的间隔
  fetchInterval = window.setInterval(() => {
    refreshLoadedBuildings()
  }, 30000) // 每30秒刷新一次
  
  isFirstLoad.value = false
  
  // 在下一个 tick 观察建筑元素
  nextTick(() => {
    observeBuildings()
  })
})

onBeforeUnmount(() => {
  isComponentMounted.value = false
  loadManager.setMountedStatus(false)
  window.removeEventListener('resize', checkScreenSize)
  
  // 清理 Intersection Observer
  if (observer.value) {
    observer.value.disconnect()
    observer.value = null
  }
  
  if (fetchInterval !== null) {
    clearInterval(fetchInterval)
    fetchInterval = null
  }
})

// 监听建筑数据变化，重新观察元素
watch(buildings, () => {
  nextTick(() => {
    observeBuildings()
  })
}, { deep: true })
</script>

<template>
  <div class="areas-container">
    <!-- 顶部标题卡片 -->
    <div class="page-header-card">
      <div class="header-content">
        <h1 class="main-title">区域监测</h1>
        <p class="subtitle">实时查看各区域人员数量与环境数据</p>
        <div class="header-decoration"></div>
      </div>
    </div>

    <!-- 搜索栏卡片 -->
    <div class="search-bar-container">
      <div class="search-bar">
        <el-row :gutter="15">
          <el-col :lg="5" :xl="5" :md="12" :sm="12" :xs="12" class="search-item">
            <el-select
                v-model="buildingFilter"
                class="custom-select"
                placeholder="选择建筑"
                size="large"
            >
              <el-option label="全部" value="all"/>
              <el-option
                  v-for="building in buildings"
                  :key="building.id"
                  :label="building.name"
                  :value="building.id"
              />
            </el-select>
          </el-col>

          <el-col :lg="5" :xl="5" :md="12" :sm="12" :xs="12" class="search-item">
            <el-select
                v-model="expectStatus"
                class="custom-select"
                placeholder="状态筛选"
                size="large"
            >
              <el-option label="全部" value="all"/>
              <el-option label="在线" value="online"/>
              <el-option label="离线" value="offline"/>
            </el-select>
          </el-col>

          <el-col :lg="10" :xl="10" :md="16" :sm="16" :xs="16" class="search-item">
            <el-input
                v-model="searchKeyword"
                class="custom-input"
                clearable
                placeholder="搜索区域名称..."
                size="large"
            >
              <template #prefix>
                <el-icon class="search-icon">
                  <Search/>
                </el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :lg="4" :xl="4" :md="8" :sm="8" :xs="8" class="search-item">
            <el-button
                class="toggle-button"
                plain
                size="large"
                type="primary"
                @click="toggleLayoutMode"
            >
              <el-icon class="toggle-icon">
                <component :is="isCompactView ? Grid : List"/>
              </el-icon>
              {{ isCompactView ? '卡片视图' : '紧凑视图' }}
            </el-button>
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- 内容区域 -->
    <div v-loading="loading" class="content-area">
      <el-skeleton :loading="loading" animated>
        <template #default>
          <div v-if="searchKeyword" class="search-results">
            <div class="search-header">
              <el-icon>
                <Search/>
              </el-icon>
              <span>搜索结果: "{{ searchKeyword }}"</span>
            </div>
            <el-row :gutter="20" class="card-row">
              <el-col
                  v-for="area in filteredAreas"
                  :key="area.id"
                  :lg="6"
                  :md="isCompactView ? 6 : 8"
                  :sm="isCompactView ? 8 : 12"
                  :xs="isCompactView ? 12 : 24"
                  class="card-animation"
              >
                <AreaCard
                    :area="area"
                    :compact="isCompactView"
                    :expectStatus="expectStatus"
                    @visible-change="(v) => handleCardVisibility(area.id, v)"
                />
              </el-col>
            </el-row>
          </div>
          <div v-else>
            <div 
              v-for="building in filteredBuildings" 
              :key="building.id" 
              :ref="(el) => setBuildingRef(el as HTMLElement, building.id)"
              :data-building-id="building.id"
              class="building-section"
            >
              <div class="building-header">
                <div class="header-icon-wrapper">
                  <el-icon>
                    <OfficeBuilding/>
                  </el-icon>
                </div>
                <h2 class="building-title">{{ building.name }}</h2>
                <!-- 新增：显示建筑类型 -->
                <el-tag v-if="(building as any).category" size="small" effect="plain">
                  {{ categoryLabelMap[(building as any).category] || '其他' }}
                </el-tag>
                <div v-if="isBuildingLoading(building.id)" class="loading-indicator">
                  <el-icon class="is-loading">
                    <Loading/>
                  </el-icon>
                  <span>加载中...</span>
                </div>
              </div>

              <div v-if="!isBuildingLoaded(building.id) && !isBuildingLoading(building.id)" class="lazy-load-placeholder">
                <el-button 
                  type="primary" 
                  plain 
                  @click="handleBuildingVisible(building.id)"
                >
                  点击加载区域数据
                </el-button>
              </div>

              <div v-else-if="isBuildingLoaded(building.id) && getBuildingAreas(building.id).length === 0" class="empty-state">
                <el-empty description="该建筑暂无区域数据"/>
              </div>

              <div v-else-if="isBuildingLoaded(building.id)">
                <el-row 
                  v-for="floor in getFloors(getBuildingAreas(building.id))" 
                  v-show="isFloorVisible(building.id, floor)" 
                  :key="floor"
                  :gutter="10"
                >
                  <el-col :span="isMobile ? 24 : 2" class="floor-header">
                    <div class="floor-header">
                      <div class="floor-icon-wrapper">
                        <el-icon>
                          <HomeFilled/>
                        </el-icon>
                      </div>
                      <h3 class="floor-title">{{ floor }}F</h3>
                    </div>
                  </el-col>
                  <el-col :span='isMobile ? 24 : 22'>
                    <el-row :gutter="20" class="card-row">
                      <el-col
                          v-for="area in getAreasByFloor(getBuildingAreas(building.id), floor)"
                          :key="area.id"
                          :class="{ 'floor-card-indent': !isCompactView }"
                          :lg="6"
                          :md="isCompactView ? 6 : 8"
                          :offset="isCompactView ? 0 : 0"
                          :sm="isCompactView ? 8 : 12"
                          :xs="isCompactView ? 12 : 24"
                          class="card-animation"
                          v-show="cardVisibilities[area.id] !== false"
                      >
                          <AreaCard
                              :area="area"
                              :compact="isCompactView"
                              :expectStatus="expectStatus"
                              @visible-change="(v) => handleCardVisibility(area.id, v)"
                          />
                      </el-col>
                    </el-row>
                  </el-col>
                </el-row>
                
                <!-- 加载更多按钮 -->
                <div 
                  v-if="buildingAreas.get(building.id)?.hasMore" 
                  class="load-more-container"
                >
                  <el-button 
                    type="primary" 
                    plain 
                    :loading="isBuildingLoading(building.id)"
                    @click="loadMoreAreas(building.id)"
                  >
                    加载更多区域
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </template>
      </el-skeleton>
    </div>
  </div>
</template>

<style scoped>
.areas-container {
  max-width: 1300px;
  margin: 0 auto;
  padding: 20px;
  min-height: 100vh;
}

/* 顶部标题卡片样式 */
.page-header-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  margin-bottom: 20px;
  padding: 30px;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.page-header-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #3498db, #1abc9c, #9b59b6);
  border-radius: 12px 12px 0 0;
}

.header-content {
  position: relative;
  display: inline-block;
}

.main-title {
  background: linear-gradient(45deg, #3498db, #1a73e8);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 12px;
  letter-spacing: 1px;
  position: relative;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.subtitle {
  color: #64748b;
  font-size: 16px;
  font-weight: 400;
  max-width: 600px;
  margin: 0 auto;
}

.header-decoration {
  width: 60px;
  height: 4px;
  background: linear-gradient(90deg, #3498db, #1abc9c);
  margin: 15px auto 0;
  border-radius: 4px;
}

/* 搜索栏样式 */
.search-bar-container {
  margin-bottom: 20px;
}

.search-bar {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

.custom-select,
.custom-input {
  width: 100%;
  transition: all 0.3s ease;
}

.custom-select:hover,
.custom-input:hover {
  transform: translateY(-2px);
}

.search-icon {
  color: #64748b;
}

.toggle-button {
  width: 100%;
  white-space: nowrap;
}

.toggle-icon {
  margin-right: 6px;
}

/* 内容区域 */
.content-area {
  background: transparent;
}

.building-section {
  margin-bottom: 20px;
  transition: all 0.4s ease;
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  transform: translateY(0);
  animation: fadeIn 0.5s ease-out;
}

.building-section:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.08);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.building-header, .floor-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon-wrapper, .floor-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3498db, #1a73e8);
  color: white;
  box-shadow: 0 4px 8px rgba(26, 115, 232, 0.2);
}

.floor-icon-wrapper {
  background: linear-gradient(135deg, #1abc9c, #16a085);
  box-shadow: 0 4px 8px rgba(26, 188, 156, 0.2);
  width: 30px;
  height: 30px;
}

.building-title {
  margin: 20px 0;
  color: #334155;
  font-weight: 600;
  font-size: 22px;
  position: relative;
  padding-bottom: 10px;
}

.building-title::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 60px;
  height: 3px;
  background: linear-gradient(90deg, #3498db, #1a73e8);
  border-radius: 3px;
}

.floor-title {
  margin: 15px 0;
  color: #475569;
  font-size: 18px;
  padding: 6px 12px;
  border-radius: 6px;
  background: linear-gradient(to right, #e0f2fe, transparent 80%);
  font-weight: 500;
}

.card-row {
  margin-bottom: 25px;
  animation: slideUp 0.4s ease-out;
  display: flex;
  flex-wrap: wrap;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.search-results {
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  animation: fadeIn 0.5s ease;
}

.search-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  font-size: 18px;
  color: #3498db;
  padding-bottom: 10px;
  border-bottom: 1px solid #e2e8f0;
}

.card-animation {
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  transform: translateY(0) scale(1);
  perspective: 1000px;
}

.card-animation:hover {
  transform: translateY(-2px) scale(1.01);
  z-index: 1;
}

.empty-state {
  padding: 30px;
  background: rgba(241, 245, 249, 0.5);
  border-radius: 8px;
  margin: 15px 0;
  transition: all 0.3s ease;
}

.search-item {
  margin: 4px 0;
}

.layout-toggle {
  display: flex;
  justify-content: flex-end;
  margin-left: auto;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .areas-container {
    padding: 15px;
  }

  .page-header-card {
    padding: 20px;
    margin-bottom: 15px;
  }

  .main-title {
    font-size: 24px;
  }

  .subtitle {
    font-size: 14px;
  }

  .building-section {
    padding: 15px;
    margin-bottom: 15px;
  }

  .search-bar {
    padding: 15px;
  }

  .building-title {
    font-size: 20px;
    margin: 10px 0;
  }

  .floor-title {
    font-size: 16px;
    margin: 10px 0;
  }

  .card-animation {
    margin-bottom: 15px;
  }

  .toggle-button {
    width: 100%;
  }
}

@media (max-width: 576px) {
  .card-animation {
    padding-left: 5px;
    padding-right: 5px;
  }

  .el-col {
    padding-left: 5px;
    padding-right: 5px;
  }

  .card-row {
    margin-left: -5px;
    margin-right: -5px;
  }
}

@media (max-width: 480px) {
  .main-title {
    font-size: 20px;
  }

  .subtitle {
    font-size: 13px;
  }

  .building-title {
    font-size: 18px;
  }

  .page-header-card {
    padding: 15px;
    margin-bottom: 10px;
  }

  .search-bar {
    padding: 12px;
  }
}

@media (min-width: 769px) and (max-width: 1024px) {
  .toggle-button {
    width: 100%;
    padding-left: 10px;
    padding-right: 10px;
  }
}
</style>