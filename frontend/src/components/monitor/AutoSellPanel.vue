<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useAuthStore, useGameStore, useToastStore } from '@/stores'

const authStore = useAuthStore()
const gameStore = useGameStore()
const toastStore = useToastStore()
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
const ORDER_TYPE = 'GTC'
const POLYMARKET_PRIVATE_KEY = 'POLYMARKET_PRIVATE_KEY'
const POLYMARKET_PROXY_ADDRESS = 'POLYMARKET_PROXY_ADDRESS'

// localStorage 持久化键
const STORAGE_PREFIX = 'AUTO_SELL_'
const getStorageKey = (key: string) => `${STORAGE_PREFIX}${key}`

function getStoredValue<T>(key: string, defaultValue: T): T {
  if (typeof window === 'undefined') return defaultValue
  const stored = localStorage.getItem(getStorageKey(key))
  if (stored === null) return defaultValue
  try {
    return JSON.parse(stored) as T
  } catch {
    return defaultValue
  }
}

function setStoredValue<T>(key: string, value: T) {
  if (typeof window === 'undefined') return
  localStorage.setItem(getStorageKey(key), JSON.stringify(value))
}

// 配置参数（每个 outcome 独立配置）
const autoSellEnabledMap = reactive<Record<string, boolean>>(getStoredValue('ENABLED_MAP', {})) // 每个 outcome 的开关
const minProfitRateMap = reactive<Record<string, number>>(getStoredValue('MIN_PROFIT_RATE_MAP', {})) // 每个 outcome 的最小利润率 %
const sellRatioMap = reactive<Record<string, number>>(getStoredValue('SELL_RATIO_MAP', {})) // 每个 outcome 的卖出比例 %
const cooldownTimeMap = reactive<Record<string, number>>(getStoredValue('COOLDOWN_TIME_MAP', {})) // 每个 outcome 的冷却时间（秒）
const refreshInterval = ref(getStoredValue('REFRESH_INTERVAL', 3)) // 持仓刷新间隔（秒）- 统一配置

// 默认参数值
const DEFAULT_MIN_PROFIT_RATE = 5
const DEFAULT_SELL_RATIO = 100
const DEFAULT_COOLDOWN_TIME = 30

// 获取 outcome 的参数（带默认值）
function getMinProfitRate(outcome: string): number {
  return minProfitRateMap[outcome] ?? DEFAULT_MIN_PROFIT_RATE
}

function getSellRatio(outcome: string): number {
  return sellRatioMap[outcome] ?? DEFAULT_SELL_RATIO
}

function getCooldownTime(outcome: string): number {
  return cooldownTimeMap[outcome] ?? DEFAULT_COOLDOWN_TIME
}

let refreshTimer: ReturnType<typeof setInterval> | null = null
let isSellLocked = false // 防止 watch 回调重入的单调锁

// 计算是否有任何一个 outcome 开启了自动卖出
const hasAnyAutoSellEnabled = computed(() => Object.values(autoSellEnabledMap).some(v => v))

// 运行状态（使用 store 中的持仓数据）
const positionSides = computed(() => gameStore.positionSides)
const positionsLoading = computed(() => gameStore.positionsLoading)
const isOrdering = ref(false)
const lastSellTime = reactive<Record<string, Date>>({}) // 每个 outcome 的最后卖出时间
const orderStats = reactive<Record<string, { count: number; amount: number }>>({})

// 计算属性
const polymarketInfo = computed(() => gameStore.polymarketInfo)
const polymarketBook = computed(() => gameStore.polymarketBook)

const statusText = computed(() => {
  if (!hasAnyAutoSellEnabled.value) return '已关闭'
  if (isOrdering.value) return '卖出中...'
  if (positionsLoading.value) return '刷新中...'
  return '监控中'
})

const statusClass = computed(() => {
  if (!hasAnyAutoSellEnabled.value) return 'text-base-content/50'
  if (isOrdering.value) return 'text-warning'
  return 'text-success'
})

// 格式化函数
function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return value.toFixed(3)
}

function formatSize(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return value.toFixed(2)
}

