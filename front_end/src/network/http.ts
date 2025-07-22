import { defaultApi, localApi } from './axios';
import type { AxiosInstance, AxiosRequestConfig } from 'axios';

/**
 * HTTP GET请求
 */
export async function httpGet<T>(
  url: string, 
  params = {}, 
  api: AxiosInstance = defaultApi,
  config: AxiosRequestConfig = {}
): Promise<T> {
  const response = await api.get(url, { 
    ...config,
    params 
  });
  return response.data;
}

/**
 * HTTP POST请求
 */
export async function httpPost<T>(
  url: string, 
  data: any, 
  api: AxiosInstance = defaultApi,
  config: AxiosRequestConfig = {}
): Promise<T> {
  const response = await api.post(url, data, config);
  return response.data;
}

/**
 * HTTP PUT请求
 */
export async function httpPut<T>(
  url: string, 
  data: any, 
  api: AxiosInstance = defaultApi,
  config: AxiosRequestConfig = {}
): Promise<T> {
  const response = await api.put(url, data, config);
  return response.data;
}

/**
 * HTTP PATCH请求
 */
export async function httpPatch<T>(
  url: string, 
  data: any, 
  api: AxiosInstance = defaultApi,
  config: AxiosRequestConfig = {}
): Promise<T> {
  const response = await api.patch(url, data, config);
  return response.data;
}

/**
 * HTTP DELETE请求
 */
export async function httpDelete<T>(
  url: string, 
  api: AxiosInstance = defaultApi,
  config: AxiosRequestConfig = {}
): Promise<T> {
  const response = await api.delete(url, config);
  return response.data;
}

/**
 * 本地服务HTTP GET请求
 */
export async function localHttpGet<T>(url: string, params = {}, config: AxiosRequestConfig = {}): Promise<T> {
  return httpGet(url, params, localApi, config);
}

/**
 * 本地服务HTTP POST请求
 */
export async function localHttpPost<T>(url: string, data: any, config: AxiosRequestConfig = {}): Promise<T> {
  return httpPost(url, data, localApi, config);
}

// 导出HTTP实用函数集合
export const http = {
  get: httpGet,
  post: httpPost,
  put: httpPut,
  patch: httpPatch,
  delete: httpDelete,
  
  // 本地API快捷方法
  local: {
    get: localHttpGet,
    post: localHttpPost,
    put: (url: string, data: any, config = {}) => httpPut(url, data, localApi, config),
    patch: (url: string, data: any, config = {}) => httpPatch(url, data, localApi, config),
    delete: (url: string, config = {}) => httpDelete(url, localApi, config)
  }
};
