<template>
  <div class="base-manager" :class="{'mobile': isMobile}">
    <div class="manager-header">
      <div class="header-left">
        <h2 class="manager-title" v-if="!isMobile">{{ title }}</h2>
        <div class="header-stats" v-if="showStats">
          <el-tag size="large" type="info" effect="plain">总数：{{ total }}</el-tag>
        </div>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="handleRefresh" class="refresh-button" :size="isMobile ? 'small' : 'default'" plain>
          <el-icon><Refresh /></el-icon>
          <span v-if="!isMobile">刷新</span>
        </el-button>
        <el-button type="primary" @click="handleAdd" class="add-button" :size="isMobile ? 'small' : 'default'">
          <el-icon><Plus /></el-icon>
          {{ isMobile ? '' : `添加${itemName}` }}
          <span v-if="isMobile">添加</span>
        </el-button>
      </div>
    </div>

    <div class="toolbar" v-if="searchable">
      <div class="search-bar">
        <el-input
          v-model="localSearchQuery"
          placeholder="输入关键字搜索"
          clearable
          @clear="handleSearchClear"
          @input="handleSearchInput"
          class="search-input"
          :size="isMobile ? 'small' : 'default'"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="handleSearch" plain :size="isMobile ? 'small' : 'default'">
          <el-icon><Search /></el-icon>
          <span v-if="!isMobile">搜索</span>
        </el-button>
      </div>
      <div class="filter-options">
        <slot name="filters"></slot>
      </div>
    </div>

    <el-card class="table-card" shadow="hover" :body-style="isMobile ? 'padding: 0; margin: 0;' : 'padding: 0px;'">
      <el-table
        v-loading="loading"
        :data="paginatedData"
        border
        style="width: 100%"
        stripe
        highlight-current-row
        :header-cell-style="{ background: '#f5f7fa', color: '#606266' }"
        row-key="id"
        empty-text="暂无数据"
        :size="isMobile ? 'small' : 'default'"
        :cell-style="isMobile ? { padding: '4px 0' } : {}"
        :height="tableHeight"
      >
        <el-table-column v-if="showIndex && !isMobile" type="index" width="50" />
        
        <el-table-column
          v-for="column in filteredColumns"
          :key="column.prop"
          :prop="column.prop"
          :label="column.label"
          :width="isMobile && column.mobileWidth ? column.mobileWidth : column.width"
          :formatter="column.formatter"
          :align="column.align || 'left'"
          :sortable="column.sortable"
          :show-overflow-tooltip="isMobile"
        >
          <template v-if="column.slot" #default="scope">
            <slot :name="`column-${column.prop}`" :row="scope.row"></slot>
          </template>
        </el-table-column>
        
        <el-table-column :label="isMobile ? '' : '操作'" :width="isMobile ? '80' : '180'" fixed="right" align="center">
          <template #default="scope">
            <div class="action-buttons" :class="{'mobile-actions': isMobile}">
              <el-button type="primary" size="small" @click="handleEdit(scope.row)" :text="!isMobile">
                <el-icon><Edit /></el-icon>
                <span v-if="!isMobile">编辑</span>
              </el-button>
              <el-button type="danger" size="small" @click="handleDelete(scope.row)" :text="!isMobile">
                <el-icon><Delete /></el-icon>
                <span v-if="!isMobile">删除</span>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <div class="pagination-container">
      <el-pagination
        v-if="pagination"
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="isMobile ? [5, 10, 20] : [10, 20, 30, 50]"
        :layout="isMobile ? 'prev, pager, next' : 'total, sizes, prev, pager, next, jumper'"
        :total="filteredTableData.length"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
        background
        :small="isMobile"
      />
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      :width="isMobile ? '95%' : '50%'"
      :before-close="handleDialogClose"
      destroy-on-close
      class="form-dialog"
      :fullscreen="isMobile"
    >
      <el-scrollbar :height="isMobile ? '75vh' : '500px'">
        <div class="dialog-content">
          <slot name="form" :form="form" :mode="formMode" :is-mobile="isMobile"></slot>
        </div>
      </el-scrollbar>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false" :size="isMobile ? 'small' : 'default'">取消</el-button>
          <el-button type="primary" @click="submitForm" :loading="submitting" :size="isMobile ? 'small' : 'default'">
            确认
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Search, Refresh } from '@element-plus/icons-vue'
import apiService from '../../services/apiService'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  resourceName: {
    type: String,
    required: true
  },
  dataLink: {
    type: String || null,
    default: null
  },
  itemName: {
    type: String,
    default: '记录'
  },
  columns: {
    type: Array,
    required: true
  },
  searchable: {
    type: Boolean,
    default: true
  },
  searchQuery: {
    type: String,
    default: ''
  },
  showIndex: {
    type: Boolean,
    default: true
  },
  pagination: {
    type: Boolean,
    default: true
  },
  defaultFormData: {
    type: Object,
    default: () => ({})
  },
  formFields: {
    type: Array,
    default: () => []
  },
  showStats: {
    type: Boolean,
    default: true
  },
  isMobile: {
    type: Boolean,
    default: false
  },
  cacheDuration: {
    type: Number,
    default: 30000 // 默认缓存30秒
  }
})

