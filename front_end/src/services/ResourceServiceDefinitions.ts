import { defaultApi, localApi, ApiMode, http } from '../network';
import type { ResourceConfig } from './ResourceManager';
import type { 
  AreaItem, Building, HardwareNode, ProcessTerminal, 
  User, Alert, Notice, HistoricalData, TemperatureHumidityData, CO2Data, LogEntry, TerminalConfig, EnvironmentInfo
} from '../types';
import { ElMessage } from 'element-plus';

/**
 * 自定义方法定义 - 集中管理各个服务的自定义方法
 */

// 区域服务自定义方法
export const areaCustomMethods = {
  getPopularAreas: (count = 5) => 
    customApiCall<AreaItem[]>(`/api/areas/popular/`, 'get', undefined, { count }, true, 30000),
    
  // 添加获取推荐区域的方法
  getSuggestedAreas: (buildingId = 2, count = 5) => 
    customApiCall<AreaItem[]>(`/api/areas/suggest/`, 'get', undefined, { building: buildingId, count }, true, 30000),
  
  getAreaHistorical: (id: number, params?: any) => 
    customApiCall<HistoricalData[]>(`/api/areas/${id}/historical/`, 'get', undefined, params),

  // 获取区域温湿度数据
  getAreaTemperatureHumidity: (id: number, hours = 24) => 
    customApiCall<TemperatureHumidityData[]>(`/api/areas/${id}/temperature_humidity/`, 'get', undefined, { hours }),

  getFavoriteAreas: async () => {
    try {
      const userInfo = await userCustomMethods.getUserInfo();
      const favorite_areas_id = userInfo.favorite_areas || [];
      
      if (favorite_areas_id.length === 0) {
        return [];
      }
      
      const { areaService } = await import('./index');
      
      const areas = await Promise.all(
        favorite_areas_id.map(async (id: number) => {
          try {
            return await areaService.getById(id);
          } catch (error) {
            console.error(`获取ID为${id}的区域失败:`, error);
            return null;
          }
        })
      );

      return areas.filter(area => area !== null);
    } catch (error) {
      console.error('获取收藏区域失败:', error);
      return [];
    }
  },

  toggleFavoriteArea: (id: number) => 
    customApiCall(`/api/areas/${id}/favor/`, 'post'),
};

// 建筑服务自定义方法
export const buildingCustomMethods = {
  getBuildingAreas: (id: number) => 
    customApiCall<AreaItem[]>(`/api/buildings/${id}/areas/`),
  
  // 新增：分页获取建筑区域
  getBuildingAreasPaginated: (id: number, page = 1, pageSize = 20) => 
    customApiCall<{
      areas: AreaItem[];
      total_count: number;
      page: number;
      page_size: number;
      has_next: boolean;
      has_previous: boolean;
    }>(`/api/buildings/${id}/areas_paginated/`, 'get', undefined, { page, page_size: pageSize }),
  
  // 新增：获取建筑基本信息
  getBuildingsBasic: () => 
    customApiCall<Building[]>('/api/buildings/list_basic/', 'get', undefined, {}, true, 5 * 60 * 1000),
  
  // 新增：批量加载多个建筑的区域
  loadBuildingsWithAreas: async (buildingIds: number[], pageSize = 20) => {
    const results = await Promise.all(
      buildingIds.map(async (id) => {
        try {
          const response = await buildingCustomMethods.getBuildingAreasPaginated(id, 1, pageSize);
          return { buildingId: id, ...response };
        } catch (error) {
          console.error(`加载建筑 ${id} 的区域失败:`, error);
          return { buildingId: id, areas: [], total_count: 0, has_next: false };
        }
      })
    );
    return results;
  }
};

// 节点服务自定义方法
export const nodeCustomMethods = {
  getDatabyAreaId: (areaId: number) =>
    customApiCall<HardwareNode[]>(`/api/areas/${areaId}/data/`, 'get', undefined, {}, true, 5000),
};

