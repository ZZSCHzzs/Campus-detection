import axios from 'axios';

/**
 * 终端消息类型定义
 */
export interface TerminalMessage {
  type: string;
  timestamp: string;
  [key: string]: any;
}

/**
 * 终端命令接口
 */
export interface TerminalCommand {
  command: string;
  params?: Record<string, any>;
  timestamp?: string;
}

/**
 * 终端状态接口
 */
export interface TerminalStatus {
  cameras: Record<string, string>;
  cpu_usage: number;
  memory_usage: number;
  push_running: boolean;
  pull_running: boolean;
  model_loaded: boolean;
  started_at?: string;
  mode?: string;
  [key: string]: any;
}

/**
 * 终端配置接口
 */
export interface TerminalConfig {
  mode: 'pull' | 'push' | 'both';
  interval: number;
  cameras: Record<string, string>;
  save_image: boolean;
  preload_model: boolean;
  [key: string]: any;
}

/**
 * 日志记录接口
 */
export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'detection';
  message: string;
  source: string;
}

/**
 * WebSocket回调函数类型
 */
export type WebSocketCallback = (data: any) => void;

/**
 * 终端通信服务 - 支持本地直连和远程连接两种模式
 */
class TerminalService {
  // 服务配置
  private mode: 'remote' | 'local' = 'remote';
  private terminalId: number | null = null;
  private localEndpoint: string = 'http://localhost:5000';
  
  // WebSocket连接
  private ws: WebSocket | null = null;
  private wsCallbacks: Map<string, WebSocketCallback> = new Map();
  
  // 重连机制
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectTimeout: number | null = null;
  private reconnectDelay: number = 2000; // 初始重连延迟(ms)
  private isReconnecting: boolean = false;

  // WebSocket URL配置
  private readonly wsPathTemplate: string = '/ws/terminals/{id}/';
  private readonly localWsId: string = 'local';
  
  /**
   * 设置连接模式
   * @param mode - 连接模式: 'local' 或 'remote'
   * @param terminalId - 远程模式下的终端ID
   * @returns 是否进行了模式切换
   */
  setMode(mode: 'remote' | 'local', terminalId: number | null = null): boolean {
    // 检查是否需要更改
    if (this.mode === mode && this.terminalId === terminalId) {
      return false;
    }
    
    this.mode = mode;
    this.terminalId = terminalId;
    
    // 断开现有WebSocket连接
    this.disconnectWebSocket();
    
    // 重置重连计数
    this.reconnectAttempts = 0;
    
    return true;
  }
  
  /**
   * 检测本地终端是否可用
   * @returns 是否可用
   */
  async detectLocalTerminal(): Promise<boolean> {
    try {
      const response = await axios.get(`${this.localEndpoint}/api/status`, { timeout: 2000 });
      return response.status === 200;
    } catch (error) {
      console.warn('本地终端检测失败:', error);
      return false;
    }
  }
  
  /**
   * 发送命令到终端
   * @param command - 命令名称
   * @param params - 命令参数
   * @returns 命令执行结果
   */
  async sendCommand(command: string, params: Record<string, any> = {}): Promise<any> {
    // 统一命令格式
    const commandData: TerminalCommand = {
      command: command,
      params: params,
      timestamp: new Date().toISOString()
    };
    
    if (this.mode === 'local') {
      return this.sendLocalCommand(commandData);
    } else {
      return this.sendRemoteCommand(commandData);
    }
  }
  
