<script setup lang="ts">
/**
 * 策略信号显示面板
 *
 * 显示来自后端策略执行器的实时信号，包括：
 * - 最新信号（类型、原因、交易详情）
 * - 市场状态（价格和、套利空间）
 * - 信号历史
 */
import { computed, ref } from 'vue'

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

interface MetricData {
  key: string
  label: string
  value: string | number | boolean | null
  unit?: string
  semantic?: 'higher_better' | 'lower_better' | 'neutral'
  priority?: number
}

interface SignalEvent {
  event_type: 'signal' | 'order' | 'error' | 'status'
  timestamp: string
  signal?: SignalData
  market?: MarketData
  execution?: ExecutionData
  strategy?: { id: string }
  metrics?: MetricData[]
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
    maxHistory: 2,
  }
)

const latestSignal = computed(() => props.signals[0] ?? null)
const signalHistory = computed(() => props.signals.slice(1, props.maxHistory))
const allHistory = computed(() => props.signals.slice(1))
const showHistoryModal = ref(false)
const MAX_METRICS = 3

const topMetrics = computed(() => {
  const metrics = latestSignal.value?.metrics
  if (!metrics || metrics.length === 0) return []
  return [...metrics]
    .sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0))
    .slice(0, MAX_METRICS)
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

function formatMetricValue(v: MetricData['value']): string {
  if (v == null) return '--'
  if (typeof v === 'number') return v.toFixed(2)
  if (typeof v === 'boolean') return v ? 'true' : 'false'
  return String(v)
}
</script>

<template>
  <div>
  <div class="card glass-card ring-1 ring-base-content/30 ring-offset-2 ring-offset-base-100">
    <div class="card-body">
      <!-- 标题栏 -->
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <h3 class="card-title text-base">策略信号</h3>
          <button
            v-if="allHistory.length > 0"
            class="btn btn-ghost btn-xs text-base-content/50"
            @click="showHistoryModal = true"
          >
            全部 ({{ allHistory.length }})
          </button>
        </div>
        <div class="flex items-center gap-2 text-xs text-base-content/60">
          <span>{{ strategyId }}</span>
          <span v-if="latestSignal" class="text-base-content/40">·</span>
          <span v-if="latestSignal" class="font-medium text-base-content/80">{{ formatTime(latestSignal.timestamp) }}</span>
        </div>
      </div>

      <!-- 最新信号 -->
      <div v-if="latestSignal" class="mt-3">
        <!-- 信号主行：徽章 + reason -->
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
        </div>

        <!-- 策略指标（仅当 metrics 存在时显示） -->
        <div v-if="topMetrics.length > 0" class="mt-2 flex flex-wrap gap-2 pl-14">
          <div
            v-for="metric in topMetrics"
            :key="metric.key"
            class="badge badge-outline badge-sm"
          >
            <span class="text-base-content/60 mr-1">{{ metric.label }}</span>
            <span class="font-medium">
              {{ formatMetricValue(metric.value) }}<span v-if="metric.unit">{{ metric.unit }}</span>
            </span>
          </div>
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

  <!-- 历史信号对话框 -->
  <Teleport to="body">
  <dialog class="modal" :class="{ 'modal-open': showHistoryModal }">
    <div class="modal-box max-w-lg max-h-[70vh]! overflow-hidden flex flex-col">
      <div class="flex items-center justify-between mb-3 shrink-0">
        <h3 class="font-bold text-base">信号历史 · {{ strategyId }}</h3>
        <button class="btn btn-sm btn-circle btn-ghost" @click="showHistoryModal = false">✕</button>
      </div>
      <div class="overflow-y-auto min-h-0 flex-1 space-y-1.5 pr-1">
        <div
          v-for="(sig, index) in allHistory"
          :key="`modal-${sig.timestamp}-${index}`"
          class="flex items-start gap-2 text-xs py-1"
          :class="{ 'border-b border-base-200/50': index < allHistory.length - 1 }"
        >
          <span class="w-16 shrink-0 text-base-content/40 pt-0.5">
            {{ formatTime(sig.timestamp) }}
          </span>
          <span class="badge badge-xs shrink-0 mt-0.5" :class="signalBadgeClass(sig.signal?.type)">
            {{ signalTypeLabel(sig.signal?.type) }}
          </span>
          <div class="flex-1 min-w-0">
            <div class="text-base-content/80">{{ sig.signal?.reason }}</div>
            <div
              v-if="sig.signal?.type === 'BUY' || sig.signal?.type === 'SELL'"
              class="mt-0.5 flex items-center gap-3 text-base-content/50"
            >
              <span><span class="text-emerald-600">Y</span> {{ formatSize(sig.signal?.yes_size) }}@{{ formatPrice(sig.signal?.yes_price) }}</span>
              <span><span class="text-rose-600">N</span> {{ formatSize(sig.signal?.no_size) }}@{{ formatPrice(sig.signal?.no_price) }}</span>
              <span
                v-if="sig.execution"
                :class="sig.execution.success ? 'text-success' : 'text-error'"
              >
                {{ sig.execution.success ? '✓' : '✗' }}
              </span>
            </div>
          </div>
        </div>
        <div v-if="allHistory.length === 0" class="py-6 text-center text-sm text-base-content/50">
          暂无历史信号
        </div>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop" @click="showHistoryModal = false">
      <button>close</button>
    </form>
  </dialog>
  </Teleport>
  </div>
</template>