function formatTimeAgo(date: Date | null): string {
  if (!date) return '--'
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 60) return `${seconds}秒前`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}分钟前`
}

// 获取配置
function getPrivateKey(): string {
  return localStorage.getItem(POLYMARKET_PRIVATE_KEY)?.trim() ?? ''
}

function getProxyAddress(): string {
  return localStorage.getItem(POLYMARKET_PROXY_ADDRESS)?.trim() ?? ''
}

function getPolymarketUserAddress() {
  const proxyAddress = getProxyAddress()
  return { userAddress: proxyAddress, proxyAddress }
}

function getMarketOutcomes(): string[] {
  const info = polymarketInfo.value
  if (!info) return []
  const outcomes = info.market_info?.outcomes?.length
    ? info.market_info.outcomes
    : info.tokens.map(token => token.outcome)
  return Array.from(new Set(outcomes.filter(Boolean)))
}

function getMarketConditionId(): string | null {
  const info = polymarketInfo.value
  if (!info) return null
  return info.condition_id ?? info.market_info?.condition_id ?? null
}

// 获取 token_id by outcome
function getTokenIdByOutcome(outcome: string): string | null {
  const info = polymarketInfo.value
  if (!info) return null
  const token = info.tokens.find(t => t.outcome === outcome)
  return token?.token_id ?? null
}

// 获取当前 bestBid
function getBestBid(tokenId: string): number | null {
  const snapshot = gameStore.polymarketBook[tokenId]
  return snapshot?.bestBid ?? null
}

// 根据 outcome 获取实时 bestBid
function getBestBidByOutcome(outcome: string): number | null {
  const tokenId = getTokenIdByOutcome(outcome)
  if (!tokenId) return null
  return getBestBid(tokenId)
}

// 获取持仓（更新到 store）
async function fetchMarketPositions() {
  if (!authStore.isAuthenticated) return
  const conditionId = getMarketConditionId()
  if (!conditionId) return

  const outcomes = getMarketOutcomes()
  const { userAddress, proxyAddress } = getPolymarketUserAddress()
  if (!userAddress && !proxyAddress) return

  gameStore.setPositionsLoading(true)
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/polymarket/positions/market`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authStore.token}`,
      },
      body: JSON.stringify({
        condition_id: conditionId,
        user_address: userAddress || proxyAddress,
        outcomes,
      }),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => null)
      throw new Error(data?.detail || '查询持仓失败')
    }

    const data = await response.json().catch(() => null)
    const sides = Array.isArray(data?.sides) ? data.sides : []
    gameStore.setPositionSides(sides)
  } catch (error) {
    // 静默失败，不显示 toast（因为是定时刷新）
    console.error('获取持仓失败:', error)
  } finally {
    gameStore.setPositionsLoading(false)
  }
}

// 计算利润率
function calculateProfitRate(avgPrice: number | null | undefined, curPrice: number | null | undefined): number | null {
  if (!avgPrice || !curPrice || avgPrice <= 0) return null
  return (curPrice - avgPrice) / avgPrice
}

// 检查是否可以卖出（使用订单簿实时 bestBid 计算利润率）
function canSellOutcome(side: { outcome: string; size: number; avg_price?: number | null }, checkEnabled = true): {
  canSell: boolean
  reason?: string
  profitRate?: number
  realtimePrice?: number
} {
  // 检查该 outcome 是否启用自动卖出（仅在自动卖出流程中检查）
  if (checkEnabled && !autoSellEnabledMap[side.outcome]) {
    return { canSell: false, reason: '未启用' }
  }

  // 检查持仓数量
  if (!side.size || side.size <= 0) {
    return { canSell: false, reason: '无持仓' }
  }

  // 获取实时 bestBid 作为现价
  const realtimePrice = getBestBidByOutcome(side.outcome)
  if (realtimePrice == null || realtimePrice <= 0) {
    return { canSell: false, reason: '无实时价格' }
  }

  // 检查均价
  if (side.avg_price == null || side.avg_price <= 0) {
    return { canSell: false, reason: '无均价数据' }
  }

  // 计算利润率（使用实时 bestBid）
  const profitRate = calculateProfitRate(side.avg_price, realtimePrice)
  if (profitRate === null) {
    return { canSell: false, reason: '无法计算利润率' }
  }

  // 检查是否达到最小利润率（使用该 outcome 的配置）
  const minProfitRateValue = getMinProfitRate(side.outcome)
  const minRate = minProfitRateValue / 100
  if (profitRate < minRate) {
    return { canSell: false, reason: `利润率不足 (${(profitRate * 100).toFixed(1)}% < ${minProfitRateValue}%)`, profitRate, realtimePrice }
  }

  // 检查冷却时间（使用该 outcome 的配置）
  const cooldownTimeValue = getCooldownTime(side.outcome)
  const lastSell = lastSellTime[side.outcome]
  if (lastSell) {
    const elapsed = (Date.now() - lastSell.getTime()) / 1000
    if (elapsed < cooldownTimeValue) {
      return { canSell: false, reason: `冷却中 (${Math.ceil(cooldownTimeValue - elapsed)}秒)`, profitRate, realtimePrice }
    }
  }

  return { canSell: true, profitRate, realtimePrice }
}

// 执行卖出
async function executeSell(side: { outcome: string; size: number; avg_price?: number | null; cur_price?: number | null }) {
  const tokenId = getTokenIdByOutcome(side.outcome)
  if (!tokenId) {
    console.error('找不到 token_id:', side.outcome)
    return false
  }

  // 获取当前 bestBid 作为卖出价格
  const bestBid = getBestBid(tokenId)
  if (!bestBid || bestBid <= 0 || bestBid >= 1) {
    console.error('无有效买价:', side.outcome)
    return false
  }

  // 计算卖出数量（使用该 outcome 的配置）
  const sellRatioValue = getSellRatio(side.outcome)
  const sellSize = Math.floor(side.size * (sellRatioValue / 100) * 100) / 100
  if (sellSize <= 0) {
    console.error('卖出数量为0:', side.outcome)
    return false
  }

  const privateKey = getPrivateKey()
  const proxyAddress = getProxyAddress()

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/polymarket/orders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authStore.token}`,
      },
      body: JSON.stringify({
        token_id: tokenId,
        side: 'SELL',
        price: bestBid,
        size: sellSize,
        order_type: ORDER_TYPE,
        private_key: privateKey,
        proxy_address: proxyAddress,
      }),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => null)
      throw new Error(data?.detail || '卖出失败')
    }

    await response.json().catch(() => null)

    // 更新统计（lastSellTime 已由调用方前置记录）
    if (!orderStats[side.outcome]) {
      orderStats[side.outcome] = { count: 0, amount: 0 }
    }
    orderStats[side.outcome].count++
    orderStats[side.outcome].amount += sellSize * bestBid

    return true
  } catch (error) {
    toastStore.showError(error instanceof Error ? error.message : '卖出失败')
    return false
  }
}

