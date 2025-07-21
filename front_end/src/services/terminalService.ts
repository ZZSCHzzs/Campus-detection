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
export type MessageCallback = (data: any) => void;

/**
 * 终端模型接口
 */
export interface Terminal {
  id: number;
  name: string;
  status: boolean;
  last_active?: string;
  cpu_usage?: number;
  memory_usage?: number;
  [key: string]: any;
}

/**
 * 环境信息接口
 */
export interface EnvironmentInfo {
  type: 'detector' | 'server';  // 环境类型
  version: string;              // 版本
  name: string;                 // 环境名称
  id: number;                   // 环境ID
  features: {                   // 功能支持
    local_detection: boolean;   // 本地检测
    websocket: boolean;         // WebSocket支持
    push_mode: boolean;         // 推送模式
    pull_mode: boolean;         // 拉取模式
  };
  terminal_mode?: 'local' | 'remote'; // 终端模式
}

/**
 * 终端服务类 - 负责终端通信管理
 * 
 * 支持两种模式：
 * 1. 本地模式：直接与本地Flask检测端通信，使用Socket.IO
 * 2. 远程模式：通过Django服务器与远程终端通信，使用WebSocket
 */
class TerminalService {
  // 基本配置
  private mode: 'local' | 'remote' = 'remote';
  private terminalId: number | null = null;
  private localEndpoint = 'http://localhost:5000';
  private remoteWsHost: string = 'smarthit.top'; // 固定使用远程服务端地址
  private remoteUseSSL: boolean = true; // 远程连接默认使用SSL
  
  // 连接状态
  private connected = false;
  
  // 消息回调
  private messageCallbacks: Map<string, MessageCallback> = new Map();
  
  // 本地模式Socket.IO连接
  private socketIO: any = null;
  
  // 远程模式WebSocket连接
  private webSocket: WebSocket | null = null;
  
  // 重连相关
  private reconnecting = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimer: number | null = null;
  
  // 环境信息缓存
  private environmentInfo: EnvironmentInfo | null = null;
  
  // 最近的状态缓存
  private lastStatus: TerminalStatus | null = null;
  
  /**
   * 初始化终端服务
   */
  constructor() {
    // 尝试从localStorage获取上次的配置
    this.loadSavedConfig();
  }
  
  /**
   * 从localStorage加载保存的配置
   * @private
   */
  private loadSavedConfig() {
    try {
      const savedMode = localStorage.getItem('terminal_mode');
      const savedId = localStorage.getItem('terminal_id');
      const savedEndpoint = localStorage.getItem('local_endpoint');
      
      if (savedMode) this.mode = savedMode as 'local' | 'remote';
      if (savedId) this.terminalId = parseInt(savedId);
      if (savedEndpoint) this.localEndpoint = savedEndpoint;
    } catch (e) {
      console.warn('无法加载保存的终端配置', e);
    }
  }
  
  /**
   * 保存当前连接配置到localStorage
   * @private
   */
  private saveConnectionConfig() {
    try {
      localStorage.setItem('terminal_mode', this.mode);
      if (this.terminalId !== null) {
        localStorage.setItem('terminal_id', this.terminalId.toString());
      }
      localStorage.setItem('local_endpoint', this.localEndpoint);
    } catch (e) {
      console.warn('无法保存终端配置', e);
    }
  }
  
