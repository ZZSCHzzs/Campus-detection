// 区域类型（对应后端Area模型）
export interface AreaItem {
    id: number
    name: string
    bound_node: number      // 关联的硬件节点ID
    description?: string
    building: number             // 区域类型
    capacity: number            // 区域容量
    floor: number            // 所属楼层
    status?: boolean          // 区域状态
    detected_count?: number    // 当前人数
    updated_at?: string       // 最后更新时间
    is_favorite?: boolean  // 是否收藏
}

// 历史数据类型（对应HistoricalData模型）
export interface HistoricalData {
    id: number
    area: number            // 关联区域ID
    detected_count: number  // 检测到的人数
    timestamp: string       // ISO格式时间
}

// 硬件节点类型（对应HardwareNode模型）
export interface HardwareNode {
    id: number
    name: string
    detected_count: number  // 检测到的人数
    status: boolean         // 节点状态
    terminal: number        // 关联的终端ID
    updated_at: string
}

// 终端类型（对应ProcessTerminal模型）
export interface ProcessTerminal {
    id: number
    name: string
    status: boolean
    nodes_count: number  // 关联的硬件节点数量
}


// 建筑类型（对应Building模型）
export interface Building {
    id: number
    name: string
    description?: string
    areas_count: number  // 区域数量
    areas?: AreaItem[]       // 关联的区域列表
}

// 用户类型（对应CustomUser模型）
export interface User {
    id: number
    username: string
    role: 'user' | 'staff'| 'admin'  // 修改为与后端一致的角色类型
    phone?: string
    email?: string
    register_time?: string  // 添加注册时间字段
    favorite_areas?: number[]  // 收藏的区域列表
}

// 告警类型（对应Alert模型）
export interface Alert {
    id: number
    area: number            // 关联区域ID
    grade: number           // 告警等级 (0:普通, 1:注意, 2:警告, 3:严重)
    alert_type: string      // 告警类型 ('fire', 'guard', 'crowd', 'health', 'other')
    publicity: boolean      // 是否公开
    message: string         // 告警信息
    timestamp: string       // 告警时间
    solved: boolean         // 是否已处理
}

// 公告类型（对应Notice模型）
export interface Notice {
    id: number
    title: string           // 公告标题
    content: string         // 公告内容
    timestamp: string       // 发布时间
    related_areas?: number[] // 相关区域ID列表
}