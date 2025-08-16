export interface AreaItem {
    id: number
    name: string
    bound_node: number
    description?: string
    building: number
    capacity: number
    floor: number
    status?: boolean
    detected_count?: number
    updated_at?: string
    is_favorite?: boolean
}

export interface HistoricalData {
    id: number
    area: number
    detected_count: number
    timestamp: string
}

export interface TemperatureHumidityData {
    id: number
    area: number
    temperature?: number
    humidity?: number
    timestamp: string
}

export interface CO2Data {
    id: number
    terminal: number
    co2_level: number
    timestamp: string
}

export interface HardwareNode {
    id: number
    name: string
    detected_count: number
    status: boolean
    terminal: number
    updated_at: string
    temperature?: number
    humidity?: number
}

export interface ProcessTerminal {
    id: number
    name: string
    status: boolean
    nodes_count?: number
    last_active?: string
    cpu_usage?: number
    memory_usage?: number
    disk_usage?: number
    disk_free?: number
    disk_total?: number
    memory_available?: number
    memory_total?: number
    model_loaded?: boolean
    push_running?: boolean
    pull_running?: boolean
    mode?: 'pull' | 'push' | 'both'
    interval?: number
    node_config?: Record<string, any>
    save_image?: boolean
    preload_model?: boolean
    nodes?: Record<string, string>
    version?: string
    co2_level?: number
    co2_status?: string
    system_uptime?: number
    frame_rate?: number
    total_frames?: number
    terminal_id?: number
    last_detection?: {
        camera_id?: number
        count?: number
        time?: string
        [key: string]: any
    }
}

export type BuildingCategory =
  | 'library'
  | 'study'
  | 'teaching'
  | 'cafeteria'
  | 'dorm'
  | 'lab'
  | 'office'
  | 'sports'
  | 'service'
  | 'other'

export interface Building {
    id: number
    name: string
    description?: string
    category?: BuildingCategory
    areas_count: number
    areas?: AreaItem[]
}

export interface User {
    id: number
    username: string
    role: 'user' | 'staff'| 'admin'
    phone?: string
    email?: string
    register_time?: string
    favorite_areas?: number[]
}

export interface Alert {
    id: number
    area: number
    grade: number
    alert_type: string
    publicity: boolean
    message: string
    timestamp: string
    solved: boolean
}

export interface Notice {
    id: number
    title: string
    content: string
    timestamp: string
    related_areas?: number[]
}

export interface SummaryData {
    nodes_count: number
    terminals_count: number
    buildings_count: number
    areas_count: number
    historical_data_count: number
    people_count: number
    notice_count: number
    alerts_count: number
    users_count: number
    nodes_online_count: number
    terminals_online_count: number
}

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
  nodes: Record<string, string | number | boolean>;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  disk_free: number;
  disk_total: number;
  memory_available: number;
  memory_total: number;
  push_running: boolean;
  pull_running: boolean;
  model_loaded: boolean;
  started_at?: string;
  mode?: string;
  co2_level?: number;
  co2_status?: string;
  system_uptime?: number;
  frame_rate?: number;
  total_frames?: number;
  terminal_id?: number;
  last_detection?: {
    camera_id?: number;
    count?: number;
    time?: string;
    [key: string]: any;
  };
  terminal_online?: boolean;
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
  co2_enabled?: boolean;
  co2_read_interval?: number;
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
 * 环境信息接口
 */
export interface EnvironmentInfo {
  type: 'detector' | 'server' | 'unknown';  // 环境类型
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