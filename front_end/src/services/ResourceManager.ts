import { defaultApi } from '../network';
import type { AxiosInstance, AxiosRequestConfig } from 'axios';

export type ResourceType = 'areas' | 'buildings' | 'nodes' | 'terminals' | 'users' | 'alerts' | 'notice' | 'historical';

interface CacheItem<T> {
  data: T;
  timestamp: number;
  expiresIn: number;
}

export interface ResourceConfig {
  api?: AxiosInstance;
  basePath?: string;
  cacheDuration?: number;
}

/**
 * 资源管理器 - 统一管理API资源的CRUD操作和缓存
 */
export class ResourceManager {
  private cache: Map<string, CacheItem<any>> = new Map();
  private globalCacheDuration: number = 5 * 60 * 1000; // 默认5分钟
  private resourceConfigs: Map<string, ResourceConfig> = new Map();
  
  constructor(private defaultApi: AxiosInstance) {}
  
  /**
   * 设置资源配置
   */
  setResourceConfig(resourceType: string, config: ResourceConfig): void {
    this.resourceConfigs.set(resourceType, config);
  }
  
  /**
   * 获取资源配置
   */
  getResourceConfig(resourceType: string): ResourceConfig {
    return this.resourceConfigs.get(resourceType) || {};
  }
  
  /**
   * 设置全局缓存时间
   */
  setGlobalCacheDuration(duration: number): void {
    this.globalCacheDuration = duration;
  }
  
  /**
   * 设置特定资源类型的缓存时间
   * @param resourceType 资源类型
   * @param duration 缓存时间（毫秒）
   */
  setResourceCacheDuration(resourceType: string, duration: number): void {
    const config = this.resourceConfigs.get(resourceType);
    
    if (config) {
      config.cacheDuration = duration;
      console.log(`已设置资源 ${resourceType} 的缓存时间为 ${duration}ms`);
    } else {
      console.warn(`未找到资源类型 ${resourceType} 的配置，无法设置缓存时间`);
    }
  }
  
  /**
   * 获取资源列表
   */
  async getList<T>(resourceType: string, params: Record<string, any> = {}, forceRefresh = false): Promise<T[]> {
    const cacheKey = this.generateCacheKey(resourceType, params);
    const config = this.getResourceConfig(resourceType);
    const cacheDuration = config.cacheDuration || this.globalCacheDuration;
    
    if (!forceRefresh) {
      const cachedData = this.getFromCache<T[]>(cacheKey);
      if (cachedData) return cachedData;
    }
    
    try {
      const api = config.api || this.defaultApi;
      const basePath = config.basePath || '/api';
      const url = `${basePath}/${resourceType}/`;
      
      const response = await api.get(url, { params });
      let data: T[];
      
      if (response.data.results && Array.isArray(response.data.results)) {
        data = response.data.results;
      } else if (Array.isArray(response.data)) {
        data = response.data;
      } else {
        data = [response.data];
      }
      
      this.setCache(cacheKey, data, cacheDuration);
      return data;
    } catch (error) {
      console.error(`获取资源列表失败: ${resourceType}`, error);
      
      const expiredCache = this.getFromCache<T[]>(cacheKey, true);
      if (expiredCache) return expiredCache;
      
      throw error;
    }
  }
  
  /**
   * 获取单个资源
   */
  async getById<T>(resourceType: string, id: number | string, forceRefresh = false): Promise<T> {
    const cacheKey = `${resourceType}_${id}`;
    const config = this.getResourceConfig(resourceType);
    const cacheDuration = config.cacheDuration || this.globalCacheDuration;
    
    if (!forceRefresh) {
      const cachedData = this.getFromCache<T>(cacheKey);
      if (cachedData) return cachedData;
    }
    
    try {
      const api = config.api || this.defaultApi;
      const basePath = config.basePath || '/api';
      const url = `${basePath}/${resourceType}/${id}/`;
      
      const response = await api.get(url);
      const data = response.data;
      
      this.setCache(cacheKey, data, cacheDuration);
      return data;
    } catch (error) {
      console.error(`获取资源详情失败: ${resourceType}/${id}`, error);
      
      const expiredCache = this.getFromCache<T>(cacheKey, true);
      if (expiredCache) return expiredCache;
      
      throw error;
    }
  }
  
  /**
   * 创建资源
   */
  async create<T>(resourceType: string, data: any): Promise<T> {
    const config = this.getResourceConfig(resourceType);
    const api = config.api || this.defaultApi;
    const basePath = config.basePath || '/api';
    const url = `${basePath}/${resourceType}/`;
    
    const response = await api.post(url, data);
    this.invalidateCache(resourceType);
    
    return response.data;
  }
  
