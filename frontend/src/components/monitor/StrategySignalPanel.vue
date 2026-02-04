<script setup lang="ts">
/**
 * 策略信号显示面板
 *
 * 显示来自后端策略执行器的实时信号，包括：
 * - 最新信号（类型、原因、交易详情）
 * - 市场状态（价格和、套利空间）
 * - 信号历史
 */
import { computed } from 'vue'

interface SignalData {
  type: 'BUY' | 'SELL' | 'HOLD'
  reason: string
  yes_size?: number | null
  no_size?: number | null
  yes_price?: number | null
  no_price?: number | null
  metadata?: Record<string, unknown>
}

interface MarketData {
  yes_price?: number
  no_price?: number
  price_sum: number
  yes_best_bid?: number | null
  yes_best_ask?: number | null
  no_best_bid?: number | null
  no_best_ask?: number | null
}

interface ExecutionData {
  success: boolean
  orders?: Array<Record<string, unknown>>
  error?: string | null
}

interface SignalEvent {
  event_type: 'signal' | 'order' | 'error' | 'status'
  timestamp: string
  signal?: SignalData
  market?: MarketData
  execution?: ExecutionData
  strategy?: { id: string }
  error?: string | null
}

const props = withDefaults(
  defineProps<{
    signals: SignalEvent[]
    strategyId?: string
    maxHistory?: number
  }>(),
  {
    strategyId: 'merge_long',
    maxHistory: 5,
  }
)

const latestSignal = computed(() => props.signals[0] ?? null)
const signalHistory = computed(() => props.signals.slice(1, props.maxHistory))

const hasArbitrageOpportunity = computed(() => {
  const priceSum = latestSignal.value?.market?.price_sum
  return priceSum != null && priceSum < 1
})

function signalTypeLabel(type?: string): string {
  const labels: Record<string, string> = {
    BUY: '买入',
    SELL: '卖出',
    HOLD: '等待',
  }
  return labels[type ?? 'HOLD'] ?? '等待'
}

function signalBadgeClass(type?: string) {
  return {
    'badge-success': type === 'BUY',
    'badge-error': type === 'SELL',
    'badge-ghost': type === 'HOLD' || !type,
  }
}

function formatTime(ts: string): string {
  // 后端返回的是 UTC 时间但不带 Z 后缀，需要手动添加以确保正确解析
  const normalizedTs = ts.endsWith('Z') || ts.includes('+') || ts.includes('-', 10)
    ? ts
    : `${ts}Z`
  return new Date(normalizedTs).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatPrice(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return '--'
  return v.toFixed(2)
}

function formatSize(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return '--'
  return v.toFixed(2)
}
</script>

<template>
  <div class="card glass-card ring-1 ring-base-content/30 ring-offset-2 ring-offset-base-100">
    <div class="card-body">
      <!-- 标题栏 -->
      <div class="flex items-center justify-between gap-3">
        <h3 class="card-title text-base">策略信号</h3>
        <div class="flex items-center gap-2 text-xs text-base-content/60">
          <span>{{ strategyId }}</span>
          <span v-if="latestSignal" class="text-base-content/40">·</span>
          <span v-if="latestSignal" class="font-medium text-base-content/80">{{ formatTime(latestSignal.timestamp) }}</span>
        </div>
      </div>

      <!-- 最新信号 -->
      <div v-if="latestSignal" class="mt-3">
        <!-- 信号主行：徽章 + reason + 价格和 -->
        <div class="flex items-center gap-2">
          <span
            class="badge badge-sm shrink-0 font-medium"
            :class="signalBadgeClass(latestSignal.signal?.type)"
          >
            {{ signalTypeLabel(latestSignal.signal?.type) }}
          </span>
          <span class="flex-1 text-sm text-base-content/80 truncate">
            {{ latestSignal.signal?.reason }}
          </span>
          <span
            v-if="latestSignal.market"
            class="shrink-0 text-xs font-medium"
            :class="hasArbitrageOpportunity ? 'text-success' : 'text-base-content/50'"
          >
            Σ {{ formatPrice(latestSignal.market.price_sum) }}
          </span>
        </div>

        <!-- BUY/SELL 信号展开详情 -->
        <div
          v-if="latestSignal.signal?.type === 'BUY' || latestSignal.signal?.type === 'SELL'"
          class="mt-2 flex items-center gap-4 text-xs text-base-content/60 pl-14"
        >
          <div class="flex items-center gap-1">
            <span class="text-emerald-600">YES</span>
            <span>{{ formatSize(latestSignal.signal?.yes_size) }}</span>
            <span class="text-base-content/40">@</span>
            <span>{{ formatPrice(latestSignal.signal?.yes_price) }}</span>
          </div>
          <div class="flex items-center gap-1">
            <span class="text-rose-600">NO</span>
            <span>{{ formatSize(latestSignal.signal?.no_size) }}</span>
            <span class="text-base-content/40">@</span>
            <span>{{ formatPrice(latestSignal.signal?.no_price) }}</span>
          </div>
          <!-- 执行结果 -->
          <div
            v-if="latestSignal.execution"
            class="ml-auto"
            :class="latestSignal.execution.success ? 'text-success' : 'text-error'"
          >
            {{ latestSignal.execution.success ? '✓ 已执行' : latestSignal.execution.error || '✗ 失败' }}
          </div>
        </div>
      </div>

      <!-- 无信号状态 -->
      <div v-else class="mt-3 py-4 text-center text-sm text-base-content/50">
        暂无信号
      </div>

      <!-- 信号历史 -->
      <div v-if="signalHistory.length > 0" class="mt-3 pt-3 border-t border-base-200/70">
        <div class="mb-2 text-xs font-medium text-base-content/50">历史</div>
        <div class="space-y-1">
          <div
            v-for="(sig, index) in signalHistory"
            :key="`${sig.timestamp}-${index}`"
            class="flex items-center gap-2 text-xs"
          >
            <span class="w-14 shrink-0 text-base-content/40">
              {{ formatTime(sig.timestamp) }}
            </span>
            <span class="badge badge-xs shrink-0" :class="signalBadgeClass(sig.signal?.type)">
              {{ signalTypeLabel(sig.signal?.type) }}
            </span>
            <span class="flex-1 truncate text-base-content/60">
              {{ sig.signal?.reason }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
