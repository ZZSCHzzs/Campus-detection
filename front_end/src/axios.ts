import axios from 'axios'

const apiClient = axios.create({
  baseURL: 'http://smarthit.top:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器（可用于未来添加JWT认证）
apiClient.interceptors.request.use(config => {
  // 此处可添加token等全局逻辑
  return config
}, error => {
  return Promise.reject(error)
})

// 响应拦截器
apiClient.interceptors.response.use(response => {
  return response.data
}, error => {
  return Promise.reject(error)
})

export default apiClient