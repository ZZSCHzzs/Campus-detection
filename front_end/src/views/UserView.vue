<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Lock, Message, Edit, Star, Delete } from '@element-plus/icons-vue'
import axios from '../axios'
import type { User as UserType } from '../types'
import CryptoJS from 'crypto-js'  // 导入CryptoJS库用于密码加密
import { Calendar, Check, InfoFilled, Location, Phone, Plus, View } from '@element-plus/icons-vue'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

// 从路由参数中获取当前Tab，默认为'profile'
const activeTab = ref('profile')

// 监听路由参数变化，更新activeTab
watch(() => route.query.tab, (newTab) => {
  if (newTab === 'profile' || newTab === 'password' || newTab === 'favorites') {
    activeTab.value = newTab as string
  } else {
    activeTab.value = 'profile'
  }
}, { immediate: true })

// 当Tab改变时更新路由
const handleTabChange = (tab: string) => {
  router.push({ path: '/profile', query: { tab } })
}

// 用户信息相关
const userInfo = ref<UserType>({
  id: 0,
  username: '',
  role: 'user',
  phone: '',
  email: '',
  register_time: ''
})

const userForm = ref({
  email: '',
  phone: ''
})

const passwordForm = ref({
  current_password: '',
  new_password: '',
  re_new_password: ''
})

const isEditing = ref(false)
const loading = ref(false)

// 表单验证规则
const profileRules = reactive({
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ]
})

const passwordRules = reactive({
  current_password: [
    { required: true, message: '请输入当前密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少为6位', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少为6位', trigger: 'blur' }
  ],
  re_new_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (passwordForm.value.new_password && value !== passwordForm.value.new_password) {
          callback(new Error('两次输入密码不一致'))
        } else {
          callback()
        }
      }, 
      trigger: 'blur' 
    }
  ]
})

const profileFormRef = ref()
const passwordFormRef = ref()

