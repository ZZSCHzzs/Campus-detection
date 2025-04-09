import api from './api'
import type { AreaItem, Building, HardwareNode, ProcessTerminal, User, Alert, Notice } from '../types'

// 资源类型定义
export type ResourceType = 'areas' | 'buildings' | 'nodes' | 'terminals' | 'users' | 'alerts' | 'notice' | 'historical'

// 资源映射到对应的类型
export interface ResourceTypeMapping {
  areas: AreaItem[];
  buildings: Building[];
  nodes: HardwareNode[];
  terminals: ProcessTerminal[];
  users: User[];
  alerts: Alert[];
  notice: Notice[];
  historical: any[]; // 使用any，因为历史数据格式可能变化
}

// 缓存接口
interface CacheItem<T> {
  data: T;
  timestamp: number;
  expiresIn: number; // 过期时间（毫秒）
}

// 默认缓存有效期（毫秒）
const DEFAULT_CACHE_DURATION = 5 * 60 * 1000; // 5分钟


// 资源管理器类
class ApiResourceManager {
  private cache: Map<string, CacheItem<any>> = new Map();
  private globalCacheDuration: number = DEFAULT_CACHE_DURATION;
  
  // 设置全局缓存时间
  setGlobalCacheDuration(duration: number): void {
    this.globalCacheDuration = duration;
    console.log(`[ApiResourceManager] Global cache duration set to ${duration}ms`);
  }
  
  // 获取当前的全局缓存设置
  getGlobalCacheDuration(): number {
    return this.globalCacheDuration;
  }
  
  // 从API获取资源并缓存
  async getResource<T extends keyof ResourceTypeMapping>(
    resourceType: T, 
    params: Record<string, any> = {}, 
    forceRefresh = false,
    cacheDuration?: number
  ): Promise<ResourceTypeMapping[T]> {
    // 如果未指定缓存时间，使用全局设置
    const effectiveCacheDuration = cacheDuration || this.globalCacheDuration;
    
    const cacheKey = this.generateCacheKey(resourceType, params);
    
    // 检查缓存是否存在且有效
    if (!forceRefresh) {
      const cachedData = this.getFromCache<ResourceTypeMapping[T]>(cacheKey);
      if (cachedData) {
        console.log(`[ApiResourceManager] Using cached data for ${resourceType}`);
        return cachedData;
      }
    }
    
    try {
      console.log(`[ApiResourceManager] Fetching ${resourceType} from API`);
      const url = `/api/${resourceType}/`;
      const response = await api.get(url, { params });
      
      let data: ResourceTypeMapping[T];
      
      // 处理可能的分页结果
      if (response.data.results && Array.isArray(response.data.results)) {
        data = response.data.results as ResourceTypeMapping[T];
      } else if (Array.isArray(response.data)) {
        data = response.data as ResourceTypeMapping[T];
      } else {
        data = [response.data] as ResourceTypeMapping[T];
      }
      
      // 缓存数据
      this.setCache(cacheKey, data, effectiveCacheDuration);
      
      return data;
    } catch (error) {
      console.error(`[ApiResourceManager] Error fetching ${resourceType}:`, error);
      
      // 如果API请求失败，尝试返回可能过期的缓存数据作为后备
      const expiredCache = this.getFromCache<ResourceTypeMapping[T]>(cacheKey, true);
      if (expiredCache) {
        console.warn(`[ApiResourceManager] Returning expired cache for ${resourceType}`);
        return expiredCache;
      }
      
      throw error;
    }
  }
  
  // 获取单个资源及其详细信息
  async getResourceById<T extends keyof ResourceTypeMapping>(
    resourceType: T,
    id: number | string,
    forceRefresh = false,
    cacheDuration = DEFAULT_CACHE_DURATION
  ): Promise<ResourceTypeMapping[T][0]> {
    const cacheKey = `${resourceType}_${id}`;
    
    // 检查缓存
    if (!forceRefresh) {
      const cachedData = this.getFromCache<ResourceTypeMapping[T][0]>(cacheKey);
      if (cachedData) {
        return cachedData;
      }
    }
    
    try {
      const url = `/api/${resourceType}/${id}/`;
      const response = await api.get(url);
      const data = response.data as ResourceTypeMapping[T][0];
      
      // 缓存数据
      this.setCache(cacheKey, data, cacheDuration);
      
      return data;
    } catch (error) {
      console.error(`[ApiResourceManager] Error fetching ${resourceType}/${id}:`, error);
      
      // 尝试从过期缓存获取
      const expiredCache = this.getFromCache<ResourceTypeMapping[T][0]>(cacheKey, true);
      if (expiredCache) {
        return expiredCache;
      }
      
      throw error;
    }
  }
  
  // 创建资源
  async createResource<T extends keyof ResourceTypeMapping>(
    resourceType: T,
    data: Partial<ResourceTypeMapping[T][0]>
  ): Promise<ResourceTypeMapping[T][0]> {
    const url = `/api/${resourceType}/`;
    const response = await api.post(url, data);
    
    // 创建后刷新此类型的列表缓存
    this.invalidateCache(resourceType);
    
    return response.data as ResourceTypeMapping[T][0];
  }
  