// 终端服务自定义方法
export const terminalCustomMethods = {
  getTerminalNodes: (id: number) => 
    customApiCall<HardwareNode[]>(`/api/terminals/${id}/nodes/`),
    
  getTerminalStatus: (id: number) => 
    customApiCall(`/api/terminals/${id}/status/`, 'get', undefined, {}, false),
    
  getTerminalLogs: (id: number, params = {}) => 
    customApiCall<LogEntry[]>(`/api/terminals/${id}/logs/`, 'get', undefined, params, false),
    
  getTerminalConfig: (id: number) => 
    customApiCall<TerminalConfig>(`/api/terminals/${id}/config/`, 'get', undefined, {}, false),
  
  // 获取终端CO2数据
  getTerminalCO2Data: (id: number, hours = 24) => 
    customApiCall<CO2Data[]>(`/api/terminals/${id}/co2_data/`, 'get', undefined, { hours }),
    
  sendTerminalCommand: (id: number, command: any) => 
    customApiCall(`/api/terminals/${id}/command/`, 'post', command),
    
  updateTerminalConfig: (id: number, config: any) => 
    customApiCall(`/api/terminals/${id}/config/`, 'put', config),
};

// 告警服务自定义方法
export const alertCustomMethods = {  
  getUnsolvedAlerts: () => 
    customApiCall<Alert[]>('/api/alerts/unsolved/', 'get', undefined, {}, true, 30000),
    
  getPublicAlerts: () => 
    customApiCall<Alert[]>('/api/alerts/public/', 'get', undefined, {}, true, 30000),
    
  solveAlert: (id: number) => 
    customApiCall(`/api/alerts/${id}/solve/`, 'post'),
};

// 通知服务自定义方法
export const noticeCustomMethods = {
  getLatestNotices: (count = 5) => 
    customApiCall<Notice[]>('/api/notice/latest/', 'get', undefined, { count }, true, 30000),
    
  getNoticeAreas: (id: number) => 
    customApiCall<AreaItem[]>(`/api/notice/${id}/areas/`),
};

// 历史数据服务自定义方法
export const historicalCustomMethods = {
  getAreaHistorical: (areaId: number, params?: any) => 
    customApiCall<HistoricalData[]>(`/api/areas/${areaId}/historical/`, 'get', undefined, params),

  getHistoricalByDateRange: (startDate: string, endDate: string, params?: any) => 
    customApiCall<HistoricalData[]>(`/api/historical/`, 'get', undefined, 
      { ...params, start_date: startDate, end_date: endDate }),

  getLatestHistorical: (count = 10) => 
    customApiCall<HistoricalData>(`/api/historical/latest/`, 'get', undefined, { count }),
};

// 温湿度数据服务自定义方法
export const temperatureHumidityCustomMethods = {
  // 获取最新温湿度数据
  getLatest: (count = 10) => 
    customApiCall<TemperatureHumidityData[]>('/api/temperature-humidity/latest/', 'get', undefined, { count }, true, 30000),
  
  // 根据区域获取温湿度数据
  getByArea: (areaId: number, hours = 24) => 
    customApiCall<TemperatureHumidityData[]>('/api/temperature-humidity/by_area/', 'get', undefined, { area_id: areaId, hours }),
  
  // 获取区域的温湿度数据（通过区域API）
  getAreaTemperatureHumidity: (areaId: number, hours = 24) => 
    customApiCall<TemperatureHumidityData[]>(`/api/areas/${areaId}/temperature_humidity/`, 'get', undefined, { hours }),
  
  // 上传温湿度数据
  upload: (data: { area_id: number; temperature?: number; humidity?: number; timestamp: string }) => 
    customApiCall('/api/upload/temperature-humidity/', 'post', data),
  
  // 根据时间范围获取温湿度数据
  getByDateRange: (startDate: string, endDate: string, areaId?: number) => {
    const params: any = { start_date: startDate, end_date: endDate };
    if (areaId) params.area_id = areaId;
    return customApiCall<TemperatureHumidityData[]>('/api/temperature-humidity/', 'get', undefined, params);
  }
};