  /**
   * 设置终端模式
   * @param mode 终端模式 - local或remote
   * @param terminalId 远程模式下的终端ID
   * @param serverUrl 远程模式下的服务器URL
   */
  async setMode(mode: 'local' | 'remote', terminalId?: number, serverUrl?: string): Promise<boolean> {
    // 如果模式没变并且ID也没变，则不进行任何操作
    if (this.mode === mode && (mode === 'local' || this.terminalId === terminalId)) {
      return false;
    }
    
    console.log(`切换终端模式: ${this.mode} -> ${mode}`);
    
    const oldMode = this.mode;
    this.mode = mode;
    
    // 断开现有连接
    this.disconnect();
    
    if (mode === 'remote') {
      // 远程模式需要终端ID
      this.terminalId = terminalId || 1;
    } else {
      // 本地模式不需要终端ID
      this.terminalId = null;
      
      // 如果提供了新的本地终端URL，更新它
      if (serverUrl && serverUrl !== this.localEndpoint) {
        this.localEndpoint = serverUrl;
      }
    }
    
    // 保存新配置
    this.saveConnectionConfig();
    
    // 如果是从本地切换到远程，通知本地终端
    if (oldMode === 'local' && mode === 'remote' && serverUrl) {
      try {
        await axios.post(`${this.localEndpoint}/api/switch_mode`, {
          mode: 'remote',
          server_url: serverUrl,
          terminal_id: this.terminalId
        });
        console.log('已通知本地终端切换到远程模式');
      } catch (error) {
        console.error('通知本地终端切换模式失败:', error);
      }
    }
    
    // 如果是从远程切换到本地，通知本地终端
    if (oldMode === 'remote' && mode === 'local') {
      try {
        await axios.post(`${this.localEndpoint}/api/switch_mode`, {
          mode: 'local'
        });
        console.log('已通知本地终端切换到本地模式');
      } catch (error) {
        console.error('通知本地终端切换模式失败:', error);
      }
    }
    
    // 返回模式是否成功切换
    return true;
  }
  
  /**
   * 连接到终端
   * @param callback 接收消息的回调函数
   * @returns 回调ID，用于后续移除回调
   */
  connect(callback: MessageCallback): string {
    if (!callback) {
      throw new Error('必须提供消息回调函数');
    }
    
    // 生成唯一回调ID
    const callbackId = Date.now().toString() + Math.random().toString(36).substring(2, 9);
    this.messageCallbacks.set(callbackId, callback);
    
    // 根据模式选择连接方法
    if (this.mode === 'local') {
      this.connectLocalSocketIO();
    } else {
      this.connectRemoteWebSocket();
    }
    
    return callbackId;
  }
  
  /**
   * 断开连接
   * @param callbackId 可选的回调ID，如果提供，只移除该回调而不断开连接
   */
  disconnect(callbackId?: string): void {
    // 如果提供了回调ID，只移除该回调
    if (callbackId && this.messageCallbacks.has(callbackId)) {
      this.messageCallbacks.delete(callbackId);
      
      // 如果还有其他回调，不断开连接
      if (this.messageCallbacks.size > 0) {
        return;
      }
    }
    
    // 没有活跃回调，断开所有连接
    
    // 断开Socket.IO连接
    if (this.socketIO) {
      try {
        console.log('断开Socket.IO连接');
        this.socketIO.off(); // 移除所有事件监听
        this.socketIO.disconnect();
      } catch (e) {
        console.error('断开Socket.IO连接时出错:', e);
      } finally {
        this.socketIO = null;
      }
    }
    
    // 断开WebSocket连接
    if (this.webSocket) {
      try {
        console.log('断开WebSocket连接');
        if (this.webSocket.readyState === WebSocket.OPEN || 
            this.webSocket.readyState === WebSocket.CONNECTING) {
          this.webSocket.close();
        }
      } catch (e) {
        console.error('断开WebSocket连接时出错:', e);
      } finally {
        this.webSocket = null;
      }
    }
    
    // 清理重连计时器
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    // 重置连接状态
    this.connected = false;
    this.reconnecting = false;
    this.reconnectAttempts = 0;
    
    // 如果没有提供callbackId，清空所有回调
    if (!callbackId) {
      this.messageCallbacks.clear();
    }
  }
  
