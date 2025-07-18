<template>
  <div class="nav-container header" :class="{'mobile-header': isMobile}">
    <div v-if="isMobile" class="mobile-nav-container">

      <div class="mobile-header-row">

        <el-button class="hamburger-btn" @click="toggleMobileMenu">
          <el-icon size="20"><Menu /></el-icon>
        </el-button>

        <div class="logo-container">
          <img alt="Logo" class="logo" src="/favicon256.ico"/>
          <span class="site-name">校园慧感</span>
        </div>

        <div v-if="authStore.isAuthenticated" class="mobile-user-button">
          <el-avatar 
            :icon="UserFilled" 
            :size="32" 
            class="user-avatar"
            @click="navigateToProfile"
          ></el-avatar>
        </div>
        <div v-else class="mobile-auth-button">
          <el-button circle size="small" type="primary" @click="navigateToLogin">
            <el-icon><UserFilled /></el-icon>
          </el-button>
        </div>
      </div>

      <div v-show="mobileMenuVisible" class="mobile-menu-overlay" @click="closeMobileMenu"></div>
      <div 
        class="mobile-side-menu" 
        :class="{'mobile-menu-open': mobileMenuVisible}"
      >

        <div class="side-menu-header">
          <div class="logo-container">
            <img alt="Logo" class="logo" src="/favicon256.ico"/>
            <span class="site-name">校园慧感</span>
          </div>
          <el-button class="close-menu-btn" @click="closeMobileMenu">
            <el-icon size="20"><Close /></el-icon>
          </el-button>
        </div>

        <el-menu 
          :default-active="activeIndex" 
          mode="vertical" 
          class="mobile-el-menu" 
          @select="handleSelect"
        >
          <el-menu-item 
            v-for="item in content" 
            :key="item.index" 
            :index="item.index" 
            class="nav-item"
            v-show="(!item.adminOnly || isAdmin) && !item.hideOnMobile"
          >
            <el-icon v-if="item.icon" :size="18" class="nav-icon">
              <component :is="getIconComponent(item.icon)"></component>
            </el-icon>
            <div class="nav-text">{{ item.title }}</div>
          </el-menu-item>
        </el-menu>

        <div v-if="authStore.isAuthenticated" class="mobile-user-area">
          <div class="user-info">
            <el-avatar :icon="UserFilled" :size="32" class="user-avatar"></el-avatar>
            <span class="username">{{ authStore.username }}</span>
          </div>
          
          <div class="user-menu-items">
            <div class="user-menu-item" @click="goToProfile('profile')">
              <el-icon><UserFilled /></el-icon>
              <span>个人信息</span>
            </div>
            <div class="user-menu-item" @click="goToProfile('password')">
              <el-icon><Lock /></el-icon>
              <span>修改密码</span>
            </div>
            <div class="user-menu-item" @click="goToProfile('favorites')">
              <el-icon><Star /></el-icon>
              <span>我的收藏</span>
            </div>
            <div class="user-menu-item logout-item" @click="confirmLogout">
              <el-icon><SwitchButton /></el-icon>
              <span>退出登录</span>
            </div>
          </div>
        </div>
        
        <div v-else class="mobile-auth-buttons">
          <el-button plain size="small" type="primary" class="login-btn" @click="navigateToLogin">登录</el-button>
          <el-button size="small" type="primary" class="register-btn" @click="navigateToRegister">注册</el-button>
        </div>

        <div class="github-link-mobile">
          <a href="https://github.com/ZZSCHzzs/Campus-detection" target="_blank" class="github-btn-mobile">
            <img src="/github_favicon.svg" alt="GitHub" class="github-icon" />
            <span>GitHub 代码仓库</span>
          </a>
        </div>
      </div>
    </div>

    <el-menu v-else :default-active="activeIndex" :ellipsis="false" class="el-menu-demo nav-container" mode="horizontal"
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

      <div class="github-button-container">
        <a href="https://github.com/ZZSCHzzs/Campus-detection" target="_blank" class="github-btn">
          <img src="/github_favicon.svg" alt="GitHub" class="github-icon" />
        </a>
      </div>

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
import {
  UserFilled, ArrowDown, HomeFilled, Menu as MenuIcon, DataLine,
  SwitchButton, Operation, Lock, Star, Bell, Menu, Close
} from '@element-plus/icons-vue'
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
    icon: 'Menu',
    hideOnMobile: false,
  },
  {
    index: '2',
    title: '数据大屏',
    path: '/screen',
    icon: 'DataLine',
    hideOnMobile: true
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
  ,
  {
    index: '5',
    title: '终端管理',
    path: '/terminal',
    icon: 'DataLine',
    adminOnly: true,
    hideOnMobile: true
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
  '4': '/admin',
  '5': '/terminal'
}

const activeIndex = ref('0')

const isProfileRoute = computed(() => {
  return route.path.includes('/profile')
})

const updateActiveIndex = () => {
  const currentPath = route.path

  if (currentPath.includes('/login') || currentPath.includes('/register')) {
    activeIndex.value = ''
    return
  }

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
    mobileMenuVisible.value = false
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
              mobileMenuVisible.value = false
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

const isMobile = ref(false)
const mobileMenuVisible = ref(false)

const checkScreenSize = () => {
  isMobile.value = window.innerWidth < 992
  if (!isMobile.value) {
    mobileMenuVisible.value = false
  }
}

const toggleMobileMenu = () => {
  mobileMenuVisible.value = !mobileMenuVisible.value
}

const goToProfile = (tab: string) => {
  router.push({ path: '/profile', query: { tab } })
  mobileMenuVisible.value = false
}

const confirmLogout = () => {
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
  ).then(async () => {
    try {
      authStore.logout()
      ElMessage({
        message: '成功退出登录',
        type: 'success',
        duration: 2000
      })
      mobileMenuVisible.value = false
      await router.push('/')
    } catch (error) {
      console.error('退出失败:', error)
      ElMessage({
        message: '退出登录失败，请重试',
        type: 'error',
        duration: 2000
      })
    }
  }).catch(() => {
    ElMessage({
      message: '取消退出登录',
      type: 'info',
      duration: 2000
    })
  })
}

const closeMobileMenu = () => {
  mobileMenuVisible.value = false
}

const navigateToProfile = () => {
  router.push({ path: '/profile', query: { tab: 'profile' } })
}

onMounted(() => {
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)
})
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

