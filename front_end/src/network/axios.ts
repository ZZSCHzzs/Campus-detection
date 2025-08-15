import axios from 'axios';
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { useAuthStore } from '../stores/auth';

export enum ApiMode {
  REMOTE = 'remote',
  LOCAL = 'local'
}

interface ApiCoreOptions {
  baseURL: string;
  timeout?: number;
  withCredentials?: boolean;
  mode?: ApiMode;
  addTrailingSlash?: boolean;
}

/**
 * API核心服务 - 创建和管理axios实例
 */
class ApiCore {
  private instances: Map<string, AxiosInstance> = new Map();
  private defaultConfig: AxiosRequestConfig = {
    timeout: 10000,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    }
  };
  
  /**
   * 创建一个新的API实例
   */
  createInstance(name: string, options: ApiCoreOptions): AxiosInstance {
    if (this.instances.has(name)) {
      console.warn(`API实例 "${name}" 已存在，将被替换`);
    }
    
    const config: AxiosRequestConfig = {
      ...this.defaultConfig,
      baseURL: options.baseURL,
      timeout: options.timeout || this.defaultConfig.timeout,
      withCredentials: options.withCredentials
    };
    
    const instance = axios.create(config);
    
    // 添加通用请求拦截器
    instance.interceptors.request.use(config => {
      // 自动添加斜杠
      if (options.addTrailingSlash !== false && 
          config.url && 
          !config.url.endsWith('/') && 
          !config.url.includes('?')) {
        config.url += '/';
      }
      
      // 远程模式自动添加认证token
      if (options.mode !== ApiMode.LOCAL) {
        const token = localStorage.getItem('access');
        if (token && config.headers) {
          config.headers['Authorization'] = `JWT ${token.trim()}`;
        }
      }
      
      return config;
    });
    
    // 远程模式添加认证刷新拦截器
    if (options.mode !== ApiMode.LOCAL) {
      instance.interceptors.response.use(
        response => response,
        async error => {
          const originalRequest = error.config;
          
          // 如果收到401错误且请求未被标记为重试过
          if (error.response && error.response.status === 401 && !originalRequest._retry) {
            if (isRefreshing) {
              // 如果正在刷新token，将请求加入队列
              return new Promise(resolve => {
                subscribeTokenRefresh(token => {
                  originalRequest.headers.Authorization = `Bearer ${token}`;
                  resolve(axios(originalRequest));
                });
              });
            }
            
            originalRequest._retry = true;
            isRefreshing = true;
            
            try {
              // 尝试刷新token
              const authStore = useAuthStore();
              const refreshSuccess = await authStore.refreshAccessToken();
              
              if (refreshSuccess) {
                const newToken = authStore.accessToken;
                onTokenRefreshed(newToken);
                originalRequest.headers.Authorization = `Bearer ${newToken}`;
                return axios(originalRequest);
              } else {
                // 刷新失败，可能需要重新登录
                console.error('Token刷新失败，需要重新登录');
                authStore.logout();
                return Promise.reject(error);
              }
            } catch (refreshError) {
              console.error('Token刷新出错:', refreshError);
              return Promise.reject(refreshError);
            } finally {
              isRefreshing = false;
            }
          }
          
          return Promise.reject(error);
        }
      );
    }
    
    this.instances.set(name, instance);
    return instance;
  }
  
  /**
   * 获取已创建的API实例
   */
  getInstance(name: string): AxiosInstance | undefined {
    return this.instances.get(name);
  }
  
  /**
   * 获取或创建API实例
   */
  getOrCreateInstance(name: string, options: ApiCoreOptions): AxiosInstance {
    const existing = this.getInstance(name);
    if (existing) return existing;
    return this.createInstance(name, options);
  }
  
  /**
   * 重置API实例
   */
  resetInstance(name: string): void {
    this.instances.delete(name);
  }
}

// 导出单例
export const apiCore = new ApiCore();

// 创建默认API实例
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://smarthit.top';
export const defaultApi = apiCore.createInstance('default', {
  baseURL: API_BASE_URL,
  mode: ApiMode.REMOTE,
  addTrailingSlash: true
});

// 创建本地API实例
export const localApi = apiCore.createInstance('local', {
  baseURL: 'http://localhost:5000',
  timeout: 5000,
  mode: ApiMode.LOCAL
});

// 创建认证API实例
export const authApi = apiCore.createInstance('auth', {
  baseURL: API_BASE_URL,
  mode: ApiMode.REMOTE,
  addTrailingSlash: true
});

// 用于跟踪正在刷新的过程
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

// 将需要重试的请求加入队列
const subscribeTokenRefresh = (cb: (token: string) => void) => {
  refreshSubscribers.push(cb);
};

// 刷新token后执行队列中的请求
const onTokenRefreshed = (token: string) => {
  refreshSubscribers.forEach(cb => cb(token));
  refreshSubscribers = [];
};
