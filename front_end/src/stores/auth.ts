import { defineStore } from 'pinia'
import AuthService from '../services/AuthService'
import { ref, computed, watch, onMounted } from 'vue'
import type { User } from '../types'

// 配置参数
const TOKEN_REFRESH_INTERVAL = 25 * 60 * 1000; // 25分钟刷新一次token
const TOKEN_CHECK_INTERVAL = 5 * 60 * 1000;    // 5分钟检查一次token状态
const TOKEN_PERSIST_DAYS = 3;                  // token持久化保存天数

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem('access') || '')
  const refreshToken = ref(localStorage.getItem('refresh') || '')
  const user = ref<User | null>(null)
  const isLoggingOut = ref(false)
  const isLoading = ref(false)
  const refreshIntervalId = ref<number | null>(null)
  const tokenCheckIntervalId = ref<number | null>(null)

  const clearAuthData = () => {
    console.log('[AUTH-STORE] 清除认证数据')
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null

    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    localStorage.removeItem('user')
    localStorage.removeItem('token_expiration')

    clearTokenRefresh()
  }

  // 更新token过期时间（从当前时间起3天）
  const updateTokenExpiration = () => {
    const expirationTime = Date.now() + (TOKEN_PERSIST_DAYS * 24 * 60 * 60 * 1000)
    localStorage.setItem('token_expiration', expirationTime.toString())
    console.log('[AUTH-STORE] 更新token过期时间：', new Date(expirationTime).toLocaleString(),
      `(${TOKEN_PERSIST_DAYS}天后)`)
  }
  // 尝试从localStorage加载用户信息和过期时间
  try {
    const storedUser = localStorage.getItem('user')
    if (storedUser) {
      user.value = JSON.parse(storedUser)
      console.log('[AUTH-STORE] 从localStorage加载用户信息')
    }

    // 检查token过期时间
    const expirationTime = localStorage.getItem('token_expiration')
    if (expirationTime) {
      const expiration = parseInt(expirationTime)
      if (Date.now() > expiration) {
        console.log('[AUTH-STORE] 存储的token已过期，清除认证数据')
        clearAuthData()
      } else {
        console.log('[AUTH-STORE] 存储的token有效期还剩：', Math.round((expiration - Date.now()) / (1000 * 60 * 60 * 24)), '天')
      }
    } else if (refreshToken.value) {
      // 如果有refresh token但没有过期时间，设置一个新的
      updateTokenExpiration()
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

      // 更新token过期时间
      updateTokenExpiration()

      // 设置token自动刷新
      setupTokenRefresh()
    } else {
      localStorage.removeItem('refresh')
      localStorage.removeItem('token_expiration')
      clearTokenRefresh()
    }
  })

  // 设置自动刷新token的定时器
  const setupTokenRefresh = () => {
    clearTokenRefresh(); // 先清除现有定时器

    // 每隔一段时间自动刷新token
    refreshIntervalId.value = window.setInterval(async () => {
      if (refreshToken.value) {
        console.log('[AUTH-STORE] 执行定时token刷新')
        await refreshAccessToken()
      }
    }, TOKEN_REFRESH_INTERVAL);

    // 定期检查token状态
    tokenCheckIntervalId.value = window.setInterval(async () => {
      if (accessToken.value) {
        const isValid = await verifyToken()
        if (!isValid) {
          console.log('[AUTH-STORE] token无效，尝试刷新')
          await refreshAccessToken()
        }
      }
    }, TOKEN_CHECK_INTERVAL);

    console.log('[AUTH-STORE] 已设置token自动刷新')
  }

  // 清除token刷新定时器
  const clearTokenRefresh = () => {
    if (refreshIntervalId.value) {
      window.clearInterval(refreshIntervalId.value)
      refreshIntervalId.value = null
    }

    if (tokenCheckIntervalId.value) {
      window.clearInterval(tokenCheckIntervalId.value)
      tokenCheckIntervalId.value = null
    }
  }

  const setAuth = (authData: { access: string, refresh: string }) => {
    console.log('[AUTH-STORE] 设置认证信息')
    accessToken.value = authData.access
    refreshToken.value = authData.refresh

    localStorage.setItem('access', authData.access)
    localStorage.setItem('refresh', authData.refresh)

    // 设置token过期时间
    updateTokenExpiration()
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



  const refreshAccessToken = async (): Promise<boolean> => {
    if (!refreshToken.value) {
      console.error('[AUTH-STORE] 没有refresh token，无法刷新')
      return false
    }

    try {
      isLoading.value = true
      console.log('[AUTH-STORE] 刷新token...')

      const response = await AuthService.refreshToken(refreshToken.value)
      if (response && response.access) {
        const newToken = response.access
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

  // 初始化：如果有token则验证并设置自动刷新
  if (accessToken.value) {
    validateSession().then(isValid => {
      if (isValid) {
        // 刷新token过期时间
        updateTokenExpiration()
        setupTokenRefresh();
      }
    }).catch(error => {
      console.error('[AUTH-STORE] 初始会话验证失败:', error)
    })
  }

  // 在组件卸载时清除定时器
  const cleanupStore = () => {
    clearTokenRefresh();
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
    validateSession,
    cleanupStore,
    // 添加新方法
    updateTokenExpiration
  }
})
