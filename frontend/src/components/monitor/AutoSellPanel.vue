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

// 配置参数
const autoSellEnabledMap = reactive<Record<string, boolean>>(getStoredValue('ENABLED_MAP', {})) // 每个 outcome 的开关
const minProfitRate = ref(getStoredValue('MIN_PROFIT_RATE', 5)) // 最小利润率 %
const sellRatio = ref(getStoredValue('SELL_RATIO', 100)) // 卖出比例 %
const refreshInterval = ref(getStoredValue('REFRESH_INTERVAL', 3)) // 刷新间隔（秒）
const cooldownTime = ref(getStoredValue('COOLDOWN_TIME', 30)) // 冷却时间（秒）

// 计算是否有任何一个 outcome 开启了自动卖出
const hasAnyAutoSellEnabled = computed(() => Object.values(autoSellEnabledMap).some(v => v))

// 运行状态（使用 store 中的持仓数据）
const positionSides = computed(() => gameStore.positionSides)
const positionsLoading = computed(() => gameStore.positionsLoading)
const isOrdering = ref(false)
const lastSellTime = reactive<Record<string, Date>>({}) // 每个 outcome 的最后卖出时间
const orderStats = reactive<Record<string, { count: number; amount: number }>>({})

let refreshTimer: ReturnType<typeof setInterval> | null = null

// 计算属性
const polymarketInfo = computed(() => gameStore.polymarketInfo)

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

