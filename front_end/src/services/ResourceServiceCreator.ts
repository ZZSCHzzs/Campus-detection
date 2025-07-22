import { resourceManager } from './apiResourceManager';
import type { ResourceType } from './apiResourceManager';

/**
 * 创建标准化API服务
 */
export function createResourceService<T>(
  resourceType: string, 
  customMethods: Record<string, Function> = {}
) {
  // 创建基础服务
  const baseService = {
    /**
     * 获取所有资源
     */
    getAll: (params = {}, forceRefresh = false) => 
      resourceManager.getList<T>(resourceType, params, forceRefresh),
    
    /**
     * 根据ID获取资源
     */
    getById: (id: number | string, forceRefresh = false) => 
      resourceManager.getById<T>(resourceType, id, forceRefresh),
    
    /**
     * 创建新资源
     */
    create: (data: Partial<T>) => 
      resourceManager.create<T>(resourceType, data),
    
    /**
     * 更新资源
     */
    update: (id: number | string, data: Partial<T>) => 
      resourceManager.update<T>(resourceType, id, data),
    
    /**
     * 部分更新资源
     */
    patch: (id: number | string, data: Partial<T>) => 
      resourceManager.patch<T>(resourceType, id, data),
    
    /**
     * 删除资源
     */
    delete: (id: number | string) => 
      resourceManager.delete(resourceType, id),
    
    /**
     * 刷新资源缓存
     */
    refresh: (params = {}) => 
      resourceManager.getList<T>(resourceType, params, true),
    
    /**
     * 刷新单个资源缓存
     */
    refreshById: (id: number | string) => 
      resourceManager.getById<T>(resourceType, id, true),
    
    /**
     * 清空资源缓存
     */
    clearCache: () => {
      resourceManager.invalidateCache(resourceType);
      return true;
    }
  };
  
  // 合并自定义方法
  const service = { ...baseService, ...customMethods };
  
  return service;
}