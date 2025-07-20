<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { terminalService } from '../services/terminalService';
import { terminalService as terminalsService } from '../services/apiService';
import { debounce } from 'lodash';

const route = useRoute();
const router = useRouter();

// 连接模式
const connectionMode = ref('remote');
const localAvailable = ref(false);
const loading = ref(true);
const wsCallbackId = ref(null);

// 终端信息
const terminal = reactive({
  id: null,
  name: '终端',
  status: false,
});

// 终端状态
const status = reactive({
  cameras: {},
  cpu_usage: 0,
  memory_usage: 0,
  push_running: false,
  pull_running: false,
  model_loaded: false
});

// 终端配置
const config = reactive({
  mode: 'both',
  interval: 5,
  cameras: [],
  save_image: true,
  preload_model: true
});

// 原始配置（用于重置）
const originalConfig = reactive({});

// 新摄像头信息
const newCamera = reactive({
  id: '',
  url: ''
});

// 终端日志
const logs = ref([]);

// 添加终端列表和终端选择
const terminalList = ref([]);
const selectedTerminalId = ref(null);

// 添加终端详细信息数据
const terminalDetails = reactive({
  id: null,
  name: '终端',
  status: false,
  cpu_usage: 0,
  memory_usage: 0,
  last_active: null
});

// 环境信息
const environmentInfo = ref(null);

// 加载终端列表
const loadTerminalList = async () => {
  try {
    const data = await terminalsService.getAll();
    terminalList.value = data;
    return data;
  } catch (error) {
    console.error('加载终端列表失败:', error);
    ElMessage.error('加载终端列表失败');
    return [];
  }
};

// 加载终端详细信息
const loadTerminalDetails = async () => {
  try {
    const details = await terminalService.getTerminalDetails();
    Object.assign(terminalDetails, details);
    
    // 更新终端基本信息
    terminal.id = terminalDetails.id;
    terminal.name = terminalDetails.name;
    terminal.status = terminalDetails.status;
    
    return details;
  } catch (error) {
    console.error('加载终端详细信息失败:', error);
    ElMessage.warning('无法获取终端详细信息');
    return null;
  }
};

// 加载终端状态
const loadTerminalStatus = async () => {
  try {
    const data = await terminalService.getStatus();
    Object.assign(status, data);
    
    // 更新终端状态
    terminal.status = status.model_loaded || status.push_running || status.pull_running;
    
    return data;
  } catch (error) {
    console.error('加载终端状态失败:', error);
    ElMessage.error('加载终端状态失败');
    return null;
  }
};

// 加载终端配置
const loadTerminalConfig = async () => {
  try {
    const configData = await terminalService.getConfig();
    
    // 更新配置数据
    config.mode = configData.mode || 'both';
    config.interval = configData.interval || 5;
    config.save_image = configData.save_image !== undefined ? configData.save_image : true;
    config.preload_model = configData.preload_model !== undefined ? configData.preload_model : true;
    
    // 转换摄像头数据格式
    config.cameras = Object.entries(configData.cameras || {}).map(([id, url]) => ({
      id: parseInt(id),
      url
    }));
    
    // 保存原始配置用于重置
    Object.assign(originalConfig, JSON.parse(JSON.stringify(config)));
    
    return configData;
  } catch (error) {
    console.error('加载终端配置失败:', error);
    ElMessage.error('加载终端配置失败');
    return null;
  }
};

// 加载日志
const loadLogs = async () => {
  try {
    const logsData = await terminalService.getLogs();
    logs.value = Array.isArray(logsData) ? logsData : [];
    return logsData;
  } catch (error) {
    console.error('加载日志失败:', error);
    ElMessage.error('加载日志失败');
    return [];
  }
};

// 设置WebSocket连接
const setupWebSocket = () => {
  if (wsCallbackId.value) {
    terminalService.disconnect(wsCallbackId.value);
  }
  
  wsCallbackId.value = terminalService.connect(handleWebSocketMessage);
};

