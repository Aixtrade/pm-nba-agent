import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  ScoreboardEventData,
  BoxscoreEventData,
  GameEndEventData,
  AnalysisChunkEventData,
  PolymarketInfoEventData,
  PolymarketBookEventData,
  StrategySignalEventData,
  AutoBuyStateEventData,
} from '@/types/sse'

interface BookLevel {
  price: number
  size: number
}

interface BookPriceSnapshot {
  assetId: string
  bestBid: number | null
  bestAsk: number | null
  bidSize: number | null
  askSize: number | null
  updatedAt: string | null
}

type BookPayload = {
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
  bids?: unknown
  asks?: unknown
  timestamp?: string
} & Record<string, unknown>

function extractBookPayload(data: PolymarketBookEventData): BookPayload | null {
  if (!data || typeof data !== 'object') return null

  const hasDirectKeys =
    'asset_id' in data ||
    'assetId' in data ||
    'token_id' in data ||
    'tokenId' in data ||
    'bids' in data ||
    'asks' in data

  if (hasDirectKeys) return data as BookPayload

  const nested = data.data || data.payload || data.message
  if (nested && typeof nested === 'object') {
    return nested as BookPayload
  }

  return null
}

function parseBookLevels(raw: unknown): BookLevel[] {
  if (!Array.isArray(raw)) return []

  const levels: BookLevel[] = []
  for (const item of raw) {
    if (Array.isArray(item) && item.length >= 2) {
      const price = Number(item[0])
      const size = Number(item[1])
      if (!Number.isNaN(price) && !Number.isNaN(size)) {
        levels.push({ price, size })
      }
      continue
    }

    if (item && typeof item === 'object') {
      const maybePrice = (item as { price?: number | string }).price
      const maybeSize = (item as { size?: number | string }).size
      const price = Number(maybePrice)
      const size = Number(maybeSize)
      if (!Number.isNaN(price) && !Number.isNaN(size)) {
        levels.push({ price, size })
      }
    }
  }

  return levels
}

function getBestBid(levels: BookLevel[]): BookLevel | null {
  if (levels.length === 0) return null
  return levels.reduce((best, level) => (level.price > best.price ? level : best))
}

function getBestAsk(levels: BookLevel[]): BookLevel | null {
  if (levels.length === 0) return null
  return levels.reduce((best, level) => (level.price < best.price ? level : best))
}