  /**
   * 连接到本地终端的Socket.IO
   * @private
   */
  private connectLocalSocketIO(): void {
    // 避免重复连接
    if (this.socketIO) {
      console.log('Socket.IO已连接，无需重新连接');
      return;
    }
    
    console.log(`正在连接本地Socket.IO: ${this.localEndpoint}`);
    
    try {
      // 动态导入socket.io-client
      import('socket.io-client').then(io => {
        // 创建Socket.IO连接
        this.socketIO = io.default(this.localEndpoint, {
          reconnection: true,                // 启用自动重连
          reconnectionAttempts: 10,          // 最大重连次数
          reconnectionDelay: 1000,           // 初始重连延迟
          reconnectionDelayMax: 5000,        // 最大重连延迟
          timeout: 10000,                    // 连接超时
          transports: ['websocket', 'polling'] // 传输方式
        });
        
        // 连接事件
        this.socketIO.on('connect', () => {
          console.log('已连接到本地Socket.IO');
          this.connected = true;
          this.broadcastMessage({
            type: 'connection_status',
            data: { connected: true, mode: 'local' },
            timestamp: new Date().toISOString()
          });
          
          // 发送初始化消息
          this.socketIO.emit('client_connected', {
            client_id: 'web_client',
            timestamp: new Date().toISOString()
          });
        });
        
        // 连接错误
        this.socketIO.on('connect_error', (error: any) => {
          console.error('Socket.IO连接错误:', error);
          this.broadcastMessage({
            type: 'error',
            data: { message: `连接错误: ${error.message}`, mode: 'local' },
            timestamp: new Date().toISOString()
          });
        });
        
        // 系统状态
        this.socketIO.on('system_status', (data: any) => {
          this.broadcastMessage({
            type: 'status',
            data: data,
            timestamp: new Date().toISOString()
          });
        });
        
        // 系统更新
        this.socketIO.on('system_update', (data: any) => {
          this.broadcastMessage({
            type: 'update',
            data: data,
            timestamp: new Date().toISOString()
          });
        });
        
        // 系统消息
        this.socketIO.on('system_message', (data: any) => {
          this.broadcastMessage({
            type: 'message',
            data: data,
            timestamp: new Date().toISOString()
          });
        });
        
        // 系统错误
        this.socketIO.on('system_error', (data: any) => {
          this.broadcastMessage({
            type: 'error',
            data: data,
            timestamp: new Date().toISOString()
          });
        });
        
        // 断开连接
        this.socketIO.on('disconnect', (reason: string) => {
          console.log(`Socket.IO断开连接: ${reason}`);
          this.connected = false;
          this.broadcastMessage({
            type: 'connection_status',
            data: { connected: false, reason: reason, mode: 'local' },
            timestamp: new Date().toISOString()
          });
        });
      }).catch(err => {
        console.error('加载socket.io-client失败:', err);
        this.broadcastMessage({
          type: 'error',
          data: { message: `加载Socket.IO客户端失败: ${err.message}`, mode: 'local' },
          timestamp: new Date().toISOString()
        });
      });
    } catch (error) {
      console.error('初始化Socket.IO连接失败:', error);
      this.broadcastMessage({
        type: 'error',
        data: { message: `初始化Socket.IO失败: ${error}`, mode: 'local' },
        timestamp: new Date().toISOString()
      });
    }
  }
  
  /**
   * 连接到远程终端的WebSocket
   * @private
   */
  private connectRemoteWebSocket(): void {
    // 避免重复连接
    if (this.webSocket && this.webSocket.readyState === WebSocket.OPEN) {
      console.log('WebSocket已连接，无需重新连接');
      return;
    }
    
    // 避免同时进行多次重连
    if (this.reconnecting) {
      console.log('WebSocket正在重连中，跳过此次连接请求');
      return;
    }
    
    // 构建WebSocket URL - 使用固定的远程地址
    const protocol = this.remoteUseSSL ? 'wss:' : 'ws:';
    const host = this.remoteWsHost; // 始终使用固定的远程主机
    const terminalId = this.terminalId || 1;
    // 确保URL格式正确 - 始终以斜杠结尾
    const wsUrl = `${protocol}//${host}/ws/terminal/${terminalId}/`;
    
    console.log(`正在连接远程WebSocket: ${wsUrl}`);
    
    try {
      // 创建WebSocket连接
      this.webSocket = new WebSocket(wsUrl);
      
      // 连接成功
      this.webSocket.onopen = () => {
        console.log('已连接到远程WebSocket');
        this.connected = true;
        this.reconnecting = false;
        this.reconnectAttempts = 0;
        
        this.broadcastMessage({
          type: 'connection_status',
          data: { connected: true, mode: 'remote' },
          timestamp: new Date().toISOString()
        });
        
        // 连接后立即请求状态更新
        this.requestStatusUpdate();
      };
      
      // 接收消息
      this.webSocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.broadcastMessage(data);
        } catch (error) {
          console.error('解析WebSocket消息失败:', error);
        }
      };
      
