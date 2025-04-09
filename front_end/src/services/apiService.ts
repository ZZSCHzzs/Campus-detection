import apiResourceManager from './apiResourceManager';
import authApi from './authApi';  
import type { ResourceType} from './apiResourceManager';
import type { AreaItem, Building, HardwareNode, ProcessTerminal, User, Alert, Notice, HistoricalData } from '../types';


const areaCustomMethods = {
  getAreaData: (id: number) => 
    apiResourceManager.customApiCall(`/api/areas/${id}/data/`),
    
  getPopularAreas: (count = 5) => 
    apiResourceManager.customApiCall<AreaItem[]>(`/api/areas/popular/`, 'get', undefined, { count }),
    
  getAreaHistorical: (id: number) => 
    apiResourceManager.customApiCall(`/api/areas/${id}/historical/`),
    
  toggleFavoriteArea: (id: number) => 
    apiResourceManager.customApiCall(`/api/areas/${id}/favor/`, 'post'),
};

const buildingCustomMethods = {
  getBuildingAreas: (id: number) => 
    apiResourceManager.customApiCall<AreaItem[]>(`/api/buildings/${id}/areas/`),
};

const nodeCustomMethods = {
  
};

const terminalCustomMethods = {
  getTerminalNodes: (id: number) => 
    apiResourceManager.customApiCall<HardwareNode[]>(`/api/terminals/${id}/nodes/`),
};

const alertCustomMethods = {  
  getUnsolvedAlerts: () => 
    apiResourceManager.customApiCall<Alert[]>('/api/alerts/unsolved/'),
    
  getPublicAlerts: () => 
    apiResourceManager.customApiCall<Alert[]>('/api/alerts/public/'),
    
  solveAlert: (id: number) => 
    apiResourceManager.customApiCall(`/api/alerts/${id}/solve/`, 'post'),
};

const noticeCustomMethods = {
  getLatestNotices: (count = 5) => 
    apiResourceManager.customApiCall<Notice[]>('/api/notice/latest/', 'get', undefined, { count }),
    
  getNoticeAreas: (id: number) => 
    apiResourceManager.customApiCall<AreaItem[]>(`/api/notice/${id}/areas/`),
};

const summaryCustomMethods = {
  getSummary: () => 
    apiResourceManager.customApiCall('/api/summary/'),
};

const historicalCustomMethods = {
  
  getAreaHistorical: (areaId: number, params?: any) => 
    apiResourceManager.customApiCall<HistoricalData[]>(`/api/areas/${areaId}/historical/`, 'get', undefined, params),
    
  
  getHistoricalByDateRange: (startDate: string, endDate: string, params?: any) => 
    apiResourceManager.customApiCall<HistoricalData[]>(`/api/historical/`, 'get', undefined, 
      { ...params, start_date: startDate, end_date: endDate }),
    
  
  getLatestHistorical: (count = 10) => 
    apiResourceManager.customApiCall<HistoricalData[]>(`/api/historical/latest/`, 'get', undefined, { count }),
};


const userCustomMethods = {
  
  getUserInfo: async () => {
    try {
      const response = await authApi.getUserInfo();
      
      return response.data;
    } catch (error) {
      console.error('获取用户信息失败:', error);
      throw error;
    }
  },
  
  
  updateUserInfo: async (data: Partial<User>) => {
    try {
      const response = await authApi.updateUserInfo(data);
      return response.data;
    } catch (error) {
      console.error('更新用户信息失败:', error);
      throw error;
    }
  },
  
  
  updatePassword: async (data: { 
    current_password: string, 
    new_password: string, 
    re_new_password: string 
  }) => {
    try {
      const response = await authApi.updatePassword(data);
      return response.data;
    } catch (error) {
      console.error('更新密码失败:', error);
      throw error;
    }
  },
  
  
  getFavoriteAreas: async (favoriteIds: number[]) => {
    if (!favoriteIds || favoriteIds.length === 0) return [];
    
    
    const promises = favoriteIds.map(id => 
      areaService.getById(id).catch(() => null)
    );
    
    const results = await Promise.all(promises);
    return results.filter(area => area !== null) as AreaItem[];
  }
};


