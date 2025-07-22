<script lang="ts" setup>
import {ref, onMounted, onBeforeUnmount, computed, watch} from 'vue'
import {ElMessage} from 'element-plus'
import {Search, HomeFilled, OfficeBuilding, Grid, List} from '@element-plus/icons-vue'
import type {AreaItem, Building} from '../types'
import {buildingService} from '../services'
import apiService from '../services'
import AreaCard from '../components/AreaCard.vue'

const buildings = ref<Building[]>([])
const loading = ref(false)
const expectStatus = ref<string | "all">("all")
const buildingFilter = ref<number | "all">("all")
const searchKeyword = ref("")

const isFirstLoad = ref(true)

watch(searchKeyword, (newVal) => {
  if (newVal) {
    buildingFilter.value = "all"
    expectStatus.value = "all"
  }
})

const filteredAreas = computed(() => {
  return buildings.value
      .flatMap(b => b.areas || [])
      .filter(a => a.name.includes(searchKeyword.value))
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

const fetchBuildings = async () => {
  if (isFirstLoad.value) {
    loading.value = true
  }
  try {
    const buildingsData = await buildingService.getAll()
    buildings.value = await Promise.all(
        buildingsData.map(async (b: Building) => {
          const areas = await buildingService.getBuildingAreas(b.id)
          return {...b, areas}
        })
    )
    console.log('建筑及区域数据加载成功:', buildings.value)
  } catch (error) {
    ElMessage.error('数据加载失败')
  } finally {
    loading.value = false
  }
}

const cardVisibilities = ref<Record<number, boolean>>({})

const handleCardVisibility = (areaId: number, visible: boolean) => {
  cardVisibilities.value[areaId] = visible
}

const isFloorVisible = (buildingId: number, floor: number) => {

  const currentBuilding = buildings.value.find(b => b.id === buildingId)
  const areasInFloor = currentBuilding?.areas?.filter(a => a.floor === floor) || []

  return areasInFloor.some(area =>
      cardVisibilities.value[area.id]
  )
}

const isBuildingVisible = computed(() => (buildingId: number) => {
  const building = filteredBuildings.value.find(b => b.id === buildingId)
  if (!building) return false
  return getFloors(building.areas).some(floor =>
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

onMounted(() => {
  fetchBuildings()
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)

  isFirstLoad.value = false

})
</script>

<template>
  <div class="areas-container">
    <div class="page-header">
      <div class="header-content">
        <h1 class="main-title">校园区域监测</h1>
        <p class="subtitle">实时查看各区域人流情况</p>
        <div class="header-decoration"></div>
      </div>
    </div>

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

    <el-skeleton v-loading="loading" :loading="loading" animated>
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
        <div v-for="building in filteredBuildings" :key="building.id" class="building-section">
          <div class="building-header">
            <div class="header-icon-wrapper">
              <el-icon>
                <OfficeBuilding/>
              </el-icon>
            </div>
            <h2 class="building-title">{{ building.name }}</h2>
          </div>

          <div v-show="!isBuildingVisible(building.id)" class="empty-state">
            <el-empty description="该建筑暂无可见区域"/>
          </div>

          <div v-show="isBuildingVisible(building.id)">
            <el-row v-for="floor in getFloors(building.areas)" v-show="isFloorVisible(building.id, floor)" :key="floor"
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
                      v-for="area in getAreasByFloor(building.areas, floor)"
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
          </div>
        </div>
      </div>
    </el-skeleton>
  </div>
</template>

<style scoped>
.areas-container {
  max-width: 1200px;
  margin: 10px auto;
  padding: 25px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 0;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
  position: relative;
  overflow: hidden;
}

.areas-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #3498db, #1abc9c, #9b59b6);
  border-radius: 16px 16px 0 0;
}

.page-header {
  text-align: center;
  margin-bottom: 35px;
  padding-bottom: 25px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  position: relative;
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

.search-bar {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

.building-filter,
.status-filter {
  flex: 1;
  min-width: 150px;
}

.search-input {
  flex: 2;
  min-width: 200px;
}

.layout-toggle {
  flex: 0 0 auto;
  display: flex;
  justify-content: flex-end;
}

.toggle-button {
  width: 100%;
  white-space: nowrap;
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

.search-bar {
  gap: 20px;
  margin-bottom: 35px;
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  align-items: center;
}

.custom-select, .custom-input {
  width: 100%;
  transition: all 0.3s ease;
}

.custom-select:hover, .custom-input:hover {
  transform: translateY(-2px);
}

.search-input-wrapper {
  position: relative;
}

.search-icon {
  color: #64748b;
}

.building-section {
  margin-bottom: 40px;
  transition: all 0.4s ease;
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.03);
  transform: translateY(0);
  animation: fadeIn 0.5s ease-out;
}

.building-section:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.05);
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
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.03);
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

@media (max-width: 768px) {
  .areas-container {
    padding: 15px;
    margin: 10px;
  }

  .main-title {
    font-size: 24px;
  }

  .building-section {
    padding: 15px;
    margin-bottom: 20px;
  }

  .search-bar {
    padding: 10px;
    gap: 12px;
    flex-direction: column;
  }

  .search-item {
    width: 100%;
  }

  .building-filter,
  .status-filter,
  .search-input,
  .layout-toggle {
    flex: 1 1 100%;
  }

  .toggle-button {
    width: 100%;
  }

  .card-row {
    margin-bottom: 15px;
  }

  .building-header {
    margin-bottom: 10px;
  }

  .building-title {
    font-size: 20px;
    margin: 10px 0;
  }

  .floor-header {
    margin-bottom: 5px;
  }

  .floor-title {
    font-size: 16px;
    margin: 10px 0;
  }

  .card-animation {
    margin-bottom: 15px;
  }

  .header-content {
    padding: 0 10px;
  }

  .subtitle {
    font-size: 14px;
  }

  .layout-toggle {
    justify-content: center;
    margin: 0;
  }

  .floor-card-indent {
    margin-left: 0;
  }

  .card-row {
    margin-bottom: 15px;
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

  .page-header {
    margin-bottom: 20px;
    padding-bottom: 15px;
  }

  .search-bar {
    padding: 12px;
    gap: 10px;
  }
}

.search-item {
  margin: 4px 0;
}

.layout-toggle {
  display: flex;
  justify-content: flex-end;
  margin-left: auto;
}

.toggle-icon {
  margin-right: 6px;
}

@media (min-width: 769px) and (max-width: 1024px) {
  .toggle-button {
    width: 100%;
    padding-left: 10px;
    padding-right: 10px;
  }
}
</style>