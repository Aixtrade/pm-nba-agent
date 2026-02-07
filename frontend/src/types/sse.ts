/**
 * SSE 相关类型定义
 * 与后端 pm_nba_agent/api/models/ 对应
 */

import type { GameData } from './index'

// SSE 请求参数
export interface LiveStreamRequest {
  url: string
  poll_interval?: number
  include_scoreboard?: boolean
  include_boxscore?: boolean
  analysis_interval?: number
  strategy_ids?: string[]
  strategy_params_map?: Record<string, Record<string, unknown>>
  proxy_address?: string
}

// Scoreboard 事件数据
export interface ScoreboardEventData {
  game_id: string
  status: string
  period: number
  game_clock: string
  status_message?: string | null
  home_team: {
    name: string
    abbreviation: string
    score: number
  }
  away_team: {
    name: string
    abbreviation: string
    score: number
  }
}

// Boxscore 事件数据 (完整 GameData)
export type BoxscoreEventData = GameData

// Heartbeat 事件数据
export interface HeartbeatEventData {
  timestamp: string
}

// AnalysisChunk 事件数据
export interface AnalysisChunkEventData {
  game_id: string
  chunk: string
  is_final: boolean
  round: number
  timestamp: string
}

// Error 事件数据
export interface ErrorEventData {
  code: string
  message: string
  recoverable: boolean
  timestamp: string
}

// GameEnd 事件数据
export interface GameEndEventData {
  game_id: string
  final_score: {
    home: number
    away: number
  }
  home_team: string
  away_team: string
  timestamp: string
}

// Polymarket 事件数据
export interface PolymarketInfoEventData {
  event_id: string
  title: string
  interval: string
  asset: string
  condition_id?: string | null
  tokens: Array<{
    token_id: string
    outcome: string
    condition_id: string
    market_slug: string
  }>
  market_info?: {
    slug: string
    question?: string | null
    description?: string | null
    condition_id?: string | null
    outcomes: string[]
    clob_token_ids: string[]
    market_id?: string | null
    raw_data?: Record<string, unknown> | null
  } | null
  event_data?: Record<string, unknown> | null
}

// Polymarket Book 事件数据
export interface PolymarketBookEventData {
  asset_id?: string
  assetId?: string
  token_id?: string
  tokenId?: string
  event_type?: string
  price_changes?: Array<{
    asset_id?: string
    price?: string | number
    size?: string | number
    side?: string
    best_bid?: string | number
    best_ask?: string | number
  }>
  bids?: Array<[number | string, number | string] | { price?: number | string; size?: number | string }>
  asks?: Array<[number | string, number | string] | { price?: number | string; size?: number | string }>
  timestamp?: string
  data?: Record<string, unknown>
  payload?: Record<string, unknown>
  message?: Record<string, unknown>
  [key: string]: unknown
}

// 策略信号事件数据
export interface StrategySignalEventData {
  signal?: {
    type: 'BUY' | 'SELL' | 'HOLD'
    reason: string
    yes_size?: number | null
    no_size?: number | null
    yes_price?: number | null
    no_price?: number | null
    metadata?: Record<string, unknown>
  }
  market?: {
    yes_price?: number
    no_price?: number
    price_sum: number
    yes_best_bid?: number | null
    yes_best_ask?: number | null
    no_best_bid?: number | null
    no_best_ask?: number | null
  }
  position?: {
    yes_size: number
    no_size: number
    yes_avg_cost: number
    no_avg_cost: number
    avg_sum: number
    imbalance: number
    is_balanced: boolean
  }
  execution?: {
    success: boolean
    orders?: Array<Record<string, unknown>>
    error?: string | null
    source?: string
    strategy_id?: string
  }
  strategy?: {
    id: string
  }
  metrics?: Array<{
    key: string
    label: string
    value: string | number | boolean | null
    unit?: string
    semantic?: 'higher_better' | 'lower_better' | 'neutral'
    priority?: number
  }>
  timestamp: string
}

export interface AutoBuyStateEventData {
  enabled: boolean
  is_ordering: boolean
  last_order_time?: string | null
  stats: Record<string, { count: number; amount: number }>
  default?: Record<string, unknown>
  strategy_rules?: Record<string, unknown>
  timestamp: string
}

// SSE 事件类型
export type SSEEventType =
  | 'scoreboard'
  | 'boxscore'
  | 'analysis_chunk'
  | 'playbyplay'
  | 'heartbeat'
  | 'polymarket_info'
  | 'polymarket_book'
  | 'strategy_signal'
  | 'error'
  | 'game_end'
  | 'task_status'
  | 'task_end'
  | 'subscribed'
  | 'auto_buy_state'

// SSE 事件处理器
export interface SSEEventHandlers {
  onScoreboard?: (data: ScoreboardEventData) => void
  onBoxscore?: (data: BoxscoreEventData) => void
  onAnalysisChunk?: (data: AnalysisChunkEventData) => void
  onHeartbeat?: (data: HeartbeatEventData) => void
  onPolymarketInfo?: (data: PolymarketInfoEventData) => void
  onPolymarketBook?: (data: PolymarketBookEventData) => void
  onStrategySignal?: (data: StrategySignalEventData) => void
  onError?: (data: ErrorEventData) => void
  onGameEnd?: (data: GameEndEventData) => void
  onAutoBuyState?: (data: AutoBuyStateEventData) => void
  onOpen?: () => void
  onClose?: () => void
}

// 连接状态
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error'