// 使用防抖处理 WebSocket 消息
const handleWebSocketMessage = (data) => {
  // 处理连接状态消息
  if (data.type === 'connection_status') {
    processConnectionStatus(data);
    return;
  }
  
  // 处理日志消息 - 使用防抖减少更新频率
  if (data.type === 'new_log' || data.message) {
    processLogMessage(data);
    return;
  }
  
  // 处理状态更新 - 使用防抖减少更新频率
  if (data.type === 'status' || data.type === 'system_update' || data.type === 'system_resources') {
    debouncedProcessStatusUpdate(data);
    return;
  }
  
  // 处理相机状态
  if (data.type === 'camera_status') {
    processCameraStatus(data);
    return;
  }
  
  // 处理检测结果
  if (data.type === 'detection_result') {
    // 可以在UI中显示最新检测结果
    console.log('检测结果:', data);
  }
};

// 处理连接状态
const processConnectionStatus = (data) => {
  // 处理连接状态变化
  if (data.data && typeof data.data.connected !== 'undefined') {
    terminal.status = data.data.connected;
  }
};

// 处理日志消息
const processLogMessage = (data) => {
  const logEntry = {
    timestamp: data.timestamp || new Date().toISOString(),
    level: data.level || 'info',
    message: data.message || JSON.stringify(data),
    source: data.source || '系统'
  };
  
  if (logs.value.length > 0 && logs.value[0].timestamp === logEntry.timestamp && 
      logs.value[0].message === logEntry.message) {
    return; // 避免重复日志
  }
  
  logs.value.unshift(logEntry);
  if (logs.value.length > 100) {
    logs.value = logs.value.slice(0, 100);
  }
};

// 使用防抖处理状态更新
const debouncedProcessStatusUpdate = debounce((data) => {
  // 更新CPU和内存
  if (data.cpu_usage !== undefined) status.cpu_usage = data.cpu_usage;
  if (data.memory_usage !== undefined) status.memory_usage = data.memory_usage;
  
  // 更新运行状态
  if (data.model_loaded !== undefined) status.model_loaded = data.model_loaded;
  if (data.push_running !== undefined) status.push_running = data.push_running;
  if (data.pull_running !== undefined) status.pull_running = data.pull_running;
  
  // 更新终端状态
  terminal.status = status.model_loaded || status.push_running || status.pull_running;
}, 300);

// 处理相机状态
const processCameraStatus = (data) => {
  if (data.id && data.status) {
    status.cameras[data.id] = data.status;
  }
};

// 发送命令到终端
const sendCommand = async (command, params = {}) => {
  try {
    loading.value = true;
    const result = await terminalService.sendCommand(command, params);
    ElMessage.success(`命令 ${command} 发送成功`);
    
    // 刷新状态
    await loadTerminalStatus();
    loading.value = false;
    return result;
  } catch (error) {
    console.error(`发送命令 ${command} 失败:`, error);
    ElMessage.error(`命令 ${command} 发送失败`);
    loading.value = false;
    throw error;
  }
};

// 刷新终端状态
const refreshStatus = async () => {
  try {
    loading.value = true;
    await loadTerminalStatus();
    ElMessage.success('状态已刷新');
    loading.value = false;
  } catch (e) {
    loading.value = false;
  }
};

// 添加摄像头
const addCamera = () => {
  if (!newCamera.id || !newCamera.url) {
    ElMessage.warning('请输入完整的摄像头信息');
    return;
  }
  
  const camId = parseInt(newCamera.id);
  
  // 检查ID是否已存在
  if (config.cameras.some(cam => cam.id === camId)) {
    ElMessage.warning(`ID ${camId} 已存在`);
    return;
  }
  
  config.cameras.push({
    id: camId,
    url: newCamera.url
  });
  
  // 清空输入
  newCamera.id = '';
  newCamera.url = '';
};

// 移除摄像头
const removeCamera = (index) => {
  config.cameras.splice(index, 1);
};

