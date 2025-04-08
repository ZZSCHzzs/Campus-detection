<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, HomeFilled, OfficeBuilding } from '@element-plus/icons-vue'
import type { AreaItem, Building } from '../types'
import axios from '../axios'
import AreaCard from '../components/AreaCard.vue'


const buildings = ref<Building[]>([])
const loading = ref(false)
const expectStatus = ref<string | "all">("all")
const buildingFilter = ref<number | "all">("all") // 新增建筑筛选状态
const searchKeyword = ref("")

// 新增监听搜索关键词
watch(searchKeyword, (newVal) => {
    if (newVal) {
        buildingFilter.value = "all"
        expectStatus.value = "all"
    }
})

// 修改后的计算属性
const filteredAreas = computed(() => {
    return buildings.value
        .flatMap(b => b.areas || [])
        .filter(a => a.name.includes(searchKeyword.value))
})
// 新增计算属性过滤建筑
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
// 获取建筑数据
const fetchBuildings = async () => {
    loading.value = true
    try {
        const { data } = await axios.get('/api/buildings')
        buildings.value = await Promise.all(
            data.map(async (b: Building) => {
                const { data: areas } = await axios.get(`/api/buildings/${b.id}/areas/`)
                return { ...b, areas }
            })
        )
        console.log('建筑及区域数据加载成功:', buildings.value)
    } catch (error) {
        ElMessage.error('数据加载失败')
    } finally {
        loading.value = false
    }
}

// 新增卡片可见性状态记录
const cardVisibilities = ref<Record<number, boolean>>({})

// 处理卡片可见性变化
const handleCardVisibility = (areaId: number, visible: boolean) => {
    cardVisibilities.value[areaId] = visible
}

// 修改楼层可见性判断
const isFloorVisible = (buildingId: number, floor: number) => {
    // 获取当前建筑的所有区域
    const currentBuilding = buildings.value.find(b => b.id === buildingId)
    const areasInFloor = currentBuilding?.areas?.filter(a => a.floor === floor) || []

    // 当存在可见区域时返回 true（至少一个区域可见）
    return areasInFloor.some(area =>
        cardVisibilities.value[area.id]
    )
}

// 重构建筑可见性计算属性
const isBuildingVisible = computed(() => (buildingId: number) => {
    const building = filteredBuildings.value.find(b => b.id === buildingId)
    if (!building) return false
    return getFloors(building.areas).some(floor =>
        isFloorVisible(buildingId, floor)
    )
})
onMounted(() => {
    fetchBuildings()
    setInterval(fetchBuildings, 30000) // 修改定时器只刷新建筑数据
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
        
        <el-row class="search-bar">
            <el-col :span="4">
                <el-select placeholder="选择建筑" v-model="buildingFilter" class="custom-select">
                    <el-option label="全部" value="all" />
                    <el-option v-for="building in buildings" :key="building.id" :label="building.name"
                        :value="building.id" />
                </el-select>
            </el-col>
            <el-col :span="4">
                <el-select placeholder="状态筛选" v-model="expectStatus" class="custom-select">
                    <el-option label="全部" value="all" />
                    <el-option label="在线" value="online" />
                    <el-option label="离线" value="offline" />
                </el-select>
            </el-col>
            <el-col :span="6">
                <div class="search-input-wrapper">
                    <el-input placeholder="搜索区域名称..." v-model="searchKeyword" clearable class="custom-input">
                        <template #prefix>
                            <el-icon class="search-icon"><Search /></el-icon>
                        </template>
                    </el-input>
                </div>
            </el-col>
        </el-row>
        
        <el-skeleton :loading="loading" v-loading="loading" animated>
            <div v-if="searchKeyword" class="search-results">
                <div class="search-header">
                    <el-icon><Search /></el-icon>
                    <span>搜索结果: "{{ searchKeyword }}"</span>
                </div>
                <el-row class="card-row" :gutter="20">
                    <el-col :span="4" v-for="area in filteredAreas" :key="area.id" class="card-animation">
                        <AreaCard :area="area" :expectStatus="expectStatus"
                            @visible-change="(v) => handleCardVisibility(area.id, v)" />
                    </el-col>
                </el-row>
            </div>
            <div v-else>
                <div v-for="building in filteredBuildings" :key="building.id" class="building-section">
                    <div class="building-header">
                        <div class="header-icon-wrapper">
                            <el-icon><OfficeBuilding /></el-icon>
                        </div>
                        <h2 class="building-title">{{ building.name }}</h2>
                    </div>
                    
                    <div v-show="!isBuildingVisible(building.id)" class="empty-state">
                        <el-empty description="该建筑暂无可见区域" />
                    </div>
                    
                    <div v-show="isBuildingVisible(building.id)">
                        <el-row class="card-row" :gutter="20" v-for="floor in getFloors(building.areas)" :key="floor"
                            v-show="isFloorVisible(building.id, floor)">
                            <div class="floor-header">
                                <div class="floor-icon-wrapper">
                                    <el-icon><HomeFilled /></el-icon>
                                </div>
                                <h3 class="floor-title">{{ floor }}F</h3>
                            </div>
                            
                            <el-col :span="5" v-for="area in getAreasByFloor(building.areas, floor)" :key="area.id" class="card-animation">
                                <AreaCard :area="area" :expectStatus="expectStatus"
                                    @visible-change="(v) => handleCardVisibility(area.id, v)" />
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
    max-width: 1400px;
    margin: 20px auto;
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
    gap: 20px;
    margin-bottom: 35px;
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
    position: relative;
    z-index: 1;
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
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
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
}

@keyframes slideUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
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

/* 响应式调整 */
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
    }
    
    .search-bar {
        padding: 15px;
        flex-direction: column;
    }
    
    .card-row {
        margin-bottom: 15px;
    }
}

@media (max-width: 1200px) and (min-width: 769px) {
    .areas-container {
        padding: 20px;
    }
}
</style>