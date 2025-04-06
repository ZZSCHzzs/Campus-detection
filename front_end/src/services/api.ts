import axios from 'axios'
import { useAuthStore } from '../stores/auth'

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

// 请求拦截器 - 添加认证token
api.interceptors.request.use(
  config => {
    const authStore = useAuthStore()
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
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
    const authStore = useAuthStore()
    
    // 如果是401错误且未尝试过刷新token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      try {
        // 尝试刷新token
        const refreshSuccess = await authStore.refreshAccessToken()
        
        if (refreshSuccess) {
          // 更新认证头并重试请求
          originalRequest.headers.Authorization = `Bearer ${authStore.accessToken}`
          return api(originalRequest)
        } else {
          // 刷新失败，登出并跳转到登录页
          authStore.logout()
          window.location.href = '/auth?mode=login'
          return Promise.reject(error)
        }
      } catch (refreshError) {
        return Promise.reject(refreshError)
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
  verifyToken: (token) => api.post('/auth/jwt/verify/', { token })
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
