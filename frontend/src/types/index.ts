/**
 * TypeScript 类型定义
 * 与后端 pm_nba_agent/models/game_data.py 对应
 */

// 球队统计
export interface TeamStatistics {
  rebounds: number
  assists: number
  field_goal_pct: number
  three_point_pct: number
  free_throw_pct: number
  turnovers: number
  steals: number
  blocks: number
}

// 球队数据
export interface TeamData {
  name: string
  abbreviation: string
  score: number
  statistics: TeamStatistics
}

// 球员统计
export interface PlayerStatistics {
  points: number
  rebounds: number
  assists: number
  minutes: string
  field_goals_made: number
  field_goals_attempted: number
  three_pointers_made: number
  three_pointers_attempted: number
  free_throws_made: number
  free_throws_attempted: number
  steals: number
  blocks: number
  turnovers: number
  plus_minus: number
}

// 球员数据
export interface PlayerData {
  name: string
  team: string
  position: string
  on_court: boolean
  stats: PlayerStatistics
}

// 比赛信息
export interface GameInfo {
  game_id: string
  game_date: string
  status: string
  period: number
  game_clock: string
}

// 比赛完整数据 (boxscore 事件)
export interface GameData {
  game_info: GameInfo
  teams: {
    home: TeamData
    away: TeamData
  }
  players: PlayerData[]
}
