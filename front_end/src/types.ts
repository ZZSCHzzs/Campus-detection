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
    current_count?: number    // 当前人数
    updated_at?: string       // 最后更新时间
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
    areas?: AreaItem[]       // 关联的区域列表
}

// 用户类型（对应CustomUser模型）
export interface User {
    id: number
    username: string
    role: 'user' | 'admin'  // 修改为与后端一致的角色类型
    phone?: string
    email?: string
    register_time?: string  // 添加注册时间字段
}