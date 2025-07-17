import axios from 'axios';

/**
 * 终端通信服务 - 支持本地直连和远程连接两种模式
 */
class TerminalService {
  constructor() {
    this.mode = 'remote'; // 'remote' 或 'local'
    this.terminalId = null;
    this.localEndpoint = 'http://localhost:5000'; // 本地终端API端点
    this.ws = null; // WebSocket连接
    this.wsCallbacks = new Map(); // 回调函数映射
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectTimeout = null;
    this.reconnectDelay = 2000; // 初始重连延迟(ms)
    this.isReconnecting = false;
  }
  
  /**
   * 设置连接模式
   * @param {string} mode - 连接模式: 'local' 或 'remote'
   * @param {number|null} terminalId - 远程模式下的终端ID
   */
  setMode(mode, terminalId = null) {
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
   * @returns {Promise<boolean>} 是否可用
   */
  async detectLocalTerminal() {
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
   * @param {string} command - 命令名称
   * @param {Object} params - 命令参数
   * @returns {Promise<Object>} 命令执行结果
   */
  async sendCommand(command, params = {}) {
    // 统一命令格式
    const commandData = {
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
  async sendLocalCommand(commandData) {
    try {
      // 根据命令类型选择合适的终端API
      let endpoint = `${this.localEndpoint}/api/control`;
      let requestData = {
        action: commandData.command,
        ...commandData.params
      };
      
      // 特殊命令处理
      if (commandData.command === 'update_config') {
        endpoint = `${this.localEndpoint}/api/config`;
        requestData = commandData.params;
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
  async sendRemoteCommand(commandData) {
    if (!this.terminalId) {
      throw new Error('远程模式下必须提供终端ID');
    }
    
    try {
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
   * @returns {Promise<Object>} 终端状态
   */
  async getStatus() {
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
        // 先尝试通过API获取状态
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
  normalizeStatusData(data) {
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
   * @returns {Promise<Object>} 终端配置
   */
  async getConfig() {
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
  normalizeConfigData(data) {
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
   * @param {Object} config - 配置对象
   * @returns {Promise<Object>} 保存结果
   */
  async saveConfig(config) {
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
   * @returns {Promise<Array>} 日志数据
   */
  async getLogs() {
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
  normalizeLogData(data) {
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
  handleApiError(context, error) {
    // 可以在这里添加错误上报逻辑
    const errorMessage = error.response ? 
      `${error.response.status}: ${JSON.stringify(error.response.data)}` : 
      error.message;
    
    console.error(`API错误 [${context}]: ${errorMessage}`);
  }
  
  /**
   * 建立WebSocket连接获取实时数据
   * @param {Function} callback - 接收消息的回调函数
   * @returns {string} 回调ID
   */
  connectWebSocket(callback) {
    if (!callback) return null;
    
    // 生成唯一回调ID
    const callbackId = Date.now().toString() + Math.random().toString(36).substr(2, 5);
    this.wsCallbacks.set(callbackId, callback);
    
    // 如果已有活跃连接，无需再次连接
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return callbackId;
    }
    
    // 清理任何现有的重连计时器
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
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
  createWebSocketConnection() {
    try {
      // 断开现有连接
      this.disconnectWebSocket();
      
      let wsUrl;
      if (this.mode === 'local') {
        // 连接本地WebSocket - 尝试检测是否支持SocketIO
        wsUrl = `ws://localhost:5000/ws`;
      } else {
        // 连接远程WebSocket
        wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/terminal/${this.terminalId}/`;
      }
      
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
  scheduleReconnect() {
    if (this.isReconnecting || this.reconnectAttempts >= this.maxReconnectAttempts) {
      return;
    }
    
    this.isReconnecting = true;
    this.reconnectAttempts++;
    
    // 指数退避重连
    const delay = Math.min(30000, this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1));
    
    console.log(`计划WebSocket重连 (尝试 ${this.reconnectAttempts}/${this.maxReconnectAttempts}, 延迟 ${delay}ms)`);
    
    this.reconnectTimeout = setTimeout(() => {
      if (this.wsCallbacks.size > 0) {
        console.log('正在尝试重新连接WebSocket...');
        this.createWebSocketConnection();
      }
    }, delay);
  }
  
  /**
   * 移除WebSocket回调
   * @param {string} callbackId - 回调ID
   */
  removeWebSocketCallback(callbackId) {
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
  disconnectWebSocket() {
    // 清理重连计时器
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
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