.el-menu--horizontal > .el-menu-item.is-active {
  border-bottom: none !important;
  background-color: transparent !important;
}

.el-menu--horizontal > .el-menu-item:not(.is-disabled):hover {
  background-color: transparent !important;
  border-bottom: none !important;
}

.nav-container .el-menu-item.is-active {
  color: #409EFF !important;
  font-weight: 700;
  border-bottom: none !important;
}

.el-menu--horizontal > .el-menu-item {
  border-bottom: none !important;
}

.flex-grow {
  flex-grow: 1;
}

.auth-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
}

.auth-buttons .el-button {
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.login-btn {
  transition: all 0.3s ease;
  border: 1px solid #409EFF;
  background-color: white;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
  background-color: rgba(64, 158, 255, 0.1);
}

.register-btn {
  transition: all 0.3s ease;
  background: linear-gradient(45deg, #409EFF, #66b1ff);
}

.register-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
  background: linear-gradient(45deg, #3a8ee6, #53a8ff);
}

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
  padding: 6px 16px;
  border-radius: 24px;
  transition: all 0.3s ease;
  background-color: #f9f9f9;
  border: 1px solid transparent;
}

.user-info-active {
  background-color: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.2);
}

.user-avatar {
  transition: transform 0.3s ease;
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.avatar-active {
  border: 2px solid var(--el-color-primary);
  transform: scale(1.05);
}

.user-info:hover {
  background-color: var(--el-color-primary-light-9);
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

.custom-dropdown .el-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
}

.custom-dropdown .el-dropdown-item i {
  font-size: 16px;
}

.logout-confirm-box {
  border-radius: 8px;
  overflow: hidden;
}

.mobile-header {
  width: 100%;
  padding: 0;
}

.mobile-nav-container {
  width: 100%;
  background-color: #fff;
}

.mobile-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid #eef1ff;
  position: relative;
}

