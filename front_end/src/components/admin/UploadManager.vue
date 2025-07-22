<template>
  <div class="upload-manager-container" :class="{ 'mobile': isMobile }">
    <h2 class="section-title">{{ title }}</h2>
    
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="数据上传" name="data">
        <el-form 
          ref="dataFormRef" 
          :model="dataForm" 
          :rules="dataRules" 
          label-width="100px"
          class="upload-form"
        >
          <el-form-item label="节点ID" prop="id">
            <el-select 
              v-model="dataForm.id" 
              filterable 
              placeholder="选择硬件节点"
              :loading="loadingNodes"
            >
              <el-option
                v-for="node in nodes"
                :key="node.id"
                :label="`${node.name} (ID: ${node.id})`"
                :value="node.id"
              >
                <div class="node-option">
                  <span>{{ node.name }}</span>
                  <span class="node-id">ID: {{ node.id }}</span>
                  <el-tag 
                    :type="node.status ? 'success' : 'danger'"
                    size="small"
                  >
                    {{ node.status ? '在线' : '离线' }}
                  </el-tag>
                </div>
              </el-option>
            </el-select>
            <el-button 
              type="primary" 
              link 
              size="small" 
              @click="refreshNodes"
              :loading="loadingNodes"
              style="margin-top: 5px;"
            >
              刷新节点列表
            </el-button>
          </el-form-item>
          
          <el-form-item label="检测数量" prop="detected_count">
            <el-input-number v-model="dataForm.detected_count" :min="0" :step="1"></el-input-number>
          </el-form-item>
          
          <el-form-item label="时间戳" prop="timestamp">
            <el-date-picker
              v-model="dataForm.timestamp"
              type="datetime"
              placeholder="选择日期和时间"
              format="YYYY-MM-DD HH:mm:ss"
              value-format="YYYY-MM-DD HH:mm:ss"
            ></el-date-picker>
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="submitDataForm" :loading="dataSubmitting">上传数据</el-button>
            <el-button @click="resetDataForm">重置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
      
      <el-tab-pane label="告警创建" name="alert">
        <el-form 
          ref="alertFormRef" 
          :model="alertForm" 
          :rules="alertRules" 
          label-width="100px"
          class="upload-form"
        >
          <el-form-item label="节点ID" prop="id">
            <el-select 
              v-model="alertForm.id" 
              filterable 
              placeholder="选择硬件节点"
              :loading="loadingNodes"
            >
              <el-option
                v-for="node in nodes"
                :key="node.id"
                :label="`${node.name} (ID: ${node.id})`"
                :value="node.id"
              >
                <div class="node-option">
                  <span>{{ node.name }}</span>
                  <span class="node-id">ID: {{ node.id }}</span>
                  <el-tag 
                    :type="node.status ? 'success' : 'danger'"
                    size="small"
                  >
                    {{ node.status ? '在线' : '离线' }}
                  </el-tag>
                </div>
              </el-option>
            </el-select>
          </el-form-item>
          
          <el-form-item label="告警类型" prop="alert_type">
            <el-select v-model="alertForm.alert_type" placeholder="选择告警类型">
              <el-option label="火灾" value="fire"></el-option>
              <el-option label="安保" value="guard"></el-option>
              <el-option label="人员密集" value="crowd"></el-option>
              <el-option label="生命危急" value="health"></el-option>
              <el-option label="其他问题" value="other"></el-option>
            </el-select>
          </el-form-item>
          
          <el-form-item label="告警等级" prop="grade">
            <el-select v-model="alertForm.grade" placeholder="选择告警等级">
              <el-option label="普通" :value="0"></el-option>
              <el-option label="注意" :value="1"></el-option>
              <el-option label="警告" :value="2"></el-option>
              <el-option label="严重" :value="3"></el-option>
            </el-select>
          </el-form-item>
          
          <el-form-item label="是否公开" prop="publicity">
            <el-switch
              v-model="alertForm.publicity"
              active-text="公开"
              inactive-text="不公开"
            ></el-switch>
          </el-form-item>
          
          <el-form-item label="告警消息" prop="message">
            <el-input
              v-model="alertForm.message"
              type="textarea"
              :rows="4"
              placeholder="请输入告警消息内容"
            ></el-input>
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="submitAlertForm" :loading="alertSubmitting">创建告警</el-button>
            <el-button @click="resetAlertForm">重置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <div v-if="resultMessage" class="result-message" :class="resultStatus">
      {{ resultMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import apiService, { nodeService } from '../../services'

const props = defineProps({
  title: String,
  isMobile: Boolean
})

const activeTab = ref('data')
const dataSubmitting = ref(false)
const alertSubmitting = ref(false)
const resultMessage = ref('')
const resultStatus = ref('')
const nodes = ref([])
const loadingNodes = ref(false)

const dataForm = reactive({
  id: null,
  detected_count: 0,
  timestamp: new Date().toISOString().slice(0, 19).replace('T', ' ')
})

const alertForm = reactive({
  id: null,
  alert_type: '',
  grade: 0,
  publicity: false,
  message: ''
})

const dataFormRef = ref(null)
const alertFormRef = ref(null)

const fetchNodes = async () => {
  loadingNodes.value = true
  try {
    nodes.value = await nodeService.getAll()
    ElMessage.success('节点列表加载成功')
  } catch (error) {
    console.error('获取节点列表失败:', error)
    ElMessage.error('获取节点列表失败，请稍后重试')
  } finally {
    loadingNodes.value = false
  }
}

const refreshNodes = () => {
  apiService.refreshCache('nodes')
  fetchNodes()
}

onMounted(() => {
  fetchNodes()
})

const dataRules = {
  id: [
    { required: true, message: '请选择硬件节点', trigger: 'change' },
    { type: 'number', message: '节点ID必须是数字', trigger: 'change' }
  ],
  detected_count: [
    { required: true, message: '请输入检测数量', trigger: 'blur' },
    { type: 'number', min: 0, message: '数量不能小于0', trigger: 'blur' }
  ],
  timestamp: [
    { required: true, message: '请选择时间', trigger: 'change' }
  ]
}

const alertRules = {
  id: [
    { required: true, message: '请选择硬件节点', trigger: 'change' },
    { type: 'number', message: '节点ID必须是数字', trigger: 'change' }
  ],
  alert_type: [
    { required: true, message: '请选择告警类型', trigger: 'change' }
  ],
  grade: [
    { required: true, message: '请选择告警等级', trigger: 'change' },
    { type: 'number', message: '告警等级必须是数字', trigger: 'change' }
  ],
  message: [
    { required: true, message: '请输入告警消息', trigger: 'blur' },
    { min: 5, max: 500, message: '消息长度应在5到500个字符之间', trigger: 'blur' }
  ]
}

const submitDataForm = async () => {
  if (!dataFormRef.value) return
  
  await dataFormRef.value.validate(async (valid, fields) => {
    if (!valid) {
      console.log('数据表单验证失败', fields)
      return
    }
    
    dataSubmitting.value = true
    resultMessage.value = ''
    resultStatus.value = ''
    
    try {

      const formData = {
        ...dataForm,
        id: Number(dataForm.id)
      }
      
      const response = await axios.post('/api/upload/', formData)
      resultMessage.value = response.data.message || '数据上传成功'
      resultStatus.value = 'success'
      ElMessage.success(resultMessage.value)
    } catch (error) {
      console.error('数据上传失败:', error)
      resultMessage.value = error.response?.data?.error || error.response?.data?.message || '数据上传失败'
      resultStatus.value = 'error'
      ElMessage.error(resultMessage.value)
    } finally {
      dataSubmitting.value = false
    }
  })
}

const submitAlertForm = async () => {
  if (!alertFormRef.value) return
  
  await alertFormRef.value.validate(async (valid, fields) => {
    if (!valid) {
      console.log('告警表单验证失败', fields)
      return
    }
    
    alertSubmitting.value = true
    resultMessage.value = ''
    resultStatus.value = ''
    
    try {

      const formData = {
        ...alertForm,
        id: Number(alertForm.id),
        grade: Number(alertForm.grade)
      }
      
      const response = await axios.post('/api/alert/', formData)
      resultMessage.value = response.data.message || '告警创建成功'
      resultStatus.value = 'success'
      ElMessage.success(resultMessage.value)
    } catch (error) {
      console.error('告警创建失败:', error)
      resultMessage.value = error.response?.data?.error || error.response?.data?.message || '告警创建失败'
      resultStatus.value = 'error'
      ElMessage.error(resultMessage.value)
    } finally {
      alertSubmitting.value = false
    }
  })
}

const resetDataForm = () => {
  if (dataFormRef.value) {
    dataFormRef.value.resetFields()
    dataForm.timestamp = new Date().toISOString().slice(0, 19).replace('T', ' ')
  }
}

const resetAlertForm = () => {
  if (alertFormRef.value) {
    alertFormRef.value.resetFields()
  }
}
</script>

<style scoped>
.upload-manager-container {
  padding: 20px;
  width: 100%;
}

.section-title {
  margin-bottom: 24px;
  color: var(--el-color-primary);
  border-bottom: 1px solid #eaeaea;
  padding-bottom: 10px;
}

.upload-form {
  max-width: 600px;
  margin: 20px auto;
}

.el-tabs {
  margin-bottom: 20px;
}

.result-message {
  margin-top: 20px;
  padding: 10px;
  border-radius: 4px;
  font-size: 14px;
  text-align: center;
}

.success {
  background-color: #f0f9eb;
  color: #67c23a;
  border: 1px solid #e1f3d8;
}

.error {
  background-color: #fef0f0;
  color: #f56c6c;
  border: 1px solid #fbc4c4;
}

.mobile .upload-form {
  max-width: 100%;
}

.mobile .el-form-item {
  margin-bottom: 15px;
}

.node-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.node-id {
  color: #909399;
  font-size: 12px;
  margin: 0 8px;
}

.node-status {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 10px;
  background-color: #f56c6c;
  color: white;
}

.node-status.active {
  background-color: #67c23a;
}
</style>