// 获取用户信息
const fetchUserInfo = async () => {
  loading.value = true
  try {
    console.log('正在获取用户信息...')
    // 先验证会话有效性
    const isSessionValid = await authStore.validateSession()
    if (!isSessionValid) {
      throw new Error('会话无效')
    }
    
    // 使用Djoser的用户信息端点
    const response = await axios.get('/auth/users/me/')
    console.log('用户信息获取成功:', response.data)
    
    // 更新用户信息 - 只使用User接口中定义的字段
    userInfo.value = {
      id: response.data.id || 0,
      username: response.data.username || '',
      role: response.data.role || 'user',
      phone: response.data.phone || '',
      email: response.data.email || '',
      register_time: response.data.register_time || ''
    }
    
    // 复制到表单
    userForm.value.email = userInfo.value.email || ''
    userForm.value.phone = userInfo.value.phone || ''
    
    // 更新store中的信息
    if (authStore.user) {
      authStore.user = {...authStore.user, ...userInfo.value}
    } else {
      authStore.setUser(userInfo.value)
    }
  } catch (error) {
    console.error('获取用户信息失败:', error)
    
    if (error.response?.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      // 如果是401错误，自动重定向到登录页
      authStore.logout()
      router.push({
        path: '/auth',
        query: { mode: 'login', redirect: '/profile' }
      })
    } else {
      ElMessage.error('获取用户信息失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
    }
  } finally {
    loading.value = false
  }
}

// 启用编辑模式
const enableEdit = () => {
  isEditing.value = true
}

// 取消编辑
const cancelEdit = () => {
  isEditing.value = false
  userForm.value.email = userInfo.value.email || ''
  userForm.value.phone = userInfo.value.phone || ''
}

// 提交用户信息更新
const submitUserUpdate = async () => {
  if (!profileFormRef.value) return
  
  await profileFormRef.value.validate(async (valid, fields) => {
    if (valid) {
      loading.value = true
      try {
        // 创建更新数据对象 - 只包含User接口中允许修改的字段
        const updateData = {
          email: userForm.value.email,
          phone: userForm.value.phone
        }
        
        // 更新用户基本信息
        const response = await axios.patch('/auth/users/me/', updateData)
        
        // 更新本地显示的信息
        userInfo.value.email = userForm.value.email
        userInfo.value.phone = userForm.value.phone
        
        // 更新store中的信息
        if (authStore.user) {
          authStore.user = {...authStore.user, ...updateData}
        }
        
        ElMessage.success('用户信息更新成功')
        isEditing.value = false
      } catch (error) {
        ElMessage.error('更新用户信息失败: ' + (error.response?.data?.detail || '未知错误'))
        console.error('更新用户信息失败:', error)
      } finally {
        loading.value = false
      }
    } else {
      console.log('表单验证失败:', fields)
    }
  })
}

// 密码加密函数 - 与AuthView一致
const encryptPassword = (password: string): string => {
  return CryptoJS.SHA256(password).toString(CryptoJS.enc.Hex)
}

// 提交密码更新
const submitPasswordUpdate = async () => {
  if (!passwordFormRef.value) return
  
  await passwordFormRef.value.validate(async (valid, fields) => {
    if (valid) {
      loading.value = true
      try {
        // 在发送请求前对密码进行加密处理
        const encryptedCurrentPassword = encryptPassword(passwordForm.value.current_password)
        const encryptedNewPassword = encryptPassword(passwordForm.value.new_password)
        const encryptedReNewPassword = encryptPassword(passwordForm.value.re_new_password)
        
        await axios.post('/auth/users/set_password/', {
          current_password: encryptedCurrentPassword,
          new_password: encryptedNewPassword,
          re_new_password: encryptedReNewPassword
        })
        
        ElMessage.success('密码更新成功')
        
        // 清空密码字段
        passwordForm.value.current_password = ''
        passwordForm.value.new_password = ''
        passwordForm.value.re_new_password = ''
      } catch (error) {
        ElMessage.error('密码更新失败: ' + (error.response?.data?.detail || '未知错误'))
        console.error('密码更新失败:', error)
      } finally {
        loading.value = false
      }
    } else {
      console.log('表单验证失败:', fields)
    }
  })
}

// 模拟的收藏区域数据
const favoriteAreas = ref([
  { id: 1, name: '图书馆阅览区', location: '图书馆一楼', capacity: 100, current_people: 65 },
  { id: 2, name: '学生活动中心', location: '大学生活动中心', capacity: 200, current_people: 120 },
  { id: 3, name: '工学院实验室', location: '工学院3号楼', capacity: 50, current_people: 25 }
])

// 移除收藏
const removeFavorite = (areaId) => {
  ElMessageBox.confirm(
    '确定要取消收藏该区域吗?',
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    // 这里应该有一个取消收藏的API调用
    // 假设API路径为 /api/favorites/{areaId}
    
    // 模拟成功响应
    favoriteAreas.value = favoriteAreas.value.filter(area => area.id !== areaId)
    ElMessage.success('取消收藏成功')
  }).catch(() => {
    // 取消操作
  })
}

// 计算区域拥挤度
const getOccupancyRate = (current, capacity) => {
  return (current / capacity) * 100
}

// 判断拥挤度状态的标签类型
const getTagType = (rate) => {
  const percentage = rate * 100
  if (percentage > 90) return 'danger'
  if (percentage > 70) return 'warning'
  if (percentage > 50) return 'info'
  return 'success'
}

// 密码强度计算
const passwordStrength = ref(0)
const passwordStrengthStatus = ref('success')

// 更新密码强度
const updatePasswordStrength = (password) => {
  if (!password) {
    passwordStrength.value = 0
    passwordStrengthStatus.value = 'success'
    return
  }
  
  let strength = 0
  
  // 长度检查
  if (password.length >= 8) strength += 20
  else if (password.length >= 6) strength += 10
  
  // 包含数字
  if (/\d/.test(password)) strength += 20
  
  // 包含小写字母
  if (/[a-z]/.test(password)) strength += 20
  
  // 包含大写字母
  if (/[A-Z]/.test(password)) strength += 20
  
  // 包含特殊字符
  if (/[^A-Za-z0-9]/.test(password)) strength += 20
  
  passwordStrength.value = Math.min(100, strength)
  
  // 设置强度状态
  if (strength < 40) passwordStrengthStatus.value = 'exception'
  else if (strength < 70) passwordStrengthStatus.value = 'warning'
  else passwordStrengthStatus.value = 'success'
}

