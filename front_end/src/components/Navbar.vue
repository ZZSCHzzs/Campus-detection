<template>
  <div class="nav-container header">
    <el-menu :default-active="activeIndex" :ellipsis="false" class="el-menu-demo nav-container" mode="horizontal"
             @select="handleSelect">
      <div class="logo-container">
        <img
            alt="Logo"
            class="logo"
            src="/favicon256.ico"/>
        <span class="site-name">校园慧感</span>
      </div>
      <el-menu-item 
        v-for="item in content" 
        :key="item.index" 
        :index="item.index" 
        class="nav-item"
        v-show="!item.adminOnly || isAdmin"
      >
        <el-icon v-if="item.icon" :size="18" class="nav-icon">
          <component :is="getIconComponent(item.icon)"></component>
        </el-icon>
        <div class="nav-text">{{ item.title }}</div>
      </el-menu-item>


      <div class="flex-grow"></div>


      <div v-if="authStore.isAuthenticated" class="user-area">
        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-info" :class="{ 'user-info-active': isProfileRoute }">
            <el-avatar :icon="UserFilled" :size="32" class="user-avatar" :class="{ 'avatar-active': isProfileRoute }"></el-avatar>
            <span class="username">{{ authStore.username }}</span>
            <el-icon>
              <ArrowDown/>
            </el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu class="custom-dropdown">
              <el-dropdown-item command="profile">
                <el-icon><UserFilled /></el-icon>个人信息
              </el-dropdown-item>
              <el-dropdown-item command="password">
                <el-icon><Lock /></el-icon>修改密码
              </el-dropdown-item>
              <el-dropdown-item command="favorites">
                <el-icon><Star /></el-icon>我的收藏
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>


      <div v-else class="auth-buttons">
        <el-button plain size="small" type="primary" class="login-btn" @click="navigateToLogin">登录</el-button>
        <el-button size="small" type="primary" class="register-btn" @click="navigateToRegister">注册</el-button>
      </div>
    </el-menu>
  </div>
</template>

<script lang="ts" setup>
import {ref, onMounted, watch, computed} from 'vue'
import router from '../router'
import {useRoute} from 'vue-router'
import {useAuthStore} from '../stores/auth'
import {UserFilled, ArrowDown, HomeFilled, Menu as MenuIcon, DataLine, SwitchButton, Operation, Lock, Star, Bell} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from 'element-plus'

const authStore = useAuthStore()
const route = useRoute()

onMounted(async () => {
  updateActiveIndex()

  if (authStore.isAuthenticated && (!authStore.user || !authStore.user.username)) {
    try {
      await authStore.getCurrentUser()
    } catch (error) {
      console.error('获取用户信息失败:', error)
    }
  }
})

const isAdmin = computed(() => {
  return authStore.user?.role === 'admin'
})

const content = ref([
  {
    index: '0',
    title: '首页',
    path: '/index',
    icon: 'HomeFilled'
  },
  {
    index: '1',
    title: '区域',
    path: '/areas',
    icon: 'Menu'
  },
  {
    index: '2',
    title: '数据大屏',
    path: '/screen',
    icon: 'DataLine'
  },
  {
    index: '3',
    title: '告警与通知',
    path: '/alerts',
    icon: 'Bell'
  },
  {
    index: '4',
    title: '管理面板',
    path: '/admin',
    icon: 'Operation',
    adminOnly: true  
  }
])

const getIconComponent = (iconName: string) => {
  const iconMap = {
    'HomeFilled': HomeFilled,
    'Menu': MenuIcon,
    'DataLine': DataLine,
    'Bell': Bell,
    'Operation': Operation
  }
  return iconMap[iconName] || HomeFilled
}

const routePathMap = {
  '0': '/index',
  '1': '/areas',
  '2': '/screen',
  '3': '/alerts',
  '4': '/admin'
}

const activeIndex = ref('0')

const isProfileRoute = computed(() => {
  return route.path.includes('/profile')
})

const updateActiveIndex = () => {
  const currentPath = route.path

  
  if (currentPath.includes('/profile')) {
    activeIndex.value = ''
    return
  }
  
  if (currentPath === '/' || currentPath === '/index') {
    activeIndex.value = '0' 
    return
  }

  for (const [index, path] of Object.entries(routePathMap)) {
    if (currentPath.startsWith(path)) {
      activeIndex.value = index
      return
    }
  }
}

