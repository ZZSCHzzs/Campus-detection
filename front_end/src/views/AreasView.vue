<script lang="ts" setup>
import {ref, onMounted, onBeforeUnmount, computed, watch, nextTick} from 'vue'
import {ElMessage} from 'element-plus'
import {Search, HomeFilled, OfficeBuilding, Grid, List} from '@element-plus/icons-vue'
import type {AreaItem, Building} from '../types'
import {buildingService} from '../services'
import {buildingCustomMethods} from '../services/ResourceServiceDefinitions'
import AreaCard from '../components/data/AreaCard.vue'

// 建筑和区域数据
const buildings = ref<Building[]>([])
const buildingAreas = ref<Map<number, {
  areas: AreaItem[];
  loaded: boolean;
  loading: boolean;
  hasMore: boolean;
  page: number;
}>>(new Map())

const loading = ref(false)
const expectStatus = ref<string | "all">("all")
const buildingFilter = ref<number | "all">("all")
const searchKeyword = ref("")

const isFirstLoad = ref(true)
const isComponentMounted = ref(true)
let fetchInterval: number | null = null

// 懒加载相关
const loadedBuildingIds = ref<Set<number>>(new Set())
const INITIAL_LOAD_COUNT = 3 // 初始加载前3个建筑
const PAGE_SIZE = 20 // 每页区域数量

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

// 获取建筑的区域数据
const getBuildingAreas = (buildingId: number): AreaItem[] => {
  return buildingAreas.value.get(buildingId)?.areas || []
}

// 检查建筑是否已加载
const isBuildingLoaded = (buildingId: number): boolean => {
  return buildingAreas.value.get(buildingId)?.loaded || false
}

// 检查建筑是否正在加载
const isBuildingLoading = (buildingId: number): boolean => {
  return buildingAreas.value.get(buildingId)?.loading || false
}

// 初始化建筑基本信息
const fetchBuildingsBasic = async () => {
  if (!isComponentMounted.value) return
  
  loading.value = true
  try {
    const buildingsData = await buildingCustomMethods.getBuildingsBasic()
    if (!isComponentMounted.value) return
    
    buildings.value = buildingsData
    
    // 初始化建筑区域数据结构
    buildingsData.forEach(building => {
      buildingAreas.value.set(building.id, {
        areas: [],
        loaded: false,
        loading: false,
        hasMore: true,
        page: 1
      })
    })
    
    // 自动加载前几个建筑的区域
    await loadInitialBuildings()
    
  } catch (error) {
    if (isComponentMounted.value) {
      console.error('建筑数据加载失败:', error)
      ElMessage.error('数据加载失败')
    }
  } finally {
    if (isComponentMounted.value) {
      loading.value = false
    }
  }
}

// 加载初始建筑区域
const loadInitialBuildings = async () => {
  const initialBuildings = buildings.value.slice(0, INITIAL_LOAD_COUNT)
  await Promise.all(
    initialBuildings.map(building => loadBuildingAreas(building.id))
  )
}

// 加载指定建筑的区域
const loadBuildingAreas = async (buildingId: number, loadMore = false) => {
  if (!isComponentMounted.value) return
  
  const buildingData = buildingAreas.value.get(buildingId)
  if (!buildingData) return
  
  // 防止重复加载
  if (buildingData.loading || (buildingData.loaded && !loadMore)) return
  
  buildingData.loading = true
  buildingAreas.value.set(buildingId, buildingData)
  
  try {
    const page = loadMore ? buildingData.page + 1 : 1
    const response = await buildingCustomMethods.getBuildingAreasPaginated(
      buildingId, 
      page, 
      PAGE_SIZE
    )
    
    if (!isComponentMounted.value) return
    
    const updatedData = {
      areas: loadMore ? [...buildingData.areas, ...response.areas] : response.areas,
      loaded: true,
      loading: false,
      hasMore: response.has_next,
      page: page
    }
    
    buildingAreas.value.set(buildingId, updatedData)
    loadedBuildingIds.value.add(buildingId)
    
  } catch (error) {
    console.error(`加载建筑 ${buildingId} 的区域失败:`, error)
    buildingData.loading = false
    buildingAreas.value.set(buildingId, buildingData)
  }
}

// 懒加载处理
const handleBuildingVisible = async (buildingId: number) => {
  if (!loadedBuildingIds.value.has(buildingId)) {
    await loadBuildingAreas(buildingId)
  }
}

// 加载更多区域
const loadMoreAreas = async (buildingId: number) => {
  await loadBuildingAreas(buildingId, true)
}

const cardVisibilities = ref<Record<number, boolean>>({})

const handleCardVisibility = (areaId: number, visible: boolean) => {
  cardVisibilities.value[areaId] = visible
}

const isFloorVisible = (buildingId: number, floor: number) => {
  const areas = getBuildingAreas(buildingId)
  const areasInFloor = areas.filter(a => a.floor === floor)
  
  return areasInFloor.some(area =>
      cardVisibilities.value[area.id]
  )
}

const isBuildingVisible = computed(() => (buildingId: number) => {
  const building = filteredBuildings.value.find(b => b.id === buildingId)
  if (!building) return false
  
  const areas = getBuildingAreas(buildingId)
  return getFloors(areas).some(floor =>
      isFloorVisible(buildingId, floor)
  )
})

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
  
  const loadedIds = Array.from(loadedBuildingIds.value)
  await Promise.all(
    loadedIds.map(id => {
      // 重置页码，重新加载第一页
      const buildingData = buildingAreas.value.get(id)
      if (buildingData) {
        buildingData.page = 1
        buildingData.loaded = false
        buildingAreas.value.set(id, buildingData)
      }
      return loadBuildingAreas(id)
    })
  )
}

onMounted(() => {
  isComponentMounted.value = true
  fetchBuildingsBasic()
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)
  
  // 设置定期刷新数据的间隔
  fetchInterval = window.setInterval(() => {
    refreshLoadedBuildings()
  }, 30000) // 每30秒刷新一次
  
  isFirstLoad.value = false
})

onBeforeUnmount(() => {
  isComponentMounted.value = false
  window.removeEventListener('resize', checkScreenSize)
  
  if (fetchInterval !== null) {
    clearInterval(fetchInterval)
    fetchInterval = null
  }
})
</script>

<template>
  <div class="areas-container">
    <!-- 顶部标题卡片 -->
    <div class="page-header-card">
      <div class="header-content">
        <h1 class="main-title">校园区域监测</h1>
        <p class="subtitle">实时查看各区域人流情况</p>
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
              class="building-section"
              v-intersection="() => handleBuildingVisible(building.id)"
            >
              <div class="building-header">
                <div class="header-icon-wrapper">
                  <el-icon>
                    <OfficeBuilding/>
                  </el-icon>
                </div>
                <h2 class="building-title">{{ building.name }}</h2>
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

              <div v-else-if="!isBuildingVisible(building.id)" class="empty-state">
                <el-empty description="该建筑暂无可见区域"/>
              </div>

              <div v-else>
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