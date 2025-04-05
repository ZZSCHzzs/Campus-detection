<template>
  <div class="header">
    <el-menu :default-active="activeIndex" class="el-menu-demo nav-container" mode="horizontal" :ellipsis="false"
      @select="handleSelect">
      <div class="logo-container">
        <img
          class="logo"
          src="/favicon256.ico"
          alt="Logo" />
      </div>
      <el-menu-item v-for="item in content" :key="item.index" :index="item.index" class="nav-item">
        {{ item.title }}
      </el-menu-item>
      
      <!-- 添加弹性空间，将后续元素推到右侧 -->
      <div class="flex-grow"></div>
      
      <!-- 根据登录状态显示不同内容 -->
      <div v-if="authStore.isAuthenticated" class="user-area">
        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-info">
            <el-avatar :size="32" :icon="UserFilled"></el-avatar>
            <span class="username">{{ authStore.username }}</span>
            <el-icon><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人中心</el-dropdown-item>
              <el-dropdown-item command="settings">账户设置</el-dropdown-item>
              <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      
      <!-- 未登录时显示登录和注册按钮 -->
      <div v-else class="auth-buttons">
        <el-button type="primary" plain size="small" @click="navigateToLogin">登录</el-button>
        <el-button type="primary" size="small" @click="navigateToRegister">注册</el-button>
      </div>
    </el-menu>
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import router from '../router'
import { useAuthStore } from '../stores/auth'
import { UserFilled, ArrowDown } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 获取认证store
const authStore = useAuthStore()

const content = ref([
  {
    index: '0',
    title: '首页',
    path: '/index',
  },
  {
    index: '1',
    title: '区域',
    path: '/areas',
  },
  {
    index: '2',
    title: '数据大屏',
    path: '/screen',
  },
])

const activeIndex = ref('0')
const handleSelect = (key: string) => {
  activeIndex.value = key
  router.push(content.value.find(item => item.index === key)?.path || '/')
}

// 导航到登录页面
const navigateToLogin = () => {
  router.push({ path: '/auth', query: { mode: 'login' } })
}

// 导航到注册页面
const navigateToRegister = () => {
  router.push({ path: '/auth', query: { mode: 'register' } })
}

// 处理下拉菜单命令
const handleCommand = (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      ElMessageBox.confirm(
        '确定要退出登录吗?',
        '提示',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        }
      )
        .then(() => {
          authStore.logout()
          ElMessage.success('已成功退出登录')
          router.push('/')
        })
        .catch(() => {
          // 取消退出
        })
      break
  }
}
</script>

<style>
.nav-container {
  display: flex;
  width: 1400px;
  margin: 0 auto;
  border-radius: 4px;
  background-color: #ffffff;
}

.el-menu-demo {
  border-bottom: 0px !important;
}

.header {
  border-bottom: 2px solid #eef1ff;
  width: 100%;
  padding: 4px 0;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.nav-item {
  position: relative;
  transition: all 0.3s ease;
  font-weight: 500;
}

.nav-item:hover {
  background-color: #f0f2ff !important;
  color: #409EFF;
}

.nav-item:hover::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 30px;
  height: 3px;
  background-color: #409EFF;
  transition: width 0.3s ease;
}

.el-menu-item.is-active {
  color: #409EFF !important;
  font-weight: 700;
}

.el-menu-item.is-active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 3px;
  background-color: #409EFF;
}

.logo-container {
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.logo {
  height: 40px;
  margin-right: 15px;
  transition: transform 0.3s ease;
}

.logo:hover {
  transform: scale(1.1);
}

el-menu-item {
  text-decoration: none !important;
}

/* 覆盖 Element Plus 默认活跃状态样式 */
.el-menu--horizontal > .el-menu-item.is-active {
  border-bottom: none !important;
  background-color: transparent !important;
}

/* 覆盖默认悬停效果 */
.el-menu--horizontal > .el-menu-item:not(.is-disabled):hover {
  background-color: #f0f2ff !important;
  border-bottom: none !important;
}

/* 确保自定义活跃样式优先级更高 */
.nav-container .el-menu-item.is-active {
  color: #409EFF !important;
  font-weight: 700;
  border-bottom: none !important;
}

/* 确保菜单项之间的分隔线不显示 */
.el-menu--horizontal > .el-menu-item {
  border-bottom: none !important;
}

/* 添加的新样式 */
.flex-grow {
  flex-grow: 1;
}

.auth-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
}

/* 为按钮添加悬停效果 */
.auth-buttons .el-button:hover {
  transform: translateY(-2px);
  transition: transform 0.3s ease;
}

/* 用户信息区域样式 */
.user-area {
  display: flex;
  align-items: center;
  padding: 0 20px;
  cursor: pointer;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.user-info:hover {
  background-color: var(--el-color-primary-light-9);
}

.username {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  margin: 0 4px;
}
</style>