onMounted(() => {
  updateActiveIndex()
})

watch(() => route.path, () => {
  updateActiveIndex()
}, { immediate: true })

const handleSelect = (key: string) => {
  console.log('Menu item selected:', key)

  const path = routePathMap[key]
  if (path) {
    console.log('Navigating to:', path)
    router.push(path)
    
  } else {
    console.warn('No path found for key:', key)
  }
}

const navigateToLogin = () => {
  router.push('/login')
}

const navigateToRegister = () => {
  router.push('/register')
}

const handleCommand = (command: string) => {
  switch (command) {
    case 'profile':
      router.push({ path: '/profile', query: { tab: 'profile' } })
      break
    case 'password':
      router.push({ path: '/profile', query: { tab: 'password' } })
      break
    case 'favorites':
      router.push({ path: '/profile', query: { tab: 'favorites' } })
      break
    case 'logout':
      ElMessageBox.confirm(
          '确定要退出登录吗?',
          '提示',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning',
            center: true,
            customClass: 'logout-confirm-box'
          }
      )
          .then(async () => {
            try {
              
              authStore.logout()
              ElMessage({
                message: '成功退出登录',
                type: 'success',
                duration: 2000
              })
              
              await router.push('/')
            } catch (error) {
              console.error('退出失败:', error)
              ElMessage({
                message: '退出登录失败，请重试',
                type: 'error',
                duration: 2000
              })
            }
          })
          .catch(() => {
            ElMessage({
              message: '取消退出登录',
              type: 'info',
              duration: 2000
            })
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
  justify-content: center;
  border-radius: 4px;
  background-color: #ffffff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0);
}

.el-menu-demo {
  border-bottom: 0 !important;
}

.header {
  border-bottom: 2px solid #eef1ff;
  width: 100%;
  padding: 4px 0;
  position: sticky;
  top: 0;
  z-index: 1000;
  transition: all 0.3s ease;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.site-name {
  font-size: 18px;
  font-weight: bold;
  color: #409EFF;
  margin-left: 8px;
  letter-spacing: 1px;
}

.nav-item {
  position: relative;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}

.nav-icon {
  margin-right: 4px;
}

.nav-item:hover .nav-icon{
  transform: scale(1.1);
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)!important;

}
.nav-item:hover .nav-text {
  transform: scale(1.05);
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)!important;

}

.nav-item:hover {
  transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275)!important;
}
.nav-item::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 3px;
  background-color: #409EFF;
  transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275)!important;

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
  transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275)!important;

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
  box-shadow: 0 0 8px rgba(64, 158, 255, 0.6);
}

.logo-container {
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.logo {
  height: 40px;
  margin-right: 5px;
  transition: transform 0.3s ease;
}

.logo:hover {
  transform: scale(1.4) rotate(5deg);
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
  background-color: transparent !important;
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
  padding: 4px 12px;
  border-radius: 20px;
  transition: all 0.3s ease;
  background-color: #f9f9f9;
  border: 1px solid transparent;
}

/* 个人中心页面激活状态 */
.user-info-active {
  background-color: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);
  box-shadow: 0 0 8px rgba(64, 158, 255, 0.3);
}

.user-avatar {
  transition: transform 0.3s ease;
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

/* 头像激活状态 */
.avatar-active {
  border: 2px solid var(--el-color-primary);
  transform: scale(1.05);
}

.user-info:hover .user-avatar {
  transform: scale(1.05);
}

.username {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  margin: 0 4px;
}

/* 下拉菜单样式 */
.custom-dropdown .el-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
}

.custom-dropdown .el-dropdown-item i {
  font-size: 16px;
}

/* 登出确认框样式 */
.logout-confirm-box {
  border-radius: 8px;
  overflow: hidden;
}

.login-btn {
  transition: all 0.3s ease;
  border: 1px solid #409EFF;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
  background-color: rgba(64, 158, 255, 0.1);
}

.register-btn {
  transition: all 0.3s ease;
}

.register-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}
</style>