  /**
   * 更新资源
   */
  async update<T>(resourceType: string, id: number | string, data: any): Promise<T> {
    const config = this.getResourceConfig(resourceType);
    const api = config.api || this.defaultApi;
    const basePath = config.basePath || '/api';
    const url = `${basePath}/${resourceType}/${id}/`;
    
    const response = await api.put(url, data);
    this.invalidateCache(`${resourceType}_${id}`);
    this.invalidateCache(resourceType);
    
    return response.data;
  }
  
  /**
   * 部分更新资源
   */
  async patch<T>(resourceType: string, id: number | string, data: any): Promise<T> {
    const config = this.getResourceConfig(resourceType);
    const api = config.api || this.defaultApi;
    const basePath = config.basePath || '/api';
    const url = `${basePath}/${resourceType}/${id}/`;
    
    const response = await api.patch(url, data);
    this.invalidateCache(`${resourceType}_${id}`);
    this.invalidateCache(resourceType);
    
    return response.data;
  }
  
  /**
   * 删除资源
   */
  async delete(resourceType: string, id: number | string): Promise<void> {
    const config = this.getResourceConfig(resourceType);
    const api = config.api || this.defaultApi;
    const basePath = config.basePath || '/api';
    const url = `${basePath}/${resourceType}/${id}/`;
    
    await api.delete(url);
    this.invalidateCache(`${resourceType}_${id}`);
    this.invalidateCache(resourceType);
  }
  
  /**
   * 自定义API调用
   */
  async customCall<T>(
    url: string, 
    method: 'get' | 'post' | 'put' | 'patch' | 'delete' = 'get',
    data?: any,
    params?: Record<string, any>,
    api?: AxiosInstance,
    useCache = false,
    cacheDuration?: number
  ): Promise<T> {
    const effectiveApi = api || this.defaultApi;
    
    if (method !== 'get' || !useCache) {
      const config: AxiosRequestConfig = { params };
      
      // 根据请求方法正确传递参数
      let response;
      if (method === 'get') {
        response = await effectiveApi.get(url, config);
      } else if (method === 'post') {
        response = await effectiveApi.post(url, data, config);
      } else if (method === 'put') {
        response = await effectiveApi.put(url, data, config);
      } else if (method === 'patch') {
        response = await effectiveApi.patch(url, data, config);
      } else if (method === 'delete') {
        response = await effectiveApi.delete(url, config);
      }
      
      return response.data;
    }
    
    const cacheKey = this.generateCacheKey(url, params || {});
    const effectiveCacheDuration = cacheDuration || this.globalCacheDuration;
    
    if (useCache) {
      const cachedData = this.getFromCache<T>(cacheKey);
      if (cachedData) return cachedData;
    }
    
    try {
      const response = await effectiveApi.get(url, { params });
      const responseData = response.data;
      
      if (useCache) {
        this.setCache(cacheKey, responseData, effectiveCacheDuration);
      }
      
      return responseData;
    } catch (error) {
      console.error(`自定义API调用失败: ${url}`, error);
      
      if (useCache) {
        const expiredCache = this.getFromCache<T>(cacheKey, true);
        if (expiredCache) return expiredCache;
      }
      
      throw error;
    }
  }
  
  /**
   * 清空所有缓存
   */
  clearCache(): void {
    this.cache.clear();
    console.log('[ResourceManager] 缓存已清空');
  }
  
  /**
   * 使特定资源缓存失效
   */
  invalidateCache(prefix: string): void {
    for (const key of this.cache.keys()) {
      if (key.startsWith(prefix)) {
        this.cache.delete(key);
      }
    }
  }
  
  /**
   * 从缓存获取数据
   */
  private getFromCache<T>(key: string, allowExpired = false): T | null {
    const cacheItem = this.cache.get(key);
    
    if (!cacheItem) {
      return null;
    }
    
    const now = Date.now();
    const isExpired = (now - cacheItem.timestamp) > cacheItem.expiresIn;
    
    if (isExpired && !allowExpired) {
      return null;
    }
    
    return cacheItem.data as T;
  }
  
  /**
   * 设置缓存
   */
  private setCache<T>(key: string, data: T, expiresIn: number): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      expiresIn
    });
  }
  
  /**
   * 生成缓存键
   */
  private generateCacheKey(base: string, params: Record<string, any>): string {
    const paramsString = Object.keys(params).length 
      ? `_${Object.entries(params).map(([k, v]) => `${k}-${v}`).join('_')}` 
      : '';
    return `${base}${paramsString}`;
  }
}

// 创建全局资源管理器实例
export const resourceManager = new ResourceManager(defaultApi);