// 保存配置
const saveConfig = async () => {
  try {
    loading.value = true;
    
    // 转换摄像头格式为对象
    const camerasObj = {};
    config.cameras.forEach(cam => {
      camerasObj[cam.id] = cam.url;
    });
    
    const configToSave = {
      mode: config.mode,
      interval: parseFloat(config.interval),
      cameras: camerasObj,
      save_image: config.save_image,
      preload_model: config.preload_model
    };
    
    // 保存原始配置用于比较
    const oldMode = originalConfig.mode;
    const oldInterval = originalConfig.interval;
    
    const result = await terminalService.saveConfig(configToSave);
    
    // 检查是否需要手动应用变更
    if (oldMode !== config.mode) {
      // 模式已变更，通知用户
      ElMessage.success(`配置已保存，检测模式已更改为: ${config.mode}`);
      
      // 刷新状态
      await loadTerminalStatus();
    } else if (oldInterval !== config.interval) {
      // 间隔已变更
      ElMessage.success(`配置已保存，拉取间隔已更新为: ${config.interval}秒`);
      
      // 刷新状态
      await loadTerminalStatus();
    } else {
      ElMessage.success('配置已保存');
    }
    
    // 如果配置要求重启，提示用户
    if (result && result.restart_required) {
      ElMessageBox.confirm(
        '配置已保存，但需要重启终端才能生效，是否立即重启？',
        '配置需要重启',
        {
          confirmButtonText: '重启',
          cancelButtonText: '稍后手动重启',
          type: 'warning',
        }
      ).then(async () => {
        await sendCommand('restart');
      }).catch(() => {
        // 用户取消重启
      });
    }
    
    // 更新原始配置
    Object.assign(originalConfig, JSON.parse(JSON.stringify(config)));
  } catch (error) {
    console.error('保存配置失败:', error);
    ElMessage.error('保存配置失败');
  } finally {
    loading.value = false;
  }
};

// 重置配置
const resetConfig = () => {
  Object.assign(config, JSON.parse(JSON.stringify(originalConfig)));
  ElMessage.info('配置已重置');
};

// 获取日志级别对应的标签类型
const getLogLevelType = (level) => {
  const types = {
    'info': 'info',
    'warning': 'warning',
    'error': 'danger',
    'detection': 'success'
  };
  return types[level] || 'info';
};

// 重启终端
const restartTerminal = async () => {
  ElMessageBox.confirm(
    '确定要重启终端吗？重启过程中将暂时无法获取检测数据。',
    '重启确认',
    {
      confirmButtonText: '重启',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    await sendCommand('restart');
  }).catch(() => {
    // 用户取消操作
  });
};

// 启动终端服务
const startService = async (mode) => {
  await sendCommand('start', { mode });
};

// 停止终端服务
const stopService = async (mode) => {
  await sendCommand('stop', { mode });
};

// 添加渐变色进度条
const customColorMethod = (percentage) => {
  if (percentage < 40) {
    return '#67C23A';
  } else if (percentage < 70) {
    return '#E6A23C';
  } else {
    return '#F56C6C';
  }
};

// 状态更新定时器
const statusRefreshTimer = ref(null);

// 改进初始化流程
onMounted(async () => {
  loading.value = true;
  
  try {
    // 1. 自动检测环境并配置连接模式
    environmentInfo.value = await terminalService.autoDetectEnvironment();
    console.log('检测到环境:', environmentInfo.value);
    
    // 无论是什么环境，都加载终端列表，以便切换
    await loadTerminalList();
    
    // 2. 根据环境信息设置连接模式
    if (environmentInfo.value.type === 'detector') {
      // 如果是检测端环境，默认使用本地模式
      connectionMode.value = 'local';
      localAvailable.value = true;
      terminal.id = environmentInfo.value.id;
      terminal.name = environmentInfo.value.name;
    } else {
      // 如果是服务端环境
      // 确定终端ID - 优先使用路由参数
      if (route.params.id) {
        terminal.id = parseInt(route.params.id);
        selectedTerminalId.value = terminal.id;
        connectionMode.value = 'remote';
      } else if (localAvailable.value) {
        // 如果本地可用且没有指定ID，使用本地模式
        connectionMode.value = 'local';
      } else if (terminalList.value.length > 0) {
        // 否则使用列表中第一个终端
        terminal.id = terminalList.value[0].id;
        selectedTerminalId.value = terminal.id;
        connectionMode.value = 'remote';
        // 修正路由路径
        router.replace(`/terminal/${terminal.id}`);
      }
    }
    
    // 3. 根据选定的模式设置终端服务
    terminalService.setMode(
      connectionMode.value, 
      connectionMode.value === 'remote' ? terminal.id : null
    );
    
    // 4. 加载数据
    await Promise.all([
      loadTerminalDetails(),
      loadTerminalStatus(),
      loadTerminalConfig(),
      loadLogs()
    ]);
    
    // 5. 设置WebSocket连接
    setupWebSocket();
    
    // 6. 设置定时刷新状态 (每15秒刷新一次)
    statusRefreshTimer.value = setInterval(async () => {
      try {
        await loadTerminalStatus();
      } catch (error) {
        console.error('自动刷新状态失败:', error);
      }
    }, 15000);
  } catch (error) {
    console.error('初始化失败:', error);
    ElMessage.error('加载终端数据失败');
  } finally {
    loading.value = false;
  }
});

