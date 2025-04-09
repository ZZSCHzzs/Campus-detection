import { defineStore } from 'pinia'
import authApi from '../services/authApi'
import { ref, computed, watch } from 'vue'
import type { User } from '../types'

export const useAuthStore = defineStore('auth', () => {
  // 状态变量
  const accessToken = ref(localStorage.getItem('access') || '')
  const refreshToken = ref(localStorage.getItem('refresh') || '')
  const user = ref<User | null>(null)
  const isLoggingOut = ref(false)
  const isLoading = ref(false)
  
  // 初始化时从localStorage加载用户信息
  try {
    const storedUser = localStorage.getItem('user')
    if (storedUser) {
      user.value = JSON.parse(storedUser)
      console.log('[AUTH-STORE] 从localStorage加载用户信息')
    }
  } catch (error) {
    console.error('[AUTH-STORE] 加载用户信息失败:', error)
    localStorage.removeItem('user')
  }
  
  // 计算属性
  const isAuthenticated = computed(() => !!accessToken.value && accessToken.value.length > 10)
  const username = computed(() => user.value?.username || '未登录')
  
  // 监听token变化，保持同步
  watch(accessToken, (newToken) => {
    if (newToken) {
      localStorage.setItem('access', newToken)
      console.log('[AUTH-STORE] 更新access token')
    } else {
      localStorage.removeItem('access')
    }
  })
  
  watch(refreshToken, (newToken) => {
    if (newToken) {
      localStorage.setItem('refresh', newToken)
      console.log('[AUTH-STORE] 更新refresh token')
    } else {
      localStorage.removeItem('refresh')
    }
  })
  
  // 设置认证信息
  const setAuth = (authData: { access: string, refresh: string }) => {
    console.log('[AUTH-STORE] 设置认证信息')
    accessToken.value = authData.access
    refreshToken.value = authData.refresh
    
    // 立即同步到localStorage
    localStorage.setItem('access', authData.access)
    localStorage.setItem('refresh', authData.refresh)
  }
  
  // 设置用户信息
  const setUser = (userData: any) => {
    console.log('[AUTH-STORE] 设置用户信息:', userData)
    if (!userData || !userData.username) {
      console.error('[AUTH-STORE] 用户数据无效')
      return
    }
    
    user.value = userData
    localStorage.setItem('user', JSON.stringify(userData))
  }
  
  // 清除认证数据
  const clearAuthData = () => {
    console.log('[AUTH-STORE] 清除认证数据')
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null
    
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    localStorage.removeItem('user')
  }
  
  // 刷新token
  const refreshAccessToken = async (): Promise<boolean> => {
    if (!refreshToken.value) {
      console.error('[AUTH-STORE] 没有refresh token，无法刷新')
      return false
    }
    
    try {
      isLoading.value = true
      console.log('[AUTH-STORE] 刷新token...')
      
      const response = await authApi.refreshToken(refreshToken.value)
      if (response.data?.access) {
        const newToken = response.data.access
        accessToken.value = newToken
        localStorage.setItem('access', newToken)
        
        console.log('[AUTH-STORE] Token刷新成功')
        return true
      }
      
      console.error('[AUTH-STORE] 刷新token返回不含access')
      return false
    } catch (error) {
      console.error('[AUTH-STORE] 刷新token失败:', error)
      return false
    } finally {
      isLoading.value = false
    }
  }
  
  // 验证token
  const verifyToken = async (): Promise<boolean> => {
    if (!accessToken.value) {
      console.log('[AUTH-STORE] 无token，跳过验证')
      return false
    }
    
    try {
      isLoading.value = true
      console.log('[AUTH-STORE] 验证token...')
      
      await authApi.verifyToken(accessToken.value)
      console.log('[AUTH-STORE] Token有效')
      return true
    } catch (error) {
      console.error('[AUTH-STORE] Token验证失败', error)
      
      // 尝试刷新token
      return await refreshAccessToken()
    } finally {
      isLoading.value = false
    }
  }
  
  // 获取用户信息
  const getCurrentUser = async () => {
    // 如果已有有效用户信息，直接返回
    if (user.value && user.value.username) {
      return user.value
    }
    
    if (!accessToken.value) {
      console.error('[AUTH-STORE] 无token，无法获取用户信息')
      return null
    }
    
    try {
      isLoading.value = true
      console.log('[AUTH-STORE] 获取用户信息...')
      
      // 确保localStorage有最新token
      if (localStorage.getItem('access') !== accessToken.value) {
        localStorage.setItem('access', accessToken.value)
      }
      
      const response = await authApi.getUserInfo()
      if (response.data) {
        setUser(response.data)
        return response.data
      }
      
      return null
    } catch (error) {
      console.error('[AUTH-STORE] 获取用户信息失败:', error)
      
      // 验证token是否有效
      const isValid = await verifyToken()
      if (!isValid) {
        logout()
      }
      
      return null
    } finally {
      isLoading.value = false
    }
  }
  
  // 登出
  const logout = () => {
    // 防止循环调用
    if (isLoggingOut.value) return
    
    try {
      isLoggingOut.value = true
      console.log('[AUTH-STORE] 执行登出')
      
      // 清理数据
      clearAuthData()
      
      // 派发登出事件
      window.dispatchEvent(new Event('auth:logout'))
    } finally {
      isLoggingOut.value = false
    }
  }
  
  // 验证会话
  const validateSession = async (): Promise<boolean> => {
    // 无token，返回false
    if (!accessToken.value) return false
    
    try {
      isLoading.value = true
      console.log('[AUTH-STORE] 验证会话...')
      
      // 验证token
      const isValid = await verifyToken()
      if (!isValid) {
        console.warn('[AUTH-STORE] Token验证失败，尝试刷新')
        
        const refreshed = await refreshAccessToken()
        if (!refreshed) {
          console.error('[AUTH-STORE] Token刷新失败，执行登出')
          logout()
          return false
        }
      }
      
      // 确保有用户信息
      if (!user.value || !user.value.username) {
        await getCurrentUser()
      }
      
      return true
    } catch (error) {
      console.error('[AUTH-STORE] 会话验证失败:', error)
      logout()
      return false
    } finally {
      isLoading.value = false
    }
  }
  
  // 如果有token，初始化时验证会话
  if (accessToken.value) {
    validateSession().catch(error => {
      console.error('[AUTH-STORE] 初始会话验证失败:', error)
    })
  }
  
  return {
    // 状态
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    username,
    isLoading,
    
    // 方法
    setAuth,
    setUser,
    refreshAccessToken,
    verifyToken,
    logout,
    getCurrentUser,
    validateSession
  }
})