// 基于收益率变化触发自动卖出（由 watch polymarketBook 触发）
async function checkAndAutoSell() {
  // isSellLocked 在任何 await 之前置位，杜绝 watch 回调重入
  if (isSellLocked || !hasAnyAutoSellEnabled.value) return
  if (!authStore.isAuthenticated) return
  if (!getPrivateKey() || !getProxyAddress()) return

  isSellLocked = true
  isOrdering.value = true
  let successCount = 0

  try {
    // 检查每个持仓的收益率
    const sellableSides: typeof positionSides.value = []
    for (const side of positionSides.value) {
      const { canSell, profitRate } = canSellOutcome(side)
      if (canSell && profitRate !== undefined) {
        sellableSides.push(side)
      }
    }

    for (const side of sellableSides) {
      // 前置记录 lastSellTime，防止同一轮次内并发重复卖出同一 outcome
      const prevSellTime = lastSellTime[side.outcome] ?? null
      lastSellTime[side.outcome] = new Date()

      const success = await executeSell(side)
      if (success) {
        successCount++
        const profitRate = calculateProfitRate(side.avg_price, getBestBidByOutcome(side.outcome))
        toastStore.showSuccess(`自动卖出 ${side.outcome} 成功 (+${((profitRate ?? 0) * 100).toFixed(1)}%)`)
      } else {
        // 下单失败则回滚 lastSellTime，不影响后续重试
        if (prevSellTime) {
          lastSellTime[side.outcome] = prevSellTime
        } else {
          delete lastSellTime[side.outcome]
        }
      }
    }

    // 卖出后刷新持仓
    if (successCount > 0) {
      await new Promise(resolve => setTimeout(resolve, 2000))
      await fetchMarketPositions()
    }
  } finally {
    isSellLocked = false
    isOrdering.value = false
  }
}

// 启动/停止持仓刷新定时器
function startRefreshTimer() {
  stopRefreshTimer()
  if (hasAnyAutoSellEnabled.value && refreshInterval.value > 0) {
    // 立即刷新一次持仓
    fetchMarketPositions()
    // 定时刷新持仓数据
    refreshTimer = setInterval(() => {
      fetchMarketPositions()
    }, refreshInterval.value * 1000)
  }
}

