<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { useAuthStore, useGameStore, useToastStore } from '@/stores'

const props = withDefaults(
  defineProps<{
    showPositionCost?: boolean
  }>(),
  {
    showPositionCost: true,
  }
)

const authStore = useAuthStore()
const gameStore = useGameStore()
const toastStore = useToastStore()
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
const ORDER_TYPE = 'GTC'
const POLYMARKET_PRIVATE_KEY = 'POLYMARKET_PRIVATE_KEY'
const POLYMARKET_PROXY_ADDRESS = 'POLYMARKET_PROXY_ADDRESS'

const polymarketInfo = computed(() => gameStore.polymarketInfo)
const bookUpdatedAt = computed(() => gameStore.polymarketBookUpdatedAt)

const rows = computed(() => {
  const info = polymarketInfo.value
  if (!info) return []

  return info.tokens.map(token => {
    const snapshot = gameStore.polymarketBook[token.token_id]
    const bestBid = snapshot?.bestBid ?? null
    const bestAsk = snapshot?.bestAsk ?? null
    return {
      tokenId: token.token_id,
      outcome: token.outcome,
      bestBid,
      bestAsk,
      bidSize: snapshot?.bidSize ?? null,
      askSize: snapshot?.askSize ?? null,
      updatedAt: snapshot?.updatedAt ?? null,
    }
  })
})

const buySizeByToken = reactive<Record<string, string>>({})
const buyPriceByToken = reactive<Record<string, string>>({})
const buyPriceLocked = reactive<Record<string, boolean>>({})
const sellSizeByToken = reactive<Record<string, string>>({})
const sellPriceByToken = reactive<Record<string, string>>({})
const sellPriceLocked = reactive<Record<string, boolean>>({})
const submitting = reactive<Record<string, boolean>>({})

// 使用 store 中的持仓数据
const positionSides = computed(() => gameStore.positionSides)
const positionsLoading = computed(() => gameStore.positionsLoading)

const positionSizeByOutcome = computed(() => {
  const map: Record<string, number> = {}
  positionSides.value.forEach(side => {
    const outcome = String(side.outcome)
    const size = Number(side.size)
    if (!Number.isNaN(size)) {
      map[outcome] = size
    }
  })
  return map
})


function formatPrice(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '--'
  return value.toFixed(3)
}

function formatPercent(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '--'
  return `${(value * 100).toFixed(1)}%`
}

function formatTime(timestamp: string | null): string {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return timestamp
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatSize(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return value.toFixed(2)
}

function normalizeSides(sides: Array<{ outcome: string; size: number; initial_value?: number | null; avg_price?: number | null; cur_price?: number | null }>) {
  return sides
    .map(side => ({
      outcome: String(side.outcome),
      size: Number(side.size),
      initial_value: side.initial_value === null || side.initial_value === undefined
        ? null
        : Number(side.initial_value),
    }))
    .sort((a, b) => a.outcome.localeCompare(b.outcome))
}

function isSameSides(
  current: Array<{ outcome: string; size: number; initial_value?: number | null; avg_price?: number | null; cur_price?: number | null }>,
  next: Array<{ outcome: string; size: number; initial_value?: number | null; avg_price?: number | null; cur_price?: number | null }>
) {
  const a = normalizeSides(current)
  const b = normalizeSides(next)
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i += 1) {
    if (a[i].outcome !== b[i].outcome) return false
    if (Number.isNaN(a[i].size) || Number.isNaN(b[i].size)) return false
    if (a[i].size !== b[i].size) return false
    if (a[i].initial_value !== b[i].initial_value) return false
  }
  return true
}

function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function getBuySize(tokenId: string): string {
  return buySizeByToken[tokenId] ?? '10'
}

function setBuySize(tokenId: string, value: string) {
  buySizeByToken[tokenId] = value
}

function getSellSize(tokenId: string): string {
  return sellSizeByToken[tokenId] ?? '10'
}

function setSellSize(tokenId: string, value: string) {
  sellSizeByToken[tokenId] = value
}