const emit = defineEmits(['add', 'edit', 'delete', 'submit', 'update-search'])

const tableData = ref([])
const loading = ref(false)
const localSearchQuery = ref('')
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const dialogVisible = ref(false)
const formMode = ref('add')
const form = ref({...props.defaultFormData})
const submitting = ref(false)

const dialogTitle = computed(() => {
  return formMode.value === 'add' 
    ? `添加${props.itemName}` 
    : `编辑${props.itemName}`
})

watch(() => props.searchQuery, (newVal) => {
  if (newVal !== localSearchQuery.value) {
    localSearchQuery.value = newVal
  }
}, { immediate: true })

watch(localSearchQuery, (newVal) => {

  if (newVal !== props.searchQuery) {
    emit('update-search', newVal)
  }
})

const handleSearch = () => {
  emit('update-search', localSearchQuery.value)
}

const handleSearchInput = () => {

}

const handleSearchClear = () => {
  localSearchQuery.value = ''
  emit('update-search', '')
}

onMounted(() => {
  // 设置该资源的缓存时间
  if (props.resourceName) {
    apiService.setResourceCacheOptions(props.resourceName, { duration: props.cacheDuration })
    console.log(`已为资源 ${props.resourceName} 设置缓存时间: ${props.cacheDuration}ms`)
  }
  
  fetchData()

  if (props.searchQuery) {
    localSearchQuery.value = props.searchQuery
  }
  
  // 初始检测设备类型
  checkIsMobile()
  
  // 添加窗口大小变化监听
  window.addEventListener('resize', checkIsMobile)
  
  // 设置自动刷新定时器 (与缓存时间一致)
  refreshTimer.value = setInterval(() => {
    fetchData()
  }, props.cacheDuration)
})

onUnmounted(() => {
  // 移除窗口大小变化监听
  window.removeEventListener('resize', checkIsMobile)
  
  // 清除自动刷新定时器
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
  }
})

const paginatedData = computed(() => {
  const startIndex = (currentPage.value - 1) * pageSize.value
  const endIndex = startIndex + pageSize.value
  return filteredTableData.value.slice(startIndex, endIndex)
})

const filteredTableData = computed(() => {
  if (!localSearchQuery.value) {
    return tableData.value
  }
  
  const query = localSearchQuery.value.toLowerCase().trim()
  return tableData.value.filter(row => {

    return Object.keys(row).some(key => {
      const value = row[key]

      if (value == null) return false

      return String(value).toLowerCase().includes(query)
    })
  })
})

