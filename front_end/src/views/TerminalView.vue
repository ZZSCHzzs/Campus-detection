<script setup lang="ts">

import { ref, reactive, onMounted, onUnmounted, watch, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import EnvironmentalChart from '../components/chart/EnvironmentalChart.vue';

import apiService from '../services';

// 导入所需的图标组件
import {
  Cpu,
  Connection,
  Monitor,
  WarningFilled,
  DataAnalysis,
  Refresh,
  Timer,
  VideoCamera,
  Picture,
  InfoFilled,
  Location,
  Opportunity,
  Calendar,
  Setting,
  Download,
  Upload,
  Open,
  TurnOff,
  RefreshRight,
  RefreshLeft,
  Tools,
  Check,
  Notebook,
  Delete,
  Plus,
  VideoPlay,
  VideoPause,
  Bell,
  Mute,
  MagicStick,
} from '@element-plus/icons-vue';

const route = useRoute();
const router = useRouter();

const frameSizes = {
  10: { size: [1600, 1200], label: 'UXGA (1600x1200)' },
  9: { size: [1280, 1024], label: 'SXGA (1280x1024)' },
  8: { size: [1024, 768], label: 'XGA (1024x768)' },
  7: { size: [800, 600], label: 'SVGA (800x600)' },
  6: { size: [640, 480], label: 'VGA (640x480)' },
  5: { size: [400, 296], label: 'CIF (400x296)' },
  4: { size: [320, 240], label: 'QVGA (320x240)' },
  3: { size: [240, 176], label: 'HQVGA (240x176)' },
  0: { size: [160, 120], label: 'QQVGA (160x120)' }
};

// 连接模式（只使用一种模式简化逻辑）
const connectionMode = ref('remote');
const loading = ref(true);
const pollTimer = ref(null);
const isActive = ref(true);
// 终端信息
const terminal = reactive({
  id: null,
  name: '终端',
  status: false,
});

// 终端状态
const status = reactive({
  nodes: {},
  cpu_usage: 0,
  memory_usage: 0,
  disk_usage: 0,
  disk_free: 0,
  disk_total: 0,
  memory_available: 0,
  memory_total: 0,
  push_running: false,
  pull_running: false,
  model_loaded: false,
  co2_level: -1,
  co2_status: '未连接',
  system_uptime: null,
  frame_rate: null,
  total_frames: null,
  terminal_online: false,
  last_detection: null,
  mode: 'both',
  terminal_id: null
});

// 终端配置
const config = reactive({
  mode: 'both',
  interval: 5,
  data_nodes: [],
  control_nodes: [],
  save_image: true,
  preload_model: true,
  co2_enabled: true,
  co2_read_interval: 30,
  camera_config: {
    frame_size: 6, // 默认使用VGA
    frame_rate: 30,
    exposure: 0,
    brightness: 0,
    contrast: 0,
    saturation: 0,
    sharpness: 0,
    gain: 0,
    white_balance: 'auto',
    auto_exposure: true,
    special_effect: 0,
    hmirror: false,
    vflip: false
  }
});

// 原始配置（用于重置）
const originalConfig = reactive({} as any);


// 新节点信息
const newDataNode = reactive({
  id: '',
  name: '',
  ip: '',
  port: 80,
  capabilities: '' // 逗号分隔输入
});
const newControlNode = reactive({
  id: '',
  name: '',
  ip: '',
  port: 80,
  capabilities: '' // 逗号分隔输入
});

// 终端日志
const logs = ref([]);

// 终端列表和终端选择
const terminalList = ref([]);
const selectedTerminalId = ref(null);

// 终端详细信息数据
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

// 判断本地终端是否可用
const localAvailable = ref(false);

// 判断远程终端是否可用
const remoteAvailable = ref(false);

// 加载终端列表
const loadTerminalList = async () => {
  try {
    const data = await apiService.terminals.getAll();
    terminalList.value = data;
    remoteAvailable.value = data && data.length > 0;
    return data;
  } catch (error) {
    console.error('加载终端列表失败:', error);
    ElMessage.error('加载终端列表失败');
    remoteAvailable.value = false;
    return [];
  }
};

// 获取当前使用的服务，根据连接模式决定
const terminalService = computed(() => {
  return connectionMode.value === 'local' ?
    apiService.localTerminal :
    apiService.terminals;
});

// 加载终端详细信息
const loadTerminalDetails = async () => {
  try {
    if (connectionMode.value === 'local') {
      const info : any = await apiService.localTerminal.getInfo();
      terminalDetails.id = info.id || 0;
      terminalDetails.name = info.name || '本地终端';
      terminalDetails.status = true;
    } else {
      const details = await apiService.terminals.getById(terminal.id);
      Object.assign(terminalDetails, details);
    }

    // 更新终端基本信息
    terminal.id = terminalDetails.id;
    terminal.name = terminalDetails.name;
    terminal.status = terminalDetails.status;

    return terminalDetails;
  } catch (error) {
    console.error('加载终端详细信息失败:', error);
    ElMessage.warning('无法获取终端详细信息');
    return null;
  }
};

// 加载终端状态
const loadTerminalStatus = async () => {
  try {
    let data;
    if (connectionMode.value === 'local') {
      data = await apiService.localTerminal.getStatus();
    } else {
      data = await apiService.terminals.getTerminalStatus(terminal.id);
    }
    // 标准化数据格式
    const statusData = {
      nodes: data.nodes || {},
      cpu_usage: data.cpu_usage || 0,
      memory_usage: data.memory_usage || 0,
      disk_usage: data.disk_usage || 0,
      disk_free: data.disk_free || 0,
      disk_total: data.disk_total || 0,
      memory_available: data.memory_available || 0,
      memory_total: data.memory_total || 0,
      push_running: data.push_running || false,
      pull_running: data.pull_running || false,
      model_loaded: data.model_loaded || false,
      co2_level: data.co2_level ?? -1,
      co2_status: data.co2_status ?? '未连接',
      system_uptime: data.system_uptime ?? null,
      frame_rate: data.frame_rate ?? null,
      total_frames: data.total_frames ?? null,
      terminal_online: data.terminal_online ?? false,
      last_detection: data.last_detection ?? null,
      mode: data.mode ?? 'both',
      terminal_id: data.terminal_id ?? null
    };
    Object.assign(status, statusData);
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
    let configData;
    if (connectionMode.value === 'local') {
      configData = await apiService.localTerminal.getConfig();
    } else {
      configData = await apiService.terminals.getTerminalConfig(terminal.id);
    }

    // 更新配置数据
    config.mode = configData.mode || 'both';
    config.interval = configData.interval || 5;
    config.save_image = configData.save_image !== undefined ? configData.save_image : true;
    config.preload_model = configData.preload_model !== undefined ? configData.preload_model : true;
    config.co2_enabled = configData.co2_enabled !== undefined ? configData.co2_enabled : true;
    config.co2_read_interval = configData.co2_read_interval !== undefined ? configData.co2_read_interval : 30;

    // 转换节点数据格式（兼容新旧格式）
    if (configData.nodes) {
      const parseEntry = (id, value, typeFallback) => {
        const nodeId = parseInt(id);
        if (value && typeof value === 'object') {
          return {
            id: nodeId,
            name: value.name || `${typeFallback === 'data' ? '数据' : '控制'}节点${nodeId}`,
            ip: value.ip || '',
            port: value.port !== undefined ? Number(value.port) : 80,
            capabilities: Array.isArray(value.capabilities) ? value.capabilities : []
          };
        }
        // 旧格式 value 为 URL 字符串，尽量解析出 ip/port
        let ip = '', port = 80;
        if (typeof value === 'string') {
          try {
            const maybeUrl = value.includes('://') ? value : `http://${value}`;
            const u = new URL(maybeUrl);
            ip = u.hostname || '';
            port = u.port ? Number(u.port) : 80;
          } catch (e) {
            ip = String(value);
            port = 80;
          }
        }
        return {
          id: nodeId,
          name: `${typeFallback === 'data' ? '数据' : '控制'}节点${nodeId}`,
          ip,
          port,
          capabilities: []
        };
      };

      if (configData.nodes.data_nodes || configData.nodes.control_nodes) {
        // 新格式：按类别划分，条目为对象
        const dataEntries = Object.entries(configData.nodes.data_nodes || {});
        const controlEntries = Object.entries(configData.nodes.control_nodes || {});
        config.data_nodes = dataEntries.map(([id, v]) => parseEntry(id, v, 'data'));
        config.control_nodes = controlEntries.map(([id, v]) => parseEntry(id, v, 'control'));
      } else {
        // 旧格式：全部视为数据节点，值为 URL 字符串
        config.data_nodes = Object.entries(configData.nodes || {}).map(([id, v]) => parseEntry(id, v, 'data'));
        config.control_nodes = [];
      }
    } else {
      config.data_nodes = [];
      config.control_nodes = [];
    }

    // 处理摄像头配置
    if (configData.camera_config) {
      Object.assign(config.camera_config, configData.camera_config);
    }

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
    let logsData;
    if (connectionMode.value === 'local') {
      logsData = await apiService.localTerminal.getLogs();
    } else {
      // 添加日志限制参数，确保获取较多的日志记录
      logsData = await apiService.terminals.getTerminalLogs(terminal.id, { limit: 200 });
    }

    // 标准化日志格式
    logs.value = Array.isArray(logsData) ? logsData.map(log => ({
      timestamp: log.timestamp || new Date().toISOString(),
      level: log.level || 'info',
      message: log.message || '未知消息',
      source: log.source || '系统'
    })) : [];

    return logsData;
  } catch (error) {
    console.error('加载日志失败:', error);
    ElMessage.error('加载日志失败');
    return [];
  }
};

// 设置轮询
const setupPolling = () => {
  // 清除现有轮询
  if (pollTimer.value) {
    clearInterval(pollTimer.value);
  }

  // 设置新的轮询间隔 (每10秒更新一次状态和日志)
  pollTimer.value = setInterval(async () => {
    try {
      await loadTerminalStatus();
      // 确保在远程模式下也能定时获取日志
      if (connectionMode.value === 'remote') {
        await loadLogs();
      }
    } catch (error) {
      console.error('状态轮询失败:', error);
    }
  }, 10000); // 10秒轮询间隔
};

// 发送命令到终端
const sendCommand = async (command, params = {}) => {
  try {
    loading.value = true;
    let result;

    if (connectionMode.value === 'local') {
      result = await apiService.localTerminal.sendCommand(command, params);
    } else {
      result = await apiService.terminals.sendTerminalCommand(terminal.id, { command, params });
    }

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

// 添加数据节点
const addDataNode = () => {
  if (!newDataNode.id || !newDataNode.ip || !newDataNode.port) {
    ElMessage.warning('请输入完整的节点信息（ID、IP、端口）');
    return;
  }
  const nodeId = parseInt(newDataNode.id);
  if (config.data_nodes.some(n => n.id === nodeId) || config.control_nodes.some(n => n.id === nodeId)) {
    ElMessage.warning(`ID ${nodeId} 已存在`);
    return;
  }
  const caps = newDataNode.capabilities
    ? newDataNode.capabilities.split(',').map(s => s.trim()).filter(Boolean)
    : [];
  config.data_nodes.push({ id: nodeId, name: newDataNode.name || `数据节点${nodeId}`, ip: newDataNode.ip, port: Number(newDataNode.port), capabilities: caps });
  newDataNode.id = '';
  newDataNode.name = '';
  newDataNode.ip = '';
  newDataNode.port = 80;
  newDataNode.capabilities = '';
};

// 添加控制节点
const addControlNode = () => {
  if (!newControlNode.id || !newControlNode.ip || !newControlNode.port) {
    ElMessage.warning('请输入完整的节点信息（ID、IP、端口）');
    return;
  }
  const nodeId = parseInt(newControlNode.id);
  if (config.data_nodes.some(n => n.id === nodeId) || config.control_nodes.some(n => n.id === nodeId)) {
    ElMessage.warning(`ID ${nodeId} 已存在`);
    return;
  }
  const caps = newControlNode.capabilities
    ? newControlNode.capabilities.split(',').map(s => s.trim()).filter(Boolean)
    : [];
  config.control_nodes.push({ id: nodeId, name: newControlNode.name || `控制节点${nodeId}`, ip: newControlNode.ip, port: Number(newControlNode.port), capabilities: caps });
  newControlNode.id = '';
  newControlNode.name = '';
  newControlNode.ip = '';
  newControlNode.port = 80;
  newControlNode.capabilities = '';
};

// 移除数据节点
const removeDataNode = (index) => {
  config.data_nodes.splice(index, 1);
};

// 移除控制节点
const removeControlNode = (index) => {
  config.control_nodes.splice(index, 1);
};

// 预览数据节点图片（仅本地模式）
const previewNodeImage = async (nodeId) => {
  if (connectionMode.value !== 'local') {
    ElMessage.warning('图片预览仅在本地模式下可用');
    return;
  }
  try {
    const blob : any = await apiService.localTerminal.getLastImage(nodeId);
    const imageUrl = URL.createObjectURL(blob);
    ElMessageBox.alert(`<img src="${imageUrl}" style="max-width: 100%; max-height: 400px;" />`, `节点 ${nodeId} 最后一次图片`, {
      dangerouslyUseHTMLString: true,
      customClass: 'image-preview-dialog',
      confirmButtonText: '关闭'
    }).finally(() => URL.revokeObjectURL(imageUrl));
  } catch (error) {
    console.error('获取节点图片失败:', error);
    ElMessage.error('获取节点图片失败');
  }
};

// 保存配置
const saveConfig = async () => {
  try {
    loading.value = true;

    // 转换节点格式为对象（新格式，包含详细字段）
    const dataNodesObj = {} as Record<string, any>;
    config.data_nodes.forEach(n => {
      dataNodesObj[n.id] = {
        type: 'data',
        ip: n.ip,
        port: Number(n.port) || 80,
        name: n.name || `数据节点${n.id}`,
        capabilities: Array.isArray(n.capabilities) ? n.capabilities : []
      };
    });
    const controlNodesObj = {} as Record<string, any>;
    config.control_nodes.forEach(n => {
      controlNodesObj[n.id] = {
        type: 'control',
        ip: n.ip,
        port: Number(n.port) || 80,
        name: n.name || `控制节点${n.id}`,
        capabilities: Array.isArray(n.capabilities) ? n.capabilities : []
      };
    });

    const configToSave = {
      mode: config.mode,
      interval: parseFloat(String(config.interval)),
      nodes: { data_nodes: dataNodesObj, control_nodes: controlNodesObj },
      save_image: config.save_image,
      preload_model: config.preload_model,
      co2_enabled: config.co2_enabled,
      co2_read_interval: config.co2_read_interval
    };

    // 保存原始配置用于比较
    const oldMode = originalConfig.mode;
    const oldInterval = originalConfig.interval;

    let result;
    if (connectionMode.value === 'local') {
      result = await apiService.localTerminal.updateConfig(configToSave);
    } else {
      result = await apiService.terminals.updateTerminalConfig(terminal.id, configToSave);
    }

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

// 保存摄像头配置
const saveCameraConfig = async () => {
  try {
    loading.value = true;
    
    // 只保存摄像头相关配置
    const cameraConfigToSave = {
      camera_config: config.camera_config
    };

    let result;
    if (connectionMode.value === 'local') {
      result = await apiService.localTerminal.updateConfig(cameraConfigToSave);
    } else {
      result = await apiService.terminals.updateTerminalConfig(terminal.id, cameraConfigToSave);
    }

    ElMessage.success('摄像头参数已保存');

    // 如果需要重启才能生效，提示用户
    if (result && result.restart_required) {
      ElMessageBox.confirm(
        '摄像头参数已保存，但需要重启终端才能生效，是否立即重启？',
        '参数需要重启',
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
  } catch (error) {
    console.error('保存摄像头参数失败:', error);
    ElMessage.error('保存摄像头参数失败');
  } finally {
    loading.value = false;
  }
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

// 获取CO2状态对应的标签类型
const getCO2StatusType = (status) => {
  const types = {
    '正常': 'success',
    '异常': 'danger',
    '未连接': 'info'
  };
  return types[status] || 'info';
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

// 配置标签页状态
const activeConfigTab = ref('basic');

// 在 data 部分添加蜂鸣器相关状态
const buzzerAvailable = ref(false);
const buzzerActive = ref(false);
const buzzerForm = reactive({
  pattern: 'SINGLE_BEEP',
  duration: 0.5,
  repeat: 1
});

// 蜂鸣器模式选项
const buzzerPatterns = [
  { value: 'SINGLE_BEEP', label: '单次短鸣', icon: 'Bell' },
  { value: 'DOUBLE_BEEP', label: '双短鸣', icon: 'Bell' },
  { value: 'LONG_BEEP', label: '长鸣', icon: 'Bell' },
  { value: 'SOS', label: 'SOS紧急信号', icon: 'Warning' },
  { value: 'ALARM', label: '警报信号', icon: 'Warning' },
];

// 检查蜂鸣器状态
const checkBuzzerStatus = async () => {
  try {
    if (connectionMode.value === 'local') {
      const { data } = await apiService.localTerminal.getBuzzerStatus();
      buzzerAvailable.value = data.available;
      buzzerActive.value = data.active;
    } else {
      const { data } = await apiService.terminals.getBuzzerStatus(terminal.id);
      buzzerAvailable.value = data.available;
      buzzerActive.value = data.active;
    }
  } catch (error) {
    console.error('获取蜂鸣器状态失败:', error);
    buzzerAvailable.value = false;
    buzzerActive.value = false;
  }
};

// 控制蜂鸣器（仅本地模式）
const controlBuzzer = async (action, params = {}) => {
  if (connectionMode.value !== 'local') {
    ElMessage.warning('硬件控制仅限本地模式');
    return;
  }
  try {
    loading.value = true;
    
    const data = {
      action,
      ...params
    };
    
    let result;
    result = await apiService.localTerminal.controlBuzzer(data);
    
    // 短暂延迟后刷新状态
    setTimeout(() => {
      checkBuzzerStatus();
    }, 500);
    
    ElMessage.success(`蜂鸣器命令已发送: ${action}`);
    return result;
  } catch (error) {
    console.error('控制蜂鸣器失败:', error);
    ElMessage.error('控制蜂鸣器失败');
  } finally {
    loading.value = false;
  }
};

// 蜂鸣器操作方法
const beep = () => controlBuzzer('beep', { duration: buzzerForm.duration });
const startBuzzer = () => controlBuzzer('start', { 
  pattern: buzzerForm.pattern, 
  repeat: buzzerForm.repeat 
});
const stopBuzzer = () => controlBuzzer('stop');

// 灯光控制状态
const lightStatus = reactive({
  node_id: 1,
  online: false,
  supports_rotate: true,
  default_angle: 90,
  auto_return_time: 3,
});
const lightAngle = ref(90);
const lightOnAngle = ref(130);
const lightOffAngle = ref(65);

// 获取灯光状态（仅本地模式）
const fetchLightStatus = async () => {
  if (connectionMode.value !== 'local') return;
  try {
    const { data } = await apiService.localTerminal.getLightStatus(lightStatus.node_id);
    lightStatus.node_id = data.node_id ?? lightStatus.node_id;
    lightStatus.online = data.online ?? false;
    lightStatus.supports_rotate = data.supports_rotate ?? false;
    lightStatus.default_angle = data.default_angle ?? 90;
    lightStatus.auto_return_time = data.auto_return_time ?? 3;
    if (!lightAngle.value) lightAngle.value = lightStatus.default_angle;
  } catch (e) {
    console.warn('获取灯光状态失败', e);
    lightStatus.online = false;
  }
};

// 旋转灯光（仅本地模式）
const rotateLight = async () => {
  if (connectionMode.value !== 'local') {
    ElMessage.warning('硬件控制仅限本地模式');
    return;
  }
  try {
    const angle = Number(lightAngle.value) || lightStatus.default_angle || 90;
    await apiService.localTerminal.controlLightRotate({ node_id: lightStatus.node_id, angle });
    ElMessage.success(`已发送灯光旋转指令：${angle}°，将于${lightStatus.auto_return_time}s自动回正`);
  } catch (e) {
    console.error('旋转灯光失败', e);
    ElMessage.error('旋转灯光失败');
  }
};

// 开灯（仅本地模式）
const turnLightOn = async () => {
  if (connectionMode.value !== 'local') {
    ElMessage.warning('硬件控制仅限本地模式');
    return;
  }
  try {
    const angle = Number(lightOnAngle.value) || 130;
    await apiService.localTerminal.controlLightRotate({ node_id: lightStatus.node_id, angle });
    ElMessage.success(`已发送开灯指令：${angle}°`);
  } catch (e) {
    console.error('开灯失败', e);
    ElMessage.error('开灯失败');
  }
};

// 关灯（仅本地模式）
const turnLightOff = async () => {
  if (connectionMode.value !== 'local') {
    ElMessage.warning('硬件控制仅限本地模式');
    return;
  }
  try {
    const angle = Number(lightOffAngle.value) || 65;
    await apiService.localTerminal.controlLightRotate({ node_id: lightStatus.node_id, angle });
    ElMessage.success(`已发送关灯指令：${angle}°`);
  } catch (e) {
    console.error('关灯失败', e);
    ElMessage.error('关灯失败');
  }
};

onMounted(async () => {
  loading.value = true;

  try {
    // 检查本地终端是否可用
    localAvailable.value = await apiService.localTerminal.checkLocalAvailable();
    if (!isActive.value) return;

    // 加载终端列表（用于远程模式）并确定远程可用性
    await loadTerminalList();
    remoteAvailable.value = terminalList.value.length > 0;

    // 根据环境可用性决定初始模式
    if (localAvailable.value) {
      // 1. 获取环境信息
      environmentInfo.value = await apiService.localTerminal.getEnvironmentInfo();


      // 如果是检测端环境，默认使用本地模式
      if (environmentInfo.value.type === 'detector') {
        connectionMode.value = 'local';
        terminal.id = environmentInfo.value.id;
        terminal.name = environmentInfo.value.name;
      }
    } else if (!remoteAvailable.value) {
      // 如果本地和远程都不可用，显示提示
      ElMessage.error('无法连接到任何终端，请检查网络连接或配置');
    }
    // 根据选定的模式加载相应数据
    if (!isActive.value) return;
    if (!localAvailable.value) {
      ElMessage.warning('未检测到本地终端服务，使用远程模式');
    }
    if (connectionMode.value === 'remote') {
      // 确定终端ID - 优先使用路由参数
      if (route.params.id) {
        terminal.id = parseInt(String(route.params.id));
        selectedTerminalId.value = terminal.id;
      } else if (terminalList.value.length > 0) {
        // 否则使用列表中第一个终端
        terminal.id = terminalList.value[0].id;
        selectedTerminalId.value = terminal.id;
        if (isActive.value) {
          router.replace(`/terminal/${terminal.id}`);
        }
      }
    }

    // 尝试加载数据，如果失败则显示空数据
    try {
      await Promise.all([
        loadTerminalDetails(),
        loadTerminalStatus(),
        loadTerminalConfig(),
        loadLogs()
      ]);

      // 设置轮询
      setupPolling();

      // 设置定时刷新状态 (每60秒刷新一次)
      statusRefreshTimer.value = setInterval(async () => {
        try {
          await loadTerminalStatus();
        } catch (error) {
          console.error('自动刷新状态失败:', error);
        }
      }, 60000);
    } catch (error) {
      console.error('加载终端数据失败:', error);
      ElMessage.warning('加载终端数据失败，显示空数据');

      // 确保显示空数据
      if (connectionMode.value === 'local' && !localAvailable.value) {
        ElMessage.error('本地终端不可用');
      } else if (connectionMode.value === 'remote' && !remoteAvailable.value) {
        ElMessage.error('远程终端不可用');
      }
    }
  } catch (error) {
    console.error('初始化失败:', error);
    ElMessage.error('初始化失败:', error.message);
  } finally {
    loading.value = false;
  }
  // 加载数据后检查蜂鸣器状态
  await checkBuzzerStatus();
  // 加载灯光状态（仅本地模式时尝试）
  await fetchLightStatus();
  
  // 添加状态轮询
  setInterval(async () => {
    if (isActive.value) {
      await checkBuzzerStatus();
      await fetchLightStatus();
    }
  }, 5000); // 每5秒检查一次状态
});

// 切换终端
const switchTerminal = async (id) => {
  if (id !== terminal.id) {
    loading.value = true;
    try {
      terminal.id = id;

      // 修正路由路径
      router.push(`/terminal/${id}`);

      // 重新加载数据
      await Promise.all([
        loadTerminalDetails(),
        loadTerminalStatus(),
        loadTerminalConfig(),
        loadLogs()
      ]);

      // 重置轮询
      setupPolling();
    } catch (error) {
      console.error('切换终端失败:', error);
      ElMessage.error(`切换终端失败: ${error.message}`);
    } finally {
      loading.value = false;
    }
  }
};

// 切换连接模式
const handleModeChange = async () => {
  // 检查模式切换条件
  if (connectionMode.value === 'local' && !localAvailable.value) {
    ElMessage.error('本地终端不可用，无法切换到本地模式');
    connectionMode.value = 'remote';
    return;
  }

  if (connectionMode.value === 'remote' && !remoteAvailable.value) {
    ElMessage.error('远程终端不可用，无法切换到远程模式');

    if (localAvailable.value) {
      // 如果本地可用，则回退到本地模式
      connectionMode.value = 'local';
    } else {
      // 如果本地也不可用，显示警告但允许继续尝试
      ElMessage.warning('本地终端不可用，将尝试连接远程终端');
    }
    return;
  }

  loading.value = true;

  try {
    // 根据新模式处理
    if (connectionMode.value === 'remote') {
      // 确保有终端ID
      if (!terminal.id || !terminalList.value.some(t => t.id === terminal.id)) {
        if (terminalList.value.length > 0) {
          terminal.id = terminalList.value[0].id;
          selectedTerminalId.value = terminal.id;
          router.push(`/terminal/${terminal.id}`);
        } else {
          throw new Error('远程模式需要终端ID，但无可用终端');
        }
      }
    } else {
      // 本地模式
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
    ]).catch(error => {
      console.error('加载终端数据失败:', error);
      ElMessage.error('加载终端数据失败');
    });

    // 重置轮询
    setupPolling();
  } catch (error) {
    console.error('切换模式失败:', error);
    ElMessage.error(`切换连接模式失败: ${error.message}`);

    // 如果失败，回退到之前的模式
    connectionMode.value = connectionMode.value === 'remote' ? 'local' : 'remote';
  } finally {
    loading.value = false;
  }
};

// 发送命令并立即应用配置变更
const applyConfig = async () => {
  try {
    loading.value = true;
    await sendCommand('change_mode', { mode: config.mode });
    await sendCommand('set_interval', { interval: parseFloat(String(config.interval)) });
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

// 格式化运行时间显示
const formatUptime = (seconds) => {
  if (!seconds) return '未知';

  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  let result = '';
  if (days > 0) result += `${days}天 `;
  if (hours > 0 || days > 0) result += `${hours}小时 `;
  result += `${minutes}分钟`;

  return result;
};

// 组件卸载时的清理
onUnmounted(() => {
  isActive.value = false;
  // 清除轮询
  if (pollTimer.value) {
    clearInterval(pollTimer.value);
    pollTimer.value = null;
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
    <el-card v-loading="loading" class="main-card" :body-style="{ padding: '0' }">
      <!-- 标题栏 -->
      <div class="terminal-header">
        <div class="title-area">
          <div class="terminal-icon">
            <el-icon>
              <Cpu />
            </el-icon>
          </div>
          <div class="terminal-info">
            <h2>{{ terminal.name }}</h2>
            <div class="tag-container">
              <el-tag :type="terminal.status ? 'success' : 'danger'" class="status-tag" size="small">
                {{ terminal.status ? '在线' : '离线' }}
              </el-tag>

              <el-tag v-if="environmentInfo" :type="environmentInfo.type === 'detector' ? 'warning' : 'info'"
                class="env-tag" size="small">
                {{ environmentInfo.type === 'detector' ? '检测端' : '服务端' }}
              </el-tag>
            </div>
          </div>
        </div>

        <div class="connection-controls">
          <el-select v-if="connectionMode === 'remote' && terminalList.length > 0" v-model="selectedTerminalId"
            placeholder="选择终端" size="small" @change="switchTerminal" style="width: 140px;">
            <el-option v-for="item in terminalList" :key="item.id" :label="item.name || `终端 #${item.id}`"
              :value="item.id" />
          </el-select>

          <el-radio-group v-model="connectionMode" size="small" class="mode-switcher">
            <el-radio-button value="remote" :disabled="!remoteAvailable && localAvailable">
              <el-icon>
                <Connection />
              </el-icon> 远程
            </el-radio-button>
            <el-radio-button value="local" :disabled="!localAvailable">
              <el-icon>
                <Monitor />
              </el-icon> 本地
            </el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <!-- 无可用终端时显示空状态 -->
      <div v-if="!localAvailable && !remoteAvailable" class="empty-state">
        <el-empty description="无法连接到任何终端">
          <template #image>
            <div class="iot-empty-image">
              <el-icon>
                <WarningFilled />
              </el-icon>
            </div>
          </template>
          <template #description>
            <div class="empty-content">
              <p>未检测到可用的终端设备，请检查：</p>
              <ul>
                <li><el-icon>
                    <Cpu />
                  </el-icon> 本地终端是否运行</li>
                <li><el-icon>
                    <Connection />
                  </el-icon> 网络连接是否正常</li>
                <li><el-icon>
                    <Monitor />
                  </el-icon> 远程服务器是否可用</li>
              </ul>
            </div>
          </template>
          <el-button type="primary" @click="localAvailable = false; remoteAvailable = false; handleModeChange()">
            <el-icon>
              <Refresh />
            </el-icon> 重试连接
          </el-button>
        </el-empty>
      </div>

      <!-- 正常显示终端内容 -->
      <div v-else class="dashboard-container">
        <!-- 左侧：系统状态和服务控制 -->
        <div class="left-panel">
          <!-- 系统资源监控 -->
          <div class="panel-section resource-panel">
            <div class="section-header">
              <h3><el-icon>
                  <DataAnalysis />
                </el-icon> 系统资源</h3>
              <el-button type="primary" @click="refreshStatus" class="icon-button">
                <el-icon>
                  <Refresh />
                </el-icon>
              </el-button>
            </div>

            <div class="resource-metrics">
              <div class="metric-item">
                <div class="metric-header">
                  <span class="metric-label">CPU 使用率</span>
                  <span class="metric-value">{{ status.cpu_usage.toFixed(1) }}%</span>
                </div>
                <el-progress :percentage="status.cpu_usage" :color="customColorMethod" :stroke-width="10"
                  :show-text="false" />
              </div>

              <div class="metric-item">
                <div class="metric-header">
                  <span class="metric-label">内存使用率</span>
                  <span class="metric-value">{{ status.memory_usage.toFixed(1) }}%</span>
                </div>
                <el-progress :percentage="status.memory_usage" :color="customColorMethod" :stroke-width="10"
                  :show-text="false" />
              </div>

              <div class="metric-item">
                <div class="metric-header">
                  <span class="metric-label">磁盘使用率</span>
                  <span class="metric-value">{{ status.disk_usage.toFixed(1) }}%</span>
                </div>
                <el-progress :percentage="status.disk_usage" :color="customColorMethod" :stroke-width="10"
                  :show-text="false" />
              </div>

              <div class="metric-item">
                <div class="metric-header">
                  <span class="metric-label">可用内存 / 总内存</span>
                  <span class="metric-value">{{ (status.memory_available / 1024 / 1024 / 1024).toFixed(2) }} / {{
                    (status.memory_total / 1024 / 1024 / 1024).toFixed(2) }} GB</span>
                </div>
              </div>

              <div class="metric-item">
                <div class="metric-header">
                  <span class="metric-label">可用磁盘 / 总磁盘</span>
                  <span class="metric-value">{{ (status.disk_free / 1024 / 1024 / 1024).toFixed(2) }} / {{
                    (status.disk_total / 1024 / 1024 / 1024).toFixed(2) }} GB</span>
                </div>
              </div>


              <!-- 添加额外系统信息显示 -->
              <div class="system-metrics">
                <div class="metric-box" v-if="status.system_uptime">
                  <div class="metric-icon"><el-icon>
                      <Timer />
                    </el-icon></div>
                  <div class="metric-data">
                    <div class="metric-title">运行时间</div>
                    <div class="metric-number">{{ formatUptime(status.system_uptime) }}</div>
                  </div>
                </div>
                <div class="metric-box" v-if="status.frame_rate !== undefined">
                  <div class="metric-icon"><el-icon>
                      <VideoCamera />
                    </el-icon></div>
                  <div class="metric-data">
                    <div class="metric-title">帧率</div>
                    <div class="metric-number">{{ status.frame_rate?.toFixed(1) || 0 }} fps</div>
                  </div>
                </div>
                <div class="metric-box" v-if="status.total_frames !== undefined">
                  <div class="metric-icon"><el-icon>
                      <Picture />
                    </el-icon></div>
                  <div class="metric-data">
                    <div class="metric-title">总帧数</div>
                    <div class="metric-number">{{ status.total_frames }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 系统信息 -->
          <div class="panel-section">
            <div class="section-header">
              <h3><el-icon>
                  <InfoFilled />
                </el-icon> 系统信息</h3>
            </div>

            <div class="info-grid">
              <div class="info-item">
                <div class="info-icon"><el-icon>
                    <Location />
                  </el-icon></div>
                <div class="info-content">
                  <span class="info-label">终端ID</span>
                  <span class="info-value chip">{{ status.terminal_id || terminal.id || '本地终端' }}</span>
                </div>
              </div>

              <div class="info-item">
                <div class="info-icon"><el-icon>
                    <Opportunity />
                  </el-icon></div>
                <div class="info-content">
                  <span class="info-label">模型状态</span>
                  <el-tag :type="status.model_loaded ? 'success' : 'warning'" size="small" class="status-chip">
                    {{ status.model_loaded ? '已加载' : '未加载' }}
                  </el-tag>
                </div>
              </div>

              <div class="info-item">
                <div class="info-icon"><el-icon>
                    <Setting />
                  </el-icon></div>
                <div class="info-content">
                  <span class="info-label">工作模式</span>
                  <span class="info-value">{{ status.mode }}</span>
                </div>
              </div>

              <div class="info-item" v-if="terminalDetails.last_active">
                <div class="info-icon"><el-icon>
                    <Calendar />
                  </el-icon></div>
                <div class="info-content">
                  <span class="info-label">最后活动</span>
                  <span class="info-value time-value">{{ terminalDetails.last_active }}</span>
                </div>
              </div>

              <div class="info-item" v-if="status.last_detection && status.last_detection.count !== undefined">
                <div class="info-icon"><el-icon>
                    <DataAnalysis />
                  </el-icon></div>
                <div class="info-content">
                  <span class="info-label">最后检测</span>
                  <span class="info-value">{{ status.last_detection.count }} 人</span>
                </div>
              </div>

              <div class="info-item">
                <div class="info-icon"><el-icon>
                    <WarningFilled />
                  </el-icon></div>
                <div class="info-content">
                  <span class="info-label">CO2浓度</span>
                  <span class="info-value">{{ status.co2_level }} ppm</span>
                  <el-tag :type="getCO2StatusType(status.co2_status)" size="small" class="status-chip">
                    {{ status.co2_status }}
                  </el-tag>
                </div>
              </div>
            </div>
          </div>

          <!-- 服务控制 -->
          <div class="panel-section">
            <div class="section-header">
              <h3><el-icon>
                  <Setting />
                </el-icon> 服务控制</h3>
            </div>

            <div class="service-controls">
              <!-- 拉取模式 -->
              <div class="service-item" :class="{ 'active-service': status.pull_running }">
                <div class="service-info">
                  <div class="service-icon">
                    <el-icon>
                      <Download />
                    </el-icon>
                  </div>
                  <div>
                    <span class="service-name">拉取模式</span>
                    <el-tag :type="status.pull_running ? 'success' : 'info'" size="small" class="service-status">
                      {{ status.pull_running ? '运行中' : '已停止' }}
                    </el-tag>
                  </div>
                </div>
                <div class="service-actions">
                  <el-button type="primary" size="small" @click="startService('pull')" :disabled="status.pull_running"
                    class="control-button">
                    <el-icon>
                      <VideoPlay />
                    </el-icon>启动
                  </el-button>
                  <el-button type="danger" size="small" @click="stopService('pull')" :disabled="!status.pull_running"
                    class="control-button">
                    <el-icon>
                      <VideoPause />
                    </el-icon>停止
                  </el-button>
                </div>
              </div>

              <!-- 接收模式 -->
              <div class="service-item" :class="{ 'active-service': status.push_running }">
                <div class="service-info">
                  <div class="service-icon">
                    <el-icon>
                      <Upload />
                    </el-icon>
                  </div>
                  <div>
                    <span class="service-name">接收模式</span>
                    <el-tag :type="status.push_running ? 'success' : 'info'" size="small" class="service-status">
                      {{ status.push_running ? '运行中' : '已停止' }}
                    </el-tag>
                  </div>
                </div>
                <div class="service-actions">
                  <el-button type="primary" size="small" @click="startService('push')" :disabled="status.push_running"
                    class="control-button">
                    <el-icon>
                      <VideoPlay />
                    </el-icon>启动
                  </el-button>
                  <el-button type="danger" size="small" @click="stopService('push')" :disabled="!status.push_running"
                    class="control-button">
                    <el-icon>
                      <VideoPause />
                    </el-icon>停止
                  </el-button>
                </div>
              </div>

              <!-- 系统操作 -->
              <div class="service-actions-panel">
                <el-button-group>
                  <el-button type="primary" size="small" @click="startService('both')"
                    :disabled="status.pull_running && status.push_running" class="action-button">
                    <el-icon>
                      <Open />
                    </el-icon>全部启动
                  </el-button>
                  <el-button type="danger" size="small" @click="stopService('both')"
                    :disabled="!status.pull_running && !status.push_running" class="action-button">
                    <el-icon>
                      <TurnOff />
                    </el-icon>全部停止
                  </el-button>
                  <el-button type="warning" @click="restartTerminal" :disabled="!terminal.status" size="small"
                    class="action-button">
                    <el-icon>
                      <RefreshRight />
                    </el-icon>重启终端
                  </el-button>
                </el-button-group>
              </div>
            </div>
          </div>

          <!-- 节点状态 -->
          <div class="panel-section">
            <div class="section-header">
              <h3><el-icon>
                  <VideoCamera />
                </el-icon> 节点状态</h3>
            </div>

            <el-empty v-if="Object.keys(status.nodes).length === 0" description="暂无节点数据" :image-size="80"></el-empty>
            <div v-else class="node-grid">
              <div v-for="[id, nodeStatus] in Object.entries(status.nodes)" :key="id" class="node-item"
                :class="{ 'node-active': nodeStatus === '在线' }">
                <div class="node-icon">
                  <el-icon>
                    <VideoCamera />
                  </el-icon>
                </div>
                <div class="node-info">
                  <div class="node-id">节点 #{{ id }}</div>
                  <el-tag :type="nodeStatus === '在线' ? 'success' : 'danger'" size="small" class="node-status">
                    {{ nodeStatus }}
                  </el-tag>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧：配置管理和日志查看 -->
        <div class="right-panel">
          <!-- 统一配置面板 -->
          <div class="panel-section">
            <div class="section-header">
              <h3><el-icon>
                  <Tools />
                </el-icon> 终端配置</h3>
              <div class="button-group">
                <el-button type="primary" size="small" @click="saveConfig" class="action-button">
                  <el-icon>
                    <Check />
                  </el-icon>保存配置
                </el-button>
                <el-button type="success" size="small" @click="applyConfig" class="action-button">
                  <el-icon>
                    <Connection />
                  </el-icon>立即应用
                </el-button>
                <el-button size="small" @click="resetConfig" class="action-button">
                  <el-icon>
                    <RefreshLeft />
                  </el-icon>重置
                </el-button>
              </div>
            </div>

            <el-tabs v-model="activeConfigTab" class="config-tabs">
              <!-- 基本设置标签页 -->
              <el-tab-pane label="基本设置" name="basic">
                <template #label>
                  <span class="tab-label">
                    <el-icon><Setting /></el-icon>
                    基本设置
                  </span>
                </template>
                
                <el-form :model="config" label-width="90px" class="config-form" size="small">
                  <div class="form-grid">
                    <el-form-item label="工作模式" class="form-item">
                      <el-select v-model="config.mode" style="width: 100%">
                        <el-option label="拉取模式" value="pull">
                          <div class="option-content">
                            <el-icon class="option-icon">
                              <Download />
                            </el-icon>
                            <span>拉取模式</span>
                          </div>
                        </el-option>
                        <el-option label="接收模式" value="push">
                          <div class="option-content">
                            <el-icon class="option-icon">
                              <Upload />
                            </el-icon>
                            <span>接收模式</span>
                          </div>
                        </el-option>
                        <el-option label="双模式" value="both">
                          <div class="option-content">
                            <el-icon class="option-icon">
                              <Refresh />
                            </el-icon>
                            <span>双模式</span>
                          </div>
                        </el-option>
                      </el-select>
                    </el-form-item>

                    <el-form-item label="拉取间隔" class="form-item">
                      <el-input-number v-model="config.interval" :min="1" :max="60"
                        style="width: 100%"></el-input-number>
                    </el-form-item>

                    <el-form-item label="高级选项" class="form-item full-width">
                      <div class="switch-grid">
                        <div class="switch-item">
                          <span>保存图像</span>
                          <el-switch v-model="config.save_image" active-color="#13ce66"></el-switch>
                        </div>
                        <div class="switch-item">
                          <span>预加载模型</span>
                          <el-switch v-model="config.preload_model" active-color="#13ce66"></el-switch>
                        </div>
                        <div class="switch-item">
                          <span>启用CO2传感器</span>
                          <el-switch v-model="config.co2_enabled" active-color="#13ce66"></el-switch>
                        </div>
                      </div>
                    </el-form-item>

                    <el-form-item label="CO2读取间隔" class="form-item" v-if="config.co2_enabled">
                      <el-input-number v-model="config.co2_read_interval" :min="10" :max="300"
                        style="width: 100%"></el-input-number>
                    </el-form-item>
                  </div>
                </el-form>
              </el-tab-pane>

              <!-- 节点管理标签页 -->
              <el-tab-pane label="节点管理" name="nodes">
                <template #label>
                  <span class="tab-label">
                    <el-icon><VideoCamera /></el-icon>
                    节点管理
                  </span>
                </template>
                
                <div class="node-config">
                  <!-- 数据节点 -->
                  <div class="node-section">
                    <div class="node-section-header">数据节点</div>
                    <div class="node-list-container">
                      <el-table :data="config.data_nodes" size="small" height="200px" class="node-table">
                        <el-table-column prop="id" label="ID" width="60" align="center" />
                        <el-table-column prop="name" label="名称" width="140" show-overflow-tooltip />
                        <el-table-column prop="ip" label="IP" width="160" show-overflow-tooltip />
                        <el-table-column prop="port" label="端口" width="80" align="center" />
                        <el-table-column label="功能" min-width="160">
                          <template #default="scope">
                            <el-tag v-for="cap in (scope.row.capabilities || [])" :key="cap" size="small" style="margin-right:4px">{{ cap }}</el-tag>
                          </template>
                        </el-table-column>
                        <el-table-column label="操作" width="140" align="center">
                          <template #default="scope">
                            <el-button size="small" @click="previewNodeImage(scope.row.id)" circle :disabled="connectionMode !== 'local'">
                              <el-icon><Picture /></el-icon>
                            </el-button>
                            <el-button type="danger" size="small" @click="removeDataNode(scope.$index)" circle>
                              <el-icon><Delete /></el-icon>
                            </el-button>
                          </template>
                        </el-table-column>
                      </el-table>
                    </div>
                    <div class="add-node-form">
                      <el-input v-model="newDataNode.id" placeholder="ID" class="node-id-input" size="small" />
                      <el-input v-model="newDataNode.name" placeholder="名称" class="node-name-input" size="small" />
                      <el-input v-model="newDataNode.ip" placeholder="IP" class="node-ip-input" size="small" />
                      <el-input v-model.number="newDataNode.port" placeholder="端口" class="node-port-input" size="small" />
                      <el-input v-model="newDataNode.capabilities" placeholder="功能(逗号分隔)" class="node-cap-input" size="small" />
                      <el-button type="primary" @click="addDataNode" size="small" class="add-button">
                        <el-icon><Plus /></el-icon>添加数据节点
                      </el-button>
                    </div>
                  </div>

                  <!-- 控制节点 -->
                  <div class="node-section" style="margin-top: 16px;">
                    <div class="node-section-header">控制节点</div>
                    <div class="node-list-container">
                      <el-table :data="config.control_nodes" size="small" height="200px" class="node-table">
                        <el-table-column prop="id" label="ID" width="60" align="center" />
                        <el-table-column prop="name" label="名称" width="140" show-overflow-tooltip />
                        <el-table-column prop="ip" label="IP" width="160" show-overflow-tooltip />
                        <el-table-column prop="port" label="端口" width="80" align="center" />
                        <el-table-column label="功能" min-width="160">
                          <template #default="scope">
                            <el-tag v-for="cap in (scope.row.capabilities || [])" :key="cap" size="small" style="margin-right:4px">{{ cap }}</el-tag>
                          </template>
                        </el-table-column>
                        <el-table-column label="操作" width="80" align="center">
                          <template #default="scope">
                            <el-button type="danger" size="small" @click="removeControlNode(scope.$index)" circle>
                              <el-icon><Delete /></el-icon>
                            </el-button>
                          </template>
                        </el-table-column>
                      </el-table>
                    </div>
                    <div class="add-node-form">
                      <el-input v-model="newControlNode.id" placeholder="ID" class="node-id-input" size="small" />
                      <el-input v-model="newControlNode.name" placeholder="名称" class="node-name-input" size="small" />
                      <el-input v-model="newControlNode.ip" placeholder="IP" class="node-ip-input" size="small" />
                      <el-input v-model.number="newControlNode.port" placeholder="端口" class="node-port-input" size="small" />
                      <el-input v-model="newControlNode.capabilities" placeholder="功能(逗号分隔)" class="node-cap-input" size="small" />
                      <el-button type="primary" @click="addControlNode" size="small" class="add-button">
                        <el-icon><Plus /></el-icon>添加控制节点
                      </el-button>
                    </div>
                  </div>
                </div>
              </el-tab-pane>

              <!-- 摄像头参数标签页 -->
              <el-tab-pane label="摄像头参数" name="camera">
                <template #label>
                  <span class="tab-label">
                    <el-icon><Picture /></el-icon>
                    摄像头参数
                  </span>
                </template>
                
                <div class="camera-config-form">
                  <el-form :model="config.camera_config" label-width="100px" size="small">
                    <el-row :gutter="12">
                      <el-col :span="8">
                        <el-form-item label="分辨率">
                          <el-select v-model="config.camera_config.frame_size">
                            <el-option v-for="(size, key) in frameSizes" :key="key" :label="size.label"
                              :value="parseInt(String(key))" />
                          </el-select>
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="亮度">
                          <el-input-number v-model="config.camera_config.brightness" :min="0" :max="2" />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="对比度">
                          <el-input-number v-model="config.camera_config.contrast" :min="0" :max="2" />
                        </el-form-item>
                      </el-col>
                    </el-row>
                    <el-row :gutter="12">
                      <el-col :span="8">
                        <el-form-item label="饱和度">
                          <el-input-number v-model="config.camera_config.saturation" :min="0" :max="2" />
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="特效">
                          <el-select v-model="config.camera_config.special_effect">
                            <el-option label="无" :value="0" />
                            <el-option label="黑白" :value="1" />
                            <el-option label="负片" :value="2" />
                          </el-select>
                        </el-form-item>
                      </el-col>
                      <el-col :span="8">
                        <el-form-item label="镜像">
                          <el-switch v-model="config.camera_config.hmirror" active-color="#13ce66" />
                          <span style="margin-left:8px;">水平</span>
                          <el-switch v-model="config.camera_config.vflip" active-color="#13ce66"
                            style="margin-left:8px;" />
                          <span style="margin-left:8px;">垂直</span>
                        </el-form-item>
                      </el-col>
                    </el-row>
                  </el-form>
                  <el-button type="primary" size="small" style="margin-top:8px;" @click="saveCameraConfig">
                    <el-icon>
                      <Check />
                    </el-icon>保存摄像头参数
                  </el-button>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
          <!-- 硬件控制面板 -->
          <div class="panel-section">
            <div class="section-header">
              <h3>
                <el-icon><MagicStick /></el-icon> 硬件控制
              </h3>
            </div>

            <!-- 蜂鸣器控制 -->
            <div class="hardware-control-section">
              <div class="hardware-title">
                <el-icon><Bell /></el-icon>
                <span>蜂鸣器控制</span>
                <el-tag :type="buzzerAvailable ? 'success' : 'info'" size="small" class="hardware-status">
                  {{ buzzerAvailable ? '可用' : '不可用' }}
                </el-tag>
                <el-tag v-if="buzzerAvailable && buzzerActive" type="warning" size="small" class="hardware-status">
                  正在鸣叫
                </el-tag>
              </div>

              <div class="buzzer-controls">
                <el-form :model="buzzerForm" label-width="80px" size="small">
                  <el-row :gutter="12">
                    <el-col :span="12">
                      <el-form-item label="鸣叫模式">
                        <el-select v-model="buzzerForm.pattern" style="width: 100%">
                          <el-option v-for="pattern in buzzerPatterns" :key="pattern.value" 
                            :label="pattern.label" :value="pattern.value">
                            <div class="option-content">
                              <el-icon class="option-icon">
                                <component :is="pattern.icon" />
                              </el-icon>
                              <span>{{ pattern.label }}</span>
                            </div>
                          </el-option>
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="buzzerForm.pattern === 'SINGLE_BEEP' ? 12 : 6">
                      <el-form-item :label="buzzerForm.pattern === 'SINGLE_BEEP' ? '持续时间' : '重复次数'">
                        <el-input-number 
                          v-if="buzzerForm.pattern === 'SINGLE_BEEP'"
                          v-model="buzzerForm.duration" 
                          :min="0.1" 
                          :max="5" 
                          :step="0.1"
                          :precision="1"
                          style="width: 100%"
                        />
                        <el-input-number 
                          v-else
                          v-model="buzzerForm.repeat" 
                          :min="1" 
                          :max="10" 
                          style="width: 100%"
                        />
                      </el-form-item>
                    </el-col>
                    <el-col :span="6" v-if="buzzerForm.pattern !== 'SINGLE_BEEP'">
                      <el-form-item label="持续时间" v-if="buzzerForm.pattern === 'LONG_BEEP'">
                        <el-input-number 
                          v-model="buzzerForm.duration" 
                          :min="0.1" 
                          :max="5" 
                          :step="0.1"
                          :precision="1"
                          style="width: 100%"
                        />
                      </el-form-item>
                    </el-col>
                  </el-row>
                </el-form>
                
                <div class="buzzer-actions">
                  <el-button-group>
                    <el-button type="primary" @click="beep" :disabled="buzzerActive">
                      <el-icon><Bell /></el-icon> 简单鸣叫
                    </el-button>
                    <el-button type="success" @click="startBuzzer" :disabled="buzzerActive">
                      <el-icon><Warning /></el-icon> 启动模式
                    </el-button>
                    <el-button type="danger" @click="stopBuzzer" :disabled="!buzzerActive">
                      <el-icon><Mute /></el-icon> 停止鸣叫
                    </el-button>
                  </el-button-group>
                </div>
              </div>
            </div>

            <!-- 灯光控制 -->
            <div class="hardware-control-section">
              <div class="hardware-title">
                <el-icon><MagicStick /></el-icon>
                <span>灯光控制</span>
                <el-tag :type="lightStatus.online ? 'success' : 'info'" size="small" class="hardware-status">
                  {{ lightStatus.online ? '可用' : '不可用' }}
                </el-tag>
                <el-tag v-if="!lightStatus.supports_rotate" type="info" size="small" class="hardware-status">
                  不支持旋转
                </el-tag>
              </div>

              <div class="buzzer-controls">
                <el-form label-width="80px" size="small">
                  <el-row :gutter="12">
                    <el-col :span="8">
                      <el-form-item label="节点ID">
                        <el-input-number v-model="lightStatus.node_id" :min="0" :step="1" :disabled="connectionMode === 'local' ? !lightStatus.online : false" @change="fetchLightStatus" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="10">
                      <el-form-item label="角度(°)">
                        <el-slider v-model="lightAngle" :min="0" :max="180" :step="5" :disabled="connectionMode === 'local' ? (!lightStatus.online || !lightStatus.supports_rotate) : false" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="6">
                      <el-form-item label=" ">
                        <el-button type="primary" :disabled="connectionMode === 'local' ? (!lightStatus.online || !lightStatus.supports_rotate) : false" @click="rotateLight">
                          <el-icon><MagicStick /></el-icon> 旋转
                        </el-button>
                      </el-form-item>
                    </el-col>
                  </el-row>
                  <el-row :gutter="12" style="margin-top: 8px;">
                    <el-col :span="8">
                      <el-form-item label="开灯角度">
                        <el-input-number v-model="lightOnAngle" :min="0" :max="180" :step="1" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="关灯角度">
                        <el-input-number v-model="lightOffAngle" :min="0" :max="180" :step="1" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label=" ">
                        <el-button type="success" @click="turnLightOn" :disabled="connectionMode === 'local' ? (!lightStatus.online || !lightStatus.supports_rotate) : false">开灯</el-button>
                        <el-button type="warning" @click="turnLightOff" :disabled="connectionMode === 'local' ? (!lightStatus.online || !lightStatus.supports_rotate) : false" style="margin-left: 8px;">关灯</el-button>
                      </el-form-item>
                    </el-col>
                  </el-row>
                  <div style="text-align:center;color:#909399;">
                    默认 {{ lightStatus.default_angle }}°，约 {{ lightStatus.auto_return_time }} 秒自动回正
                  </div>
                </el-form>
              </div>
            </div>
          </div>
          <!-- CO2数据图表 -->
          <div class="panel-section">
            <div class="section-header">
              <h3><el-icon>
                  <WarningFilled />
                </el-icon> CO2浓度监测</h3>
              <el-tag :type="getCO2StatusType(status.co2_status)" size="small" class="status-chip">
                {{ status.co2_status }}
              </el-tag>
            </div>

            <div class="co2-chart-container">
              <EnvironmentalChart
                :terminal-id="terminal.id"
                data-type="co2"
                height="250px"
              />
            </div>
          </div>

          <!-- 日志查看 -->
          <div class="panel-section">
            <div class="section-header">
              <h3><el-icon>
                  <Notebook />
                </el-icon> 系统日志</h3>
              <el-button size="small" type="primary" plain @click="loadLogs" class="refresh-button">
                <el-icon>
                  <Refresh />
                </el-icon>刷新
              </el-button>
            </div>

            <div class="logs-container">
              <el-empty v-if="logs.length === 0" description="暂无日志数据" :image-size="80"></el-empty>
              <el-table v-else :data="logs" height="350px" border stripe size="small" class="logs-table">
                <el-table-column prop="timestamp" label="时间" width="160" show-overflow-tooltip></el-table-column>
                <el-table-column prop="level" label="级别" width="80" align="center">
                  <template #default="scope">
                    <el-tag :type="getLogLevelType(scope.row.level)" size="small" effect="dark" class="log-level">
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
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.terminal-view {
  padding: 12px;
  max-width: 1400px;
  margin: 0 auto;
  /* 删除 min-height 固定高度限制 */
}

.main-card {
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  background: #fff;
  /* 修改为 auto 高度，确保卡片可以随内容扩展 */
  height: auto;
  min-height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
}

/* 终端标题栏 */
.terminal-header {
  background: linear-gradient(135deg, #34495e, #2c3e50);
  color: white;
  padding: 15px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #2c3e50;
  /* 添加固定定位，确保头部始终可见 */
  position: sticky;
  top: 0;
  z-index: 10;
}

.title-area {
  display: flex;
  align-items: center;
}

.terminal-icon {
  width: 40px;
  height: 40px;
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-right: 15px;
  font-size: 22px;
}

.terminal-info h2 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.tag-container {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.connection-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mode-switcher {
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* 主要仪表盘区域 */
.dashboard-container {
  display: flex;
  /* 删除固定高度限制 */
  height: auto;
  /* 允许内容溢出时滚动 */
  overflow: visible;
  padding-top: 1px;
  /* 防止margin塌陷 */
}

.left-panel {
  width: 42%;
  background-color: #f4f6f9;
  border-right: 1px solid #e6e9ed;
  /* 内容溢出时可滚动 */
  overflow-y: visible;
  padding: 16px;
}

.right-panel {
  width: 58%;
  /* 内容溢出时可滚动 */
  overflow-y: visible;
  padding: 16px;
}

/* 面板部分 */
.panel-section {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}

.section-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 500;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-header h3 el-icon {
  color: #409EFF;
}

/* 资源监控样式 */
.resource-panel {
  background: linear-gradient(to bottom, #fff, #f9fafc);
}

.resource-metrics {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-label {
  font-weight: 500;
  color: #606266;
  font-size: 0.9rem;
}

.metric-value {
  font-weight: 600;
  color: #2c3e50;
  font-size: 0.9rem;
}

/* 系统指标 */
.system-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 16px;
}

.metric-box {
  background: #f8f9fb;
  border-radius: 6px;
  padding: 10px;
  display: flex;
  align-items: center;
  border: 1px solid #ebeef5;
}

.metric-icon {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  background: rgba(64, 158, 255, 0.1);
  color: #409EFF;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 18px;
  margin-right: 10px;
}

.metric-data {
  flex: 1;
}

.metric-title {
  font-size: 0.75rem;
  color: #909399;
  margin-bottom: 2px;
}

.metric-number {
  font-size: 0.9rem;
  font-weight: 600;
  color: #2c3e50;
}

/* 信息网格 */
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 6px;
  background: #f8f9fb;
  border: 1px solid #ebeef5;
}

.info-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: rgba(64, 158, 255, 0.1);
  color: #409EFF;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 16px;
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-label {
  font-size: 0.75rem;
  color: #909399;
}

.info-value {
  font-size: 0.85rem;
  font-weight: 600;
  color: #2c3e50;
}

.chip {
  background: #f0f2f5;
  padding: 2px 8px;
  border-radius: 12px;
  display: inline-block;
}

.status-chip {
  border-radius: 12px;
  font-weight: 500;
}

.time-value {
  font-size: 0.8rem;
  color: #606266;
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
  padding: 12px 16px;
  background-color: #f8f9fb;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  transition: all 0.3s ease;
}

.service-item.active-service {
  background: linear-gradient(to right, rgba(64, 158, 255, 0.1), rgba(64, 158, 255, 0.05));
  border-color: rgba(64, 158, 255, 0.2);
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.1);
}

.service-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.service-icon {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  background: rgba(64, 158, 255, 0.1);
  color: #409EFF;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 18px;
}

.service-name {
  font-weight: 500;
  color: #2c3e50;
  display: block;
  margin-bottom: 2px;
}

.service-status {
  margin-top: 2px;
  font-size: 0.7rem;
}

.service-actions {
  display: flex;
  gap: 8px;
}

.control-button {
  min-width: 60px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.service-actions-panel {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}

.action-button {
  min-width: 90px;
}

/* 节点显示 */
.node-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 6px;
  background: #f8f9fb;
  border: 1px solid #ebeef5;
  transition: all 0.3s ease;
}

.node-active {
  background: linear-gradient(to right, rgba(19, 206, 102, 0.1), rgba(19, 206, 102, 0.05));
  border-color: rgba(19, 206, 102, 0.2);
}

.node-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: rgba(64, 158, 255, 0.1);
  color: #409EFF;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 16px;
}

.node-active .node-icon {
  background: rgba(19, 206, 102, 0.1);
  color: #13ce66;
}

.node-info {
  flex: 1;
}

.node-id {
  font-size: 0.85rem;
  font-weight: 500;
  color: #2c3e50;
  margin-bottom: 3px;
}

.node-status {
  font-size: 0.7rem;
}

/* 配置表单样式 */
.config-form {
  margin-top: 0;
}

/* 配置标签页样式 */
.config-tabs {
  margin-top: 16px;
}

.config-tabs .el-tabs__header {
  margin-bottom: 20px;
}

.config-tabs .el-tabs__nav-wrap {
  background: #f8f9fb;
  border-radius: 8px;
  padding: 4px;
}

.config-tabs .el-tabs__item {
  border-radius: 6px;
  margin: 0 2px;
  transition: all 0.3s ease;
}

.config-tabs .el-tabs__item.is-active {
  background: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
}

.tab-label el-icon {
  font-size: 16px;
}

.config-tabs .el-tabs__content {
  padding: 0;
}

.config-tabs .el-tab-pane {
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  padding: 10px;
}

.form-item {
  margin-bottom: 0;
}

.form-item.full-width {
  grid-column: 1 / -1;
}

.switch-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.switch-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  color: #606266;
}

.node-config {
  padding: 10px;
}

.node-list-container {
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #ebeef5;
  margin-bottom: 12px;
}

.add-node-form {
  display: flex;
  gap: 10px;
  padding: 12px;
  background-color: #f8f9fb;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.node-id-input {
  width: 80px;
}

.node-url-input {
  flex-grow: 1;
}

.add-button {
  min-width: 80px;
}

/* 日志查看 */
.logs-container {
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #ebeef5;
}

.logs-table {
  width: 100%;
}

.log-level {
  padding: 2px 6px;
  font-size: 0.7rem;
}

/* CO2图表样式 */
.co2-chart-container {
  min-height: 280px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.no-co2-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 280px;
  background-color: #f9fafc;
  border-radius: 8px;
  border: 1px dashed #dcdfe6;
}

/* 空状态样式 */
.empty-state {
  padding: 60px 0;
  text-align: center;
  background: linear-gradient(to bottom, #f9fafc, #f4f6f9);
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.iot-empty-image {
  font-size: 48px;
  color: #909399;
  margin-bottom: 20px;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #f0f2f5;
  display: flex;
  justify-content: center;
  align-items: center;
}

.empty-content {
  margin: 15px 0;
}

.empty-content p {
  color: #606266;
  margin-bottom: 10px;
  font-weight: 500;
}

.empty-content ul {
  text-align: left;
  display: inline-block;
  margin: 0 auto;
  color: #909399;
  list-style-type: none;
  padding: 0;
}

.empty-content li {
  margin: 8px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.empty-content li el-icon {
  margin-right: 8px;
  font-size: 1rem;
}

/* 按钮样式 */
.icon-button {
  padding: 6px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.button-group {
  display: flex;
  gap: 8px;
}

.refresh-button {
  min-width: 70px;
}

/* 选项内容 */
.option-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.option-icon {
  color: #409EFF;
}

/* 响应式布局 */
@media (max-width: 1200px) {
  .dashboard-container {
    flex-direction: column;
    height: auto;
  }

  .left-panel,
  .right-panel {
    width: 100%;
    padding: 12px;
    /* 确保在移动视图下内容可以滚动 */
    overflow-y: visible;
  }

  .system-metrics {
    grid-template-columns: repeat(2, 1fr);
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .terminal-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .connection-controls {
    width: 100%;
    justify-content: space-between;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .system-metrics {
    grid-template-columns: 1fr;
  }

  .service-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .service-actions {
    width: 100%;
    justify-content: space-between;
  }

  .node-grid {
    grid-template-columns: 1fr;
  }

  .switch-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .add-node-form {
    flex-direction: column;
  }

  .node-id-input,
  .node-url-input {
    width: 100%;
  }

  .service-actions-panel {
    flex-direction: column;
    gap: 8px;
  }

  .service-actions-panel .el-button-group {
    display: flex;
    flex-direction: column;
    width: 100%;
  }

  .service-actions-panel .el-button {
    margin-left: 0 !important;
    border-radius: 4px !important;
    margin-bottom: 8px;
  }
}
/* 硬件控制部分样式 */
.hardware-control-section {
  background-color: #f8f9fb;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  border: 1px solid #ebeef5;
}

.hardware-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-weight: 500;
  color: #2c3e50;
}

.hardware-title .el-icon {
  font-size: 18px;
  color: #409EFF;
}

.hardware-status {
  margin-left: auto;
}

.buzzer-controls {
  background-color: #fff;
  border-radius: 6px;
  padding: 16px;
  border: 1px solid #ebeef5;
}

.buzzer-actions {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.buzzer-actions .el-button {
  min-width: 90px;
}
</style>