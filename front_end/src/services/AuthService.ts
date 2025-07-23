import { authApi } from '../network/axios';
import type { User } from '../types';

/**
 * 认证服务 - 处理用户认证和授权
 */
class AuthService {
  /**
   * 用户登录
   * @param username 用户名
   * @param password 密码
   */
  async login(username: string, password: string) {
    try {
      const response = await authApi.post('/auth/jwt/create/', { username, password });
      return response.data;
    } catch (error) {
      console.error('登录失败:', error);
      throw error;
    }
  }
  
  /**
   * 用户注册
   * @param userData 用户数据
   */
  async register(userData: any) {
    try {
      const response = await authApi.post('/auth/users/', userData);
      return response.data;
    } catch (error) {
      console.error('注册失败:', error);
      throw error;
    }
  }
  
  /**
   * 刷新访问令牌
   * @param refreshToken 刷新令牌
   */
  async refreshToken(refreshToken: string) {
    try {
      const response = await authApi.post('/auth/jwt/refresh/', { refresh: refreshToken });
      return response.data; // 直接返回data，无需嵌套在data属性中
    } catch (error) {
      console.error('刷新令牌失败:', error);
      throw error;
    }
  }
  
  /**
   * 验证令牌
   * @param token 要验证的令牌
   */
  async verifyToken(token: string) {
    try {
      const response = await authApi.post('/auth/jwt/verify/', { token });
      return response.data;
    } catch (error) {
      console.error('验证令牌失败:', error);
      throw error;
    }
  }
  
  /**
   * 获取当前用户信息
   */
  async getUserInfo(): Promise<User> {
    const token = localStorage.getItem('access');
    if (!token) throw new Error('未登录');
    
    try {
      const response = await authApi.get('/auth/users/me/');
      return response.data;
    } catch (error) {
      console.error('获取用户信息失败:', error);
      throw error;
    }
  }
  
  /**
   * 更新用户信息
   * @param data 更新的用户数据
   */
  async updateUserInfo(data: Partial<User>) {
    try {
      const response = await authApi.patch('/auth/users/me/', data);
      return response.data;
    } catch (error) {
      console.error('更新用户信息失败:', error);
      throw error;
    }
  }
  
  /**
   * 更新密码
   * @param data 密码更新数据
   */
  async updatePassword(data: { 
    current_password: string, 
    new_password: string, 
    re_new_password: string 
  }) {
    try {
      const response = await authApi.post('/auth/users/set_password/', data);
      return response.data;
    } catch (error) {
      console.error('更新密码失败:', error);
      throw error;
    }
  }
  
  /**
   * 检查用户是否已登录
   */
  isAuthenticated(): boolean {
    return !!localStorage.getItem('access');
  }
  
  /**
   * 退出登录
   */
  logout() {
    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
    localStorage.removeItem('user');
    localStorage.removeItem('token_expiration');
  }
  
  /**
   * 获取token有效期剩余时间（毫秒）
   */
  getTokenTimeRemaining(): number {
    const expirationTime = localStorage.getItem('token_expiration');
    if (!expirationTime) return 0;
    
    const expiration = parseInt(expirationTime);
    return Math.max(0, expiration - Date.now());
  }
  
  /**
   * 检查token是否即将过期（12小时内）
   */
  isTokenExpiringSoon(): boolean {
    const remainingTime = this.getTokenTimeRemaining();
    const twelveHours = 12 * 60 * 60 * 1000;
    return remainingTime > 0 && remainingTime < twelveHours;
  }
}

// 导出单例实例
export const authService = new AuthService();
export default authService;
