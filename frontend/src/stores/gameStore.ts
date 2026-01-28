import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  ScoreboardEventData,
  BoxscoreEventData,
  PlayByPlayEventData,
  GameEndEventData,
  AnalysisChunkEventData,
} from '@/types/sse'
import type { PlayAction } from '@/types'

export const useGameStore = defineStore('game', () => {
  // 状态
  const scoreboard = ref<ScoreboardEventData | null>(null)
  const boxscore = ref<BoxscoreEventData | null>(null)
  const playByPlayActions = ref<PlayAction[]>([])
  const gameEndData = ref<GameEndEventData | null>(null)
  const analysisChunks = ref<AnalysisChunkEventData[]>([])

  // 计算属性
  const gameId = computed(() => scoreboard.value?.game_id ?? boxscore.value?.game_info.game_id ?? null)

  const gameStatus = computed(() => scoreboard.value?.status ?? boxscore.value?.game_info.status ?? '')

  const isGameEnded = computed(() => gameEndData.value !== null)

  const homeTeam = computed(() => {
    if (boxscore.value) {
      return boxscore.value.teams.home
    }
    if (scoreboard.value) {
      return {
        name: scoreboard.value.home_team.name,
        abbreviation: scoreboard.value.home_team.abbreviation,
        score: scoreboard.value.home_team.score,
        statistics: {} as never,
      }
    }
    return null
  })

  const awayTeam = computed(() => {
    if (boxscore.value) {
      return boxscore.value.teams.away
    }
    if (scoreboard.value) {
      return {
        name: scoreboard.value.away_team.name,
        abbreviation: scoreboard.value.away_team.abbreviation,
        score: scoreboard.value.away_team.score,
        statistics: {} as never,
      }
    }
    return null
  })

  const homePlayers = computed(() => {
    if (!boxscore.value) return []
    const homeAbbr = boxscore.value.teams.home.abbreviation
    return boxscore.value.players.filter(p => p.team === homeAbbr)
  })

  const awayPlayers = computed(() => {
    if (!boxscore.value) return []
    const awayAbbr = boxscore.value.teams.away.abbreviation
    return boxscore.value.players.filter(p => p.team === awayAbbr)
  })

  // Actions
  function setScoreboard(data: ScoreboardEventData) {
    scoreboard.value = data
  }

  function setBoxscore(data: BoxscoreEventData) {
    boxscore.value = data
  }

  function setPlayByPlay(data: PlayByPlayEventData) {
    // 合并新动作，按 actionNumber 去重并排序
    const existingIds = new Set(playByPlayActions.value.map(a => a.actionNumber))
    const newActions = data.actions.filter(a => !existingIds.has(a.actionNumber))
    playByPlayActions.value = [...playByPlayActions.value, ...newActions].sort(
      (a, b) => b.actionNumber - a.actionNumber
    )
  }

  function setGameEnd(data: GameEndEventData) {
    gameEndData.value = data
  }

  function appendAnalysisChunk(data: AnalysisChunkEventData) {
    analysisChunks.value = [...analysisChunks.value, data]
  }

  function clearAnalysis() {
    analysisChunks.value = []
  }

  function reset() {
    scoreboard.value = null
    boxscore.value = null
    playByPlayActions.value = []
    gameEndData.value = null
    analysisChunks.value = []
  }

  return {
    // 状态
    scoreboard,
    boxscore,
    playByPlayActions,
    gameEndData,
    analysisChunks,
    // 计算属性
    gameId,
    gameStatus,
    isGameEnded,
    homeTeam,
    awayTeam,
    homePlayers,
    awayPlayers,
    // Actions
    setScoreboard,
    setBoxscore,
    setPlayByPlay,
    setGameEnd,
    appendAnalysisChunk,
    clearAnalysis,
    reset,
  }
})
