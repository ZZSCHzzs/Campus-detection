import axios from 'axios'
// 移除直接引入 store，避免循环依赖
// import { useAuthStore } from '../stores/auth'

// 从环境变量获取API基础URL，如果未设置则使用默认值
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://smarthit.top:8000'

// 创建axios实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})
api.interceptors.request.use(
  config => {
    if (config.url && !config.url.endsWith('/')) {
      config.url += '/'
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 请求拦截器 - 添加认证token (优化版)
api.interceptors.request.use(
  config => {
    // 直接从 localStorage 获取 token，避免使用 store
    const token = localStorage.getItem('access')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 处理token过期
api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config
    
    // 如果是401错误且未尝试过刷新token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      try {
        // 获取刷新token
        const refreshToken = localStorage.getItem('refresh')
        
        if (refreshToken) {
          // 尝试刷新token
          const response = await axios.post(`${API_BASE_URL}/auth/jwt/refresh/`, {
            refresh: refreshToken
          })
          
          if (response.data && response.data.access) {
            // 更新localStorage和认证头
            const newToken = response.data.access
            localStorage.setItem('access', newToken)
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            
            // 发布自定义事件，通知token已更新
            window.dispatchEvent(new CustomEvent('auth:token-refreshed', { 
              detail: { token: newToken }
            }))
            
            // 重试原始请求
            return api(originalRequest)
          }
        }
        
        // 如果没有刷新token或刷新失败，清除认证状态并重定向
        localStorage.removeItem('access')
        localStorage.removeItem('refresh')
        localStorage.removeItem('user')
        
        // 发布认证失败事件
        window.dispatchEvent(new Event('auth:logout'))
        
        // 仅当不是登录相关的请求时才重定向
        if (!originalRequest.url.includes('/auth/')) {
          window.location.href = '/auth?mode=login'
        }
      } catch (refreshError) {
        // 刷新失败，清除认证状态
        localStorage.removeItem('access')
        localStorage.removeItem('refresh')
        localStorage.removeItem('user')
        
        // 发布认证失败事件
        window.dispatchEvent(new Event('auth:logout'))
        
        // 仅当不是登录相关的请求时才重定向
        if (!originalRequest.url.includes('/auth/')) {
          window.location.href = '/auth?mode=login'
        }
      }
    }
    
    return Promise.reject(error)
  }
)

// 认证相关API方法
export const authService = {
  register: (userData) => api.post('/auth/users/', userData),
  login: (credentials) => api.post('/auth/jwt/create/', credentials),
  refreshToken: (refreshToken) => api.post('/auth/jwt/refresh/', { refresh: refreshToken }),
  verifyToken: (token) => api.post('/auth/jwt/verify/', { token }),
  getMe: () => api.get('/auth/users/me/')
}

// 通用CRUD方法
export const apiService = {
  // 获取所有资源
  getAll: (resource) => api.get(`/api/${resource}`),
  
  // 获取单个资源
  get: (resource, id) => api.get(`/api/${resource}/${id}`),
  
  // 创建资源
  create: (resource, data) => api.post(`/api/${resource}`, data),
  
  // 更新资源
  update: (resource, id, data) => api.put(`/api/${resource}/${id}`, data),
  
  // 部分更新资源
  patch: (resource, id, data) => api.patch(`/api/${resource}/${id}`),
  
  // 删除资源
  delete: (resource, id) => api.delete(`/api/${resource}/${id}`),
  
  // 自定义GET请求
  customGet: (url) => api.get(`/api/${url}`),
  
  // 自定义POST请求
  customPost: (url, data) => api.post(`/api/${url}`, data)
}

export default api