  /**
   * 发送命令到本地终端
   * @private
   */
  private async sendLocalCommand(commandData: TerminalCommand): Promise<any> {
    try {
      // 根据命令类型选择合适的终端API
      let endpoint = `${this.localEndpoint}/api/control`;
      let requestData: Record<string, any> = {
        action: commandData.command,
        ...commandData.params
      };
      
      // 特殊命令处理
      if (commandData.command === 'update_config') {
        endpoint = `${this.localEndpoint}/api/config`;
        requestData = commandData.params || {};
      }
      
      const response = await axios.post(endpoint, requestData, {
        timeout: 5000,
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      return response.data;
    } catch (error) {
      console.error('本地命令执行失败:', error);
      this.handleApiError('local_command', error);
      throw error;
    }
  }
  
  /**
   * 发送命令到远程终端
   * @private
   */
  private async sendRemoteCommand(commandData: TerminalCommand): Promise<any> {
    if (!this.terminalId) {
      throw new Error('远程模式下必须提供终端ID');
    }
    
    try {
      // 使用一致的复数形式URL
      const response = await axios.post(`/api/terminals/${this.terminalId}/command/`, commandData, {
        timeout: 10000,
        headers: {
          'Content-Type': 'application/json'
        }
      });
      return response.data;
    } catch (error) {
      console.error('远程命令执行失败:', error);
      this.handleApiError('remote_command', error);
      throw error;
    }
  }
  
  /**
   * 获取终端状态
   * @returns 终端状态
   */
  async getStatus(): Promise<TerminalStatus> {
    if (this.mode === 'local') {
      try {
        const response = await axios.get(`${this.localEndpoint}/api/status`, {
          timeout: 5000
        });
        return this.normalizeStatusData(response.data);
      } catch (error) {
        console.error('获取本地状态失败:', error);
        this.handleApiError('local_status', error);
        throw error;
      }
    } else {
      try {
        // 使用一致的复数形式URL
        const response = await axios.get(`/api/terminals/${this.terminalId}/status/`, {
          timeout: 8000
        });
        return this.normalizeStatusData(response.data);
      } catch (error) {
        // 如果API不可用，尝试通过命令获取
        try {
          console.warn('通过API获取远程状态失败，尝试使用命令获取');
          const commandResponse = await this.sendRemoteCommand({
            command: 'get_status',
            params: {},
            timestamp: new Date().toISOString()
          });
          return this.normalizeStatusData(commandResponse);
        } catch (cmdError) {
          console.error('获取远程状态失败:', error, cmdError);
          this.handleApiError('remote_status', error);
          throw error;
        }
      }
    }
  }
  
  /**
   * 标准化状态数据格式
   * @private
   */
  private normalizeStatusData(data: any): TerminalStatus {
    // 确保返回数据格式一致
    return {
      cameras: data.cameras || {},
      cpu_usage: data.cpu_usage || 0,
      memory_usage: data.memory_usage || 0,
      push_running: data.push_running || false,
      pull_running: data.pull_running || false,
      model_loaded: data.model_loaded || false,
      ...data
    };
  }
  
  /**
   * 获取终端配置
   * @returns 终端配置
   */
  async getConfig(): Promise<TerminalConfig> {
    if (this.mode === 'local') {
      try {
        const response = await axios.get(`${this.localEndpoint}/api/config`, {
          timeout: 5000
        });
        return this.normalizeConfigData(response.data);
      } catch (error) {
        console.error('获取本地配置失败:', error);
        this.handleApiError('local_config', error);
        throw error;
      }
    } else {
      // 通过命令获取配置
      try {
        const response = await this.sendRemoteCommand({
          command: 'get_config',
          params: {},
          timestamp: new Date().toISOString()
        });
        return this.normalizeConfigData(response);
      } catch (error) {
        console.error('获取远程配置失败:', error);
        this.handleApiError('remote_config', error);
        throw error;
      }
    }
  }
  
  /**
   * 标准化配置数据格式
   * @private
   */
  private normalizeConfigData(data: any): TerminalConfig {
    // 确保返回配置格式一致
    return {
      mode: data.mode || 'both',
      interval: data.interval || 5,
      cameras: data.cameras || {},
      save_image: typeof data.save_image === 'boolean' ? data.save_image : true,
      preload_model: typeof data.preload_model === 'boolean' ? data.preload_model : true,
      ...data
    };
  }
  
  /**
   * 保存终端配置
   * @param config - 配置对象
   * @returns 保存结果
   */
  async saveConfig(config: Partial<TerminalConfig>): Promise<any> {
    if (this.mode === 'local') {
      try {
        const response = await axios.post(`${this.localEndpoint}/api/config`, config, {
          timeout: 5000,
          headers: {
            'Content-Type': 'application/json'
          }
        });
        return response.data;
      } catch (error) {
        console.error('保存本地配置失败:', error);
        this.handleApiError('save_local_config', error);
        throw error;
      }
    } else {
      // 通过命令更新配置
      try {
        return await this.sendRemoteCommand({
          command: 'update_config',
          params: config,
          timestamp: new Date().toISOString()
        });
      } catch (error) {
        console.error('保存远程配置失败:', error);
        this.handleApiError('save_remote_config', error);
        throw error;
      }
    }
  }
  
  /**
   * 获取终端日志
   * @returns 日志数据
   */
  async getLogs(): Promise<LogEntry[]> {
    if (this.mode === 'local') {
      try {
        const response = await axios.get(`${this.localEndpoint}/api/logs`, {
          timeout: 5000
        });
        return this.normalizeLogData(response.data);
      } catch (error) {
        console.error('获取本地日志失败:', error);
        this.handleApiError('local_logs', error);
        throw error;
      }
    } else {
      // 尝试通过API获取日志
      try {
        const response = await axios.get(`/api/terminals/${this.terminalId}/logs/`, {
          timeout: 8000
        });
        return this.normalizeLogData(response.data);
      } catch (error) {
        // 如果API不可用，尝试通过命令获取
        try {
          console.warn('通过API获取远程日志失败，尝试使用命令获取');
          const commandResponse = await this.sendRemoteCommand({
            command: 'get_logs',
            params: {},
            timestamp: new Date().toISOString()
          });
          return this.normalizeLogData(commandResponse);
        } catch (cmdError) {
          console.error('获取远程日志失败:', error, cmdError);
          this.handleApiError('remote_logs', error);
          return []; // 返回空数组而非抛出错误，确保UI不会崩溃
        }
      }
    }
  }
  
  /**
   * 标准化日志数据格式
   * @private
   */
  private normalizeLogData(data: any[]): LogEntry[] {
    if (!Array.isArray(data)) return [];
    
    return data.map(log => ({
      timestamp: log.timestamp || new Date().toISOString(),
      level: log.level || 'info',
      message: log.message || '未知消息',
      source: log.source || '系统'
    }));
  }
  
  /**
   * 处理API错误
   * @private
   */
  private handleApiError(context: string, error: any): void {
    // 可以在这里添加错误上报逻辑
    const errorMessage = error.response ? 
      `${error.response.status}: ${JSON.stringify(error.response.data)}` : 
      error.message;
    
    console.error(`API错误 [${context}]: ${errorMessage}`);
  }
  
  /**
   * 构建WebSocket URL
   * @private
   */
  private getWebSocketUrl(): string {
    // 确定协议(ws/wss)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    
    if (this.mode === 'local') {
      // 本地模式统一使用标准格式
      return `ws://localhost:5000${this.wsPathTemplate.replace('{id}', this.localWsId)}`;
    } else {
      // 远程模式使用当前域名
      const host = window.location.host;
      return `${protocol}//${host}${this.wsPathTemplate.replace('{id}', String(this.terminalId))}`;
    }
  }
  
  /**
   * 建立WebSocket连接获取实时数据
   * @param callback - 接收消息的回调函数
   * @returns 回调ID
   */
  connectWebSocket(callback: WebSocketCallback): string | null {
    if (!callback) return null;
    
    // 生成唯一回调ID
    const callbackId = Date.now().toString() + Math.random().toString(36).substr(2, 5);
    this.wsCallbacks.set(callbackId, callback);
    
    // 如果已有活跃连接，无需再次连接
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return callbackId;
    }
    
    // 清理任何现有的重连计时器
    if (this.reconnectTimeout !== null) {
      window.clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    // 创建新连接
    this.createWebSocketConnection();
    
    return callbackId;
  }
  
  /**
   * 创建WebSocket连接
   * @private
   */
  private createWebSocketConnection(): void {
    try {
      // 断开现有连接
      this.disconnectWebSocket();
      
      // 获取统一格式的WebSocket URL
      const wsUrl = this.getWebSocketUrl();
      
      console.log(`尝试WebSocket连接: ${wsUrl}`);
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log('WebSocket连接已建立');
        this.reconnectAttempts = 0;
        this.isReconnecting = false;
        
        // 如果是远程模式，发送认证消息
        if (this.mode === 'remote' && this.terminalId) {
          this.ws.send(JSON.stringify({
            type: 'authenticate',
            terminal_id: this.terminalId
          }));
        }
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // 调用所有注册的回调
          this.wsCallbacks.forEach(cb => cb(data));
        } catch (e) {
          console.error('WebSocket消息解析错误:', e, event.data);
        }
      };
      
      this.ws.onclose = (event) => {
        console.log(`WebSocket连接已关闭 (代码: ${event.code})`);
        
        // 如果不是主动断开，则尝试重连
        if (this.wsCallbacks.size > 0 && !this.isReconnecting) {
          this.scheduleReconnect();
        }
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket错误:', error);
        
        // 错误后会触发onclose，所以在onclose中处理重连
      };
    } catch (error) {
      console.error('创建WebSocket连接失败:', error);
      
      // 尝试重连
      if (this.wsCallbacks.size > 0 && !this.isReconnecting) {
        this.scheduleReconnect();
      }
    }
  }
  