onMounted(async () => {
  console.log('UserView组件已挂载，准备获取用户信息')
  // 检查登录状态
  if (!authStore.isAuthenticated) {
    ElMessage.warning('请先登录')
    router.push({
      path: '/auth',
      query: { mode: 'login', redirect: '/profile' }
    })
    return
  }
  
  await fetchUserInfo()
})
</script>

<template>
  <div class="user-center-container">
    <!-- 重新设计的个人中心顶部 - 改为浅色系 -->
    <div class="user-header">
      <div class="user-header-content">
        <div class="user-info-brief">
          <div class="user-header-text">
            <h1 class="page-title">{{ userInfo.username }}</h1>
            <div class="user-meta">
              <el-tag :type="userInfo.role === 'admin' ? 'danger' : 'primary'" effect="plain" class="role-tag">
                {{ userInfo.role === 'admin' ? '管理员' : '普通用户' }}
              </el-tag>
              <span class="join-date">注册于 {{ userInfo.register_time && userInfo.register_time.split('T')[0] }}</span>
            </div>
          </div>
        </div>
        <div class="user-stats">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-statistic title="收藏区域" :value="favoriteAreas.length">
                <template #prefix>
                  <el-icon class="stat-icon"><Star /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="最近登录" value="今天">
                <template #prefix>
                  <el-icon class="stat-icon"><Calendar /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="账户状态" value="正常">
                <template #prefix>
                  <el-icon class="stat-icon"><Check /></el-icon>
                </template>
              </el-statistic>
            </el-col>
          </el-row>
        </div>
      </div>
    </div>
    
    <div class="tabs-container">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange" class="main-tabs">
        <el-tab-pane label="个人信息" name="profile">
          <div class="tab-content">
            <el-card v-loading="loading" class="profile-card content-card">
              <!-- 个人资料部分 -->
              <div class="section-header">
                <div class="section-title">
                  <el-icon :size="22" color="#409EFF"><User /></el-icon>
                  <h2>个人资料</h2>
                </div>
                <el-button v-if="!isEditing" type="primary" text @click="enableEdit" :icon="Edit">
                  编辑资料
                </el-button>
              </div>
              
              <div v-if="!isEditing" class="info-display">
                <el-descriptions :column="1" border>
                  <el-descriptions-item label="用户名">
                    <el-tag size="small">{{ userInfo.username }}</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="邮箱">
                    <span v-if="userInfo.email">{{ userInfo.email }}</span>
                    <el-tag v-else size="small" type="warning">未设置</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="电话">
                    <span v-if="userInfo.phone">{{ userInfo.phone }}</span>
                    <el-tag v-else size="small" type="warning">未设置</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="注册时间">
                    {{ userInfo.register_time }}
                  </el-descriptions-item>
                </el-descriptions>
              </div>
              
              <el-form 
                v-else 
                ref="profileFormRef"
                :model="userForm" 
                :rules="profileRules"
                label-position="top"
                class="edit-form"
              >
                <div class="form-header">
                  <el-alert
                    title="请完善您的个人信息"
                    type="info"
                    :closable="false"
                    show-icon
                  >
                    <template #default>
                      更新您的个人信息有助于我们提供更好的服务
                    </template>
                  </el-alert>
                </div>
                
                <el-form-item label="用户名">
                  <el-input v-model="userInfo.username" disabled placeholder="用户名不可修改">
                    <template #prefix>
                      <el-icon><User /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
                
                <el-form-item label="邮箱" prop="email">
                  <el-input v-model="userForm.email" placeholder="请输入邮箱地址">
                    <template #prefix>
                      <el-icon><Message /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
                
                <el-form-item label="电话" prop="phone">
                  <el-input v-model="userForm.phone" placeholder="请输入电话号码">
                    <template #prefix>
                      <el-icon><Phone /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
                
                <div class="form-actions">
                  <el-button @click="cancelEdit" plain>取消</el-button>
                  <el-button type="primary" @click="submitUserUpdate" :loading="loading">
                    保存修改
                  </el-button>
                </div>
              </el-form>
            </el-card>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="修改密码" name="password">
          <div class="tab-content">
            <el-row :gutter="20">
              <el-col :md="14" :sm="24" :xs="24">
                <el-card class="password-card content-card" shadow="hover">
                  <template #header>
                    <div class="pw-card-header">
                      <span class="title">
                        <el-icon :size="20"><Lock /></el-icon>
                        密码管理
                      </span>
                    </div>
                  </template>
                  
                  <el-form 
                    ref="passwordFormRef"
                    :model="passwordForm" 
                    :rules="passwordRules"
                    label-position="top"
                    class="password-form"
                    status-icon
                  >
                    <el-alert
                      type="warning"
                      :closable="false"
                      show-icon
                      class="mb-4"
                    >
                      <template #title>
                        为保障账户安全，建议定期更换密码
                      </template>
                      <template #default>
                        请使用包含大小写字母、数字和特殊符号的强密码
                      </template>
                    </el-alert>
                    
                    <el-form-item label="当前密码" prop="current_password">
                      <el-input 
                        v-model="passwordForm.current_password" 
                        type="password"
                        show-password
                        placeholder="请输入当前密码"
                      >
                        <template #prefix>
                          <el-icon><Lock /></el-icon>
                        </template>
                      </el-input>
                    </el-form-item>
                    
                    <el-form-item label="新密码" prop="new_password">
                      <el-input 
                        v-model="passwordForm.new_password" 
                        type="password"
                        show-password
                        placeholder="请输入新密码"
                        @input="updatePasswordStrength"
                      >
                        <template #prefix>
                          <el-icon><Lock /></el-icon>
                        </template>
                      </el-input>
                      <div class="password-strength" v-if="passwordForm.new_password">
                        <span>密码强度:</span>
                        <el-progress 
                          :percentage="passwordStrength"
                          :status="passwordStrengthStatus"
                          :stroke-width="8"
                          :text-inside="true"
                        ></el-progress>
                      </div>
                    </el-form-item>
                    
                    <el-form-item label="确认新密码" prop="re_new_password">
                      <el-input 
                        v-model="passwordForm.re_new_password" 
                        type="password"
                        show-password
                        placeholder="请再次输入新密码"
                      >
                        <template #prefix>
                          <el-icon><Lock /></el-icon>
                        </template>
                      </el-input>
                    </el-form-item>
                    
                    <div class="form-actions">
                      <el-button type="primary" @click="submitPasswordUpdate" :loading="loading" class="full-width-btn">
                        <el-icon><Check /></el-icon>
                        确认修改密码
                      </el-button>
                    </div>
                  </el-form>
                </el-card>
              </el-col>
              
              <el-col :md="10" :sm="24" :xs="24">
                <el-card class="security-tips-card" shadow="hover">
                  <template #header>
                    <div class="security-card-header">
                      <span class="title">
                        <el-icon :size="20"><InfoFilled /></el-icon>
                        安全提示
                      </span>
                    </div>
                  </template>
                  
                  <div class="security-tips">
                    <el-timeline>
                      <el-timeline-item 
                        type="primary" 
                        size="large" 
                        icon="Warning"
                        timestamp="重要提示"
                      >
                        密码是您账户的唯一防线，请妥善保管
                      </el-timeline-item>
                      <el-timeline-item type="success" icon="Check">
                        建议使用至少8位以上的密码
                      </el-timeline-item>
                      <el-timeline-item type="success" icon="Check">
                        包含大小写字母、数字和特殊字符
                      </el-timeline-item>
                      <el-timeline-item type="success" icon="Check">
                        避免使用生日、手机号等个人信息
                      </el-timeline-item>
                      <el-timeline-item type="warning" icon="InfoFilled">
                        定期更换密码，提高账户安全性
                      </el-timeline-item>
                    </el-timeline>
                  </div>
                </el-card>
              </el-col>
            </el-row>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="我的收藏" name="favorites">
          <div class="tab-content">
            <div class="favorites-header">
              <div class="header-title">
                <el-icon :size="22" color="#409EFF"><Star /></el-icon>
                <h2>我收藏的区域</h2>
              </div>
              <el-button type="primary" @click="router.push('/areas')">
                <el-icon><Plus /></el-icon>
                <span>浏览所有区域</span>
              </el-button>
            </div>
            
            <div v-if="favoriteAreas.length > 0" class="favorites-container">
              <el-row :gutter="20">
                <el-col v-for="area in favoriteAreas" :key="area.id" :xs="24" :sm="12" :md="8" :lg="8">
                  <el-card class="favorite-item" shadow="hover">
                    <template #header>
                      <div class="favorite-header">
                        <h3>{{ area.name }}</h3>
                        <el-tooltip content="取消收藏" placement="top">
                          <el-button 
                            type="danger" 
                            :icon="Delete" 
                            circle
                            plain
                            size="small"
                            @click="removeFavorite(area.id)"
                          ></el-button>
                        </el-tooltip>
                      </div>
                    </template>
                    
                    <div class="favorite-details">
                      <el-descriptions :column="1" size="small" border>
                        <el-descriptions-item label="位置">
                          <span class="location-text">
                            <el-icon><Location /></el-icon>
                            {{ area.location }}
                          </span>
                        </el-descriptions-item>
                        <el-descriptions-item label="容量">
                          <el-progress 
                            :percentage="getOccupancyRate(area.current_people, area.capacity)" 
                            :status="getOccupancyRate(area.current_people, area.capacity) > 90 ? 'exception' : (getOccupancyRate(area.current_people, area.capacity) > 70 ? 'warning' : 'success')"
                            :stroke-width="10"
                            :format="() => `${area.current_people}/${area.capacity}`"
                          ></el-progress>
                        </el-descriptions-item>
                        <el-descriptions-item label="状态">
                          <el-tag 
                            :type="getTagType(area.current_people / area.capacity)" 
                            effect="dark"
                            size="small"
                          >
                            {{ 
                              getOccupancyRate(area.current_people, area.capacity) > 90 ? '非常拥挤' : 
                              (getOccupancyRate(area.current_people, area.capacity) > 70 ? '较为拥挤' : 
                              (getOccupancyRate(area.current_people, area.capacity) > 50 ? '一般' : '空闲')) 
                            }}
                          </el-tag>
                        </el-descriptions-item>
                      </el-descriptions>
                      
                      <el-button type="primary" plain @click="router.push(`/areas/${area.id}`)" class="view-details-btn">
                        <el-icon><View /></el-icon>
                        查看详情
                      </el-button>
                    </div>
                  </el-card>
                </el-col>
              </el-row>
            </div>
            
            <el-empty 
              v-else
              description="您还没有收藏任何区域"
              class="empty-favorites"
            >
              <template #image>
                <el-icon :size="60" color="#909399"><Star /></el-icon>
              </template>
              <el-button type="primary" @click="router.push('/areas')">浏览区域</el-button>
            </el-empty>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<style scoped>
