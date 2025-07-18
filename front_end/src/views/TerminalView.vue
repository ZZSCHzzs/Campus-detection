<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { terminalService } from '../services/terminalService';

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

// 检测本地终端是否可用
const detectLocalTerminal = async () => {
  try {
    localAvailable.value = await terminalService.detectLocalTerminal();
    if (localAvailable.value) {
      ElMessage.success('检测到本地终端');
    }
  } catch (e) {
    localAvailable.value = false;
  }
};

// 加载终端列表
const loadTerminalList = async () => {
  try {
    const response = await fetch('/api/terminals/');
    const data = await response.json();
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

// 处理连接模式变更
const handleModeChange = async () => {
  loading.value = true;
  if (connectionMode.value === 'remote') {
    if (!terminal.id) {
      if (terminalList.value.length > 0) {
        // 如果有可用终端，使用第一个
        terminal.id = terminalList.value[0].id;
        selectedTerminalId.value = terminal.id;
      } else {
        ElMessage.error('远程模式需要终端ID，但无可用终端');
        if (localAvailable.value) {
          connectionMode.value = 'local';
        } else {
          router.push('/terminals');
          return;
        }
      }
    }
    terminalService.setMode('remote', terminal.id);
  } else {
    terminalService.setMode('local');
  }
  
  // 重新加载数据
  try {
    await Promise.all([
      loadTerminalDetails(),
      loadTerminalStatus(),
      loadTerminalConfig(),
      loadLogs()
    ]);
    
    // 重新连接WebSocket
    setupWebSocket();
    
    loading.value = false;
  } catch (error) {
    console.error('切换模式失败:', error);
    ElMessage.error('切换连接模式失败');
    loading.value = false;
  }
};

// 切换终端
const switchTerminal = (id) => {
  if (id === terminal.id) return;
  
  // 保存新ID到路由
  router.push(`/terminals/${id}`);
};

// 初始化
onMounted(async () => {
  loading.value = true;
  
  // 加载终端列表
  await loadTerminalList();
  
  // 检测本地终端
  await detectLocalTerminal();
  
  // 确定连接模式
  if (route.params.id) {
    terminal.id = parseInt(route.params.id);
    selectedTerminalId.value = terminal.id;
    connectionMode.value = 'remote';
    terminalService.setMode('remote', terminal.id);
  } else if (localAvailable.value) {
    connectionMode.value = 'local';
    terminalService.setMode('local');
  } else if (terminalList.value.length > 0) {
    // 如果有终端列表但没有指定ID，使用第一个
    terminal.id = terminalList.value[0].id;
    selectedTerminalId.value = terminal.id;
    connectionMode.value = 'remote';
    terminalService.setMode('remote', terminal.id);
    router.replace(`/terminals/${terminal.id}`);
  } else {
    // 无终端可用
    ElMessage.warning('无法连接到终端，请先添加终端');
  }
  
  // 加载数据
  try {
    await Promise.all([
      loadTerminalDetails(),
      loadTerminalStatus(),
      loadTerminalConfig(),
      loadLogs()
    ]);
    
    // 设置WebSocket连接
    setupWebSocket();
    
    loading.value = false;
  } catch (error) {
    console.error('初始化失败:', error);
    ElMessage.error('加载终端数据失败');
    loading.value = false;
  }
});

// 在组件销毁时清理
onUnmounted(() => {
  if (wsCallbackId.value) {
    terminalService.removeWebSocketCallback(wsCallbackId.value);
  }
});

// 监听连接模式变化
watch(connectionMode, handleModeChange);

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
    terminalService.removeWebSocketCallback(wsCallbackId.value);
  }
  
  wsCallbackId.value = terminalService.connectWebSocket(handleWebSocketMessage);
};

