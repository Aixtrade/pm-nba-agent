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
  timestamp: number
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
    isRunning?: boolean
    maxHistory?: number
  }>(),
  {
    strategyId: 'merge_long',
    isRunning: true,
    maxHistory: 5,
  }
)

const latestSignal = computed(() => props.signals[0] ?? null)
const signalHistory = computed(() => props.signals.slice(1, props.maxHistory))

const hasArbitrageOpportunity = computed(() => {
  const priceSum = latestSignal.value?.market?.price_sum
  return priceSum != null && priceSum < 1
})

const arbitrageGap = computed(() => {
  const priceSum = latestSignal.value?.market?.price_sum
  if (priceSum == null) return null
  return 1 - priceSum
})

function signalTypeClass(type?: string) {
  return {
    'bg-success text-success-content': type === 'BUY',
    'bg-error text-error-content': type === 'SELL',
    'bg-base-300 text-base-content/70': type === 'HOLD' || !type,
  }
}

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

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatPrice(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return '--'
  return v.toFixed(4)
}

function formatSize(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return '--'
  return v.toFixed(2)
}

function formatPct(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return '--'
  return `${(v * 100).toFixed(2)}%`
}
</script>

<template>
  <div class="card glass-card ring-1 ring-base-content/30 ring-offset-2 ring-offset-base-100">
    <div class="card-body">
      <!-- 标题栏 -->
      <div class="flex items-center justify-between">
        <h3 class="card-title text-base">策略信号</h3>
        <div class="flex items-center gap-2 text-xs">
          <span class="badge badge-sm" :class="isRunning ? 'badge-success' : 'badge-ghost'">
            {{ strategyId }}
          </span>
          <span :class="isRunning ? 'text-success' : 'text-base-content/50'">
            {{ isRunning ? '运行中' : '已停止' }}
          </span>
        </div>
      </div>

      <!-- 最新信号 -->
      <div v-if="latestSignal" class="mt-3 rounded-lg border border-base-200/70 p-3 ring-1 ring-base-content/20">
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-start gap-3">
            <!-- 信号类型标签 -->
            <div
              class="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg text-sm font-bold"
              :class="signalTypeClass(latestSignal.signal?.type)"
            >
              {{ signalTypeLabel(latestSignal.signal?.type) }}
            </div>
            <!-- 信号详情 -->
            <div class="min-w-0">
              <div class="text-sm font-medium leading-tight">
                {{ latestSignal.signal?.reason }}
              </div>
              <!-- BUY 信号显示交易详情 -->
              <div
                v-if="latestSignal.signal?.type === 'BUY'"
                class="mt-1.5 space-y-0.5 text-xs text-base-content/60"
              >
                <div class="flex items-center gap-1">
                  <span class="text-emerald-600">YES:</span>
                  <span>{{ formatSize(latestSignal.signal?.yes_size) }}</span>
                  <span class="text-base-content/40">@</span>
                  <span>{{ formatPrice(latestSignal.signal?.yes_price) }}</span>
                </div>
                <div class="flex items-center gap-1">
                  <span class="text-rose-600">NO:</span>
                  <span>{{ formatSize(latestSignal.signal?.no_size) }}</span>
                  <span class="text-base-content/40">@</span>
                  <span>{{ formatPrice(latestSignal.signal?.no_price) }}</span>
                </div>
              </div>
              <!-- 执行结果 -->
              <div
                v-if="latestSignal.execution"
                class="mt-1 text-xs"
                :class="latestSignal.execution.success ? 'text-success' : 'text-error'"
              >
                {{ latestSignal.execution.success ? '执行成功' : latestSignal.execution.error || '执行失败' }}
              </div>
            </div>
          </div>
          <!-- 时间戳 -->
          <div class="shrink-0 text-xs text-base-content/50">
            {{ formatTime(latestSignal.timestamp) }}
          </div>
        </div>

        <!-- 市场状态 -->
        <div v-if="latestSignal.market" class="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
          <div class="rounded-md bg-base-200/50 px-2 py-1.5">
            <div class="text-[11px] text-base-content/50">价格和</div>
            <div class="font-semibold" :class="hasArbitrageOpportunity ? 'text-success' : ''">
              {{ formatPrice(latestSignal.market.price_sum) }}
            </div>
          </div>
          <div class="rounded-md bg-base-200/50 px-2 py-1.5">
            <div class="text-[11px] text-base-content/50">套利空间</div>
            <div class="font-semibold" :class="hasArbitrageOpportunity ? 'text-success' : 'text-base-content/40'">
              {{ hasArbitrageOpportunity ? formatPct(arbitrageGap) : '--' }}
            </div>
          </div>
          <div class="rounded-md bg-base-200/50 px-2 py-1.5">
            <div class="text-[11px] text-base-content/50">阈值</div>
            <div class="font-semibold">&lt; 1.0000</div>
          </div>
        </div>
      </div>

      <!-- 无信号状态 -->
      <div v-else class="mt-3 py-6 text-center text-sm text-base-content/50">
        暂无信号
      </div>

      <!-- 信号历史 -->
      <div v-if="signalHistory.length > 0" class="mt-3">
        <div class="mb-2 text-xs font-medium text-base-content/60">信号历史</div>
        <div class="space-y-1">
          <div
            v-for="(sig, index) in signalHistory"
            :key="`${sig.timestamp}-${index}`"
            class="flex items-center gap-2 rounded-md bg-base-200/30 px-2 py-1.5 text-xs"
          >
            <span class="w-14 shrink-0 text-base-content/50">
              {{ formatTime(sig.timestamp) }}
            </span>
            <span class="badge badge-xs shrink-0" :class="signalBadgeClass(sig.signal?.type)">
              {{ signalTypeLabel(sig.signal?.type) }}
            </span>
            <span class="flex-1 truncate text-base-content/70">
              {{ sig.signal?.reason }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