/* 自定义变量 */
:root {
  --primary-color: #409EFF;
  --success-color: #67C23A;
  --warning-color: #E6A23C;
  --danger-color: #F56C6C;
  --info-color: #909399;
  --bg-color: #f5f7fa;
  --text-color: #303133;
  --text-color-light: #606266;
  --border-color: #EBEEF5;
  --border-radius: 6px;
  --card-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  --transition-time: 0.3s;
}

/* 工具类 */
.mb-4 { margin-bottom: 16px; }
.mt-3 { margin-top: 12px; }
.full-width-btn { width: 100%; }

/* 基础布局样式 */
.user-center-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0;
  min-height: calc(100vh - 200px);
}

/* 重新设计的顶部区域 - 浅色系风格 */
.user-header {
  background-color: #f7faff;
  background-image: linear-gradient(to right, rgba(236, 245, 255, 0.8), rgba(243, 248, 255, 0.5)), 
                     repeating-linear-gradient(45deg, rgba(200, 222, 255, 0.12), rgba(200, 222, 255, 0.12) 15px, rgba(255, 255, 255, 0.5) 15px, rgba(255, 255, 255, 0.5) 30px);
  color: #333;
  padding: 30px 20px;
  border-radius: var(--border-radius);
  margin: 20px 20px 30px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(64, 158, 255, 0.1);
  position: relative;
  overflow: hidden;
}