// CO2数据服务自定义方法
export const co2CustomMethods = {
  // 获取最新CO2数据
  getLatest: (count = 10) => 
    customApiCall<CO2Data[]>('/api/co2/latest/', 'get', undefined, { count }, true, 30000),
  
  // 根据终端获取CO2数据
  getByTerminal: (terminalId: number, hours = 24) => 
    customApiCall<CO2Data[]>('/api/co2/by_terminal/', 'get', undefined, { terminal_id: terminalId, hours }),
  
  // 获取终端的CO2数据（通过终端API）
  getTerminalCO2Data: (terminalId: number, hours = 24) => 
    customApiCall<CO2Data[]>(`/api/terminals/${terminalId}/co2_data/`, 'get', undefined, { hours }),
  
  // 上传CO2数据
  upload: (data: { terminal_id: number; co2_level: number; timestamp: string }) => 
    customApiCall('/api/upload/co2/', 'post', data),
  
  // 根据时间范围获取CO2数据
  getByDateRange: (startDate: string, endDate: string, terminalId?: number) => {
    const params: any = { start_date: startDate, end_date: endDate };
    if (terminalId) params.terminal_id = terminalId;
    return customApiCall<CO2Data[]>('/api/co2/', 'get', undefined, params);
  }
};

// 用户服务自定义方法
export const userCustomMethods = {
  getUserInfo: async () => {
    try {
      // 动态导入 AuthService 避免循环依赖
      const { authService } = await import('./AuthService');
      const userData = await authService.getUserInfo();
      
      // 动态导入 authStore 避免循环依赖
      const { useAuthStore } = await import('../stores/auth');
      const authStore = useAuthStore();
      authStore.setUser(userData);
      
      return userData;
    } catch (error) {
      console.error('获取用户信息失败:', error);
      throw error;
    }
  },

  updateUserInfo: async (data: Partial<User>) => {
    try {
      // 动态导入 AuthService 避免循环依赖
      const { authService } = await import('./AuthService');
      const userData = await authService.updateUserInfo(data);
      return userData;
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
      // 动态导入 AuthService 避免循环依赖
      const { authService } = await import('./AuthService');
      const result = await authService.updatePassword(data);
      return result;
    } catch (error) {
      console.error('更新密码失败:', error);
      throw error;
    }
  },
};

export const uploadDataCustomMethods = {
  upload: (data: any) => {
    return customApiCall('/api/upload/', 'post', data);
  },
  alert: (data: any) => {
    return customApiCall('/api/alert/', 'post', data);
  }
}

// 本地终端服务自定义方法
export const localTerminalCustomMethods = {
  // localTerminal 服务
  getBuzzerStatus: async () => {
  return localApi.get('/api/buzzer/status/');
  },
  controlBuzzer: async (data) => {
    return localApi.post('/api/buzzer/', data);
  },
  
  // 灯光控制相关方法
  controlLightRotate: async (data) => {
      return localApi.post('/api/light/rotate/', data);
  },
  getLightStatus: async (nodeId) => {
      return localApi.get(`/api/light/status/${nodeId}`);
  },
  
  // 获取终端状态
  getStatus: async () => {
    return await http.local.get('/api/status');
  },
  
  // 获取配置
  getConfig: async () => {
    return await http.local.get('/api/config');
  },
  
  // 更新配置
  updateConfig: async (config: any) => {
    return await http.local.post('/api/config', config);
  },
  
  // 获取日志
  getLogs: async () => {
    return await http.local.get('/api/logs');
  },
  
  // 发送控制命令
  sendCommand: async (action: string, params = {}) => {
    return await http.local.post('/api/control', { action, ...params });
  },
  
  // 获取终端信息
  getInfo: async () => {
    return await http.local.get('/api/info');
  },
  
  // 获取环境信息
  getEnvironmentInfo: async (): Promise<EnvironmentInfo> => {
    try {
      return await http.local.get<EnvironmentInfo>('/api/environment');
    } catch (error) {
      ElMessage.warning('未检测到本地终端服务');
      return {
        type: 'unknown',
        version: 'unknown',
        name: '未知环境',
        id: null,
        features: {
          local_detection: false,
          websocket: false,
          push_mode: false,
          pull_mode: false
        }
      };
    }
  },
  
  // 检查本地终端是否可用
  checkLocalAvailable: async () => {
    try {
      await http.local.get('/api/heartbeat', { timeout: 3000 });
      return true;
    } catch (error) {
      console.error('本地终端不可用:', error);
      return false;
    }
  },
  
  // 自动检测环境
  autoDetectEnvironment: async () => {
    try {
      const localAvailable = await localTerminalCustomMethods.checkLocalAvailable();
      
      if (localAvailable) {
        try {
          const data = await localTerminalCustomMethods.getEnvironmentInfo();
          if (data && data.type === 'detector') {
            return data;
          }
        } catch (error) {
          console.warn('获取本地环境信息失败:', error);
        }
      }
      
      // 返回默认环境信息
      ElMessage({
        message: '未检测到本地终端环境，使用远程模式',
        type: 'warning',
      });
      
      return {
        type: 'server',
        version: 'unknown',
        name: '远程服务器',
        id: 1,
        features: {
          local_detection: false,
          websocket: true,
          push_mode: true,
          pull_mode: true
        }
      };
    } catch (error) {
      console.error('自动检测环境失败:', error);
      throw error;
    }
  },

  // 获取数据节点最后一次图片（返回Blob）
  getLastImage: async (nodeId: number) => {
    return await http.local.get(`/api/image/last/${nodeId}`, {}, { responseType: 'blob' });
  },
};