function stopRefreshTimer() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// 监控订单簿变化，实时计算收益率，达到阈值立即卖出
watch(
  polymarketBook,
  () => {
    if (!hasAnyAutoSellEnabled.value) return
    checkAndAutoSell()
  },
  { deep: true }
)

// 监听开关变化，启动/停止持仓刷新
watch(hasAnyAutoSellEnabled, (enabled) => {
  if (enabled) {
    startRefreshTimer()
  } else {
    stopRefreshTimer()
  }
})

// 持久化 autoSellEnabledMap
watch(autoSellEnabledMap, (value) => setStoredValue('ENABLED_MAP', value), { deep: true })

// 监听刷新间隔变化，重启定时器
watch(refreshInterval, () => {
  if (hasAnyAutoSellEnabled.value) {
    startRefreshTimer()
  }
})

// 配置变化时持久化
watch(minProfitRateMap, (value) => setStoredValue('MIN_PROFIT_RATE_MAP', value), { deep: true })
watch(sellRatioMap, (value) => setStoredValue('SELL_RATIO_MAP', value), { deep: true })
watch(cooldownTimeMap, (value) => setStoredValue('COOLDOWN_TIME_MAP', value), { deep: true })
watch(refreshInterval, (value) => setStoredValue('REFRESH_INTERVAL', value))

// 组件销毁时清理定时器
onBeforeUnmount(() => {
  stopRefreshTimer()
})

// 重置统计
function resetStats() {
  Object.keys(orderStats).forEach(key => {
    delete orderStats[key]
  })
  Object.keys(lastSellTime).forEach(key => {
    delete lastSellTime[key]
  })
}

const hasStats = computed(() => Object.keys(orderStats).length > 0)

const statsDisplay = computed(() => {
  const entries = Object.entries(orderStats)
  if (entries.length === 0) return '--'
  return entries
    .map(([outcome, stat]) => `${outcome} x${stat.count} ($${stat.amount.toFixed(2)})`)
    .join(', ')
})

// 持仓状态显示
const positionStatusList = computed(() => {
  return positionSides.value.map(side => {
    const enabled = !!autoSellEnabledMap[side.outcome]
    // 不检查启用状态，以便显示其他原因
    const { canSell, reason, profitRate, realtimePrice } = canSellOutcome(side, false)
    return {
      ...side,
      realtimePrice, // 实时 bestBid
      profitRate,
      enabled,
      // 只有启用且满足条件才显示可卖
      canSell: enabled && canSell,
      reason: enabled ? reason : '未启用',
      lastSell: lastSellTime[side.outcome] ?? null,
      // 各自的参数配置
      minProfitRate: getMinProfitRate(side.outcome),
      sellRatio: getSellRatio(side.outcome),
      cooldownTime: getCooldownTime(side.outcome),
    }
  })
})

// 切换单个 outcome 的自动卖出开关
function toggleAutoSell(outcome: string) {
  autoSellEnabledMap[outcome] = !autoSellEnabledMap[outcome]
}
</script>

