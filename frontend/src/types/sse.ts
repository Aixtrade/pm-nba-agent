/**
 * SSE 相关类型定义
 * 与后端 pm_nba_agent/api/models/ 对应
 */

import type { GameData, PlayAction } from './index'

// SSE 请求参数
export interface LiveStreamRequest {
  url: string
  poll_interval?: number
  include_scoreboard?: boolean
  include_boxscore?: boolean
  include_playbyplay?: boolean
  playbyplay_limit?: number
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

// PlayByPlay 事件数据
export interface PlayByPlayEventData {
  game_id: string
  actions: PlayAction[]
}

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

// SSE 事件类型
export type SSEEventType =
  | 'scoreboard'
  | 'boxscore'
  | 'playbyplay'
  | 'analysis_chunk'
  | 'heartbeat'
  | 'polymarket_info'
  | 'polymarket_book'
  | 'error'
  | 'game_end'

// SSE 事件处理器
export interface SSEEventHandlers {
  onScoreboard?: (data: ScoreboardEventData) => void
  onBoxscore?: (data: BoxscoreEventData) => void
  onPlayByPlay?: (data: PlayByPlayEventData) => void
  onAnalysisChunk?: (data: AnalysisChunkEventData) => void
  onHeartbeat?: (data: HeartbeatEventData) => void
  onPolymarketInfo?: (data: PolymarketInfoEventData) => void
  onPolymarketBook?: (data: PolymarketBookEventData) => void
  onError?: (data: ErrorEventData) => void
  onGameEnd?: (data: GameEndEventData) => void
  onOpen?: () => void
  onClose?: () => void
}

// 连接状态
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error'