function setQuickSellSize(outcome: string, tokenId: string, ratio: number) {
  const baseSize = positionSizeByOutcome.value[outcome] ?? 0
  const sizeValue = Math.max(0, baseSize * ratio)
  setSellSize(tokenId, sizeValue.toFixed(2))
}

function getBuyPrice(tokenId: string, defaultPrice: number | null): string {
  if (buyPriceLocked[tokenId] && buyPriceByToken[tokenId] !== undefined) {
    return buyPriceByToken[tokenId]
  }
  return defaultPrice !== null ? defaultPrice.toString() : ''
}

function getSellPrice(tokenId: string, defaultPrice: number | null): string {
  if (sellPriceLocked[tokenId] && sellPriceByToken[tokenId] !== undefined) {
    return sellPriceByToken[tokenId]
  }
  return defaultPrice !== null ? defaultPrice.toString() : ''
}

function toggleBuyPriceLock(tokenId: string, currentPrice: number | null) {
  if (buyPriceLocked[tokenId]) {
    buyPriceLocked[tokenId] = false
  } else {
    buyPriceByToken[tokenId] = currentPrice?.toString() ?? ''
    buyPriceLocked[tokenId] = true
  }
}

function toggleSellPriceLock(tokenId: string, currentPrice: number | null) {
  if (sellPriceLocked[tokenId]) {
    sellPriceLocked[tokenId] = false
  } else {
    sellPriceByToken[tokenId] = currentPrice?.toString() ?? ''
    sellPriceLocked[tokenId] = true
  }
}

function setBuyPrice(tokenId: string, value: string) {
  buyPriceByToken[tokenId] = value
}

function setSellPrice(tokenId: string, value: string) {
  sellPriceByToken[tokenId] = value
}

function getOrderPrice(
  side: 'BUY' | 'SELL',
  row: { tokenId: string; bestBid: number | null; bestAsk: number | null }
): number | null {
  if (side === 'BUY') {
    const inputPrice = buyPriceByToken[row.tokenId]
    if (inputPrice !== undefined && inputPrice !== '') {
      const parsed = Number(inputPrice)
      return Number.isNaN(parsed) ? null : parsed
    }
    return row.bestAsk
  } else {
    const inputPrice = sellPriceByToken[row.tokenId]
    if (inputPrice !== undefined && inputPrice !== '') {
      const parsed = Number(inputPrice)
      return Number.isNaN(parsed) ? null : parsed
    }
    return row.bestBid
  }
}

function getOrderSize(side: 'BUY' | 'SELL', tokenId: string): number {
  const sizeStr = side === 'BUY' ? getBuySize(tokenId) : getSellSize(tokenId)
  return Number(sizeStr)
}

function getPolymarketConfig() {
  const privateKey = localStorage.getItem(POLYMARKET_PRIVATE_KEY)?.trim() ?? ''
  const proxyAddress = localStorage.getItem(POLYMARKET_PROXY_ADDRESS)?.trim() ?? ''
  return { privateKey, proxyAddress }
}

function getPolymarketUserAddress() {
  const proxyAddress = localStorage.getItem(POLYMARKET_PROXY_ADDRESS)?.trim() ?? ''
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

async function fetchMarketPositions(options: {
  retries?: number
  delayMs?: number
  retryOnEmpty?: boolean
  retryAlways?: boolean
  skipImmediate?: boolean
  initialDelayMs?: number
} = {}) {
  if (!authStore.isAuthenticated) return
  const conditionId = getMarketConditionId()
  if (!conditionId) return

  const outcomes = getMarketOutcomes()
  const { userAddress, proxyAddress } = getPolymarketUserAddress()
  if (!userAddress && !proxyAddress) {
    return
  }

  const retries = options.retries ?? 0
  const delayMs = options.delayMs ?? 1000
  const retryOnEmpty = options.retryOnEmpty ?? false
  const retryAlways = options.retryAlways ?? false
  const skipImmediate = options.skipImmediate ?? false
  const initialDelayMs = options.initialDelayMs ?? delayMs

  gameStore.setPositionsLoading(true)
  let lastError: Error | null = null
  const totalAttempts = Math.max(1, retries + 1)
  const startAttempt = skipImmediate ? 1 : 0

  try {
    if (skipImmediate) {
      await sleep(initialDelayMs)
    }

    for (let attempt = startAttempt; attempt < totalAttempts; attempt += 1) {
      const step = attempt - startAttempt
      if (step > 0) {
        const backoff = delayMs * Math.pow(2, step - 1)
        await sleep(backoff)
      }

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
        const unchanged = isSameSides(positionSides.value, sides)
        gameStore.setPositionSides(sides)

        if (attempt < totalAttempts - 1) {
          if (retryAlways && unchanged) {
            continue
          }
          if (retryOnEmpty && sides.length === 0) {
            continue
          }
        }

        lastError = null
        break
      } catch (error) {
        lastError = error instanceof Error ? error : new Error('查询持仓失败')
        if (attempt >= totalAttempts - 1) {
          throw lastError
        }
      }
    }
  } catch (error) {
    toastStore.showToast(error instanceof Error ? error.message : '查询持仓失败', 'error')
  } finally {
    gameStore.setPositionsLoading(false)
  }
}