  /**
   * 安排WebSocket重连
   * @private
   */
  private scheduleReconnect(): void {
    if (this.isReconnecting || this.reconnectAttempts >= this.maxReconnectAttempts) {
      return;
    }
    
    this.isReconnecting = true;
    this.reconnectAttempts++;
    
    // 指数退避重连
    const delay = Math.min(30000, this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1));
    
    console.log(`计划WebSocket重连 (尝试 ${this.reconnectAttempts}/${this.maxReconnectAttempts}, 延迟 ${delay}ms)`);
    
    this.reconnectTimeout = window.setTimeout(() => {
      if (this.wsCallbacks.size > 0) {
        console.log('正在尝试重新连接WebSocket...');
        this.createWebSocketConnection();
      }
      this.reconnectTimeout = null;
    }, delay);
  }
  
  /**
   * 移除WebSocket回调
   * @param callbackId - 回调ID
   */
  removeWebSocketCallback(callbackId: string): void {
    if (this.wsCallbacks.has(callbackId)) {
      this.wsCallbacks.delete(callbackId);
      
      // 如果没有回调了，断开连接
      if (this.wsCallbacks.size === 0) {
        this.disconnectWebSocket();
      }
    }
  }
  
  /**
   * 断开WebSocket连接
   */
  disconnectWebSocket(): void {
    // 清理重连计时器
    if (this.reconnectTimeout !== null) {
      window.clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.ws) {
      // 只有在连接打开或正在连接时才需要close()
      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close();
      }
      this.ws = null;
    }
    
    this.isReconnecting = false;
  }
}

// 导出服务实例
export const terminalService = new TerminalService();
