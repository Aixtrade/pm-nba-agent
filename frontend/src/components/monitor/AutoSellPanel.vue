<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAuthStore, useGameStore, useTaskStore, useToastStore } from '@/stores'
import { taskService } from '@/services/taskService'

const POLYMARKET_PRIVATE_KEY = 'POLYMARKET_PRIVATE_KEY'
const POLYMARKET_PROXY_ADDRESS = 'POLYMARKET_PROXY_ADDRESS'

const DEFAULT_MIN_PROFIT_RATE = 5
const DEFAULT_SELL_RATIO = 100
const DEFAULT_COOLDOWN_TIME = 30
const DEFAULT_REFRESH_INTERVAL = 3

const authStore = useAuthStore()
const gameStore = useGameStore()
const taskStore = useTaskStore()
const toastStore = useToastStore()

const requestPending = ref(false)
const formOutcomeRules = ref<Record<string, {
  enabled: boolean
  min_profit_rate: number
  sell_ratio: number
  cooldown_time: number
}>>({})
const formRefreshInterval = ref(DEFAULT_REFRESH_INTERVAL)

const polymarketInfo = computed(() => gameStore.polymarketInfo)
const polymarketBook = computed(() => gameStore.polymarketBook)
const positionSides = computed(() => gameStore.positionSides)
const autoSellState = computed(() => gameStore.autoSellState)
const currentTaskId = computed(() => taskStore.currentTaskId)

const allOutcomes = computed(() => {
  const fromPositions = positionSides.value.map((side) => side.outcome)
  const fromMarket = polymarketInfo.value?.tokens?.map((token) => token.outcome) ?? []
  return Array.from(new Set([...fromMarket, ...fromPositions].filter(Boolean)))
})

const hasAnyEnabled = computed(() => {
  return Object.values(formOutcomeRules.value).some((rule) => !!rule?.enabled)
})

const effectiveEnabled = computed(() => autoSellState.value?.enabled ?? hasAnyEnabled.value)
const effectiveIsOrdering = computed(() => autoSellState.value?.is_ordering ?? false)

const statusText = computed(() => {
  if (!effectiveEnabled.value) return '已关闭'
  if (effectiveIsOrdering.value) return '卖出中...'
  return '监控中'
})

const statusClass = computed(() => {
  if (!effectiveEnabled.value) return 'text-base-content/50'
  if (effectiveIsOrdering.value) return 'text-warning'
  return 'text-success'
})

const positionByOutcome = computed(() => {
  const map: Record<string, { size: number; avg_price?: number | null; initial_value?: number | null; cur_price?: number | null }> = {}
  for (const side of positionSides.value) {
    map[side.outcome] = side
  }
  return map
})

const positionStatusList = computed(() => {
  return allOutcomes.value.map((outcome) => {
    const side = positionByOutcome.value[outcome]
    const tokenId = polymarketInfo.value?.tokens?.find((token) => token.outcome === outcome)?.token_id
    const bestBid = tokenId ? (polymarketBook.value[tokenId]?.bestBid ?? null) : null
    const avgPrice = side?.avg_price ?? null
    const size = side?.size ?? 0

    const rule = formOutcomeRules.value[outcome] ?? {
      enabled: false,
      min_profit_rate: DEFAULT_MIN_PROFIT_RATE,
      sell_ratio: DEFAULT_SELL_RATIO,
      cooldown_time: DEFAULT_COOLDOWN_TIME,
    }

    let profitRate: number | null = null
    let canSell = false
    let reason = '未启用'

    if (rule.enabled) {
      if (!size || size <= 0) {
        reason = '无持仓'
      } else if (bestBid == null || bestBid <= 0) {
        reason = '无实时价格'
      } else if (avgPrice == null || avgPrice <= 0) {
        reason = '无均价数据'
      } else {
        profitRate = (bestBid - avgPrice) / avgPrice
        if (profitRate < (rule.min_profit_rate / 100)) {
          reason = `利润率不足 (${(profitRate * 100).toFixed(1)}% < ${rule.min_profit_rate}%)`
        } else {
          canSell = true
          reason = '可卖'
        }
      }
    }

    const lastSellTime = autoSellState.value?.last_sell_time?.[outcome] ?? null
    return {
      outcome,
      size,
      avg_price: avgPrice,
      realtimePrice: bestBid,
      profitRate,
      canSell,
      reason,
      enabled: rule.enabled,
      minProfitRate: rule.min_profit_rate,
      sellRatio: rule.sell_ratio,
      cooldownTime: rule.cooldown_time,
      lastSellTime,
    }
  })
})

const hasStats = computed(() => {
  return Object.keys(autoSellState.value?.stats ?? {}).length > 0
})

const statsDisplay = computed(() => {
  const stats = autoSellState.value?.stats ?? {}
  const entries = Object.entries(stats)
  if (entries.length === 0) return '--'
  return entries.map(([outcome, stat]) => `${outcome} x${stat.count} ($${stat.amount.toFixed(2)})`).join(', ')
})