async function placeOrder(
  row: { tokenId: string; bestBid: number | null; bestAsk: number | null },
  side: 'BUY' | 'SELL'
) {
  if (!authStore.isAuthenticated) {
    toastStore.showToast('请先登录获取访问令牌', 'error')
    return
  }

  const price = getOrderPrice(side, row)
  if (price === null || Number.isNaN(price)) {
    toastStore.showToast('请输入有效价格', 'error')
    return
  }

  const { privateKey, proxyAddress } = getPolymarketConfig()
  if (!privateKey) {
    toastStore.showToast('请先在顶部配置 Polymarket 私钥', 'error')
    return
  }
  if (!proxyAddress) {
    toastStore.showToast('请先在顶部配置 Polymarket 代理地址', 'error')
    return
  }

  const sizeValue = getOrderSize(side, row.tokenId)
  if (!sizeValue || Number.isNaN(sizeValue) || sizeValue <= 0) {
    toastStore.showToast('请输入正确的份数', 'error')
    return
  }

  submitting[row.tokenId] = true

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/polymarket/orders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authStore.token}`,
      },
      body: JSON.stringify({
        token_id: row.tokenId,
        side,
        price,
        size: sizeValue,
        order_type: ORDER_TYPE,
        private_key: privateKey,
        proxy_address: proxyAddress,
      }),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => null)
      throw new Error(data?.detail || '下单失败')
    }

    await response.json().catch(() => null)
    toastStore.showToast('下单成功', 'success')
    void fetchMarketPositions({
      retries: 2,
      delayMs: 4000,
      retryOnEmpty: true,
      retryAlways: true,
      skipImmediate: true,
      initialDelayMs: 2000,
    })
  } catch (error) {
    toastStore.showToast(error instanceof Error ? error.message : '下单失败', 'error')
  } finally {
    submitting[row.tokenId] = false
  }
}

function getQuickSellDisabled(outcome: string) {
  const sizeValue = positionSizeByOutcome.value[outcome] ?? 0
  return !sizeValue || Number.isNaN(sizeValue) || sizeValue <= 0
}

watch(
  () => [polymarketInfo.value?.condition_id, polymarketInfo.value?.market_info?.condition_id],
  async () => {
    await fetchMarketPositions()
  }
)

watch(
  () => authStore.isAuthenticated,
  async isAuthed => {
    if (isAuthed) {
      await fetchMarketPositions()
    }
  }
)
</script>

<template>
  <div class="card glass-card ring-1 ring-base-content/30 ring-offset-2 ring-offset-base-100">
    <div class="card-body">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h3 class="card-title">Polymarket 盘口</h3>
        </div>
        <div class="text-right text-xs text-base-content/60">
          <div>最新更新</div>
          <div class="font-medium text-base-content/80">{{ formatTime(bookUpdatedAt) }}</div>
        </div>
      </div>

      <div v-if="!authStore.isAuthenticated" class="mt-3 text-right text-xs text-amber-600/80">
        下单前请先登录
      </div>

        <div class="mt-3 rounded-lg border border-base-200/70 px-3 py-2 ring-1 ring-base-content/20">
        <div class="flex items-center justify-between gap-3">
          <div class="text-sm font-semibold">当前持仓</div>
          <div class="flex items-center gap-2 text-xs text-base-content/60">
            <span>{{ positionsLoading ? '刷新中...' : '双边份额' }}</span>
            <button
              class="btn btn-ghost btn-xs"
              :disabled="positionsLoading"
              @click="fetchMarketPositions()"
              title="刷新持仓"
            >
              ↻
            </button>
          </div>
        </div>
      <div class="mt-2 grid grid-cols-2 gap-2 text-xs">
        <div
          v-for="side in positionSides"
          :key="side.outcome"
          class="rounded-md bg-base-100/60 px-2 py-2"
        >
          <div class="flex items-baseline justify-between">
            <span class="text-sm font-semibold text-base-content">{{ side.outcome }}</span>
            <span class="text-sm font-semibold text-base-content">{{ formatSize(side.size) }}</span>
          </div>
          <div v-if="props.showPositionCost" class="mt-0.5 flex items-center justify-between text-[10px] text-base-content/50">
            <span>成本</span>
            <span class="text-base-content/70">{{ formatSize(side.initial_value ?? null) }}</span>
          </div>
          <div class="mt-0.5 flex items-center justify-between text-[10px] text-base-content/50">
            <span>均价 / 现价</span>
            <span class="text-base-content/70">{{ side.avg_price != null ? formatPrice(side.avg_price) : '-' }} / {{ side.cur_price != null ? formatPrice(side.cur_price) : '-' }}</span>
          </div>
        </div>
        <div v-if="positionSides.length === 0" class="col-span-2 text-center text-base-content/50">
          暂无持仓数据
        </div>
      </div>
      </div>

      <div v-if="rows.length === 0" class="py-6 text-center text-base-content/50">
        暂无订单簿数据
      </div>

      <div v-else class="mt-4 space-y-3">
        <div
          v-for="row in rows"
          :key="row.tokenId"
          class="rounded-lg border border-base-200/70 px-3 py-2 ring-1 ring-base-content/20"
        >
          <div class="flex items-center justify-between gap-3">
            <div>
              <div class="text-sm font-semibold">{{ row.outcome }}</div>
            </div>
            <div class="text-xs text-base-content/60">
              更新 {{ formatTime(row.updatedAt) }}
            </div>
          </div>

          <div class="mt-2 grid grid-cols-2 gap-2 text-center text-xs">
            <div class="rounded-md bg-emerald-50/70 px-2 py-2">
              <div class="text-[11px] text-emerald-700/70">最佳买价</div>
              <div class="text-sm font-semibold text-emerald-900">
                {{ formatPrice(row.bestBid) }}
              </div>
              <div class="text-[11px] text-emerald-700/70">
                {{ formatPercent(row.bestBid) }} · {{ row.bidSize ?? '--' }}
              </div>
            </div>
            <div class="rounded-md bg-rose-50/70 px-2 py-2">
              <div class="text-[11px] text-rose-700/70">最佳卖价</div>
              <div class="text-sm font-semibold text-rose-900">
                {{ formatPrice(row.bestAsk) }}
              </div>
              <div class="text-[11px] text-rose-700/70">
                {{ formatPercent(row.bestAsk) }} · {{ row.askSize ?? '--' }}
              </div>
            </div>
          </div>

          <div class="mt-3 space-y-2">
            <div class="flex items-center gap-2">
              <span class="text-xs text-emerald-700/70 font-medium w-8">买入</span>
              <input
                :value="getBuySize(row.tokenId)"
                type="number"
                min="0"
                step="1"
                class="input input-bordered input-sm w-20"
                placeholder="份数"
                @input="setBuySize(row.tokenId, ($event.target as HTMLInputElement).value)"
              />
              <div class="relative">
                <input
                  :value="getBuyPrice(row.tokenId, row.bestAsk)"
                  type="number"
                  min="0"
                  max="1"
                  step="0.001"
                  class="input input-bordered input-sm w-24 pr-7"
                  :class="{ 'border-amber-400': buyPriceLocked[row.tokenId] }"
                  placeholder="价格"
                  @input="setBuyPrice(row.tokenId, ($event.target as HTMLInputElement).value); buyPriceLocked[row.tokenId] = true"
                />
                <button
                  class="absolute right-1 top-1/2 -translate-y-1/2 text-xs opacity-60 hover:opacity-100"
                  :class="buyPriceLocked[row.tokenId] ? 'text-amber-500' : 'text-base-content/40'"
                  :title="buyPriceLocked[row.tokenId] ? '点击解锁，跟随市价' : '点击锁定当前价格'"
                  @click="toggleBuyPriceLock(row.tokenId, row.bestAsk)"
                >
                  {{ buyPriceLocked[row.tokenId] ? '🔒' : '🔓' }}
                </button>
              </div>
              <button
                class="btn btn-sm btn-success flex-1"
                :disabled="submitting[row.tokenId]"
                @click="placeOrder(row, 'BUY')"
              >
                买入
              </button>
            </div>
            <div class="flex flex-col gap-2">
              <div class="flex items-center gap-2">
                <span class="text-xs text-rose-700/70 font-medium w-8">卖出</span>
                <input
                  :value="getSellSize(row.tokenId)"
                  type="number"
                  min="0"
                  step="1"
                  class="input input-bordered input-sm w-20"
                  placeholder="份数"
                  @input="setSellSize(row.tokenId, ($event.target as HTMLInputElement).value)"
                />
                <div class="relative">
                  <input
                    :value="getSellPrice(row.tokenId, row.bestBid)"
                    type="number"
                    min="0"
                    max="1"
                    step="0.001"
                    class="input input-bordered input-sm w-24 pr-7"
                    :class="{ 'border-amber-400': sellPriceLocked[row.tokenId] }"
                    placeholder="价格"
                    @input="setSellPrice(row.tokenId, ($event.target as HTMLInputElement).value); sellPriceLocked[row.tokenId] = true"
                  />
                  <button
                    class="absolute right-1 top-1/2 -translate-y-1/2 text-xs opacity-60 hover:opacity-100"
                    :class="sellPriceLocked[row.tokenId] ? 'text-amber-500' : 'text-base-content/40'"
                    :title="sellPriceLocked[row.tokenId] ? '点击解锁，跟随市价' : '点击锁定当前价格'"
                    @click="toggleSellPriceLock(row.tokenId, row.bestBid)"
                  >
                    {{ sellPriceLocked[row.tokenId] ? '🔒' : '🔓' }}
                  </button>
                </div>
                <button
                  class="btn btn-sm btn-error flex-1"
                  :disabled="submitting[row.tokenId]"
                  @click="placeOrder(row, 'SELL')"
                >
                  卖出
                </button>
              </div>
              <div class="flex items-center justify-between gap-2 text-[11px] text-base-content/60">
                <div class="flex items-center gap-2">
                  <button
                    class="btn btn-xs btn-ghost border border-base-300/80 bg-base-100/80 text-base-content/70 hover:border-base-400 hover:bg-base-200/60"
                    :disabled="getQuickSellDisabled(row.outcome)"
                    @click="setQuickSellSize(row.outcome, row.tokenId, 0.25)"
                  >
                    25%
                  </button>
                  <button
                    class="btn btn-xs btn-ghost border border-base-300/80 bg-base-100/80 text-base-content/70 hover:border-base-400 hover:bg-base-200/60"
                    :disabled="getQuickSellDisabled(row.outcome)"
                    @click="setQuickSellSize(row.outcome, row.tokenId, 0.5)"
                  >
                    50%
                  </button>
                  <button
                    class="btn btn-xs btn-ghost border border-base-300/80 bg-base-100/80 text-base-content/70 hover:border-base-400 hover:bg-base-200/60"
                    :disabled="getQuickSellDisabled(row.outcome)"
                    @click="setQuickSellSize(row.outcome, row.tokenId, 1)"
                  >
                    MAX
                  </button>
                </div>
                <span class="text-[10px] text-base-content/50">
                  可用 {{ formatSize(positionSizeByOutcome[row.outcome] ?? 0) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>