// 汇总服务自定义方法
export const summaryCustomMethods = {
  getSummary: () => 
    customApiCall('/api/summary/', 'get', undefined, {}, true, 30000),
};

// 服务资源配置
export const serviceConfigs: Record<string, ResourceConfig> = {
  areas: {
    basePath: '/api',
    cacheDuration: 60 * 1000, // 1分钟
  },
  buildings: {
    basePath: '/api',
    cacheDuration: 5 * 60 * 1000, // 5分钟
  },
  nodes: {
    basePath: '/api',
    cacheDuration: 30 * 1000, // 30秒
  },
  terminals: {
    basePath: '/api',
    cacheDuration: 30 * 1000, // 30秒
  },
  alerts: {
    basePath: '/api',
    cacheDuration: 30 * 1000, // 30秒
  },
  notice: {
    basePath: '/api',
    cacheDuration: 60 * 1000, // 1分钟
  },
  users: {
    basePath: '/api',
    cacheDuration: 5 * 60 * 1000, // 5分钟
  },
  historical: {
    basePath: '/api',
    cacheDuration: 5 * 60 * 1000, // 5分钟
  },
  'temperature-humidity': {
    basePath: '/api',
    cacheDuration: 2 * 60 * 1000, // 2分钟
  },
  co2: {
    basePath: '/api',
    cacheDuration: 2 * 60 * 1000, // 2分钟
  }
};

// 统一的自定义API调用函数
export async function customApiCall<T>(
  url: string, 
  method: 'get' | 'post' | 'put' | 'patch' | 'delete' = 'get',
  data?: any,
  params?: Record<string, any>,
  useCache = false,
  cacheDuration?: number
): Promise<T> {
  // 动态导入apiResourceManager以避免循环依赖
  const { resourceManager } = await import('./ResourceManager');
  return resourceManager.customCall<T>(url, method, data, params, defaultApi, useCache, cacheDuration);
}

// 添加资源类型的默认缓存时间常量
export const DEFAULT_CACHE_DURATIONS = {
  areas: 60 * 1000, // 1分钟
  buildings: 5 * 60 * 1000, // 5分钟
  nodes: 30 * 1000, // 30秒
  terminals: 30 * 1000, // 30秒
  alerts: 30 * 1000, // 30秒
  notice: 60 * 1000, // 1分钟
  users: 5 * 60 * 1000, // 5分钟
  historical: 5 * 60 * 1000, // 5分钟
  'temperature-humidity': 2 * 60 * 1000, // 2分钟
  co2: 2 * 60 * 1000, // 2分钟
  global: 2 * 60 * 1000, // 全局默认2分钟
};