export const useGameStore = defineStore('game', () => {
  // 状态
  const scoreboard = ref<ScoreboardEventData | null>(null)
  const boxscore = ref<BoxscoreEventData | null>(null)
  const gameEndData = ref<GameEndEventData | null>(null)
  const analysisChunks = ref<AnalysisChunkEventData[]>([])
  const polymarketInfo = ref<PolymarketInfoEventData | null>(null)
  const polymarketBook = ref<Record<string, BookPriceSnapshot>>({})
  const polymarketBookUpdatedAt = ref<string | null>(null)
  // 按策略分组的信号存储
  const strategySignalsByStrategy = ref<Record<string, StrategySignalEventData[]>>({})
  const latestSignalByStrategy = ref<Record<string, StrategySignalEventData | null>>({})
  const MAX_STRATEGY_SIGNALS = 20
  const autoBuyState = ref<AutoBuyStateEventData | null>(null)

  // 向后兼容的 computed
  const latestStrategySignal = computed<StrategySignalEventData | null>(() => {
    let newest: StrategySignalEventData | null = null
    for (const sig of Object.values(latestSignalByStrategy.value)) {
      if (!sig) continue
      if (!newest || sig.timestamp > newest.timestamp) newest = sig
    }
    return newest
  })
  const strategySignals = computed<StrategySignalEventData[]>(() => {
    const all: StrategySignalEventData[] = []
    for (const list of Object.values(strategySignalsByStrategy.value)) {
      all.push(...list)
    }
    return all.sort((a, b) => (b.timestamp > a.timestamp ? 1 : -1))
  })

  // 按策略查询
  function getSignalsForStrategy(id: string): StrategySignalEventData[] {
    return strategySignalsByStrategy.value[id] ?? []
  }
  function getLatestSignalForStrategy(id: string): StrategySignalEventData | null {
    return latestSignalByStrategy.value[id] ?? null
  }
  const activeStrategyIds = computed(() =>
    Object.keys(latestSignalByStrategy.value).filter(k => latestSignalByStrategy.value[k] !== null)
  )

  // 持仓状态
  const positionSides = ref<
    Array<{
      outcome: string
      size: number
      initial_value?: number | null
      avg_price?: number | null
      cur_price?: number | null
    }>
  >([])
  const positionsLoading = ref(false)
  const positionsUpdatedAt = ref<string | null>(null)

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


  function setGameEnd(data: GameEndEventData) {
    gameEndData.value = data
  }

  function appendAnalysisChunk(data: AnalysisChunkEventData) {
    analysisChunks.value = [...analysisChunks.value, data]
  }

  function setPolymarketInfo(data: PolymarketInfoEventData) {
    polymarketInfo.value = data
  }

  function updatePolymarketBook(data: PolymarketBookEventData) {
    const payload = extractBookPayload(data)
    if (!payload) return

    if (Array.isArray(payload.price_changes)) {
      const updatedAt = payload.timestamp
        ? new Date(Number(payload.timestamp)).toISOString()
        : new Date().toISOString()

      const updates: Record<string, BookPriceSnapshot> = {}
      for (const change of payload.price_changes) {
        const assetId = change.asset_id
        if (!assetId) continue

        const bestBid = change.best_bid !== undefined ? Number(change.best_bid) : null
        const bestAsk = change.best_ask !== undefined ? Number(change.best_ask) : null

        updates[assetId] = {
          assetId,
          bestBid: Number.isNaN(bestBid) ? null : bestBid,
          bestAsk: Number.isNaN(bestAsk) ? null : bestAsk,
          bidSize: null,
          askSize: null,
          updatedAt,
        }
      }

      if (Object.keys(updates).length > 0) {
        polymarketBook.value = {
          ...polymarketBook.value,
          ...updates,
        }
        polymarketBookUpdatedAt.value = updatedAt
      }

      return
    }

    const assetId =
      (payload.asset_id as string | undefined) ||
      (payload.assetId as string | undefined) ||
      (payload.token_id as string | undefined) ||
      (payload.tokenId as string | undefined)

    if (!assetId) return

    const bids = parseBookLevels(payload.bids)
    const asks = parseBookLevels(payload.asks)

    const bestBid = getBestBid(bids)
    const bestAsk = getBestAsk(asks)

    const updatedAt = payload.timestamp
      ? new Date(Number(payload.timestamp)).toISOString()
      : new Date().toISOString()

    const previous = polymarketBook.value[assetId]

    polymarketBook.value = {
      ...polymarketBook.value,
      [assetId]: {
        assetId,
        bestBid: bestBid?.price ?? previous?.bestBid ?? null,
        bestAsk: bestAsk?.price ?? previous?.bestAsk ?? null,
        bidSize: bestBid?.size ?? previous?.bidSize ?? null,
        askSize: bestAsk?.size ?? previous?.askSize ?? null,
        updatedAt,
      },
    }

    polymarketBookUpdatedAt.value = updatedAt
  }

  function clearAnalysis() {
    analysisChunks.value = []
  }

  function addStrategySignal(data: StrategySignalEventData) {
    const sid = data.strategy?.id ?? '_unknown_'

    // 始终更新该策略的最新信号（包括 HOLD）
    latestSignalByStrategy.value = { ...latestSignalByStrategy.value, [sid]: data }

    // 只有 BUY/SELL 信号保存到该策略的历史列表
    const signalType = data.signal?.type
    if (signalType === 'BUY' || signalType === 'SELL') {
      const prev = strategySignalsByStrategy.value[sid] ?? []
      strategySignalsByStrategy.value = {
        ...strategySignalsByStrategy.value,
        [sid]: [data, ...prev.slice(0, MAX_STRATEGY_SIGNALS - 1)],
      }
    }
  }

  function clearStrategySignals() {
    strategySignalsByStrategy.value = {}
    latestSignalByStrategy.value = {}
  }

  function setPositionSides(
    sides: Array<{
      outcome: string
      size: number
      initial_value?: number | null
      avg_price?: number | null
      cur_price?: number | null
    }>
  ) {
    positionSides.value = sides
    positionsUpdatedAt.value = new Date().toISOString()
  }

  function setPositionsLoading(loading: boolean) {
    positionsLoading.value = loading
  }

  function setAutoBuyState(data: AutoBuyStateEventData) {
    autoBuyState.value = data
  }

  function reset() {
    scoreboard.value = null
    boxscore.value = null
    gameEndData.value = null
    analysisChunks.value = []
    polymarketInfo.value = null
    polymarketBook.value = {}
    polymarketBookUpdatedAt.value = null
    strategySignalsByStrategy.value = {}
    latestSignalByStrategy.value = {}
    positionSides.value = []
    positionsLoading.value = false
    positionsUpdatedAt.value = null
    autoBuyState.value = null
  }

  return {
    // 状态
    scoreboard,
    boxscore,
    gameEndData,
    analysisChunks,
    polymarketInfo,
    polymarketBook,
    polymarketBookUpdatedAt,
    strategySignals,
    latestStrategySignal,
    strategySignalsByStrategy,
    latestSignalByStrategy,
    activeStrategyIds,
    getSignalsForStrategy,
    getLatestSignalForStrategy,
    positionSides,
    positionsLoading,
    positionsUpdatedAt,
    autoBuyState,
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
    setGameEnd,
    appendAnalysisChunk,
    setPolymarketInfo,
    updatePolymarketBook,
    addStrategySignal,
    clearStrategySignals,
    clearAnalysis,
    setPositionSides,
    setPositionsLoading,
    setAutoBuyState,
    reset,
  }
})