const fetchData = async () => {
  loading.value = true
  try {
    let response;
    
    const url = props.dataLink
    if(!url) {
      
      response = await apiService[props.resourceName].getAll()
    }
    else{
      response = await apiService.customGet(url)
    }
    
    
    if (response && response.data) {
      
      if (response.data.results !== undefined) {
        
        tableData.value = response.data.results
        total.value = response.data.count || response.data.results.length
      } else {
        
        tableData.value = response.data
        total.value = response.data.length
      }
    } else if (Array.isArray(response)) {
      
      tableData.value = response
      total.value = response.length
    } else if (response && response.results) {
      
      tableData.value = response.results
      total.value = response.count || response.results.length
    } else {
      
      tableData.value = response || []
      total.value = Array.isArray(response) ? response.length : 0
    }
  } catch (error) {
    console.error('获取数据失败:', error)
    ElMessage.error('获取数据失败')
    tableData.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const handleSizeChange = (size) => {
  pageSize.value = size

  if (currentPage.value * size > filteredTableData.value.length) {

    currentPage.value = 1
  }
}

const handleCurrentChange = (page) => {
  currentPage.value = page

}

const handleAdd = () => {
  formMode.value = 'add'
  form.value = {...props.defaultFormData}
  dialogVisible.value = true
  emit('add')
}

const handleEdit = (row) => {
  formMode.value = 'edit'
  form.value = {...row}
  dialogVisible.value = true
  emit('edit', row)
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确认删除${props.itemName} "${row.name || row.username || row.id}" 吗?`, 
    '警告', 
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await apiService[props.resourceName].delete(row.id)
      ElMessage.success('删除成功')
      await fetchData()
      emit('delete', row)
    } catch (error) {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }).catch(() => {
    ElMessage.info('已取消删除')
  })
}

const submitForm = async () => {
  submitting.value = true
  try {
    if (formMode.value === 'add') {
      await apiService[props.resourceName].create(form.value)
      ElMessage.success(`${props.itemName}添加成功`)
    } else {
      await apiService[props.resourceName].update(form.value.id, form.value)
      ElMessage.success(`${props.itemName}更新成功`)
    }
    dialogVisible.value = false
    await fetchData()
    emit('submit', form.value, formMode.value)
  } catch (error) {
    console.error('提交失败:', error)
    ElMessage.error(`${formMode.value === 'add' ? '添加' : '更新'}失败: ${error.response?.data?.message || '未知错误'}`)
  } finally {
    submitting.value = false
  }
}

const handleDialogClose = () => {
  dialogVisible.value = false
}

const isMobile = ref(false)

// 检测设备是否为移动端
const checkIsMobile = () => {
  isMobile.value = window.innerWidth < 768
}

// 过滤移动端下不需要显示的列
const filteredColumns = computed(() => {
  if (!isMobile.value) {
    return props.columns;
  }
  
  // 在移动端模式下，过滤掉标记为在移动端隐藏的列
  return props.columns.filter(column => !column.hideOnMobile);
});

// 表格固定高度设置
const tableHeight = computed(() => {
  // 设置固定高度，基于每页10行数据
  // 每行大约40px高度，表头约50px，预留一些边距
  return isMobile.value ? 400 : 500;
});

const refreshTimer = ref(null)

const handleRefresh = () => {
  // 强制刷新，跳过缓存
  apiService.refreshCache(props.resourceName)
  fetchData()
  ElMessage.success('数据已刷新')
}
</script>

<style scoped>
.base-manager {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.manager-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.manager-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.header-stats {
  display: flex;
  gap: 8px;
}

.add-button {
  border-radius: 4px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.search-bar {
  display: flex;
  gap: 10px;
  align-items: center;
}

.search-input {
  width: 300px;
}

.table-card {
  margin: 10px 0;
  width: 100%;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.dialog-content {
  padding: 10px 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.form-dialog :deep(.el-form-item__label) {
  font-weight: 500;
}

@media (max-width: 768px) {
  .manager-header {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }
  
  .header-actions {
    width: auto;
  }
  
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .search-bar {
    width: 100%;
    flex-wrap: nowrap;
  }
  
  .search-input {
    width: 100%;
    flex: 1;
  }
  
  .pagination-container {
    overflow-x: auto;
    justify-content: center;
  }
  
  .dialog-content {
    padding: 5px 0;
  }
  
  .table-card :deep(.el-table) {
    font-size: 12px;
  }
  
  .add-button {
    padding: 8px 12px;
  }
  
  .table-card {
    margin: 5px 0;
  }
  
  .dialog-footer {
    justify-content: space-between;
  }
}

/* 移动端特有样式 */
.base-manager.mobile {
  gap: 8px;
}

.mobile .manager-title {
  font-size: 16px;
}

.mobile-actions {
  display: flex;
  justify-content: center;
  gap: 4px;
}

.mobile-actions .el-button {
  padding: 4px;
  min-height: 24px;
}

.mobile .el-table :deep(td),
.mobile .el-table :deep(th) {
  padding: 6px 0;
}

.mobile .el-table :deep(.el-table__header) th {
  font-size: 12px;
  padding: 4px 0;
}

.mobile .el-table :deep(.el-table__row) td {
  font-size: 12px;
}

/* 确保表格容器具有足够的高度 */
.table-card {
  margin: 10px 0;
  width: 100%;
}

.el-table {
  overflow-y: auto;
}

.refresh-button {
  margin-right: 8px;
  border-radius: 4px;
}

@media (max-width: 768px) {
  .refresh-button {
    padding: 8px 12px;
  }
}
</style>