// 改进模式变更处理
const handleModeChange = async () => {
  loading.value = true;
  
  try {
    // 根据模式设置终端服务
    if (connectionMode.value === 'remote') {
      // 确保有终端ID
      if (!terminal.id || !terminalList.value.some(t => t.id === terminal.id)) {
        if (terminalList.value.length > 0) {
          terminal.id = terminalList.value[0].id;
          selectedTerminalId.value = terminal.id;
        } else {
          // 如果没有可用终端，尝试重新加载终端列表
          await loadTerminalList();
          
          if (terminalList.value.length > 0) {
            terminal.id = terminalList.value[0].id;
            selectedTerminalId.value = terminal.id;
          } else {
            throw new Error('远程模式需要终端ID，但无可用终端');
          }
        }
      }
      
      // 设置服务模式并更新路由
      terminalService.setMode('remote', terminal.id);
      
      // 修复路由逻辑，使用正确的路径格式
      if (route.name !== 'terminal-detail' || parseInt(route.params.id) !== terminal.id) {
        router.push(`/terminal/${terminal.id}`);
      }
    } else {
      // 本地模式
      terminalService.setMode('local');
      
      // 如果当前在终端详情页，跳转到终端页
      if (route.name === 'terminal-detail') {
        router.push('/terminal');
      }
    }
    
    // 重新加载数据
    await Promise.all([
      loadTerminalDetails(),
      loadTerminalStatus(),
      loadTerminalConfig(),
      loadLogs()
    ]);
    
    // 重新连接WebSocket
    setupWebSocket();
  } catch (error) {
    console.error('切换模式失败:', error);
    ElMessage.error(`切换连接模式失败: ${error.message}`);
    
    // 如果失败，回退到之前的模式
    connectionMode.value = connectionMode.value === 'remote' ? 'local' : 'remote';
  } finally {
    loading.value = false;
  }
};

// 切换终端
const switchTerminal = async (id) => {
  if (id !== terminal.id) {
    loading.value = true;
    try {
      terminal.id = id;
      await terminalService.setMode('remote', id);
      // 修正路由路径
      router.push(`/terminal/${id}`);
      
      // 重新加载数据
      await Promise.all([
        loadTerminalDetails(),
        loadTerminalStatus(),
        loadTerminalConfig(),
        loadLogs()
      ]);
      
      // 重新连接WebSocket
      setupWebSocket();
    } catch (error) {
      console.error('切换终端失败:', error);
      ElMessage.error(`切换终端失败: ${error.message}`);
    } finally {
      loading.value = false;
    }
  }
};

// 发送命令并立即应用配置变更
const applyConfig = async () => {
  try {
    loading.value = true;
    await sendCommand('change_mode', { mode: config.mode });
    await sendCommand('set_interval', { interval: parseFloat(config.interval) });
    ElMessage.success('配置已立即应用');
    
    // 刷新状态
    await loadTerminalStatus();
  } catch (error) {
    console.error('应用配置失败:', error);
    ElMessage.error('应用配置失败: ' + error.message);
  } finally {
    loading.value = false;
  }
};

// 改进组件卸载时的清理
onUnmounted(() => {
  // 清除所有防抖函数
  if (debouncedProcessStatusUpdate && debouncedProcessStatusUpdate.cancel) {
    debouncedProcessStatusUpdate.cancel();
  }
  
  // 确保清除WebSocket回调
  if (wsCallbackId.value) {
    try {
      terminalService.disconnect(wsCallbackId.value);
      wsCallbackId.value = null;
    } catch (e) {
      console.error('清除WebSocket回调失败:', e);
    }
  }
  
  // 清除状态刷新定时器
  if (statusRefreshTimer.value) {
    clearInterval(statusRefreshTimer.value);
    statusRefreshTimer.value = null;
  }
});

// 监听连接模式变化
watch(connectionMode, handleModeChange);
</script>

