<script lang="ts" setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, Edit, Star } from '@element-plus/icons-vue'
import authApi from '../services/authApi'
import { areaService, userService } from '../services/apiService'  // 只保留areaService
import type { User as UserType, AreaItem } from '../types'
import CryptoJS from 'crypto-js'  // 导入CryptoJS库用于密码加密
import { Calendar, Check, InfoFilled, Phone, Plus, Grid, List } from '@element-plus/icons-vue'
import AreaCard from '../components/AreaCard.vue'

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
    userInfo.value = await userService.getUserInfo()
  } catch (error) {
    console.error('获取用户信息失败:', error)

    if (error.response?.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      // 如果是401错误，自动重定向到登录页
      authStore.logout()
      await router.push({
        path: '/auth',
        query: {mode: 'login', redirect: '/profile'}
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
        // 创建更新数据对象
        const updateData = {
          email: userForm.value.email,
          phone: userForm.value.phone
        }

        // 使用统一的authApi更新用户信息
        await authApi.updateUserInfo(updateData)

        // 更新本地显示的信息
        userInfo.value.email = userForm.value.email
        userInfo.value.phone = userForm.value.phone

        // 更新store中的信息
        if (authStore.user) {
          authStore.user = { ...authStore.user, ...updateData }
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

        // 使用统一的authApi更新密码
        await authApi.updatePassword({
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

// 收藏区域数据
const favoriteAreas = ref<AreaItem[]>([])
const loadingFavorites = ref(false)

// 获取收藏区域
const fetchFavoriteAreas = async () => {
  loadingFavorites.value = true
  try {
    favoriteAreas.value = await areaService.getFavoriteAreas()
  } catch (error) {
    console.error('获取收藏区域失败:', error)
    ElMessage.error('获取收藏区域失败')
  } finally {
    loadingFavorites.value = false
  }
}

// 处理收藏状态变化
const handleFavoriteChange = async (event) => {
  const { areaId, isFavorite } = event

  // 更新本地收藏列表
  if (!isFavorite) {
    // 从列表中移除
    favoriteAreas.value = favoriteAreas.value.filter(area => area.id !== areaId)

    ElMessage.success('已取消收藏')
  } else {
    // 添加到列表中 - 理论上在收藏页面不会有这种情况，但为了完整性考虑
    ElMessage.success('已添加到收藏')

    // 刷新用户信息，获取最新收藏列表
    await fetchUserInfo()
  }
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

// 添加布局切换状态 - 默认跟随页面整体状态
const isCompactView = ref(false)

// 检查设备类型并设置默认布局
const checkScreenSize = () => {
  const isMobile = window.innerWidth < 768
  // 移动端默认使用紧凑视图
  isCompactView.value = isMobile
}

const toggleLayoutMode = () => {
  isCompactView.value = !isCompactView.value
}

onMounted(async () => {
  console.log('UserView组件已挂载，准备获取用户信息')
  
  // 检查设备类型并设置默认布局
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)
  
  // 检查登录状态
  if (!authStore.isAuthenticated) {
    ElMessage.warning('请先登录')
    await router.push({
      path: '/auth',
      query: {mode: 'login', redirect: '/profile'}
    })
    return
  }

  await fetchUserInfo()
  await fetchFavoriteAreas()

})

// 格式化日期时间显示
const formatDateTime = (dateTimeStr) => {
  if (!dateTimeStr) return '未知';

  try {
    const date = new Date(dateTimeStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).replace(/\//g, '-');
  } catch (e) {
    return dateTimeStr;
  }
}

// 获取角色显示名称
const getRoleDisplayName = (role: string) => {
  switch (role) {
    case 'admin':
      return '管理员';
    case 'staff':
      return '工作人员';
    case 'user':
    default:
      return '普通用户';
  }
}

// 获取角色对应的标签类型
const getRoleTagType = (role: string) => {
  switch (role) {
    case 'admin':
      return 'danger';
    case 'staff':
      return 'warning';
    case 'user':
    default:
      return 'primary';
  }
}
</script>

<template>
  <div class="user-center-container">

    <div class="user-header">
      <div class="user-header-content">
        <div class="user-info-brief">
          <div class="user-header-text">
            <h1 class="page-title">{{ userInfo.username }}</h1>
            <div class="user-meta">
              <el-tag :type="getRoleTagType(userInfo.role)" class="role-tag" effect="plain">
                {{ getRoleDisplayName(userInfo.role) }}
              </el-tag>
              <span class="join-date">注册于 {{
                userInfo.register_time &&
                userInfo.register_time.split('T')[0]
              }}</span>
            </div>
          </div>
        </div>
        <div class="user-stats">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-statistic :value="favoriteAreas.length" title="收藏区域">
                <template #prefix>
                  <el-icon class="stat-icon">
                    <Star />
                  </el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="最近登录" value="今天">
                <template #prefix>
                  <el-icon class="stat-icon">
                    <Calendar />
                  </el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="8">
              <el-statistic title="账户状态" value="正常">
                <template #prefix>
                  <el-icon class="stat-icon">
                    <Check />
                  </el-icon>
                </template>
              </el-statistic>
            </el-col>
          </el-row>
        </div>
      </div>
    </div>

    <div class="tabs-container">
      <el-tabs v-model="activeTab" class="main-tabs" @tab-change="handleTabChange">
        <el-tab-pane label="个人信息" name="profile">
          <div class="tab-content">
            <el-card v-loading="loading" :shadow="false" class="profile-card content-card">

              <div class="section-header">
                <div class="section-title">
                  <el-icon :size="22" color="#409EFF">
                    <User />
                  </el-icon>
                  <h2>个人资料</h2>
                </div>
                <el-button v-if="!isEditing" :icon="Edit" text type="primary" @click="enableEdit">
                  编辑资料
                </el-button>
              </div>

              <div v-if="!isEditing" class="info-display">
                <el-descriptions :column="1" border class="custom-descriptions">
                  <el-descriptions-item content-class-name="custom-content" label="用户名" label-class-name="custom-label">
                    <el-tag size="small">{{ userInfo.username }}</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item content-class-name="custom-content" label="邮箱" label-class-name="custom-label">
                    <span v-if="userInfo.email && userInfo.email.trim() !== ''">{{
                      userInfo.email
                    }}</span>
                    <el-tag v-else size="small" type="warning">未设置</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item content-class-name="custom-content" label="电话" label-class-name="custom-label">
                    <span v-if="userInfo.phone && userInfo.phone.trim() !== ''">{{
                      userInfo.phone
                    }}</span>
                    <el-tag v-else size="small" type="warning">未设置
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item content-class-name="custom-content" label="注册时间"
                    label-class-name="custom-label">
                    {{ formatDateTime(userInfo.register_time) }}
                  </el-descriptions-item>
                </el-descriptions>
              </div>

              <el-form v-else ref="profileFormRef" :model="userForm" :rules="profileRules" class="edit-form"
                label-position="top">
                <div class="form-header">
                  <el-alert :closable="false" class="form-alert" show-icon title="请完善您的个人信息" type="info">
                    <template #default>
                      更新您的个人信息有助于我们提供更好的服务
                    </template>
                  </el-alert>
                </div>

                <div class="form-body">
                  <el-form-item class="custom-form-item" label="用户名">
                    <el-input v-model="userInfo.username" class="custom-input disabled-input" disabled
                      placeholder="用户名不可修改">
                      <template #prefix>
                        <el-icon class="input-icon">
                          <User />
                        </el-icon>
                      </template>
                      <template #suffix>
                        <el-tooltip content="用户名创建后不可修改" placement="top">
                          <el-icon class="info-icon">
                            <InfoFilled />
                          </el-icon>
                        </el-tooltip>
                      </template>
                    </el-input>
                  </el-form-item>

                  <el-form-item class="custom-form-item" label="邮箱" prop="email">
                    <el-input v-model="userForm.email" class="custom-input" placeholder="请输入邮箱地址">
                      <template #prefix>
                        <el-icon class="input-icon">
                          <Message />
                        </el-icon>
                      </template>
                    </el-input>
                    <div class="field-hint">用于接收重要通知和找回密码</div>
                  </el-form-item>

                  <el-form-item class="custom-form-item" label="电话" prop="phone">
                    <el-input v-model="userForm.phone" class="custom-input" placeholder="请输入电话号码">
                      <template #prefix>
                        <el-icon class="input-icon">
                          <Phone />
                        </el-icon>
                      </template>
                    </el-input>
                    <div class="field-hint">用于接收紧急信息通知</div>
                  </el-form-item>
                </div>

                <div class="form-actions">
                  <el-button class="cancel-btn" plain @click="cancelEdit">取消</el-button>
                  <el-button :loading="loading" class="submit-btn" type="primary" @click="submitUserUpdate">
                    <el-icon>
                      <Check />
                    </el-icon>
                    <span>保存修改</span>
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
                <el-card :shadow="false" class="password-card content-card">
                  <template #header>
                    <div class="pw-card-header">
                      <span class="title">
                        <el-icon :size="20">
                          <Lock />
                        </el-icon>
                        密码管理
                      </span>
                    </div>
                  </template>

                  <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" class="password-form"
                    label-position="top" status-icon>
                    <el-alert :closable="false" class="mb-4" show-icon type="warning">
                      <template #title>
                        为保障账户安全，建议定期更换密码
                      </template>
                      <template #default>
                        请使用包含大小写字母、数字和特殊符号的强密码
                      </template>
                    </el-alert>

                    <el-form-item label="当前密码" prop="current_password">
                      <el-input v-model="passwordForm.current_password" placeholder="请输入当前密码" show-password
                        type="password">
                        <template #prefix>
                          <el-icon>
                            <Lock />
                          </el-icon>
                        </template>
                      </el-input>
                    </el-form-item>

                    <el-form-item label="新密码" prop="new_password">
                      <el-input v-model="passwordForm.new_password" placeholder="请输入新密码" show-password type="password"
                        @input="updatePasswordStrength">
                        <template #prefix>
                          <el-icon>
                            <Lock />
                          </el-icon>
                        </template>
                      </el-input>
                      <div v-if="passwordForm.new_password" class="password-strength">
                        <span>密码强度:</span>
                        <el-progress :percentage="passwordStrength" :status="passwordStrengthStatus" :stroke-width="8"
                          :text-inside="true"></el-progress>
                      </div>
                    </el-form-item>

                    <el-form-item label="确认新密码" prop="re_new_password">
                      <el-input v-model="passwordForm.re_new_password" placeholder="请再次输入新密码" show-password
                        type="password">
                        <template #prefix>
                          <el-icon>
                            <Lock />
                          </el-icon>
                        </template>
                      </el-input>
                    </el-form-item>

                    <div class="form-actions">
                      <el-button :loading="loading" class="full-width-btn" type="primary" @click="submitPasswordUpdate">
                        <el-icon>
                          <Check />
                        </el-icon>
                        确认修改密码
                      </el-button>
                    </div>
                  </el-form>
                </el-card>
              </el-col>

              <el-col :md="10" :sm="24" :xs="24">
                <el-card :shadow="false" class="security-tips-card">
                  <template #header>
                    <div class="security-card-header">
                      <span class="title">
                        <el-icon :size="20">
                          <InfoFilled />
                        </el-icon>
                        安全提示
                      </span>
                    </div>
                  </template>

                  <div class="security-tips">
                    <el-timeline>
                      <el-timeline-item icon="Warning" size="large" timestamp="重要提示" type="primary">
                        密码是您账户的唯一防线，请妥善保管
                      </el-timeline-item>
                      <el-timeline-item icon="Check" type="success">
                        建议使用至少8位以上的密码
                      </el-timeline-item>
                      <el-timeline-item icon="Check" type="success">
                        包含大小写字母、数字和特殊字符
                      </el-timeline-item>
                      <el-timeline-item icon="Check" type="success">
                        避免使用生日、手机号等个人信息
                      </el-timeline-item>
                      <el-timeline-item icon="InfoFilled" type="warning">
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
                <el-icon :size="22" color="#409EFF">
                  <Star />
                </el-icon>
                <h2>我收藏的区域</h2>
              </div>
              
              <div class="header-actions">
                <!-- 添加布局切换按钮 -->
                <el-button 
                  class="toggle-view-btn"
                  plain
                  @click="toggleLayoutMode"
                >
                  <el-icon class="toggle-icon"><component :is="isCompactView ? Grid : List" /></el-icon>
                  {{ isCompactView ? '卡片视图' : '紧凑视图' }}
                </el-button>
                
                <el-button type="primary" @click="router.push('/areas')">
                  <el-icon>
                    <Plus />
                  </el-icon>
                  <span>浏览所有区域</span>
                </el-button>
              </div>
            </div>

            <div v-if="favoriteAreas.length > 0" class="favorites-container">
              <el-skeleton v-if="loadingFavorites" :count="3" :loading="loadingFavorites" animated>
                <template #template>
                  <div style="padding: 14px;">
                    <el-skeleton-item style="width: 50%;" variant="h3" />
                    <div style="display: flex; align-items: center; margin-top: 16px; justify-content: space-between;">
                      <el-skeleton-item style="margin-right: 16px; width: 30%;" variant="text" />
                      <el-skeleton-item style="width: 30%;" variant="text" />
                    </div>
                  </div>
                </template>
              </el-skeleton>

              <el-row v-else :gutter="20">
                <el-col 
                  v-for="area in favoriteAreas" 
                  :key="area.id" 
                  :lg="isCompactView ? 6 : 8"
                  :md="isCompactView ? 6 : 8"
                  :sm="isCompactView ? 8 : 12"
                  :xs="isCompactView ? 12 : 24"
                  class="favorite-col"
                >
                  <AreaCard 
                    :area="area" 
                    :compact="isCompactView"
                    :isFavorite="true" 
                    @favorite-change="handleFavoriteChange" 
                  />
                </el-col>
              </el-row>
            </div>

            <el-empty v-else class="empty-favorites" description="您还没有收藏任何区域">
              <template #image>
                <el-icon :size="60" color="#909399">
                  <Star />
                </el-icon>
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
.mb-4 {
  margin-bottom: 16px;
}

.mt-3 {
  margin-top: 12px;
}

.full-width-btn {
  width: 100%;
}

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

/* 修复激活条样式 */
:deep(.el-tabs__active-bar) {
  height: 5px !important;
  bottom: -2px !important;
}

.tab-content {
  animation: fadeIn 0.3s ease;
}

/* 卡片共享样式 - 移除阴影 */
.content-card {
  margin-bottom: 25px;
  border-radius: var(--border-radius);
  transition: all var(--transition-time);
  overflow: hidden;
  border: 1px solid var(--border-color);
  padding: 20px;
  background-color: white;
}

.content-card:hover {
  border-color: #e0e6ed;
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

.custom-descriptions {
  width: 100%;
}

.custom-descriptions :deep(.el-descriptions__body) {
  background-color: #fcfcfc;
}

.custom-descriptions :deep(.el-descriptions__label) {
  width: 100px;
  font-weight: 600;
  color: #606266;
  background-color: #f5f7fa;
  text-align: right;
  padding-right: 15px;
}

.custom-descriptions :deep(.el-descriptions__content) {
  padding: 12px 15px;
}

.custom-descriptions :deep(.el-tag) {
  margin: 0;
}

/* 表单部分 */
.edit-form {
  max-width: 600px;
  margin: 0 auto;
  padding: 0;
  border-radius: var(--border-radius);
  background-color: white;
  transition: all 0.3s ease;
  overflow: hidden;
  animation: fadeIn 0.4s ease;
}

.form-header {
  margin-bottom: 25px;
}

.form-alert {
  border-left: 3px solid var(--primary-color);
}

.form-body {
  padding: 15px 20px 20px;
  background-color: #f9fbfe;
  border-radius: var(--border-radius);
  border: 1px solid #eef2f8;
}

.custom-form-item {
  margin-bottom: 24px;
}

.custom-form-item:last-child {
  margin-bottom: 10px;
}

.custom-form-item :deep(.el-form-item__label) {
  padding-bottom: 8px;
  font-weight: 600;
  color: #606266;
  font-size: 14px;
}

.custom-input {
  transition: all 0.3s;
}

.custom-input :deep(.el-input__wrapper) {
  padding: 1px 15px;
  border-radius: 6px;
  box-shadow: 0 0 0 1px #dcdfe6;
}

.custom-input:hover :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #b6c3da !important;
}

.custom-input:focus-within :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--primary-color) !important;
}

.disabled-input :deep(.el-input__wrapper) {
  background-color: #f5f7fa;
}

.input-icon {
  color: #909399;
  margin-right: 5px;
}

.info-icon {
  color: #909399;
  cursor: help;
}

.field-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  padding-left: 2px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 15px;
  margin-top: 30px;
}

.submit-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 10px 20px;
  font-weight: 500;
}

.cancel-btn {
  border-color: #dcdfe6;
}

.cancel-btn:hover {
  border-color: #c0c4cc;
  color: #606266;
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

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.toggle-view-btn {
  display: flex;
  align-items: center;
  gap: 5px;
}

.toggle-icon {
  margin-right: 2px;
}

.favorites-container {
  margin-bottom: 30px;
}

.favorite-item {
  margin-bottom: 20px;
  transition: all var(--transition-time);
  height: 100%;
  border: 1px solid var(--border-color);
}

.favorite-item:hover {
  transform: translateY(-5px);
  border-color: #e0e6ed;
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

.favorite-col {
  margin-bottom: 20px;
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
  
  .header-actions {
    width: 100%;
  }
  
  .toggle-view-btn,
  .header-actions .el-button {
    flex: 1;
  }
}

/* 动画效果 */
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
</style>