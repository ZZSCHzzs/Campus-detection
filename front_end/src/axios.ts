import api, { apiService, authService } from './services/api'

// 确保baseURL正确设置
if (api.defaults.baseURL === '/api') {
  api.defaults.baseURL = 'http://smarthit.top:8000'
}

// 导出统一的API实例和服务
export const apiClient = api
export const apiServices = apiService
export const authServices = authService

// 默认导出，保持兼容性
export default api