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

// SSE 事件类型
export type SSEEventType =
  | 'scoreboard'
  | 'boxscore'
  | 'playbyplay'
  | 'analysis_chunk'
  | 'heartbeat'
  | 'error'
  | 'game_end'

// SSE 事件处理器
export interface SSEEventHandlers {
  onScoreboard?: (data: ScoreboardEventData) => void
  onBoxscore?: (data: BoxscoreEventData) => void
  onPlayByPlay?: (data: PlayByPlayEventData) => void
  onAnalysisChunk?: (data: AnalysisChunkEventData) => void
  onHeartbeat?: (data: HeartbeatEventData) => void
  onError?: (data: ErrorEventData) => void
  onGameEnd?: (data: GameEndEventData) => void
  onOpen?: () => void
  onClose?: () => void
}

// 连接状态
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error'