.user-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, #409EFF, #79bbff);
}

.user-header-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 30px;
  position: relative;
  z-index: 1;
}

.user-info-brief {
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.user-header-text {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.page-title {
  margin: 0;
  color: #333;
  font-size: 32px;
  font-weight: 700;
  text-shadow: 1px 1px 0 rgba(255, 255, 255, 0.8);
  position: relative;
  padding-bottom: 10px;
}

.page-title::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 3px;
  background-color: #409EFF;
  border-radius: 3px;
}

.user-meta {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-top: 15px;
}

.role-tag {
  font-weight: 500;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.join-date {
  font-size: 14px;
  color: #606266;
}

.user-stats {
  background-color: white;
  border-radius: var(--border-radius);
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(235, 238, 245, 0.8);
}

.user-stats :deep(.el-statistic__title) {
  color: #606266;
  font-weight: 500;
  font-size: 13px;
}

.user-stats :deep(.el-statistic__content) {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #303133;
  font-weight: 600;
}

.stat-icon {
  color: #409EFF;
  background-color: rgba(64, 158, 255, 0.1);
  border-radius: 50%;
  padding: 5px;
  margin-right: 5px;
}

/* Tab Container Style */
.tabs-container {
  padding: 0 20px;
}

.main-tabs :deep(.el-tabs__header) {
  margin-bottom: 25px;
  border-bottom: 2px solid #f0f2f5;
}

.main-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.main-tabs :deep(.el-tabs__item) {
  font-size: 16px;
  height: 50px;
  line-height: 50px;
  font-weight: 500;
  padding: 0 25px;
  transition: all var(--transition-time);
}

.main-tabs :deep(.el-tabs__item.is-active) {
  color: var(--primary-color);
  font-weight: 600;
}

.main-tabs :deep(.el-tabs__active-bar) {
  height: 3px;
  background-color: var(--primary-color);
}

.tab-content {
  animation: fadeIn 0.3s ease;
}

/* 卡片共享样式 */
.content-card {
  margin-bottom: 25px;
  border-radius: var(--border-radius);
  transition: all var(--transition-time);
  overflow: hidden;
  border: none;
  padding: 20px;
}

/* 个人信息卡片样式 */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 15px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-title h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color);
}