watch(allOutcomes, (outcomes) => {
  const nextRules = { ...formOutcomeRules.value }
  for (const outcome of outcomes) {
    if (nextRules[outcome]) continue
    nextRules[outcome] = {
      enabled: false,
      min_profit_rate: DEFAULT_MIN_PROFIT_RATE,
      sell_ratio: DEFAULT_SELL_RATIO,
      cooldown_time: DEFAULT_COOLDOWN_TIME,
    }
  }
  formOutcomeRules.value = nextRules
}, { immediate: true })

watch(currentTaskId, () => {
  void loadTaskConfig()
}, { immediate: true })

function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return value.toFixed(3)
}

function formatSize(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return value.toFixed(2)
}

function formatTime(value: string | null | undefined): string {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

async function loadTaskConfig() {
  if (!currentTaskId.value || !authStore.token) return

  try {
    const response = await taskService.getTaskConfig(currentTaskId.value, authStore.token)
    const config = (response.config ?? {}) as Record<string, unknown>
    const autoSell = (config.auto_sell ?? {}) as Record<string, unknown>
    const defaultCfg = (autoSell.default ?? {}) as Record<string, unknown>

    if (typeof defaultCfg.refresh_interval === 'number') {
      formRefreshInterval.value = defaultCfg.refresh_interval
    }

    const rawRules = (autoSell.outcome_rules ?? {}) as Record<string, Record<string, unknown>>
    const nextRules = { ...formOutcomeRules.value }
    for (const [outcome, rule] of Object.entries(rawRules)) {
      nextRules[outcome] = {
        enabled: !!rule.enabled,
        min_profit_rate: typeof rule.min_profit_rate === 'number' ? rule.min_profit_rate : DEFAULT_MIN_PROFIT_RATE,
        sell_ratio: typeof rule.sell_ratio === 'number' ? rule.sell_ratio : DEFAULT_SELL_RATIO,
        cooldown_time: typeof rule.cooldown_time === 'number' ? rule.cooldown_time : DEFAULT_COOLDOWN_TIME,
      }
    }
    formOutcomeRules.value = nextRules
  } catch (error) {
    const message = error instanceof Error ? error.message : '加载自动卖出配置失败'
    toastStore.showWarning(message)
  }
}

async function pushConfigPatch() {
  if (!currentTaskId.value) {
    toastStore.showWarning('请先创建并订阅任务')
    return
  }
  if (!authStore.token) {
    toastStore.showWarning('请先登录')
    return
  }

  requestPending.value = true
  try {
    const privateKey = localStorage.getItem(POLYMARKET_PRIVATE_KEY)?.trim() || null
    const proxyAddress = localStorage.getItem(POLYMARKET_PROXY_ADDRESS)?.trim() || null

    const outcomeRules: Record<string, unknown> = {}
    for (const [outcome, rule] of Object.entries(formOutcomeRules.value)) {
      outcomeRules[outcome] = {
        enabled: rule.enabled,
        min_profit_rate: rule.min_profit_rate,
        sell_ratio: rule.sell_ratio,
        cooldown_time: rule.cooldown_time,
      }
    }

    await taskService.updateTaskConfig(
      currentTaskId.value,
      {
        patch: {
          private_key: privateKey,
          proxy_address: proxyAddress,
          auto_sell: {
            enabled: hasAnyEnabled.value,
            default: {
              refresh_interval: formRefreshInterval.value,
            },
            outcome_rules: outcomeRules,
          },
        },
      },
      authStore.token,
    )
  } catch (error) {
    const message = error instanceof Error ? error.message : '更新自动卖出配置失败'
    toastStore.showError(message)
  } finally {
    requestPending.value = false
  }
}

function toggleOutcome(outcome: string) {
  const current = formOutcomeRules.value[outcome] ?? {
    enabled: false,
    min_profit_rate: DEFAULT_MIN_PROFIT_RATE,
    sell_ratio: DEFAULT_SELL_RATIO,
    cooldown_time: DEFAULT_COOLDOWN_TIME,
  }
  formOutcomeRules.value = {
    ...formOutcomeRules.value,
    [outcome]: {
      ...current,
      enabled: !current.enabled,
    },
  }
  void pushConfigPatch()
}

function setRuleField(
  outcome: string,
  field: 'min_profit_rate' | 'sell_ratio' | 'cooldown_time',
  value: number,
) {
  const current = formOutcomeRules.value[outcome]
  if (!current || !Number.isFinite(value)) return
  formOutcomeRules.value = {
    ...formOutcomeRules.value,
    [outcome]: {
      ...current,
      [field]: value,
    },
  }
}

function commitRule(outcome: string) {
  if (!formOutcomeRules.value[outcome]) return
  void pushConfigPatch()
}

function updateRefreshInterval(value: number) {
  if (!Number.isFinite(value) || value <= 0) return
  formRefreshInterval.value = value
  void pushConfigPatch()
}

function setRefreshIntervalInput(value: number) {
  if (!Number.isFinite(value) || value <= 0) return
  formRefreshInterval.value = value
}

function resetStats() {
  toastStore.showInfo('统计由后台维护，重置功能待接入')
}
</script>

<template>
  <div class="card glass-card ring-1 ring-base-content/30 ring-offset-2 ring-offset-base-100">
    <div class="card-body">
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-baseline gap-2">
          <h3 class="card-title text-base">自动卖出</h3>
          <span class="text-[10px] text-base-content/40">现价/均价 ≥ 阈值时卖出（后端任务执行）</span>
        </div>
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-1" title="持仓刷新间隔">
            <span class="text-[10px] text-base-content/50">刷新</span>
            <input
              :value="formRefreshInterval"
              type="number"
              min="1"
              max="60"
              step="1"
              class="input input-bordered input-xs w-10 text-center text-[10px] px-1"
              :disabled="requestPending"
              @input="setRefreshIntervalInput(Number(($event.target as HTMLInputElement).value))"
              @change="updateRefreshInterval(Number(($event.target as HTMLInputElement).value))"
            ><span class="text-[10px] text-base-content/40">秒</span>
          </div>
          <span :class="statusClass" class="text-xs">{{ statusText }}</span>
        </div>
      </div>

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
                :disabled="!currentTaskId || requestPending"
                @change="toggleOutcome(pos.outcome)"
              >
              <span class="text-sm font-semibold text-base-content">{{ pos.outcome }}</span>
            </div>
            <span class="text-xs" :class="pos.canSell ? 'text-success font-semibold' : 'text-base-content/50'">
              {{ pos.canSell ? '可卖' : pos.reason }}
            </span>
          </div>
          <div class="mt-1 flex flex-wrap gap-x-3 text-xs text-base-content/60">
            <span>持仓: {{ formatSize(pos.size) }}</span>
            <span>均价: {{ formatPrice(pos.avg_price) }}</span>
            <span>现价: {{ formatPrice(pos.realtimePrice) }}</span>
            <span :class="(pos.profitRate ?? 0) >= 0 ? 'text-success' : 'text-error'">
              收益: {{ pos.profitRate != null ? `${(pos.profitRate * 100).toFixed(1)}%` : '--' }}
            </span>
          </div>
          <div class="text-xs text-base-content/40">
            上次卖出: {{ formatTime(pos.lastSellTime) }}
          </div>

          <div class="mt-2 pt-2 border-t border-base-200/50 flex flex-wrap gap-x-4 gap-y-1">
            <div class="flex items-center gap-1" title="最小利润率">
              <span class="text-xs text-base-content/50">利润</span>
              <input
                :value="pos.minProfitRate"
                type="number"
                min="0"
                max="100"
                step="1"
                class="input input-bordered input-xs w-12 text-center"
                :disabled="!currentTaskId || requestPending || pos.enabled"
                @input="setRuleField(pos.outcome, 'min_profit_rate', Number(($event.target as HTMLInputElement).value))"
                @change="commitRule(pos.outcome)"
              ><span class="text-xs text-base-content/40">%</span>
            </div>
            <div class="flex items-center gap-1" title="卖出比例">
              <span class="text-xs text-base-content/50">比例</span>
              <input
                :value="pos.sellRatio"
                type="number"
                min="1"
                max="100"
                step="1"
                class="input input-bordered input-xs w-12 text-center"
                :disabled="!currentTaskId || requestPending || pos.enabled"
                @input="setRuleField(pos.outcome, 'sell_ratio', Number(($event.target as HTMLInputElement).value))"
                @change="commitRule(pos.outcome)"
              ><span class="text-xs text-base-content/40">%</span>
            </div>
            <div class="flex items-center gap-1" title="冷却时间">
              <span class="text-xs text-base-content/50">冷却</span>
              <input
                :value="pos.cooldownTime"
                type="number"
                min="0"
                max="300"
                step="5"
                class="input input-bordered input-xs w-12 text-center"
                :disabled="!currentTaskId || requestPending || pos.enabled"
                @input="setRuleField(pos.outcome, 'cooldown_time', Number(($event.target as HTMLInputElement).value))"
                @change="commitRule(pos.outcome)"
              ><span class="text-xs text-base-content/40">秒</span>
            </div>
          </div>
        </div>

        <div v-if="positionStatusList.length === 0" class="col-span-2 text-center text-xs text-base-content/50 py-2">
          暂无持仓数据
        </div>
      </div>

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

      <div v-if="!currentTaskId" class="mt-3 text-xs text-amber-600/80">
        请先创建并订阅任务
      </div>
      <div v-else-if="!authStore.isAuthenticated" class="mt-3 text-xs text-amber-600/80">
        请先登录
      </div>
    </div>
  </div>
</template>
