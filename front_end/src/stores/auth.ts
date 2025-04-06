import { defineStore } from 'pinia'
import axios from '../services/api'
import { ref, computed, onMounted } from 'vue'
import type { User } from '../types'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const accessToken = ref(localStorage.getItem('access') || '')
  const refreshToken = ref(localStorage.getItem('refresh') || '')
  const user = ref<User | null>(null)
  
  // 初始化时尝试从localStorage加载用户信息
  try {
    const storedUser = localStorage.getItem('user')
    if (storedUser) {
      user.value = JSON.parse(storedUser)
    }
  } catch (error) {
    console.error('加载用户信息失败:', error)
    localStorage.removeItem('user')
  }
  
  // 计算属性
  const isAuthenticated = computed(() => !!accessToken.value)
  const username = computed(() => user.value?.username || 'Unknown')
  
  // 监听自定义事件
  if (typeof window !== 'undefined') {
    // 监听token刷新事件
    window.addEventListener('auth:token-refreshed', ((event: CustomEvent) => {
      accessToken.value = event.detail.token
    }) as EventListener)
    
    // 监听登出事件
    window.addEventListener('auth:logout', () => {
      logout()
    })
  }
  
  // 获取当前用户信息
  const getCurrentUser = async () => {
    // 如果已经有用户信息且有效，直接返回
    if (user.value && user.value.username) {
      return user.value
    }
    
    // 如果有token但没有用户信息，尝试获取
    if (accessToken.value) {
      try {
        const response = await axios.get('/auth/users/me/')
        if (response.data) {
          setUser(response.data)
          return response.data
        }
      } catch (error) {
        console.error('获取用户信息失败:', error)
        // 如果获取失败，可能是token已失效
        const isValid = await verifyToken()
        if (!isValid) {
          logout()
        }
      }
    }
    return null
  }
  
  // 动作
  // 设置认证信息
  const setAuth = (authData: { access: string, refresh: string }) => {
    accessToken.value = authData.access
    refreshToken.value = authData.refresh
    localStorage.setItem('access', authData.access)
    localStorage.setItem('refresh', authData.refresh)
  }
  
  // 设置用户信息
  const setUser = (userData: any) => {
    console.log('设置用户信息:', userData) // 添加日志
    if (!userData || !userData.username) {
      console.error('用户数据无效或缺少用户名')
      return
    }
    user.value = userData
    localStorage.setItem('user', JSON.stringify(userData))
  }
  
  // 刷新token
  const refreshAccessToken = async () => {
    if (!refreshToken.value) return false
    try {
      const response = await axios.post('/auth/jwt/refresh/', {
        refresh: refreshToken.value
      })
      accessToken.value = response.data.access
      localStorage.setItem('access', response.data.access)
      return true
    } catch (error) {
      console.error('刷新Token失败:', error)
      return false
    }
  }
  
  // 验证token
  const verifyToken = async () => {
    if (!accessToken.value) return false
    try {
      await axios.post('/auth/jwt/verify/', {
        token: accessToken.value
      })
      return true
    } catch (error) {
      console.error('Token验证失败:', error)
      return false
    }
  }
  
  // 登出
  const logout = () => {
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    localStorage.removeItem('user')
  }
  
  // 登录后初始化
  const initializeAfterLogin = async () => {
    if (accessToken.value && !user.value) {
      await getCurrentUser()
    }
  }
  
  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    username,
    setAuth,
    setUser,
    refreshAccessToken,
    verifyToken,
    logout,
    getCurrentUser,
    initializeAfterLogin
  }
})