<template>
  <div class="terminal-view">
    <el-card v-loading="loading" class="main-card">
      <template #header>
        <div class="header-section">
          <div class="title-area">
            <h2>{{ terminal.name }} 管理</h2>
            <el-tag :type="terminal.status ? 'success' : 'danger'" class="status-tag">
              {{ terminal.status ? '在线' : '离线' }}
            </el-tag>
            
            <el-tag v-if="environmentInfo" :type="environmentInfo.type === 'detector' ? 'warning' : 'info'" class="env-tag">
              {{ environmentInfo.type === 'detector' ? '检测端' : '服务端' }}
            </el-tag>
          </div>
          
          <div class="connection-controls">
            <el-select 
              v-if="connectionMode === 'remote' && terminalList.length > 0" 
              v-model="selectedTerminalId" 
              placeholder="选择终端" 
              size="small"
              @change="switchTerminal"
              style="margin-right: 10px; width: 140px;"
            >
              <el-option 
                v-for="item in terminalList" 
                :key="item.id" 
                :label="item.name || `终端 #${item.id}`" 
                :value="item.id"
              />
            </el-select>
            
            <el-radio-group 
              v-if="localAvailable || terminalList.length > 0" 
              v-model="connectionMode" 
              size="small"
            >
              <!-- 移除了禁用条件，允许随时切换到远程模式 -->
              <el-radio-button label="remote">远程模式</el-radio-button>
              <el-radio-button label="local" :disabled="!localAvailable">本地模式</el-radio-button>
            </el-radio-group>
          </div>
        </div>
      </template>
      
      <!-- 重新设计布局：不再使用标签页，而是使用统一的卡片式布局 -->
      <div class="dashboard-layout">
        <!-- 左侧：系统状态和服务控制 -->
        <div class="left-panel">
          <!-- 系统资源监控 -->
          <div class="panel-section">
            <div class="section-header">
              <h3>系统资源</h3>
              <el-button type="text" @click="refreshStatus" icon="el-icon-refresh">刷新</el-button>
            </div>
            
            <div class="resource-metrics">
              <div class="metric-item">
                <span class="metric-label">CPU 使用率</span>
                <el-progress :percentage="status.cpu_usage" :color="customColorMethod" :stroke-width="18" />
                <span class="metric-value">{{ status.cpu_usage.toFixed(1) }}%</span>
              </div>
              
              <div class="metric-item">
                <span class="metric-label">内存使用率</span>
                <el-progress :percentage="status.memory_usage" :color="customColorMethod" :stroke-width="18" />
                <span class="metric-value">{{ status.memory_usage.toFixed(1) }}%</span>
              </div>
            </div>
          </div>
          
          <!-- 系统信息 -->
          <div class="panel-section">
            <div class="section-header">
              <h3>系统信息</h3>
            </div>
            
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">终端ID</span>
                <span class="info-value">{{ terminal.id || '本地终端' }}</span>
              </div>
              
              <div class="info-item">
                <span class="info-label">模型状态</span>
                <el-tag :type="status.model_loaded ? 'success' : 'warning'" size="small">
                  {{ status.model_loaded ? '已加载' : '未加载' }}
                </el-tag>
              </div>
              
              <div class="info-item" v-if="terminalDetails.last_active">
                <span class="info-label">最后活动</span>
                <span class="info-value">{{ terminalDetails.last_active }}</span>
              </div>
            </div>
          </div>
          
          <!-- 服务控制 -->
          <div class="panel-section">
            <div class="section-header">
              <h3>服务控制</h3>
            </div>
            
            <div class="service-controls">
              <!-- 拉取模式 -->
              <div class="service-item">
                <div class="service-info">
                  <span class="service-name">拉取模式</span>
                  <el-tag :type="status.pull_running ? 'success' : 'info'" size="small">
                    {{ status.pull_running ? '运行中' : '已停止' }}
                  </el-tag>
                </div>
                <div class="service-actions">
                  <el-button 
                    type="primary" 
                    size="small" 
                    @click="startService('pull')" 
                    :disabled="status.pull_running"
                    plain
                  >启动</el-button>
                  <el-button 
                    type="danger" 
                    size="small" 
                    @click="stopService('pull')"
                    :disabled="!status.pull_running"
                    plain
                  >停止</el-button>
                </div>
              </div>
              
              <!-- 接收模式 -->
              <div class="service-item">
                <div class="service-info">
                  <span class="service-name">接收模式</span>
                  <el-tag :type="status.push_running ? 'success' : 'info'" size="small">
                    {{ status.push_running ? '运行中' : '已停止' }}
                  </el-tag>
                </div>
                <div class="service-actions">
                  <el-button 
                    type="primary" 
                    size="small" 
                    @click="startService('push')"
                    :disabled="status.push_running"
                    plain
                  >启动</el-button>
                  <el-button 
                    type="danger" 
                    size="small" 
                    @click="stopService('push')"
                    :disabled="!status.push_running"
                    plain
                  >停止</el-button>
                </div>
              </div>
              
              <!-- 系统操作 -->
              <div class="service-item">
                <div class="service-info">
                  <span class="service-name">系统操作</span>
                </div>
                <div class="service-actions">
                  <el-button 
                    type="primary" 
                    size="small" 
                    @click="startService('both')"
                    :disabled="status.pull_running && status.push_running"
                  >全部启动</el-button>
                  <el-button 
                    type="danger" 
                    size="small" 
                    @click="stopService('both')"
                    :disabled="!status.pull_running && !status.push_running"
                  >全部停止</el-button>
                  <el-button 
                    type="warning" 
                    @click="restartTerminal" 
                    :disabled="!terminal.status"
                    size="small"
                  >重启终端</el-button>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 摄像头状态 -->
          <div class="panel-section">
            <div class="section-header">
              <h3>摄像头状态</h3>
            </div>
            
            <el-empty v-if="Object.keys(status.cameras).length === 0" description="暂无摄像头数据"></el-empty>
            <el-table 
              v-else
              :data="Object.entries(status.cameras).map(([id, status]) => ({ id, status }))" 
              border
              stripe
              size="small"
              style="width: 100%"
            >
              <el-table-column prop="id" label="摄像头ID" width="100" align="center"></el-table-column>
              <el-table-column prop="status" label="状态" align="center">
                <template #default="scope">
                  <el-tag 
                    :type="scope.row.status === '在线' ? 'success' : 'danger'"
                    size="small"
                  >
                    {{ scope.row.status }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
        
        <!-- 右侧：配置管理和日志查看 -->
        <div class="right-panel">
          <!-- 配置管理 -->
          <div class="panel-section">
            <div class="section-header">
              <h3>配置管理</h3>
              <div class="section-actions">
                <el-button type="primary" size="small" @click="saveConfig">
                  保存配置
                </el-button>
                <el-button type="success" size="small" @click="applyConfig">
                  立即应用
                </el-button>
                <el-button size="small" @click="resetConfig">
                  重置
                </el-button>
              </div>
            </div>
            
            <el-form :model="config" label-width="100px" class="config-form">
              <el-row :gutter="20">
                <!-- 基本配置 -->
                <el-col :xs="24" :md="12">
                  <div class="form-section">
                    <h4>基本配置</h4>
                    <el-form-item label="工作模式">
                      <el-select v-model="config.mode" style="width: 100%">
                        <el-option label="拉取模式" value="pull"></el-option>
                        <el-option label="接收模式" value="push"></el-option>
                        <el-option label="双模式" value="both"></el-option>
                      </el-select>
                    </el-form-item>
                    
                    <el-form-item label="拉取间隔">
                      <el-input-number v-model="config.interval" :min="1" :max="60" style="width: 100%"></el-input-number>
                    </el-form-item>
                    
                    <el-form-item label="高级选项">
                      <div class="switch-group">
                        <div class="switch-item">
                          <span>保存图像</span>
                          <el-switch v-model="config.save_image"></el-switch>
                        </div>
                        <div class="switch-item">
                          <span>预加载模型</span>
                          <el-switch v-model="config.preload_model"></el-switch>
                        </div>
                      </div>
                    </el-form-item>
                  </div>
                </el-col>
                
                <!-- 摄像头配置 -->
                <el-col :xs="24" :md="12">
                  <div class="form-section">
                    <h4>摄像头配置</h4>
                    <div class="camera-list">
                      <el-table 
                        :data="config.cameras" 
                        border 
                        size="small"
                        height="200px"
                      >
                        <el-table-column prop="id" label="ID" width="60" align="center"></el-table-column>
                        <el-table-column prop="url" label="URL" show-overflow-tooltip></el-table-column>
                        <el-table-column label="操作" width="70" align="center">
                          <template #default="scope">
                            <el-button 
                              type="danger" 
                              size="small"
                              @click="removeCamera(scope.$index)"
                              icon="el-icon-delete"
                              circle
                            ></el-button>
                          </template>
                        </el-table-column>
                      </el-table>
                    </div>
                    
                    <div class="add-camera-form">
                      <el-input v-model="newCamera.id" placeholder="ID" class="camera-id-input" size="small"></el-input>
                      <el-input v-model="newCamera.url" placeholder="摄像头URL" class="camera-url-input" size="small"></el-input>
                      <el-button type="primary" @click="addCamera" size="small" icon="el-icon-plus">添加</el-button>
                    </div>
                  </div>
                </el-col>
              </el-row>
            </el-form>
          </div>
          
          <!-- 日志查看 -->
          <div class="panel-section">
            <div class="section-header">
              <h3>系统日志</h3>
              <el-button size="small" type="primary" plain @click="loadLogs" icon="el-icon-refresh">刷新</el-button>
            </div>
            
            <el-empty v-if="logs.length === 0" description="暂无日志数据"></el-empty>
            <el-table 
              v-else
              :data="logs" 
              height="350px" 
              border
              stripe
              size="small"
              style="width: 100%"
            >
              <el-table-column prop="timestamp" label="时间" width="160" show-overflow-tooltip></el-table-column>
              <el-table-column prop="level" label="级别" width="80" align="center">
                <template #default="scope">
                  <el-tag 
                    :type="getLogLevelType(scope.row.level)"
                    size="small"
                  >
                    {{ scope.row.level }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="source" label="来源" width="100" show-overflow-tooltip></el-table-column>
              <el-table-column prop="message" label="消息" show-overflow-tooltip></el-table-column>
            </el-table>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.terminal-view {
  padding: 15px;
  max-width: 1400px;
  margin: 0 auto;
}

.main-card {
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-area {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-tag, .env-tag {
  margin-left: 8px;
}

h2, h3, h4 {
  margin: 0;
  font-weight: 500;
}

h2 {
  font-size: 1.4rem;
  color: #303133;
}

h3 {
  font-size: 1.1rem;
  color: #409EFF;
}

h4 {
  font-size: 1rem;
  color: #606266;
  margin-bottom: 12px;
}

/* 新的布局样式 */
.dashboard-layout {
  display: flex;
  gap: 20px;
  margin-top: 15px;
}

.left-panel {
  width: 40%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.right-panel {
  width: 60%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel-section {
  background-color: #f8f9fa;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 15px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}

.section-actions {
  display: flex;
  gap: 10px;
}

/* 资源监控样式 */
.resource-metrics {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.metric-label {
  font-weight: 500;
  color: #606266;
}

.metric-value {
  text-align: right;
  color: #909399;
  font-weight: 500;
}

/* 信息网格 */
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.info-label {
  font-size: 0.9rem;
  color: #909399;
}

.info-value {
  font-weight: 500;
}

/* 服务控制样式 */
.service-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.service-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background-color: #fff;
  border-radius: 4px;
  border-left: 4px solid #ebeef5;
}

.service-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.service-name {
  font-weight: 500;
  min-width: 80px;
}

.service-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 摄像头配置样式 */
.camera-list {
  margin-bottom: 15px;
  border-radius: 4px;
  overflow: hidden;
}

.add-camera-form {
  display: flex;
  gap: 10px;
  margin-top: 15px;
  background-color: #f8f8f8;
  padding: 10px;
  border-radius: 4px;
}

.camera-id-input {
  width: 80px;
}

.camera-url-input {
  flex-grow: 1;
}

/* 配置表单样式 */
.config-form {
  margin-top: 10px;
}

.form-section {
  padding: 15px;
  background-color: #fff;
  border-radius: 4px;
}

.switch-group {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.switch-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 响应式布局 */
@media (max-width: 1200px) {
  .dashboard-layout {
    flex-direction: column;
  }
  
  .left-panel, .right-panel {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .header-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .service-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .service-actions {
    width: 100%;
    justify-content: space-between;
  }
  
  .add-camera-form {
    flex-direction: column;
  }
  
  .camera-id-input, .camera-url-input {
    width: 100%;
  }
}
</style>