.hamburger-btn {
  border: none;
  background: transparent;
  padding: 8px;
  cursor: pointer;
  position: relative;
  z-index: 2;
}

.close-menu-btn {
  border: none;
  background: transparent;
  padding: 8px;
  cursor: pointer;
}

.mobile-user-button {
  cursor: pointer;
}

.mobile-user-button .user-avatar {
  transition: all 0.3s ease;
  border: 2px solid white;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.mobile-user-button .user-avatar:hover {
  transform: scale(1.05);
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.15);
}

.mobile-auth-button {
  display: flex;
  align-items: center;
}

.mobile-menu-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  z-index: 1000;
  transition: opacity 0.3s ease;
}

.mobile-side-menu {
  position: fixed;
  top: 0;
  left: -280px;
  height: 100%;
  width: 260px;
  background: white;
  z-index: 1001;
  transition: left 0.3s ease;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.mobile-menu-open {
  left: 0;
}

.side-menu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px;
  border-bottom: 1px solid #eef1ff;
}

.mobile-el-menu {
  border-right: none;
  flex: 1;
}

.mobile-el-menu .el-menu-item {
  height: 50px;
  line-height: 50px;
}

.mobile-user-area {
  padding: 15px;
  border-top: 1px solid #eaeaea;
}

.mobile-user-area .user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
  padding: 10px;
  border-radius: 8px;
  background-color: #f0f7ff;
}

.user-menu-items {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.user-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 4px;
}

.user-menu-item:hover {
  background-color: #f0f7ff;
}

.user-menu-item .el-icon {
  font-size: 16px;
  color: #409EFF;
}

.logout-item {
  color: #F56C6C;
}

.logout-item .el-icon {
  color: #F56C6C;
}

.mobile-auth-buttons {
  display: flex;
  padding: 15px;
  gap: 12px;
  justify-content: center;
  border-top: 1px solid #eaeaea;
}

.mobile-auth-buttons .el-button {
  flex: 1;
  padding: 10px;
  border-radius: 20px;
}

.mobile-el-menu .el-menu-item.is-active {
  color: #409EFF !important;
  font-weight: 700;
}

.mobile-el-menu .el-menu-item.is-active::after {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background-color: #409EFF;
  box-shadow: 0 0 8px rgba(64, 158, 255, 0.6);
}

@media (max-width: 992px) {
  .nav-container {
    width: 100%;
  }
  
  .logo {
    height: 30px;
  }
  
  .site-name {
    font-size: 16px;
  }
  
  .mobile-menu .nav-item {
    height: 50px;
    line-height: 50px;
  }
  
  .mobile-menu .nav-item::after {
    display: none;
  }
  
  .mobile-menu .el-menu-item.is-active::after {
    content: '';
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 3px;
    height: 20px;
    background-color: #409EFF;
    box-shadow: 0 0 8px rgba(64, 158, 255, 0.6);
  }
}

/* 添加外部链接图标样式 */
.external-link-icon {
  margin-left: 4px;
  font-size: 12px;
  opacity: 0.7;
}

.nav-item:hover .external-link-icon {
  opacity: 1;
}

/* GitHub按钮样式 */
.github-button-container {
  display: flex;
  align-items: center;
  margin-right: 10px;
}

.github-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: #f5f7fa;
  transition: all 0.3s ease;
}

.github-btn:hover {
  background-color: #ecf5ff;
  transform: translateY(-3px) rotate(5deg);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.github-icon {
  width: 20px;
  height: 20px;
}

/* 移动版GitHub链接样式 */
.github-link-mobile {
  padding: 15px;
  border-top: 1px solid #eaeaea;
}

.github-btn-mobile {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 8px;
  background-color: #f5f7fa;
  text-decoration: none;
  color: #606266;
  transition: all 0.2s ease;
}

.github-btn-mobile:hover {
  background-color: #ecf5ff;
}
</style>
