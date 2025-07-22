// 导入网络模块
import { 
  apiCore, 
  defaultApi, 
  localApi, 
  ApiMode 
} from '../network';

// 导入资源管理器
import { resourceManager } from './ResourceManager.ts';
import type { ResourceType } from './ResourceManager.ts';

// 导入创建资源服务工厂函数
import { createResourceService } from './ResourceServiceCreator.ts';

// 导入自定义方法定义
import {
  areaCustomMethods,
  buildingCustomMethods,
  nodeCustomMethods,
  terminalCustomMethods,
  alertCustomMethods,
  noticeCustomMethods,
  historicalCustomMethods,
  userCustomMethods,
  summaryCustomMethods,
  localTerminalCustomMethods,
  serviceConfigs,
  DEFAULT_CACHE_DURATIONS
} from './ResourceServiceDefinitions.ts';

// 导入类型
import type { 
  AreaItem, Building, HardwareNode, ProcessTerminal, 
  User, Alert, Notice, HistoricalData 
} from '../types';

// 创建各个资源服务
export const areaService = createResourceService<AreaItem>('areas', areaCustomMethods);
export const buildingService = createResourceService<Building>('buildings', buildingCustomMethods);
export const nodeService = createResourceService<HardwareNode>('nodes', nodeCustomMethods);
export const terminalService = createResourceService<ProcessTerminal>('terminals', terminalCustomMethods);
export const alertService = createResourceService<Alert>('alerts', alertCustomMethods);
export const noticeService = createResourceService<Notice>('notice', noticeCustomMethods);
export const userService = createResourceService<User>('users', userCustomMethods);
export const historicalService = createResourceService<HistoricalData>('historical', historicalCustomMethods);
export const summaryService = summaryCustomMethods;
export const localTerminalService = localTerminalCustomMethods;

// 初始化服务配置
for (const [resourceType, config] of Object.entries(serviceConfigs)) {
  resourceManager.setResourceConfig(resourceType, config);
}

// API服务初始化函数
export async function initializeApi() {
  try {
    // 预加载常用资源
    await Promise.allSettled([
      buildingService.getAll({}, true),
      // 可以添加其他需要预加载的资源
    ]);
    return true;
  } catch (error) {
    console.error('API初始化失败:', error);
    return false;
  }
}

// 清除所有缓存
export function clearAllCaches() {
  resourceManager.clearCache();
}

// 刷新特定资源缓存
export function refreshResourceCache(resourceType: string) {
  resourceManager.invalidateCache(resourceType);
}

// 设置全局缓存时间
export function setGlobalCacheDuration(duration: number) {
  resourceManager.setGlobalCacheDuration(duration);
}

// 设置特定资源类型的缓存时间
export function setResourceCacheDuration(resourceType: string, duration: number) {
  resourceManager.setResourceCacheDuration(resourceType, duration);
}

// 获取资源类型的默认缓存时间
export function getDefaultCacheDuration(resourceType: string): number {
  return DEFAULT_CACHE_DURATIONS[resourceType] || DEFAULT_CACHE_DURATIONS.global;
}

// 重置资源类型的缓存时间为默认值
export function resetCacheDuration(resourceType: string) {
  const defaultDuration = getDefaultCacheDuration(resourceType);
  resourceManager.setResourceCacheDuration(resourceType, defaultDuration);
  return defaultDuration;
}

// 统一的API服务对象
const apiService = {
  // 核心服务
  apiCore,
  resourceManager,
  
  // 模式和API实例
  ApiMode,
  defaultApi,
  localApi,
  
  // 各个资源服务
  areas: areaService,
  buildings: buildingService,
  nodes: nodeService,
  terminals: terminalService,
  alerts: alertService,
  notices: noticeService,
  users: userService,
  historical: historicalService,
  summary: summaryService,
  localTerminal: localTerminalService,
  
  // 工具函数
  initialize: initializeApi,
  clearCache: clearAllCaches,
  refreshCache: refreshResourceCache,
  setCacheDuration: setResourceCacheDuration,  // 保留旧接口以兼容
  setGlobalCacheDuration, // 设置全局缓存时间
  setResourceCacheDuration, // 设置特定资源缓存时间
  getDefaultCacheDuration, // 获取默认缓存时间
  resetCacheDuration, // 重置为默认缓存时间
  
  // 自定义API调用
  async customGet<T>(url: string, params = {}, useCache = false) {
    const { customApiCall } = await import('./ResourceServiceDefinitions.ts');
    return customApiCall<T>(url, 'get', undefined, params, useCache);
  },
  
  async customPost<T>(url: string, data: any) {
    const { customApiCall } = await import('./ResourceServiceDefinitions.ts');
    return customApiCall<T>(url, 'post', data);
  },
  
  async customPut<T>(url: string, data: any) {
    const { customApiCall } = await import('./ResourceServiceDefinitions.ts');
    return customApiCall<T>(url, 'put', data);
  },
  
  async customDelete<T>(url: string) {
    const { customApiCall } = await import('./ResourceServiceDefinitions.ts');
    return customApiCall<T>(url, 'delete');
  }
};

// 导出默认API服务
export default apiService;