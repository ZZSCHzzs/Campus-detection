import api from './api'
import type { AreaItem, Building, HardwareNode, ProcessTerminal, User, Alert, Notice } from '../types'

export type ResourceType = 'areas' | 'buildings' | 'nodes' | 'terminals' | 'users' | 'alerts' | 'notice' | 'historical'

export interface ResourceTypeMapping {
  areas: AreaItem[];
  buildings: Building[];
  nodes: HardwareNode[];
  terminals: ProcessTerminal[];
  users: User[];
  alerts: Alert[];
  notice: Notice[];
  historical: any[];
}

interface CacheItem<T> {
  data: T;
  timestamp: number;
  expiresIn: number;
}

const DEFAULT_CACHE_DURATION = 5 * 60 * 1000;

class ApiResourceManager {
  private cache: Map<string, CacheItem<any>> = new Map();
  private globalCacheDuration: number = DEFAULT_CACHE_DURATION;

  private resourceCacheDuration: Map<ResourceType, number> = new Map();

  setGlobalCacheDuration(duration: number): void {
    this.globalCacheDuration = duration;
    console.log(`[ApiResourceManager] Global cache duration set to ${duration}ms`);
  }

  getGlobalCacheDuration(): number {
    return this.globalCacheDuration;
  }

  setResourceCacheDuration(resourceType: ResourceType, duration: number): void {
    this.resourceCacheDuration.set(resourceType, duration);
    console.log(`[ApiResourceManager] Cache duration for ${resourceType} set to ${duration}ms`);
  }

  getResourceCacheDuration(resourceType: ResourceType): number {
    return this.resourceCacheDuration.get(resourceType) || this.globalCacheDuration;
  }

  setMultipleResourceCacheDurations(settings: Record<ResourceType, number>): void {
    for (const [resourceType, duration] of Object.entries(settings)) {
      this.setResourceCacheDuration(resourceType as ResourceType, duration);
    }
    console.log(`[ApiResourceManager] Set cache durations for multiple resources:`, settings);
  }

