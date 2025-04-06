import { defineStore } from 'pinia'
import axios from 'axios'
import { ref, computed } from 'vue'
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
    logout
  }
})