      // 连接关闭
      this.webSocket.onclose = (event) => {
        console.log(`WebSocket连接关闭: ${event.code} - ${event.reason}`);
        this.connected = false;
        this.webSocket = null;
        
        this.broadcastMessage({
          type: 'connection_status',
          data: { 
            connected: false, 
            code: event.code,
            reason: event.reason,
            mode: 'remote'
          },
          timestamp: new Date().toISOString()
        });
        
        // 如果不是主动关闭，尝试重连
        if (!event.wasClean && this.messageCallbacks.size > 0) {
          this.scheduleReconnect();
        }
      };
      
      // 连接错误
      this.webSocket.onerror = (event) => {
        console.error('WebSocket连接错误:', event);
        
        this.broadcastMessage({
          type: 'error',
          data: { message: 'WebSocket连接错误', mode: 'remote' },
          timestamp: new Date().toISOString()
        });
      };
    } catch (error) {
      console.error('创建WebSocket连接失败:', error);
      
      this.broadcastMessage({
        type: 'error',
        data: { message: `创建WebSocket连接失败: ${error}`, mode: 'remote' },
        timestamp: new Date().toISOString()
      });
      
      // 尝试重连
      this.scheduleReconnect();
    }
  }
  
  /**
   * 处理WebSocket状态更新
   * @param data 状态数据
   * @private
   */
  private handleStatusUpdate(data: any): void {
    // 通知所有回调
    this.broadcastMessage({
      type: 'status',
      ...data,
      timestamp: data.timestamp || new Date().toISOString()
    });
    
    // 缓存最新状态
    this.lastStatus = {
      ...this.lastStatus,
      ...data.data || data,
      lastUpdated: new Date().toISOString()
    };
  }

  /**
   * 请求终端状态更新
   */
  requestStatusUpdate(): void {
    if (this.mode === 'remote') {
      this.requestRemoteStatusUpdate();
    } else {
      this.requestLocalStatusUpdate();
    }
  }

  /**
   * 请求远程终端状态更新
   * @private
   */
  private requestRemoteStatusUpdate(): void {
    if (!this.connected || !this.webSocket || this.webSocket.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket未连接，无法请求状态更新');
      return;
    }
    
    try {
      const message = JSON.stringify({
        type: 'request',
        request: 'get_status',
        timestamp: new Date().toISOString()
      });
      
      this.webSocket.send(message);
      console.log('已发送远程状态更新请求');
    } catch (error) {
      console.error('发送状态更新请求失败:', error);
    }
  }

  /**
   * 请求本地终端状态更新
   * @private
   */
  private requestLocalStatusUpdate(): void {
    if (!this.socketIO) {
      console.warn('Socket.IO未连接，无法请求本地状态更新');
      return;
    }
    
    try {
      this.socketIO.emit('request_status', {
        client_id: 'web_client',
        timestamp: new Date().toISOString()
      });
      console.log('已发送本地状态更新请求');
    } catch (error) {
      console.error('发送本地状态更新请求失败:', error);
    }
  }
  
  /**
   * 安排WebSocket重连
   * @private
   */
  private scheduleReconnect(): void {
    // 避免同时多次重连
    if (this.reconnecting) {
      return;
    }
    
    this.reconnecting = true;
    this.reconnectAttempts++;
    
    // 超过最大重试次数
    if (this.reconnectAttempts > this.maxReconnectAttempts) {
      console.log(`已达到最大重连次数(${this.maxReconnectAttempts})，停止重连`);
      this.reconnecting = false;
      
      this.broadcastMessage({
        type: 'error',
        data: { message: `WebSocket重连失败，已达到最大尝试次数: ${this.maxReconnectAttempts}`, mode: 'remote' },
        timestamp: new Date().toISOString()
      });
      
      return;
    }
    
    // 计算重连延迟（指数退避）
    const delay = Math.min(30000, 1000 * Math.pow(1.5, this.reconnectAttempts - 1));
    
    console.log(`安排WebSocket重连，${delay}ms后尝试 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    // 清理现有重连计时器
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
    }
    
    // 设置新的重连计时器
    this.reconnectTimer = window.setTimeout(() => {
      console.log(`执行WebSocket重连尝试 #${this.reconnectAttempts}`);
      this.reconnectTimer = null;
      this.connectRemoteWebSocket();
    }, delay);
  }
  
  /**
   * 向所有回调广播消息
   * @param message 要广播的消息
   * @private
   */
  private broadcastMessage(message: any): void {
    // 创建一个回调副本，防止在迭代过程中修改
    const callbacks = [...this.messageCallbacks.entries()];
    
    for (const [id, callback] of callbacks) {
      try {
        if (this.messageCallbacks.has(id)) { // 确保回调仍然存在
          callback(message);
        }
      } catch (error) {
        console.error('执行消息回调出错:', error);
      }
    }
  }
  
  /**
   * 发送命令到终端
   * @param command 命令名称
   * @param params 命令参数
   * @returns 命令执行结果
   */
  async sendCommand(command: string, params: Record<string, any> = {}): Promise<any> {
    // 构建命令数据
    const commandData: TerminalCommand = {
      command,
      params,
      timestamp: new Date().toISOString()
    };
    
    // 根据模式选择发送方法
    if (this.mode === 'local') {
      return this.sendLocalCommand(commandData);
    } else {
      return this.sendRemoteCommand(commandData);
    }
  }
  
  /**
   * 发送命令到本地终端
   * @param commandData 命令数据
   * @private
   */
  private async sendLocalCommand(commandData: TerminalCommand): Promise<any> {
    try {
      // 根据命令类型选择API路径
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
      
      // 发送命令
      const response = await axios.post(endpoint, requestData, {
        timeout: 5000,
        headers: { 'Content-Type': 'application/json' }
      });
      
      return response.data;
    } catch (error) {
      console.error('发送本地命令失败:', error);
      throw error;
    }
  }
  
  /**
   * 发送命令到远程终端
   * @param commandData 命令数据
   * @private
   */
  private async sendRemoteCommand(commandData: TerminalCommand): Promise<any> {
    if (!this.terminalId) {
      console.warn('未设置终端ID，使用默认值1');
      this.terminalId = 1;
    }
    
    try {
      // 使用固定的远程服务器地址
      const baseUrl = this.remoteUseSSL ? 'https://' : 'http://';
      const apiUrl = `${baseUrl}${this.remoteWsHost}/api/terminals/${this.terminalId}/command/`;
      
      // 发送命令
      const response = await axios.post(apiUrl, commandData, {
        timeout: 10000,
        headers: { 'Content-Type': 'application/json' }
      });
      
      return response.data;
    } catch (error) {
      console.error('发送远程命令失败:', error);
      throw error;
    }
  }
  
  /**
   * 获取终端状态
   * @returns 终端状态
   */
  async getStatus(): Promise<TerminalStatus> {
    try {
      if (this.mode === 'local') {
        const response = await axios.get(`${this.localEndpoint}/api/status`, { timeout: 5000 });
        return this.normalizeStatusData(response.data);
      } else {
        // 使用固定的远程服务器地址
        const baseUrl = this.remoteUseSSL ? 'https://' : 'http://';
        const apiUrl = `${baseUrl}${this.remoteWsHost}/api/terminals/${this.terminalId}/status/`;
        const response = await axios.get(apiUrl, { timeout: 8000 });
        return this.normalizeStatusData(response.data);
      }
    } catch (error) {
      console.error(`获取${this.mode === 'local' ? '本地' : '远程'}终端状态失败:`, error);
      throw error;
    }
  }
  
  /**
   * 标准化状态数据格式
   * @private
   */
  private normalizeStatusData(data: any): TerminalStatus {
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
    try {
      if (this.mode === 'local') {
        const response = await axios.get(`${this.localEndpoint}/api/config`, { timeout: 5000 });
        return this.normalizeConfigData(response.data);
      } else {
        const response = await this.sendRemoteCommand({
          command: 'get_config',
          params: {}
        });
        return this.normalizeConfigData(response);
      }
    } catch (error) {
      console.error(`获取${this.mode === 'local' ? '本地' : '远程'}终端配置失败:`, error);
      throw error;
    }
  }
  
  /**
   * 标准化配置数据格式
   * @private
   */
  private normalizeConfigData(data: any): TerminalConfig {
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
   * @param config 要保存的配置
   * @returns 保存结果
   */
  async saveConfig(config: Partial<TerminalConfig>): Promise<any> {
    try {
      if (this.mode === 'local') {
        const response = await axios.post(`${this.localEndpoint}/api/config`, config, {
          timeout: 5000,
          headers: { 'Content-Type': 'application/json' }
        });
        return response.data;
      } else {
        return await this.sendRemoteCommand({
          command: 'update_config',
          params: config
        });
      }
    } catch (error) {
      console.error(`保存${this.mode === 'local' ? '本地' : '远程'}终端配置失败:`, error);
      throw error;
    }
  }
  
  /**
   * 获取终端日志
   * @returns 日志数据
   */
  async getLogs(): Promise<LogEntry[]> {
    try {
      if (this.mode === 'local') {
        const response = await axios.get(`${this.localEndpoint}/api/logs`, { timeout: 5000 });
        return this.normalizeLogData(response.data);
      } else {
        // 使用固定的远程服务器地址
        const baseUrl = this.remoteUseSSL ? 'https://' : 'http://';
        const apiUrl = `${baseUrl}${this.remoteWsHost}/api/terminals/${this.terminalId}/logs/`;
        const response = await axios.get(apiUrl, { timeout: 8000 });
        return this.normalizeLogData(response.data);
      }
    } catch (error) {
      console.error(`获取${this.mode === 'local' ? '本地' : '远程'}终端日志失败:`, error);
      
      // 日志获取失败返回空数组而不是抛出错误
      return [];
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
   * 获取终端详情
   * @returns 终端详情
   */
  async getTerminalDetails(): Promise<Terminal> {
    try {
      if (this.mode === 'local') {
        // 本地模式获取终端信息
        const infoResponse = await axios.get(`${this.localEndpoint}/api/info`, { timeout: 3000 });
        const statusResponse = await axios.get(`${this.localEndpoint}/api/status`, { timeout: 3000 });
        
        return {
          id: infoResponse.data.id || 0,
          name: infoResponse.data.name || '本地终端',
          status: true,
          cpu_usage: statusResponse.data.cpu_usage || 0,
          memory_usage: statusResponse.data.memory_usage || 0,
          version: infoResponse.data.version || 'unknown'
        };
      } else {
        // 远程模式获取终端详情 - 使用固定的远程服务器地址
        const baseUrl = this.remoteUseSSL ? 'https://' : 'http://';
        const apiUrl = `${baseUrl}${this.remoteWsHost}/api/terminals/${this.terminalId}/`;
        const response = await axios.get(apiUrl);
        
        return {
          id: response.data.id,
          name: response.data.name || `终端 #${response.data.id}`,
          status: response.data.status || false,
          cpu_usage: response.data.cpu_usage || 0,
          memory_usage: response.data.memory_usage || 0,
          last_active: response.data.last_active
        };
      }
    } catch (error) {
      console.error(`获取${this.mode === 'local' ? '本地' : '远程'}终端详情失败:`, error);
      
      // 返回最小可用的终端数据
      return {
        id: this.terminalId || 0,
        name: this.mode === 'local' ? '本地终端' : `终端 #${this.terminalId || 1}`,
        status: false
      };
    }
  }
  
  /**
   * 自动检测环境并设置合适的模式
   * @returns 环境信息
   */
  async autoDetectEnvironment(): Promise<EnvironmentInfo> {
    // 如果已有环境信息，直接返回
    if (this.environmentInfo) {
      return this.environmentInfo;
    }
    
    try {
      // 首先尝试检测本地环境
      const isLocalAvailable = await this.isLocalAvailable();
      
      if (isLocalAvailable) {
        // 本地环境可用，获取环境信息
        try {
          const response = await axios.get(`${this.localEndpoint}/api/environment`, { timeout: 2000 });
          const envInfo: EnvironmentInfo = response.data;
          
          // 根据环境信息设置模式
          if (envInfo.terminal_mode === 'remote') {
            // 如果本地终端报告它处于远程模式，则跟随切换
            console.log('本地终端处于远程模式，跟随切换');
            await this.setMode('remote', envInfo.id);
          } else {
            // 否则使用本地模式
            await this.setMode('local');
          }
          
          // 缓存环境信息
          this.environmentInfo = envInfo;
          return envInfo;
        } catch (error) {
          console.warn('获取本地环境信息失败:', error);
        }
      }
      
      // 本地环境不可用或获取信息失败，尝试获取远程环境信息
      try {
        // 使用固定的远程服务器地址
        const baseUrl = this.remoteUseSSL ? 'https://' : 'http://';
        const apiUrl = `${baseUrl}${this.remoteWsHost}/api/environment`;
        const apiResponse = await axios.get(apiUrl, { timeout: 5000 });
        const envInfo: EnvironmentInfo = apiResponse.data;
        
        // 设置为远程模式
        await this.setMode('remote', this.terminalId || envInfo.id);
        
        // 缓存环境信息
        this.environmentInfo = envInfo;
        return envInfo;
      } catch (error) {
        console.warn('获取远程环境信息失败:', error);
        
        // 创建默认环境信息
        const defaultEnv: EnvironmentInfo = {
          type: 'server',
          version: 'unknown',
          name: '未知环境',
          id: 1,
          features: {
            local_detection: false,
            websocket: true,
            push_mode: true,
            pull_mode: true
          }
        };
        
        // 默认使用远程模式
        await this.setMode('remote', 1);
        
        // 缓存环境信息
        this.environmentInfo = defaultEnv;
        return defaultEnv;
      }
    } catch (error) {
      console.error('自动检测环境失败:', error);
      throw error;
    }
  }
  
  /**
   * 检查本地终端是否可用
   * @returns 是否可用
   * @private
   */
  private async isLocalAvailable(): Promise<boolean> {
    try {
      const response = await axios.get(`${this.localEndpoint}/api/status`, { timeout: 2000 });
      return response.status === 200;
    } catch (error) {
      return false;
    }
  }
  
  /**
   * 获取当前连接状态
   * @returns 连接状态
   */
  getConnectionState(): { connected: boolean, mode: 'local' | 'remote' } {
    return {
      connected: this.connected,
      mode: this.mode
    };
  }
  
  /**
   * 获取当前终端ID
   * @returns 终端ID，如果是本地模式则返回null
   */
  getTerminalId(): number | null {
    return this.terminalId;
  }
  
  /**
   * 设置远程WebSocket服务器地址
   * @param host WebSocket服务器地址（不包括协议和路径）
   */
  setRemoteWsHost(host: string): void {
    if (host && host !== this.remoteWsHost) {
      console.log(`设置远程WebSocket主机: ${host}`);
      this.remoteWsHost = host;
      // 如果当前是远程模式且已连接，重新连接以应用新主机
      if (this.mode === 'remote' && this.connected) {
        this.disconnect();
        this.connectRemoteWebSocket();
      }
    }
  }
  
  /**
   * 获取当前使用的WebSocket主机
   * @returns 当前WebSocket主机
   */
  getRemoteWsHost(): string {
    return this.remoteWsHost || window.location.host;
  }
}

// 导出单例实例
export const terminalService = new TerminalService();
