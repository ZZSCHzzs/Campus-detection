import axios from 'axios'


const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://smarthit.top:8000'


const authAxios = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})


authAxios.interceptors.request.use(config => {
  if (config.url && !config.url.endsWith('/') && !config.url.includes('?')) {
    config.url += '/'
  }
  return config
})

/**
 * 认证相关API服务
 */
const authApi = {
  /**
   * 用户登录
   */
  login: (username, password) => 
    authAxios.post('/auth/jwt/create/', { username, password }),
    
  /**
   * 用户注册
   */
  register: (userData) => 
    authAxios.post('/auth/users/', userData),
    
  /**
   * 刷新令牌
   */
  refreshToken: (refreshToken) => 
    authAxios.post('/auth/jwt/refresh/', { refresh: refreshToken }),
    
  /**
   * 验证令牌
   */
  verifyToken: (token) => 
    authAxios.post('/auth/jwt/verify/', { token }),
    
  /**
   * 获取当前用户信息
   */
  getUserInfo: async () => {
    const token = localStorage.getItem('access')
    if (!token) throw new Error('No access token available')
    
    try {
      const response = await authAxios.get('/auth/users/me/', {
        headers: {
          'Authorization': `JWT ${token.trim()}`
        }
      })
      return response.data
    } catch (error) {
      console.error('获取用户信息失败:', error)
      throw error
    }
  },
  
  /**
   * 更新用户信息
   */
  updateUserInfo: async (data) => {
    const token = localStorage.getItem('access')
    if (!token) throw new Error('No access token available')
    
    return authAxios.patch('/auth/users/me/', data, {
      headers: {
        'Authorization': `JWT ${token.trim()}`
      }
    })
  },
  
  /**
   * 更新密码
   */
  updatePassword: async (data) => {
    const token = localStorage.getItem('access')
    if (!token) throw new Error('No access token available')
    
    return authAxios.post('/auth/users/set_password/', data, {
      headers: {
        'Authorization': `JWT ${token.trim()}`
      }
    })
  }
}

export default authApi
