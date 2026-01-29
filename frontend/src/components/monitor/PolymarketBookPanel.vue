<script setup lang="ts">
import { computed } from 'vue'
import { useGameStore } from '@/stores'

const gameStore = useGameStore()

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
</script>

<template>
  <div class="card glass-card">
    <div class="card-body">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h3 class="card-title">Polymarket 盘口</h3>
          <p class="text-xs text-base-content/60">
            {{ polymarketInfo?.title || '等待市场信息...' }}
          </p>
          <p v-if="polymarketInfo?.market_info?.question" class="text-xs text-base-content/50">
            {{ polymarketInfo.market_info.question }}
          </p>
        </div>
        <div class="text-right text-xs text-base-content/60">
          <div>最新更新</div>
          <div class="font-medium text-base-content/80">{{ formatTime(bookUpdatedAt) }}</div>
        </div>
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
        </div>
      </div>
    </div>
  </div>
</template>
