import axios from 'axios'
import type { AxiosRequestHeaders } from 'axios'
import { useAuthStore } from '../stores/auth'


const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://smarthit.top'

/**
 * 创建标准化的API实例
 */
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

/**
 * 请求拦截器 - 添加JWT认证头和URL格式化
 */
api.interceptors.request.use(config => {
  
  if (config.url && !config.url.endsWith('/') && !config.url.includes('?')) {
    config.url += '/'
  }
  
  const token = localStorage.getItem('access')
  if (token) {
    if (!config.headers) {
      config.headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      } as AxiosRequestHeaders;
    }
    config.headers['Authorization'] = `JWT ${token.trim()}`
  }
  
  return config
}, error => Promise.reject(error))

/**
 * 响应拦截器 - 自动处理401错误和token刷新
 */
api.interceptors.response.use(
  response => response,
  async error => {
    if (!error.response) return Promise.reject(error)
    const originalRequest = error.config
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        const authStore = useAuthStore()
        const refreshed = await authStore.refreshAccessToken()
        
        if (refreshed) {
          
          const token = localStorage.getItem('access')
          originalRequest.headers['Authorization'] = `JWT ${token}`
          return api(originalRequest)
        } else {
          
          authStore.logout()
        }
      } catch (error) {
        const authStore = useAuthStore()
        authStore.logout()
      }
    }
    return Promise.reject(error)
  }
)

export default api
