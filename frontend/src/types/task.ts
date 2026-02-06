/**
 * 任务管理相关类型定义
 * 与后端 pm_nba_agent/shared/task_models.py 对应
 */

// 任务状态枚举
export type TaskState = 'pending' | 'running' | 'completed' | 'cancelled' | 'failed'

// 任务状态
export interface TaskStatus {
  task_id: string
  state: TaskState
  created_at: string
  updated_at: string
  game_id?: string | null
  error?: string | null
  home_team?: string | null
  away_team?: string | null
}

// 任务状态更新事件
export type TaskStatusEventData = TaskStatus

// 创建任务请求
export interface CreateTaskRequest {
  url: string
  poll_interval?: number
  include_scoreboard?: boolean
  include_boxscore?: boolean
  analysis_interval?: number
  strategy_ids?: string[]
  strategy_params_map?: Record<string, Record<string, unknown>>
  strategy_id?: string
  strategy_params?: Record<string, unknown>
  enable_trading?: boolean
  execution_mode?: 'SIMULATION' | 'REAL'
  order_type?: 'GTC' | 'GTD'
  order_expiration?: string | null
  min_order_amount?: number
  trade_cooldown_seconds?: number
  private_key?: string | null
  proxy_address?: string | null
}

// 创建任务响应
export interface CreateTaskResponse {
  task_id: string
  status: TaskState
}

// 任务列表响应
export interface TaskListResponse {
  tasks: TaskStatus[]
}

// 任务结束事件
export interface TaskEndEventData {
  task_id: string
  state: TaskState
}

// 订阅成功事件
export interface SubscribedEventData {
  task_id: string
}