.info-display {
  margin-bottom: 20px;
}

.info-display :deep(.el-descriptions__label) {
  width: 120px;
  font-weight: 600;
}

.edit-form {
  max-width: 600px;
  margin: 0 auto;
  padding: 0;
}

.form-header {
  margin-bottom: 20px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 25px;
}

/* 密码表单样式 */
.password-card .pw-card-header,
.security-tips-card .security-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.password-card .pw-card-header .title,
.security-tips-card .security-card-header .title {
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;
}

.password-form {
  padding: 10px 0;
}

.password-strength {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
  font-size: 14px;
}

.password-strength .el-progress {
  flex: 1;
}

.security-tips-card {
  height: 100%;
}

.security-tips {
  padding: 10px 0;
}

/* 收藏区域样式 */
.favorites-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-title h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color);
}

.favorites-container {
  margin-bottom: 30px;
}

.favorite-item {
  margin-bottom: 20px;
  transition: all var(--transition-time);
  height: 100%;
}

.favorite-item:hover {
  transform: translateY(-5px);
}

.favorite-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.favorite-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--primary-color);
}

.favorite-details {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.location-text {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
}

.view-details-btn {
  margin-top: 15px;
  width: 100%;
}

.empty-favorites {
  padding: 50px 0;
  background-color: white;
  border-radius: var(--border-radius);
  margin-top: 20px;
}

/* 响应式设计优化 */
@media (max-width: 768px) {
  .user-header {
    margin: 10px;
    padding: 20px 15px;
  }
  
  .page-title {
    font-size: 24px;
  }
  
  .main-tabs :deep(.el-tabs__item) {
    padding: 0 15px;
    font-size: 14px;
  }
  
  .favorites-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }
}

/* 动画效果 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>