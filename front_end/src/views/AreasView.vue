<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
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
        <el-row class="search-bar">
            <el-col :span="4">
                <el-select placeholder="选择建筑" v-model="buildingFilter">
                    <el-option label="全部" value="all" />
                    <el-option v-for="building in buildings" :key="building.id" :label="building.name"
                        :value="building.id" />
                </el-select>
            </el-col>
            <el-col :span="4">

                <el-select placeholder="状态筛选" v-model="expectStatus">
                    <el-option label="全部" value="all" />
                    <el-option label="在线" value="online" />
                    <el-option label="离线" value="offline" />
                </el-select>
            </el-col>
            <el-col :span="6">
                <el-input placeholder="搜索区域名称..." v-model="searchKeyword" clearable />
            </el-col>


        </el-row>
        <el-skeleton :loading="loading" v-loading="loading" animated>
            <div v-if="searchKeyword">
                <!-- 搜索模式下显示所有匹配结果 -->
                <el-row class="card-row" :gutter="20">
                    <el-col :span="6" v-for="area in filteredAreas" :key="area.id">
                        <AreaCard :area="area" :expectStatus="expectStatus"
                            @visible-change="(v) => handleCardVisibility(area.id, v)" />
                    </el-col>
                </el-row>
            </div>
            <div v-else>
                <div v-for="building in filteredBuildings" :key="building.id" class="building-section">
                    <h2 class="building-title">{{ building.name }}</h2>
                    <div v-show="!isBuildingVisible(building.id)">
                        <el-empty description="该建筑暂无可见区域" />
                    </div>
                    <div v-show="isBuildingVisible(building.id)">
                        <el-row class="card-row" :gutter="20" v-for="floor in getFloors(building.areas)" :key="floor"
                            v-show="isFloorVisible(building.id, floor)">
                            <h3 class="floor-title">{{ floor }}F</h3>
                            <el-col :span="6" v-for="area in getAreasByFloor(building.areas, floor)" :key="area.id">
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
/* 新增样式 */
.info-item {
    margin: 8px 0;
    font-size: 14px;
}

.label {
    color: #666;
    margin-right: 8px;
}

.areas-container {
    max-width: 1200px;
    margin: 20px auto;
}

.search-bar {
    gap: 20px;
    margin-bottom: 20px;
}

.area-card {
    margin-bottom: 20px;
}

/* 新增建筑和楼层标题样式 */
.building-title {
    margin: 20px 0;
    color: #333;
    border-bottom: 2px solid #eee;
    padding-bottom: 10px;
}

.floor-title {
    margin: 15px 0;
    color: #666;
    font-size: 16px;
}

.card-row {
    margin-bottom: 20px;
}
</style>