export interface AreaItem {
  id: number
  name: string
  current_count: number
  max_capacity: number
  status: 'normal' | 'abnormal'
  update_time: string
}