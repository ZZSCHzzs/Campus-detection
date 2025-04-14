
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

export interface HardwareNode {
    id: number
    name: string
    detected_count: number
    status: boolean
    terminal: number
    updated_at: string
}

export interface ProcessTerminal {
    id: number
    name: string
    status: boolean
    nodes_count: number
}

export interface Building {
    id: number
    name: string
    description?: string
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
}