  async getResource<T extends keyof ResourceTypeMapping>(
    resourceType: T, 
    params: Record<string, any> = {}, 
    forceRefresh = false,
    cacheDuration?: number
  ): Promise<ResourceTypeMapping[T]> {

    const effectiveCacheDuration = cacheDuration || 
      this.resourceCacheDuration.get(resourceType) || 
      this.globalCacheDuration;
    
    const cacheKey = this.generateCacheKey(resourceType, params);

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

      if (response.data.results && Array.isArray(response.data.results)) {
        data = response.data.results as ResourceTypeMapping[T];
      } else if (Array.isArray(response.data)) {
        data = response.data as ResourceTypeMapping[T];
      } else {
        data = [response.data] as ResourceTypeMapping[T];
      }

      this.setCache(cacheKey, data, effectiveCacheDuration);
      
      return data;
    } catch (error) {
      console.error(`[ApiResourceManager] Error fetching ${resourceType}:`, error);

      const expiredCache = this.getFromCache<ResourceTypeMapping[T]>(cacheKey, true);
      if (expiredCache) {
        console.warn(`[ApiResourceManager] Returning expired cache for ${resourceType}`);
        return expiredCache;
      }
      
      throw error;
    }
  }

  async getResourceById<T extends keyof ResourceTypeMapping>(
    resourceType: T,
    id: number | string,
    forceRefresh = false,
    cacheDuration?: number
  ): Promise<ResourceTypeMapping[T][0]> {

    const effectiveCacheDuration = cacheDuration || 
      this.resourceCacheDuration.get(resourceType) || 
      this.globalCacheDuration;
    
    const cacheKey = `${resourceType}_${id}`;

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

      this.setCache(cacheKey, data, effectiveCacheDuration);
      
      return data;
    } catch (error) {
      console.error(`[ApiResourceManager] Error fetching ${resourceType}/${id}:`, error);

      const expiredCache = this.getFromCache<ResourceTypeMapping[T][0]>(cacheKey, true);
      if (expiredCache) {
        return expiredCache;
      }
      
      throw error;
    }
  }

  async createResource<T extends keyof ResourceTypeMapping>(
    resourceType: T,
    data: Partial<ResourceTypeMapping[T][0]>
  ): Promise<ResourceTypeMapping[T][0]> {
    const url = `/api/${resourceType}/`;
    const response = await api.post(url, data);

    this.invalidateCache(resourceType);
    
    return response.data as ResourceTypeMapping[T][0];
  }

  async updateResource<T extends keyof ResourceTypeMapping>(
    resourceType: T,
    id: number | string,
    data: Partial<ResourceTypeMapping[T][0]>
  ): Promise<ResourceTypeMapping[T][0]> {
    const url = `/api/${resourceType}/${id}/`;
    const response = await api.put(url, data);

    this.invalidateCache(resourceType);
    this.invalidateCache(`${resourceType}_${id}`);
    
    return response.data as ResourceTypeMapping[T][0];
  }

  async patchResource<T extends keyof ResourceTypeMapping>(
    resourceType: T,
    id: number | string,
    data: Partial<ResourceTypeMapping[T][0]>
  ): Promise<ResourceTypeMapping[T][0]> {
    const url = `/api/${resourceType}/${id}/`;
    const response = await api.patch(url, data);

    this.invalidateCache(resourceType);
    this.invalidateCache(`${resourceType}_${id}`);
    
    return response.data as ResourceTypeMapping[T][0];
  }

  async deleteResource<T extends keyof ResourceTypeMapping>(
    resourceType: T,
    id: number | string
  ): Promise<void> {
    const url = `/api/${resourceType}/${id}/`;
    await api.delete(url);

    this.invalidateCache(resourceType);
    this.invalidateCache(`${resourceType}_${id}`);
  }

  async customApiCall<T>(
    url: string,
    method: 'get' | 'post' | 'put' | 'patch' | 'delete' = 'get',
    data?: any,
    params: Record<string, any> = {},
    useCache = true,
    cacheDuration?: number
  ): Promise<T> {

    const effectiveCacheDuration = cacheDuration || this.globalCacheDuration;

    if (method !== 'get' || !useCache) {
      const response = await api[method](url, data, { params });
      return response.data as T;
    }
    
    const cacheKey = this.generateCacheKey(url, params);

    if (useCache) {
      const cachedData = this.getFromCache<T>(cacheKey);
      if (cachedData) {
        return cachedData;
      }
    }
    
    try {
      const response = await api.get(url, { params });
      const responseData = response.data as T;

      if (useCache) {
        this.setCache(cacheKey, responseData, effectiveCacheDuration);
      }
      
      return responseData;
    } catch (error) {
      console.error(`[ApiResourceManager] Error in custom API call to ${url}:`, error);

      if (useCache) {
        const expiredCache = this.getFromCache<T>(cacheKey, true);
        if (expiredCache) {
          return expiredCache;
        }
      }
      
      throw error;
    }
  }

  async refreshCache<T extends keyof ResourceTypeMapping>(resourceType: T, params: Record<string, any> = {}): Promise<ResourceTypeMapping[T]> {
    return this.getResource(resourceType, params, true);
  }

  async refreshById<T extends keyof ResourceTypeMapping>(
    resourceType: T,
    id: number | string,
    params: Record<string, any> = {}
  ): Promise<ResourceTypeMapping[T][0]> {

    this.invalidateCache(`${resourceType}_${id}`);

    console.log(`[ApiResourceManager] Refreshing ${resourceType}/${id}`);
    return this.getResourceById(resourceType, id, true);
  }

  async refreshAll<T extends keyof ResourceTypeMapping>(
    resourceType: T,
    params: Record<string, any> = {}
  ): Promise<ResourceTypeMapping[T]> {

    this.invalidateCache(resourceType);

    console.log(`[ApiResourceManager] Refreshing all ${resourceType}`);
    return this.getResource(resourceType, params, true);
  }

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

  clearCache(): void {
    this.cache.clear();
    console.log('[ApiResourceManager] Cache cleared');
  }

  invalidateCache(resourceKeyPrefix: string): void {
    for (const key of this.cache.keys()) {
      if (key.startsWith(resourceKeyPrefix)) {
        this.cache.delete(key);
      }
    }
    console.log(`[ApiResourceManager] Cache for ${resourceKeyPrefix} invalidated`);
  }

  private getFromCache<T>(key: string, allowExpired = false): T | null {
    const cacheItem = this.cache.get(key);
    
    if (!cacheItem) {
      return null;
    }

    const now = Date.now();
    const isExpired = (now - cacheItem.timestamp) > cacheItem.expiresIn;
    
    if (isExpired && !allowExpired) {
      console.log(`[ApiResourceManager] Cache for ${key} has expired`);
      return null;
    }
    
    return cacheItem.data as T;
  }

  private setCache<T>(key: string, data: T, expiresIn: number): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      expiresIn
    });
  }

  private generateCacheKey(base: string, params: Record<string, any> = {}): string {
    const paramsString = Object.keys(params).length 
      ? `_${Object.entries(params).map(([k, v]) => `${k}-${v}`).join('_')}` 
      : '';
    return `${base}${paramsString}`;
  }
}

const apiResourceManager = new ApiResourceManager();

export default apiResourceManager;