// 检查是否可以卖出
function canSellOutcome(side: { outcome: string; size: number; avg_price?: number | null; cur_price?: number | null }, checkEnabled = true): {
  canSell: boolean
  reason?: string
  profitRate?: number
} {
  // 检查该 outcome 是否启用自动卖出（仅在自动卖出流程中检查）
  if (checkEnabled && !autoSellEnabledMap[side.outcome]) {
    return { canSell: false, reason: '未启用' }
  }

  // 检查持仓数量
  if (!side.size || side.size <= 0) {
    return { canSell: false, reason: '无持仓' }
  }

  // 检查价格数据
  if (side.avg_price == null || side.cur_price == null) {
    return { canSell: false, reason: '无价格数据' }
  }

  // 计算利润率
  const profitRate = calculateProfitRate(side.avg_price, side.cur_price)
  if (profitRate === null) {
    return { canSell: false, reason: '无法计算利润率' }
  }

  // 检查是否达到最小利润率
  const minRate = minProfitRate.value / 100
  if (profitRate < minRate) {
    return { canSell: false, reason: `利润率不足 (${(profitRate * 100).toFixed(1)}% < ${minProfitRate.value}%)`, profitRate }
  }

  // 检查冷却时间
  const lastSell = lastSellTime[side.outcome]
  if (lastSell) {
    const elapsed = (Date.now() - lastSell.getTime()) / 1000
    if (elapsed < cooldownTime.value) {
      return { canSell: false, reason: `冷却中 (${Math.ceil(cooldownTime.value - elapsed)}秒)`, profitRate }
    }
  }

  return { canSell: true, profitRate }
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

  // 计算卖出数量
  const sellSize = Math.floor(side.size * (sellRatio.value / 100) * 100) / 100
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

    // 更新状态
    lastSellTime[side.outcome] = new Date()
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

// 检查并执行自动卖出
async function checkAndAutoSell() {
  if (!hasAnyAutoSellEnabled.value || isOrdering.value) return
  if (!authStore.isAuthenticated) return
  if (!getPrivateKey() || !getProxyAddress()) return

  // 先刷新持仓
  await fetchMarketPositions()

  // 检查每个持仓
  const sellableSides: typeof positionSides.value = []
  for (const side of positionSides.value) {
    const { canSell, profitRate } = canSellOutcome(side)
    if (canSell && profitRate !== undefined) {
      sellableSides.push(side)
    }
  }

  if (sellableSides.length === 0) return

  isOrdering.value = true
  let successCount = 0

  try {
    for (const side of sellableSides) {
      const success = await executeSell(side)
      if (success) {
        successCount++
        const profitRate = calculateProfitRate(side.avg_price, side.cur_price)
        toastStore.showSuccess(`自动卖出 ${side.outcome} 成功 (+${((profitRate ?? 0) * 100).toFixed(1)}%)`)
      }
    }

    // 卖出后刷新持仓
    if (successCount > 0) {
      await new Promise(resolve => setTimeout(resolve, 2000))
      await fetchMarketPositions()
    }
  } finally {
    isOrdering.value = false
  }
}

// 启动/停止定时器
function startRefreshTimer() {
  stopRefreshTimer()
  if (hasAnyAutoSellEnabled.value && refreshInterval.value > 0) {
    // 立即执行一次
    checkAndAutoSell()
    // 设置定时器
    refreshTimer = setInterval(() => {
      checkAndAutoSell()
    }, refreshInterval.value * 1000)
  }
}

function stopRefreshTimer() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// 监听开关变化
watch(hasAnyAutoSellEnabled, (enabled) => {
  if (enabled) {
    startRefreshTimer()
  } else {
    stopRefreshTimer()
  }
})

// 持久化 autoSellEnabledMap
watch(autoSellEnabledMap, (value) => setStoredValue('ENABLED_MAP', value), { deep: true })

// 监听刷新间隔变化
watch(refreshInterval, () => {
  if (hasAnyAutoSellEnabled.value) {
    startRefreshTimer()
  }
})

// 配置变化时持久化
watch(minProfitRate, (value) => setStoredValue('MIN_PROFIT_RATE', value))
watch(sellRatio, (value) => setStoredValue('SELL_RATIO', value))
watch(refreshInterval, (value) => setStoredValue('REFRESH_INTERVAL', value))
watch(cooldownTime, (value) => setStoredValue('COOLDOWN_TIME', value))

// 组件销毁时清理
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
    const profitRate = calculateProfitRate(side.avg_price, side.cur_price)
    const enabled = !!autoSellEnabledMap[side.outcome]
    // 不检查启用状态，以便显示其他原因
    const { canSell, reason } = canSellOutcome(side, false)
    return {
      ...side,
      profitRate,
      enabled,
      // 只有启用且满足条件才显示可卖
      canSell: enabled && canSell,
      reason: enabled ? reason : '未启用',
      lastSell: lastSellTime[side.outcome] ?? null,
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
        <span :class="statusClass" class="text-xs">{{ statusText }}</span>
      </div>

      <!-- 配置区域 - 紧凑两行布局 -->
      <div class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2">
        <!-- 利润率 -->
        <div class="flex items-center gap-1.5" title="最小利润率：(现价-均价)/均价 达到此值才触发卖出">
          <span class="text-xs text-base-content/60 shrink-0 cursor-help border-b border-dashed border-base-content/30">利润</span>
          <input
            v-model.number="minProfitRate"
            type="number"
            min="0"
            max="100"
            step="1"
            class="input input-bordered input-xs w-14 text-center"
            :disabled="hasAnyAutoSellEnabled"
          />
          <span class="text-xs text-base-content/50">%</span>
        </div>

        <!-- 卖出比例 -->
        <div class="flex items-center gap-1.5" title="卖出比例：触发时卖出持仓的百分比，100%为全部卖出">
          <span class="text-xs text-base-content/60 shrink-0 cursor-help border-b border-dashed border-base-content/30">比例</span>
          <input
            v-model.number="sellRatio"
            type="number"
            min="1"
            max="100"
            step="1"
            class="input input-bordered input-xs w-14 text-center"
            :disabled="hasAnyAutoSellEnabled"
          />
          <span class="text-xs text-base-content/50">%</span>
        </div>

        <!-- 刷新间隔 -->
        <div class="flex items-center gap-1.5" title="刷新间隔：每隔多少秒检查一次持仓和价格">
          <span class="text-xs text-base-content/60 shrink-0 cursor-help border-b border-dashed border-base-content/30">间隔</span>
          <input
            v-model.number="refreshInterval"
            type="number"
            min="1"
            max="60"
            step="1"
            class="input input-bordered input-xs w-14 text-center"
            :disabled="hasAnyAutoSellEnabled"
          />
          <span class="text-xs text-base-content/50">秒</span>
        </div>

        <!-- 冷却时间 -->
        <div class="flex items-center gap-1.5" title="冷却时间：同一边卖出后需等待的时间，防止重复卖出">
          <span class="text-xs text-base-content/60 shrink-0 cursor-help border-b border-dashed border-base-content/30">冷却</span>
          <input
            v-model.number="cooldownTime"
            type="number"
            min="0"
            max="300"
            step="5"
            class="input input-bordered input-xs w-14 text-center"
            :disabled="hasAnyAutoSellEnabled"
          />
          <span class="text-xs text-base-content/50">秒</span>
        </div>
      </div>

      <!-- 持仓状态区域 -->
      <div class="mt-3 rounded-lg border border-base-200/70 px-3 py-2 ring-1 ring-base-content/20">
        <div class="text-sm font-semibold">持仓监控</div>

        <div class="mt-2 space-y-2">
          <div
            v-for="pos in positionStatusList"
            :key="pos.outcome"
            class="rounded-md bg-base-100/60 px-2 py-2"
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
            <div class="mt-1 flex items-center justify-between text-[11px] text-base-content/60">
              <span>持仓: {{ formatSize(pos.size) }}</span>
              <span>均价: {{ formatPrice(pos.avg_price) }}</span>
              <span>现价: {{ formatPrice(pos.cur_price) }}</span>
            </div>
            <div class="mt-0.5 flex items-center justify-between text-[11px]">
              <span
                :class="(pos.profitRate ?? 0) >= 0 ? 'text-success' : 'text-error'"
              >
                收益率: {{ pos.profitRate !== null ? `${(pos.profitRate * 100).toFixed(1)}%` : '--' }}
              </span>
              <span v-if="pos.lastSell" class="text-[10px] text-base-content/40">
                上次卖出: {{ formatTimeAgo(pos.lastSell) }}
              </span>
            </div>
          </div>

          <div v-if="positionStatusList.length === 0" class="text-center text-xs text-base-content/50 py-2">
            暂无持仓数据
          </div>
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
