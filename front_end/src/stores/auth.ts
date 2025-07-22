import { defineStore } from 'pinia'
import AuthService from '../services/AuthService'
import { ref, computed, watch } from 'vue'
import type { User } from '../types'

export const useAuthStore = defineStore('auth', () => {

  const accessToken = ref(localStorage.getItem('access') || '')
  const refreshToken = ref(localStorage.getItem('refresh') || '')
  const user = ref<User | null>(null)
  const isLoggingOut = ref(false)
  const isLoading = ref(false)

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

  const isAuthenticated = computed(() => !!accessToken.value && accessToken.value.length > 10)
  const username = computed(() => user.value?.username || '未登录')

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

  const setAuth = (authData: { access: string, refresh: string }) => {
    console.log('[AUTH-STORE] 设置认证信息')
    accessToken.value = authData.access
    refreshToken.value = authData.refresh

    localStorage.setItem('access', authData.access)
    localStorage.setItem('refresh', authData.refresh)
  }

  const setUser = (userData: any) => {
    console.log('[AUTH-STORE] 设置用户信息:', userData)
    if (!userData || !userData.username) {
      console.error('[AUTH-STORE] 用户数据无效')
      return
    }
    
    user.value = userData
    localStorage.setItem('user', JSON.stringify(userData))
  }

  const clearAuthData = () => {
    console.log('[AUTH-STORE] 清除认证数据')
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null
    
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    localStorage.removeItem('user')
  }

  const refreshAccessToken = async (): Promise<boolean> => {
    if (!refreshToken.value) {
      console.error('[AUTH-STORE] 没有refresh token，无法刷新')
      return false
    }
    
    try {
      isLoading.value = true
      console.log('[AUTH-STORE] 刷新token...')
      
      const response = await AuthService.refreshToken(refreshToken.value)
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

  const verifyToken = async (): Promise<boolean> => {
    if (!accessToken.value) {
      console.log('[AUTH-STORE] 无token，跳过验证')
      return false
    }
    
    try {
      isLoading.value = true
      console.log('[AUTH-STORE] 验证token...')
      
      await AuthService.verifyToken(accessToken.value)
      console.log('[AUTH-STORE] Token有效')
      return true
    } catch (error) {
      console.error('[AUTH-STORE] Token验证失败', error)

      return await refreshAccessToken()
    } finally {
      isLoading.value = false
    }
  }

  const getCurrentUser = async () => {

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

      if (localStorage.getItem('access') !== accessToken.value) {
        localStorage.setItem('access', accessToken.value)
      }
      
      const data = await AuthService.getUserInfo()
      if (data) {
        setUser(data)
        return data
      }
      
      return null
    } catch (error) {
      console.error('[AUTH-STORE] 获取用户信息失败:', error)

      const isValid = await verifyToken()
      if (!isValid) {
        logout()
      }
      
      return null
    } finally {
      isLoading.value = false
    }
  }

  const logout = () => {

    if (isLoggingOut.value) return
    
    try {
      isLoggingOut.value = true
      console.log('[AUTH-STORE] 执行登出')

      clearAuthData()

      window.dispatchEvent(new Event('auth:logout'))
    } finally {
      isLoggingOut.value = false
    }
  }

  const validateSession = async (): Promise<boolean> => {

    if (!accessToken.value) return false
    
    try {
      isLoading.value = true
      console.log('[AUTH-STORE] 验证会话...')

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

  if (accessToken.value) {
    validateSession().catch(error => {
      console.error('[AUTH-STORE] 初始会话验证失败:', error)
    })
  }
  
  return {

    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    username,
    isLoading,

    setAuth,
    setUser,
    refreshAccessToken,
    verifyToken,
    logout,
    getCurrentUser,
    validateSession
  }
})
