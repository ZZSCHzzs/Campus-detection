import { defineStore } from 'pinia'
import axios from 'axios'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const accessToken = ref(localStorage.getItem('access') || '')
  const refreshToken = ref(localStorage.getItem('refresh') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  
  // 计算属性
  const isAuthenticated = computed(() => !!accessToken.value)
  const username = computed(() => user.value?.username || '')
  
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