<template>
  <div class="card glass-card ring-1 ring-base-content/30 ring-offset-2 ring-offset-base-100">
    <div class="card-body">
      <!-- 标题 -->
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-baseline gap-2">
          <h3 class="card-title text-base">自动卖出</h3>
          <span class="text-[10px] text-base-content/40">现价/均价 &ge; 阈值时卖出</span>
        </div>
        <div class="flex items-center gap-3">
          <!-- 刷新间隔 -->
          <div class="flex items-center gap-1" title="持仓刷新间隔">
            <span class="text-[10px] text-base-content/50">刷新</span>
            <input
              v-model.number="refreshInterval"
              type="number"
              min="1"
              max="60"
              step="1"
              class="input input-bordered input-xs w-10 text-center text-[10px] px-1"
              :disabled="hasAnyAutoSellEnabled"
            /><span class="text-[10px] text-base-content/40">秒</span>
          </div>
          <span :class="statusClass" class="text-xs">{{ statusText }}</span>
        </div>
      </div>

      <!-- 持仓状态区域 -->
      <div class="mt-3 grid grid-cols-2 gap-4">
          <div
            v-for="pos in positionStatusList"
            :key="pos.outcome"
            class="rounded-lg bg-base-100 px-3 py-2 ring-1 ring-base-content/15"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <input
                  type="checkbox"
                  :checked="pos.enabled"
                  class="toggle toggle-error toggle-xs"
                  :disabled="!polymarketInfo || !authStore.isAuthenticated || !getPrivateKey() || !getProxyAddress()"
                  @change="toggleAutoSell(pos.outcome)"
                />
                <span class="text-sm font-semibold text-base-content">{{ pos.outcome }}</span>
              </div>
              <span
                class="text-xs"
                :class="pos.canSell ? 'text-success font-semibold' : 'text-base-content/50'"
              >
                {{ pos.canSell ? '可卖' : pos.reason }}
              </span>
            </div>
            <div class="mt-1 flex flex-wrap gap-x-3 text-xs text-base-content/60">
              <span>持仓: {{ formatSize(pos.size) }}</span>
              <span>均价: {{ formatPrice(pos.avg_price) }}</span>
              <span title="实时订单簿 bestBid">现价: {{ formatPrice(pos.realtimePrice) }}</span>
              <span :class="(pos.profitRate ?? 0) >= 0 ? 'text-success' : 'text-error'">
                收益: {{ pos.profitRate != null ? `${(pos.profitRate * 100).toFixed(1)}%` : '--' }}
              </span>
            </div>
            <div v-if="pos.lastSell" class="text-xs text-base-content/40">
              上次卖出: {{ formatTimeAgo(pos.lastSell) }}
            </div>
            <!-- 独立参数配置 -->
            <div class="mt-2 pt-2 border-t border-base-200/50 flex flex-wrap gap-x-4 gap-y-1">
              <div class="flex items-center gap-1" title="最小利润率：(现价-均价)/均价 达到此值才触发卖出">
                <span class="text-xs text-base-content/50">利润</span>
                <input
                  :value="minProfitRateMap[pos.outcome] ?? DEFAULT_MIN_PROFIT_RATE"
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  class="input input-bordered input-xs w-12 text-center"
                  :disabled="pos.enabled"
                  @input="minProfitRateMap[pos.outcome] = Number(($event.target as HTMLInputElement).value)"
                /><span class="text-xs text-base-content/40">%</span>
              </div>
              <div class="flex items-center gap-1" title="卖出比例：触发时卖出持仓的百分比">
                <span class="text-xs text-base-content/50">比例</span>
                <input
                  :value="sellRatioMap[pos.outcome] ?? DEFAULT_SELL_RATIO"
                  type="number"
                  min="1"
                  max="100"
                  step="1"
                  class="input input-bordered input-xs w-12 text-center"
                  :disabled="pos.enabled"
                  @input="sellRatioMap[pos.outcome] = Number(($event.target as HTMLInputElement).value)"
                /><span class="text-xs text-base-content/40">%</span>
              </div>
              <div class="flex items-center gap-1" title="冷却时间：卖出后等待时间">
                <span class="text-xs text-base-content/50">冷却</span>
                <input
                  :value="cooldownTimeMap[pos.outcome] ?? DEFAULT_COOLDOWN_TIME"
                  type="number"
                  min="0"
                  max="300"
                  step="5"
                  class="input input-bordered input-xs w-12 text-center"
                  :disabled="pos.enabled"
                  @input="cooldownTimeMap[pos.outcome] = Number(($event.target as HTMLInputElement).value)"
                /><span class="text-xs text-base-content/40">秒</span>
              </div>
            </div>
          </div>

        <div v-if="positionStatusList.length === 0" class="col-span-2 text-center text-xs text-base-content/50 py-2">
          暂无持仓数据
        </div>
      </div>

      <!-- 统计区域 -->
      <div class="mt-3 rounded-lg border border-base-200/70 px-3 py-2 ring-1 ring-base-content/20">
        <div class="grid grid-cols-2 gap-2 text-xs">
          <div>
            <div class="text-base-content/50">累计卖出</div>
            <div class="font-medium text-base-content text-[11px]">{{ statsDisplay }}</div>
          </div>
          <div class="text-right">
            <button
              v-if="hasStats"
              class="btn btn-ghost btn-xs text-base-content/50"
              @click="resetStats"
            >
              重置
            </button>
          </div>
        </div>
      </div>

      <!-- 未连接提示 -->
      <div v-if="!polymarketInfo" class="mt-3 text-xs text-amber-600/80">
        请先连接到 Polymarket 比赛
      </div>

      <!-- 未登录提示 -->
      <div v-else-if="!authStore.isAuthenticated" class="mt-3 text-xs text-amber-600/80">
        请先登录
      </div>

      <!-- 未配置提示 -->
      <div v-else-if="!getPrivateKey() || !getProxyAddress()" class="mt-3 text-xs text-amber-600/80">
        请先配置 Polymarket 私钥和代理地址
      </div>
    </div>
  </div>
</template>
