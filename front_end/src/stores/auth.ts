import { defineStore } from 'pinia'
import api from '../services/api'
import { ref, computed, watch } from 'vue'
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
  
  // 监听token变化，保持同步
  watch(accessToken, (newToken) => {
    localStorage.setItem('access', newToken)
  })
  
  watch(refreshToken, (newToken) => {
    localStorage.setItem('refresh', newToken)
  })
  
  // 监听自定义事件
  if (typeof window !== 'undefined') {
    // 监听token刷新事件
    window.addEventListener('auth:token-refreshed', ((event: CustomEvent) => {
      accessToken.value = event.detail.token
      console.log('Token已通过事件更新')
    }) as EventListener)
    
    // 监听登出事件
    window.addEventListener('auth:logout', () => {
      logout()
      console.log('收到登出事件，已清除认证状态')
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
        console.log('获取用户信息中，当前token:', accessToken.value.slice(0, 10) + '...')
        const response = await api.get('/auth/users/me/')
        if (response.data) {
          setUser(response.data)
          return response.data
        }
      } catch (error) {
        console.error('获取用户信息失败:', error)
        // 如果获取失败，可能是token已失效
        const isValid = await verifyToken()
        if (!isValid) {
          console.warn('Token验证失败，执行登出')
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
    console.log('认证信息已设置')
  }
  
  // 设置用户信息
  const setUser = (userData: any) => {
    console.log('设置用户信息:', userData)
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
      console.log('尝试刷新token')
      // 使用axios直接请求，避免拦截器循环
      const response = await api.post('/auth/jwt/refresh/', {
        refresh: refreshToken.value
      })
      
      if (response.data.access) {
        accessToken.value = response.data.access
        localStorage.setItem('access', response.data.access)
        console.log('Token刷新成功')
        
        // 触发自定义事件通知token已刷新
        window.dispatchEvent(new CustomEvent('auth:token-refreshed', {
          detail: { token: response.data.access }
        }))
        
        return true
      }
      return false
    } catch (error) {
      console.error('刷新Token失败:', error)
      // 刷新失败，清除认证状态
      logout()
      return false
    }
  }
  
  // 验证token
  const verifyToken = async () => {
    if (!accessToken.value) return false
    try {
      console.log('验证token有效性')
      await api.post('/auth/jwt/verify/', {
        token: accessToken.value
      })
      console.log('Token验证成功')
      return true
    } catch (error) {
      console.error('Token验证失败:', error)
      
      // 如果验证失败，尝试刷新token
      const refreshed = await refreshAccessToken()
      if (!refreshed) {
        logout()
      }
      return refreshed
    }
  }
  
  // 登出
  const logout = () => {
    console.log('执行登出操作')
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    localStorage.removeItem('user')
    
    // 触发登出事件
    window.dispatchEvent(new Event('auth:logout'))
  }
  
  // 自动验证token有效性
  const validateSession = async () => {
    if (accessToken.value) {
      console.log('会话验证开始')
      try {
        const isValid = await verifyToken()
        if (!isValid) {
          console.warn('Token无效，尝试刷新')
          const refreshed = await refreshAccessToken()
          if (!refreshed) {
            console.error('无法刷新token，执行登出')
            logout()
            return false
          }
        }
        
        // 如果验证成功但没有用户信息，获取用户信息
        if (!user.value || !user.value.username) {
          await getCurrentUser()
        }
        
        return true
      } catch (error) {
        console.error('会话验证出错:', error)
        logout()
        return false
      }
    }
    return false
  }
  
  // 初始验证
  if (accessToken.value) {
    validateSession()
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
    validateSession
  }
})