export const initializeApiService = async () => {
  try {
    await apiResourceManager.preloadCommonResources();
    return true;
  } catch (error) {
    console.error('Failed to initialize API service:', error);
    return false;
  }
};


export const clearApiCache = () => {
  apiResourceManager.clearCache();
};


export const refreshResourceCache = (resourceType: string) => {
  apiResourceManager.invalidateCache(resourceType);
};


interface ResourceService<T> {
  getAll: (params?: any) => Promise<T[]>;
  getById: (id: number | string) => Promise<T>;
  create: (data: Partial<T>) => Promise<T>;
  update: (id: number | string, data: Partial<T>) => Promise<T>;
  patch?: (id: number | string, data: Partial<T>) => Promise<T>;
  delete: (id: number | string) => Promise<void>;
  [key: string]: any; // 添加索引签名，允许任意自定义方法
}


function createResourceService<T, R extends ResourceType = ResourceType>(
  resourceType: R, 
  customMethods: Record<string, Function> = {}
): ResourceService<T> {
  
  const baseService = {
    getAll: (params = {}) => 
      apiResourceManager.getResource(resourceType, params) as unknown as Promise<T[]>,
      
    getById: (id: number | string) => 
      apiResourceManager.getResourceById(resourceType, id) as Promise<T>,
      
    create: (data: Partial<T>) => 
      apiResourceManager.createResource(resourceType, data) as Promise<T>,
      
    update: (id: number | string, data: Partial<T>) => 
      apiResourceManager.updateResource(resourceType, id, data) as Promise<T>,
    
    patch: (id: number | string, data: Partial<T>) => 
      apiResourceManager.patchResource(resourceType, id, data) as Promise<T>,
      
    delete: (id: number | string) => 
      apiResourceManager.deleteResource(resourceType, id)
  };
  
  
  return { ...baseService, ...customMethods };
}


const serviceRegistry = new Map<string, any>();


function registerService(name: string, service: any): void {
  serviceRegistry.set(name, service);
}


function getService(name: string): any {
  return serviceRegistry.get(name);
}


const areaService = createResourceService<AreaItem>('areas', areaCustomMethods);
const buildingService = createResourceService<Building>('buildings', buildingCustomMethods);
const nodeService = createResourceService<HardwareNode>('nodes', nodeCustomMethods);
const terminalService = createResourceService<ProcessTerminal>('terminals', terminalCustomMethods);
const alertService = createResourceService<Alert>('alerts', alertCustomMethods);
const noticeService = createResourceService<Notice>('notice', noticeCustomMethods);
const userService = createResourceService<User>('users', userCustomMethods);
const historicalService = createResourceService<HistoricalData>('historical', historicalCustomMethods);


registerService('areas', areaService);
registerService('buildings', buildingService);
registerService('nodes', nodeService);
registerService('terminals', terminalService);
registerService('alerts', alertService);
registerService('notices', noticeService);
registerService('notice', noticeService);
registerService('users', userService);
registerService('summary', summaryCustomMethods);
registerService('historical', historicalService);


export { 
  areaService,
  buildingService,
  nodeService,
  terminalService,
  alertService,
  noticeService,
  userService,
  historicalService,
  summaryCustomMethods as summaryService
};


const apiService = {
  customGet: (url, params = {}) => {
    const formattedUrl = `${url}`;
    return apiResourceManager.customApiCall(formattedUrl, 'get', undefined, params);
  },
  customPost: (url, data) => {
    const formattedUrl = `${url}`;
    return apiResourceManager.customApiCall(formattedUrl, 'post', data);
  },
  
  registerService,
  getService,
  getAllServices: () => Object.fromEntries(serviceRegistry),
  
  
  
  areas: areaService,
  buildings: buildingService,
  nodes: nodeService,
  terminals: terminalService,
  alerts: alertService,
  notices: noticeService,
  notice: noticeService,
  historical: historicalService,
  summary: summaryCustomMethods,
  users: userService,
  
  
  clearCache: clearApiCache,
  refreshCache: refreshResourceCache,
  
  
  initialize: initializeApiService,
  
  
  setCacheOptions: (options: { duration?: number, enabled?: boolean }) => {
    
    if (options.duration) {
      
      apiResourceManager.setGlobalCacheDuration(options.duration);
    }
  }
};

export default apiService;
