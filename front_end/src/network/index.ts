// 导入axios相关
import { apiCore, defaultApi, localApi, authApi, ApiMode } from './axios';


// 导出HTTP工具函数
export { 
  http,
  httpGet,
  httpPost,
  httpPut,
  httpPatch,
  httpDelete,
  localHttpGet,
  localHttpPost
} from './http';

// 核心导出
export {
  apiCore,
  defaultApi,
  localApi,
  authApi,
  ApiMode
};