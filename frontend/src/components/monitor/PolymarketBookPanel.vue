<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useAuthStore, useGameStore, useToastStore } from '@/stores'

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

const sizeByToken = reactive<Record<string, string>>({})
const submitting = reactive<Record<string, boolean>>({})
const batchSubmitting = ref(false)
const batchSize = ref('10')

const isBatchReady = computed(() => {
  if (rows.value.length === 0) return false
  return rows.value.every(row => {
    const priceOk = row.bestAsk !== null && !Number.isNaN(row.bestAsk)
    const sizeValue = Number(sizeByToken[row.tokenId] ?? '10')
    const sizeOk = !Number.isNaN(sizeValue) && sizeValue > 0
    return priceOk && sizeOk
  })
})


function formatPrice(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '--'
  return value.toFixed(3)
}

function formatSize(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '--'
  return value.toString()
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

function getSize(tokenId: string): string {
  return sizeByToken[tokenId] ?? '10'
}

function setSize(tokenId: string, value: string) {
  sizeByToken[tokenId] = value
}

function setAllSizes(value: string) {
  rows.value.forEach(row => {
    sizeByToken[row.tokenId] = value
  })
}

function getPrice(
  side: 'BUY' | 'SELL',
  row: { bestBid: number | null; bestAsk: number | null }
) {
  return side === 'BUY' ? row.bestAsk : row.bestBid
}

function getPolymarketConfig() {
  const privateKey = localStorage.getItem(POLYMARKET_PRIVATE_KEY)?.trim() ?? ''
  const proxyAddress = localStorage.getItem(POLYMARKET_PROXY_ADDRESS)?.trim() ?? ''
  return { privateKey, proxyAddress }
}



async function placeOrder(
  row: { tokenId: string; bestBid: number | null; bestAsk: number | null },
  side: 'BUY' | 'SELL'
) {
  if (!authStore.isAuthenticated) {
    toastStore.showToast('请先登录获取访问令牌', 'error')
    return
  }

  const price = getPrice(side, row)
  if (price === null || Number.isNaN(price)) {
    toastStore.showToast('暂无可用价格', 'error')
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

  const sizeValue = Number(getSize(row.tokenId))
  if (!sizeValue || Number.isNaN(sizeValue) || sizeValue <= 0) {
    toastStore.showToast('请输入正确的购买份数', 'error')
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
  } catch (error) {
    toastStore.showToast(error instanceof Error ? error.message : '下单失败', 'error')
  } finally {
    submitting[row.tokenId] = false
  }
}

async function placeBatchBuy() {
  if (!authStore.isAuthenticated) {
    toastStore.showToast('请先登录获取访问令牌', 'error')
    return
  }

  if (rows.value.length === 0) {
    toastStore.showToast('暂无可用盘口', 'error')
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

  const orders = rows.value.map(row => {
    const price = row.bestAsk
    const sizeValue = Number(getSize(row.tokenId))
    return {
      token_id: row.tokenId,
      side: 'BUY',
      price,
      size: sizeValue,
      order_type: ORDER_TYPE,
      private_key: privateKey,
      proxy_address: proxyAddress,
    }
  })

  const invalidOrder = orders.find(order => {
    return (
      order.price === null ||
      Number.isNaN(order.price) ||
      Number.isNaN(order.size) ||
      order.size <= 0
    )
  })
  if (invalidOrder) {
    toastStore.showToast('请确认双边卖价与份数有效', 'error')
    return
  }

  batchSubmitting.value = true

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/polymarket/orders/batch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authStore.token}`,
      },
      body: JSON.stringify({ orders }),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => null)
      throw new Error(data?.detail || '批量下单失败')
    }

    await response.json().catch(() => null)
    toastStore.showToast('双边买入批量下单成功', 'success')
  } catch (error) {
    toastStore.showToast(error instanceof Error ? error.message : '批量下单失败', 'error')
  } finally {
    batchSubmitting.value = false
  }
}
</script>

<template>
  <div class="card glass-card">
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

      <div v-if="rows.length === 0" class="py-6 text-center text-base-content/50">
        暂无订单簿数据
      </div>

      <div v-else class="mt-4 space-y-3">
        <div
          v-for="row in rows"
          :key="row.tokenId"
          class="rounded-lg border border-base-200/70 px-3 py-2"
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

          <div class="mt-3 grid grid-cols-[1fr_auto_auto] gap-2 items-center">
            <input
              :value="getSize(row.tokenId)"
              type="number"
              min="0"
              step="1"
              class="input input-bordered input-sm w-full"
              placeholder="份数"
              @input="setSize(row.tokenId, ($event.target as HTMLInputElement).value)"
            />
            <button
              class="btn btn-sm btn-success"
              :disabled="submitting[row.tokenId] || row.bestAsk === null"
              @click="placeOrder(row, 'BUY')"
            >
              买入@卖价
            </button>
            <button
              class="btn btn-sm btn-outline"
              :disabled="submitting[row.tokenId] || row.bestBid === null"
              @click="placeOrder(row, 'SELL')"
            >
              卖出@买价
            </button>
          </div>
        </div>
        <div class="rounded-lg border border-base-200/70 px-3 py-3">
          <div class="flex items-center justify-between gap-3">
            <div class="text-sm font-semibold">双边买入批量下单</div>
            <div class="text-xs text-base-content/60">使用当前卖价</div>
          </div>
          <div class="mt-3 flex flex-wrap items-center gap-2">
            <div class="text-xs text-base-content/60">统一份数</div>
            <input
              v-model="batchSize"
              type="number"
              min="0"
              step="1"
              class="input input-bordered input-sm w-28"
              placeholder="份数"
            />
            <button
              class="btn btn-sm btn-outline"
              :disabled="batchSubmitting"
              @click="setAllSizes(batchSize)"
            >
              一键填充
            </button>
          </div>
          <div class="mt-3 space-y-2">
            <div
              v-for="row in rows"
              :key="`batch-${row.tokenId}`"
              class="grid grid-cols-[1fr_auto_auto] items-center gap-2"
            >
              <div class="text-sm">{{ row.outcome }}</div>
              <div class="text-xs text-base-content/60">
                卖价 {{ formatPrice(row.bestAsk) }}
              </div>
              <input
                :value="getSize(row.tokenId)"
                type="number"
                min="0"
                step="1"
                class="input input-bordered input-sm w-24"
                placeholder="份数"
                @input="setSize(row.tokenId, ($event.target as HTMLInputElement).value)"
              />
            </div>
          </div>
          <div class="mt-3 flex items-center justify-between gap-3">
            <div class="text-xs text-base-content/60">
              需要两边都有卖价与有效份数
            </div>
            <button
              class="btn btn-sm btn-primary"
              :disabled="batchSubmitting || !isBatchReady"
              @click="placeBatchBuy"
            >
              双边买入
            </button>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>