// 处理WebSocket消息
const handleWebSocketMessage = (data) => {
  // 处理日志消息
  if (data.type === 'new_log' || data.message) {
    const logEntry = {
      timestamp: data.timestamp || new Date().toISOString(),
      level: data.level || 'info',
      message: data.message || JSON.stringify(data),
      source: data.source
    };
    
    logs.value.unshift(logEntry);
    if (logs.value.length > 100) {
      logs.value = logs.value.slice(0, 100);
    }
  }
  
  // 处理状态更新
  if (data.type === 'system_update' || data.type === 'system_resources') {
    // 更新CPU和内存
    if (data.cpu !== undefined) status.cpu_usage = data.cpu;
    if (data.memory !== undefined) status.memory_usage = data.memory;
    
    // 更新运行状态
    if (data.model_loaded !== undefined) status.model_loaded = data.model_loaded;
    if (data.push_running !== undefined) status.push_running = data.push_running;
    if (data.pull_running !== undefined) status.pull_running = data.pull_running;
    
    // 更新终端状态
    terminal.status = status.model_loaded || status.push_running || status.pull_running;
  }
  
  // 处理相机状态
  if (data.type === 'camera_status') {
    if (data.id && data.status) {
      status.cameras[data.id] = data.status;
    }
  }
  
  // 处理检测结果
  if (data.type === 'detection_result') {
    // 可以在UI中显示最新检测结果
    console.log('检测结果:', data);
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
    
    const result = await terminalService.saveConfig(configToSave);
    ElMessage.success('配置已保存');
    
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
    loading.value = false;
  } catch (error) {
    console.error('保存配置失败:', error);
    ElMessage.error('保存配置失败');
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
          </div>
          <div class="connection-controls">
            <!-- 添加终端选择器 -->
            <el-select 
              v-if="connectionMode === 'remote'" 
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
            
            <el-radio-group v-model="connectionMode" size="small">
              <el-radio-button label="remote" :disabled="terminalList.length === 0">远程模式</el-radio-button>
              <el-radio-button label="local" :disabled="!localAvailable">本地模式</el-radio-button>
            </el-radio-group>
          </div>
        </div>
      </template>
      
      <!-- 使用标签页布局代替垂直堆叠卡片 -->
      <el-tabs type="border-card" class="main-tabs">
        <!-- 状态监控标签页 -->
        <el-tab-pane>
          <template #label>
            <span><i class="el-icon-monitor"></i> 状态监控</span>
          </template>
          
          <div class="tab-content">
            <el-row :gutter="20">
              <!-- 基本状态信息 -->
              <el-col :xs="24" :sm="24" :md="12">
                <div class="status-panel">
                  <div class="panel-header">
                    <h3>系统状态</h3>
                    <el-button type="text" @click="refreshStatus" icon="el-icon-refresh">刷新</el-button>
                  </div>
                  
                  <el-descriptions :column="1" border size="small" class="descriptions-block">
                    <el-descriptions-item label="终端ID">{{ terminal.id || '本地终端' }}</el-descriptions-item>
                    <el-descriptions-item label="CPU使用率">
                      <el-progress :percentage="status.cpu_usage" :color="customColorMethod"></el-progress>
                    </el-descriptions-item>
                    <el-descriptions-item label="内存使用率">
                      <el-progress :percentage="status.memory_usage" :color="customColorMethod"></el-progress>
                    </el-descriptions-item>
                    <el-descriptions-item label="模型状态">
                      <el-tag :type="status.model_loaded ? 'success' : 'warning'" size="small">
                        {{ status.model_loaded ? '已加载' : '未加载' }}
                      </el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item v-if="terminalDetails.last_active" label="最后活动">
                      {{ terminalDetails.last_active }}
                    </el-descriptions-item>
                  </el-descriptions>
                </div>
              </el-col>
              
              <!-- 服务控制 -->
              <el-col :xs="24" :sm="24" :md="12">
                <div class="status-panel">
                  <div class="panel-header">
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
                    
                    <!-- 所有服务 -->
                    <div class="service-item">
                      <div class="service-info">
                        <span class="service-name">所有服务</span>
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
                      </div>
                    </div>
                    
                    <div class="divider"></div>
                    
                    <!-- 系统操作 -->
                    <div class="service-item">
                      <el-button 
                        type="warning" 
                        @click="restartTerminal" 
                        :disabled="!terminal.status"
                        icon="el-icon-refresh-right"
                      >重启终端</el-button>
                    </div>
                  </div>
                </div>
              </el-col>
            </el-row>
            
            <!-- 摄像头状态 -->
            <div class="camera-status-panel">
              <div class="panel-header">
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
        </el-tab-pane>
        
        <!-- 配置管理标签页 -->
        <el-tab-pane>
          <template #label>
            <span><i class="el-icon-setting"></i> 配置管理</span>
          </template>
          
          <div class="tab-content">
            <div class="config-toolbar">
              <div class="config-summary">
                <el-tag>{{ 
                  config.mode === 'pull' ? '拉取模式' : 
                  config.mode === 'push' ? '接收模式' : '双模式' 
                }}</el-tag>
                <el-tag type="info">拉取间隔: {{ config.interval }}秒</el-tag>
                <el-tag type="info">摄像头: {{ config.cameras.length }}个</el-tag>
                <el-tag v-if="config.save_image" type="success">保存图像</el-tag>
                <el-tag v-if="config.preload_model" type="success">预加载模型</el-tag>
              </div>
              <div class="config-actions">
                <el-button type="primary" size="small" @click="saveConfig">
                  <i class="el-icon-check"></i> 保存配置
                </el-button>
                <el-button size="small" @click="resetConfig">
                  <i class="el-icon-refresh-left"></i> 重置
                </el-button>
              </div>
            </div>
            
            <el-form :model="config" label-width="100px" class="config-form">
              <el-row :gutter="20">
                <!-- 基本配置 -->
                <el-col :xs="24" :sm="24" :md="12">
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
                <el-col :xs="24" :sm="24" :md="12">
                  <div class="form-section">
                    <h4>摄像头配置</h4>
                    <div class="camera-list">
                      <el-table 
                        :data="config.cameras" 
                        border 
                        size="small"
                        height="250px"
                      >
                        <el-table-column prop="id" label="ID" width="60" align="center"></el-table-column>
                        <el-table-column prop="url" label="URL" show-overflow-tooltip></el-table-column>
                        <el-table-column label="操作" width="70" align="center">
                          <template #default="scope">
                            <el-button 
                              type="danger" 
                              size="mini" 
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
        </el-tab-pane>
        
        <!-- 日志查看标签页 -->
        <el-tab-pane>
          <template #label>
            <span><i class="el-icon-document"></i> 日志查看</span>
          </template>
          
          <div class="tab-content">
            <div class="log-header">
              <h3>终端日志</h3>
              <el-button size="small" type="primary" plain @click="loadLogs" icon="el-icon-refresh">刷新</el-button>
            </div>
            
            <el-empty v-if="logs.length === 0" description="暂无日志数据"></el-empty>
            <el-table 
              v-else
              :data="logs" 
              height="400px" 
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
                    size="mini"
                  >
                    {{ scope.row.level }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="source" label="来源" width="100" show-overflow-tooltip></el-table-column>
              <el-table-column prop="message" label="消息" show-overflow-tooltip></el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<style scoped>
.terminal-view {
  padding: 15px;
  max-width: 1200px;
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

.status-tag {
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

.main-tabs {
  border: none;
  box-shadow: none;
}

.tab-content {
  padding: 15px 0;
}

/* 状态监控样式 */
.status-panel {
  background: #f8f8f8;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 15px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.descriptions-block {
  margin-top: 10px;
}

.service-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.service-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background-color: #fff;
  border-radius: 4px;
  border: 1px solid #ebeef5;
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
}

.divider {
  height: 1px;
  background-color: #ebeef5;
  margin: 5px 0;
}

.camera-status-panel {
  background: #f8f8f8;
  border-radius: 4px;
  padding: 12px;
}

/* 配置管理样式 */
.config-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f8f8;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 15px;
}

.config-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.config-actions {
  display: flex;
  gap: 8px;
}

.config-form {
  margin-top: 15px;
}

.form-section {
  background: #f8f8f8;
  border-radius: 4px;
  padding: 15px;
  height: 100%;
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

.camera-list {
  margin-bottom: 12px;
}

.add-camera-form {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.camera-id-input {
  width: 70px;
  flex-shrink: 0;
}

.camera-url-input {
  flex-grow: 1;
}

/* 日志查看样式 */
.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f8f8;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 15px;
}

.connection-controls {
  display: flex;
  align-items: center;
}

/* 适配移动设备 */
@media (max-width: 768px) {
  .terminal-view {
    padding: 10px;
  }
  
  .header-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
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
  
  .config-toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .config-actions {
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