  // 更新资源
  async updateResource<T extends keyof ResourceTypeMapping>(
    resourceType: T,
    id: number | string,
    data: Partial<ResourceTypeMapping[T][0]>
  ): Promise<ResourceTypeMapping[T][0]> {
    const url = `/api/${resourceType}/${id}/`;
    const response = await api.put(url, data);
    
    // 更新后刷新相关缓存
    this.invalidateCache(resourceType);
    this.invalidateCache(`${resourceType}_${id}`);
    
    return response.data as ResourceTypeMapping[T][0];
  }
  
  // 部分更新资源
  async patchResource<T extends keyof ResourceTypeMapping>(
    resourceType: T,
    id: number | string,
    data: Partial<ResourceTypeMapping[T][0]>
  ): Promise<ResourceTypeMapping[T][0]> {
    const url = `/api/${resourceType}/${id}/`;
    const response = await api.patch(url, data);
    
    // 更新后刷新相关缓存
    this.invalidateCache(resourceType);
    this.invalidateCache(`${resourceType}_${id}`);
    
    return response.data as ResourceTypeMapping[T][0];
  }
  
  // 删除资源
  async deleteResource<T extends keyof ResourceTypeMapping>(
    resourceType: T,
    id: number | string
  ): Promise<void> {
    const url = `/api/${resourceType}/${id}/`;
    await api.delete(url);
    
    // 删除后刷新相关缓存
    this.invalidateCache(resourceType);
    this.invalidateCache(`${resourceType}_${id}`);
  }
  
  // 自定义API调用（带缓存）
  async customApiCall<T>(
    url: string,
    method: 'get' | 'post' | 'put' | 'patch' | 'delete' = 'get',
    data?: any,
    params: Record<string, any> = {},
    useCache = true,
    cacheDuration = DEFAULT_CACHE_DURATION
  ): Promise<T> {
    // 只对GET请求进行缓存
    if (method !== 'get' || !useCache) {
      const response = await api[method](url, data, { params });
      return response.data as T;
    }
    
    const cacheKey = this.generateCacheKey(url, params);
    
    // 检查缓存
    if (useCache) {
      const cachedData = this.getFromCache<T>(cacheKey);
      if (cachedData) {
        return cachedData;
      }
    }
    
    try {
      const response = await api.get(url, { params });
      const responseData = response.data as T;
      
      // 缓存数据
      if (useCache) {
        this.setCache(cacheKey, responseData, cacheDuration);
      }
      
      return responseData;
    } catch (error) {
      console.error(`[ApiResourceManager] Error in custom API call to ${url}:`, error);
      
      // 尝试从过期缓存获取（仅GET请求）
      if (useCache) {
        const expiredCache = this.getFromCache<T>(cacheKey, true);
        if (expiredCache) {
          return expiredCache;
        }
      }
      
      throw error;
    }
  }
  
  // 刷新资源缓存
  async refreshCache<T extends keyof ResourceTypeMapping>(resourceType: T, params: Record<string, any> = {}): Promise<ResourceTypeMapping[T]> {
    return this.getResource(resourceType, params, true);
  }
  
  // 批量预加载常用资源
  async preloadCommonResources(): Promise<void> {
    console.log('[ApiResourceManager] Preloading common resources...');
    const resources: ResourceType[] = ['buildings'];
    
    await Promise.allSettled(
      resources.map(resource => 
        this.getResource(resource as keyof ResourceTypeMapping, {}, true)
          .catch(err => console.error(`Preloading ${resource} failed:`, err))
      )
    );
    
    console.log('[ApiResourceManager] Preloading completed');
  }
  
  // 清除缓存
  clearCache(): void {
    this.cache.clear();
    console.log('[ApiResourceManager] Cache cleared');
  }
  
  // 只清除特定资源的缓存
  invalidateCache(resourceKeyPrefix: string): void {
    for (const key of this.cache.keys()) {
      if (key.startsWith(resourceKeyPrefix)) {
        this.cache.delete(key);
      }
    }
    console.log(`[ApiResourceManager] Cache for ${resourceKeyPrefix} invalidated`);
  }
  
  // 从缓存中获取数据
  private getFromCache<T>(key: string, allowExpired = false): T | null {
    const cacheItem = this.cache.get(key);
    
    if (!cacheItem) {
      return null;
    }
    
    // 检查缓存是否过期
    const now = Date.now();
    const isExpired = (now - cacheItem.timestamp) > cacheItem.expiresIn;
    
    if (isExpired && !allowExpired) {
      console.log(`[ApiResourceManager] Cache for ${key} has expired`);
      return null;
    }
    
    return cacheItem.data as T;
  }
  
  // 设置缓存
  private setCache<T>(key: string, data: T, expiresIn: number): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      expiresIn
    });
  }
  
  // 生成缓存键
  private generateCacheKey(base: string, params: Record<string, any> = {}): string {
    const paramsString = Object.keys(params).length 
      ? `_${Object.entries(params).map(([k, v]) => `${k}-${v}`).join('_')}` 
      : '';
    return `${base}${paramsString}`;
  }
}

// 创建单例实例
const apiResourceManager = new ApiResourceManager();

export default apiResourceManager;
