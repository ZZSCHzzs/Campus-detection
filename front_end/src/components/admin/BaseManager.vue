<template>
  <div class="base-manager">
    <div class="manager-header">
      <div class="header-left">
        <h2 class="manager-title">{{ title }}</h2>
        <div class="header-stats" v-if="showStats">
          <el-tag size="large" type="info" effect="plain">总数：{{ total }}</el-tag>
        </div>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="handleAdd" class="add-button">
          <el-icon><Plus /></el-icon>
          添加{{ itemName }}
        </el-button>
      </div>
    </div>

    <!-- 搜索和过滤区域 -->
    <div class="toolbar" v-if="searchable">
      <div class="search-bar">
        <el-input
          v-model="searchQuery"
          placeholder="输入关键字搜索"
          clearable
          @clear="fetchData"
          class="search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="fetchData" plain>
          <el-icon><Search /></el-icon>
          搜索
        </el-button>
      </div>
      <div class="filter-options">
        <slot name="filters"></slot>
      </div>
    </div>

    <!-- 数据表格 -->
    <el-card class="table-card" shadow="hover" body-style="padding: 0px;">
      <el-table
        v-loading="loading"
        :data="tableData"
        border
        style="width: 100%"
        stripe
        highlight-current-row
        :header-cell-style="{ background: '#f5f7fa', color: '#606266' }"
        row-key="id"
        empty-text="暂无数据"
      >
        <el-table-column v-if="showIndex" type="index" width="50" />
        
        <el-table-column
          v-for="column in columns"
          :key="column.prop"
          :prop="column.prop"
          :label="column.label"
          :width="column.width"
          :formatter="column.formatter"
          :align="column.align || 'left'"
          :sortable="column.sortable"
        >
          <template v-if="column.slot" #default="scope">
            <slot :name="`column-${column.prop}`" :row="scope.row"></slot>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="scope">
            <el-button type="primary" size="small" @click="handleEdit(scope.row)" text>
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(scope.row)" text>
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 分页 -->
    <div class="pagination-container">
      <el-pagination
        v-if="pagination"
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 30, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
        background
      />
    </div>

    <!-- 表单对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="50%"
      :before-close="handleDialogClose"
      destroy-on-close
      class="form-dialog"
    >
      <el-scrollbar height="500px">
        <div class="dialog-content">
          <slot name="form" :form="form" :mode="formMode"></slot>
        </div>
      </el-scrollbar>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm" :loading="submitting">
            确认
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Search } from '@element-plus/icons-vue'
import { apiServices as apiService } from '../../axios.ts'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  resourceName: {
    type: String,
    required: true
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
  }
})

const emit = defineEmits(['add', 'edit', 'delete', 'submit'])

// 数据相关
const tableData = ref([])
const loading = ref(false)
const searchQuery = ref('')
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

// 表单相关
const dialogVisible = ref(false)
const formMode = ref('add') // 'add' 或 'edit'
const form = ref({...props.defaultFormData})
const submitting = ref(false)

// 对话框标题
const dialogTitle = computed(() => {
  return formMode.value === 'add' 
    ? `添加${props.itemName}` 
    : `编辑${props.itemName}`
})

// 监听搜索查询变化
watch(searchQuery, () => {
  if (searchQuery.value === '') {
    fetchData()
  }
})

// 组件挂载时获取数据
onMounted(() => {
  fetchData()
})

// 获取数据
const fetchData = async () => {
  loading.value = true
  try {
    let url = props.resourceName
    if (!url.endsWith('/')) {
      url += '/'
    }
    // 暂时取消分页参数
    // if (props.pagination) {
    //   url += `?page=${currentPage.value}&page_size=${pageSize.value}`
    // }
    if (searchQuery.value) {
    //   // 由于取消了分页参数，直接使用 ? 开始查询
    //   url += `?search=${searchQuery.value}`
    }
    
    const response = await apiService.customGet(url)
    
    if (response.data.results) {
      // DRF分页响应结构
      tableData.value = response.data.results
      total.value = response.data.count
    } else {
      // 直接返回数据列表
      tableData.value = response.data
      total.value = response.data.length
    }
  } catch (error) {
    console.error('获取数据失败:', error)
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

// 处理分页大小变化
const handleSizeChange = (size) => {
  pageSize.value = size
  fetchData()
}

// 处理当前页变化
const handleCurrentChange = (page) => {
  currentPage.value = page
  fetchData()
}

// 处理添加
const handleAdd = () => {
  formMode.value = 'add'
  form.value = {...props.defaultFormData}
  dialogVisible.value = true
  emit('add')
}

// 处理编辑
const handleEdit = (row) => {
  formMode.value = 'edit'
  form.value = {...row}
  dialogVisible.value = true
  emit('edit', row)
}

// 处理删除
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
      const resourceUrl = `${props.resourceName}/${row.id}/`
      await apiService.delete(resourceUrl)
      ElMessage.success('删除成功')
      fetchData()
      emit('delete', row)
    } catch (error) {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }).catch(() => {
    ElMessage.info('已取消删除')
  })
}

// 提交表单
const submitForm = async () => {
  submitting.value = true
  try {
    if (formMode.value === 'add') {
      let url = props.resourceName
      if (!url.endsWith('/')) {
        url += '/'
      }
      await apiService.create(url, form.value)
      ElMessage.success(`${props.itemName}添加成功`)
    } else {
      await apiService.update(props.resourceName,form.value.id, form.value)
      ElMessage.success(`${props.itemName}更新成功`)
    }
    dialogVisible.value = false
    fetchData()
    emit('submit', form.value, formMode.value)
  } catch (error) {
    console.error('提交失败:', error)
    ElMessage.error(`${formMode.value === 'add' ? '添加' : '更新'}失败: ${error.response?.data?.message || '未知错误'}`)
  } finally {
    submitting.value = false
  }
}

// 关闭对话框
const handleDialogClose = () => {
  dialogVisible.value = false
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
</style>
