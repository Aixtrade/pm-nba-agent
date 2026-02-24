<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useAuthStore, useGameStore, useTaskStore, useToastStore } from '@/stores'
import { taskService } from '@/services/taskService'

const props = defineProps<{
  tokenId: string
  outcome: string
  bestAsk: number | null
}>()

const DEFAULT_BUDGET = 10
const DEFAULT_INTERVAL = 120
const DEFAULT_MAX_TOTAL = 0

const authStore = useAuthStore()
const gameStore = useGameStore()
const taskStore = useTaskStore()
const toastStore = useToastStore()

const enabled = ref(false)
const budgetUsdc = ref(DEFAULT_BUDGET)
const intervalSeconds = ref(DEFAULT_INTERVAL)
const maxTotalBudget = ref(DEFAULT_MAX_TOTAL)
const requestPending = ref(false)
const appliedConfigVersion = ref(0)
const pendingEnabled = ref<boolean | null>(null)
const pendingVersion = ref<number | null>(null)

const buyCount = ref(0)
const totalSpent = ref(0)
const lastBuyAt = ref(0)
const countdown = ref(0)

const autoTradeState = computed(() => gameStore.autoTradeState)
const currentTaskId = computed(() => taskStore.currentTaskId)
const ruleId = computed(() => `periodic_buy_${normalizeRuleSuffix(props.outcome)}`)
const effectiveEnabled = computed(() => pendingEnabled.value ?? enabled.value)

// --- localStorage persistence (full-map, backward compat) ---

interface AutoTradeRule {
  id?: string
  type?: string
  enabled: boolean
  budgetUsdc?: number
  intervalSeconds?: number
  maxTotalBudget?: number
  priority?: number
  scope?: Record<string, unknown>
  cooldown_seconds?: number
  config?: Record<string, unknown>
  risk?: Record<string, unknown>
}

interface RuleRuntime {
  last_trigger_at?: number
  last_order_at?: number
  order_count?: number
  total_spent?: number
  next_run_at?: number
}

watch(currentTaskId, () => {
  void loadRuleFromTaskConfig()
}, { immediate: true })

watch(autoTradeState, () => {
  syncFormFromState()
  syncRuntimeFromState()
})

watch(() => props.outcome, () => {
  void loadRuleFromTaskConfig()
})

function normalizeRuleSuffix(value: string): string {
  const normalized = value.trim().toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')
  return normalized || 'unknown'
}

function parseRules(config: Record<string, unknown>): AutoTradeRule[] {
  const autoTrade = config.auto_trade
  if (!autoTrade || typeof autoTrade !== 'object') return []
  const rules = (autoTrade as Record<string, unknown>).rules
  return Array.isArray(rules) ? rules as AutoTradeRule[] : []
}

function getConfigVersionFromState(): number {
  const raw = Number(autoTradeState.value?.config_version ?? 0)
  if (!Number.isFinite(raw) || raw < 0) return 0
  return Math.floor(raw)
}

function getConfigVersionFromConfig(config: Record<string, unknown>): number {
  const autoTrade = config.auto_trade
  if (!autoTrade || typeof autoTrade !== 'object') return 0
  const raw = Number((autoTrade as Record<string, unknown>).config_version ?? 0)
  if (!Number.isFinite(raw) || raw < 0) return 0
  return Math.floor(raw)
}

function getRuleRuntime(): RuleRuntime | null {
  const runtime = autoTradeState.value?.runtime
  if (!runtime) return null
  return runtime[ruleId.value] ?? null
}

function syncRuntimeFromState() {
  const runtime = getRuleRuntime()
  if (!runtime) return
  buyCount.value = Number(runtime.order_count ?? 0)
  totalSpent.value = Number(runtime.total_spent ?? 0)
  if (Number.isFinite(runtime.last_order_at)) {
    lastBuyAt.value = Number(runtime.last_order_at)
  }
}

function syncFormFromState() {
  const incomingVersion = getConfigVersionFromState()
  if (pendingVersion.value !== null && incomingVersion < pendingVersion.value) {
    return
  }
  appliedConfigVersion.value = Math.max(appliedConfigVersion.value, incomingVersion)
  if (pendingVersion.value !== null && incomingVersion >= pendingVersion.value) {
    pendingVersion.value = null
    pendingEnabled.value = null
  }

  const rules = autoTradeState.value?.rules
  if (!Array.isArray(rules)) return
  const found = rules.find((rule) => {
    if (!rule || typeof rule !== 'object') return false
    return (rule as Record<string, unknown>).id === ruleId.value
  })
  if (!found || typeof found !== 'object') {
    enabled.value = false
    return
  }

  const rule = found as Record<string, unknown>
  enabled.value = !!rule.enabled
  const config = rule.config
  if (config && typeof config === 'object') {
    const cfg = config as Record<string, unknown>
    const budgetValue = Number(cfg.budget_usdc)
    const intervalValue = Number(cfg.interval_seconds)
    const maxTotalValue = Number(cfg.max_total_budget)
    if (Number.isFinite(budgetValue) && budgetValue > 0) {
      budgetUsdc.value = budgetValue
    }
    if (Number.isFinite(intervalValue) && intervalValue >= 5) {
      intervalSeconds.value = intervalValue
    }
    if (Number.isFinite(maxTotalValue) && maxTotalValue >= 0) {
      maxTotalBudget.value = maxTotalValue
    }
  }
}

async function loadRuleFromTaskConfig() {
  if (!currentTaskId.value || !authStore.token) return
  try {
    const response = await taskService.getTaskConfig(currentTaskId.value, authStore.token)
    const configVersion = getConfigVersionFromConfig(response.config)
    appliedConfigVersion.value = Math.max(appliedConfigVersion.value, configVersion)
    if (pendingVersion.value !== null && configVersion >= pendingVersion.value) {
      pendingVersion.value = null
      pendingEnabled.value = null
    }
    const rules = parseRules(response.config)
    const found = rules.find((item) => item.id === ruleId.value)
    if (!found) {
      enabled.value = false
      return
    }

    enabled.value = !!found.enabled
    const config = found.config
    if (config && typeof config === 'object') {
      const cfg = config as Record<string, unknown>
      const budgetValue = Number(cfg.budget_usdc)
      const intervalValue = Number(cfg.interval_seconds)
      const maxTotalValue = Number(cfg.max_total_budget)
      if (Number.isFinite(budgetValue) && budgetValue > 0) {
        budgetUsdc.value = budgetValue
      }
      if (Number.isFinite(intervalValue) && intervalValue >= 5) {
        intervalSeconds.value = intervalValue
      }
      if (Number.isFinite(maxTotalValue) && maxTotalValue >= 0) {
        maxTotalBudget.value = maxTotalValue
      }
    }
  } catch {
    // ignore load failures for panel resilience
  }
}

function createRule(): AutoTradeRule {
  return {
    id: ruleId.value,
    type: 'periodic_buy',
    enabled: enabled.value,
    priority: 300,
    scope: {
      outcome: props.outcome,
    },
    cooldown_seconds: 0,
    config: {
      interval_seconds: Math.max(5, Math.floor(intervalSeconds.value || DEFAULT_INTERVAL)),
      budget_usdc: Math.max(1, Number(budgetUsdc.value || DEFAULT_BUDGET)),
      max_total_budget: Math.max(0, Number(maxTotalBudget.value || 0)),
      order_type: 'GTC',
    },
    risk: {
      max_total_budget: 0,
      max_order_count: 0,
      max_slippage: 0,
    },
  }
}

async function onRuleChange() {
  if (!currentTaskId.value) {
    toastStore.showWarning('请先创建并订阅任务')
    return
  }
  if (!authStore.token) {
    toastStore.showWarning('请先登录')
    return
  }

  const targetEnabled = enabled.value
  const optimisticVersion = Math.max(appliedConfigVersion.value, getConfigVersionFromState()) + 1
  pendingEnabled.value = targetEnabled
  pendingVersion.value = optimisticVersion

  requestPending.value = true
  try {
    const response = await taskService.getTaskConfig(currentTaskId.value, authStore.token)
    const config = response.config
    const rules = parseRules(config)
    const nextRule = createRule()
    const nextRules = rules.filter((item) => item.id !== ruleId.value)
    nextRules.push(nextRule)

    await taskService.updateTaskConfig(
      currentTaskId.value,
      {
        patch: {
          auto_trade: {
            enabled: true,
            rules: nextRules,
          },
        },
      },
      authStore.token,
    )
    await loadRuleFromTaskConfig()
  } catch (error) {
    pendingEnabled.value = null
    pendingVersion.value = null
    await loadRuleFromTaskConfig()
    toastStore.showError(error instanceof Error ? error.message : '更新定时买入配置失败')
  } finally {
    requestPending.value = false
  }
}

let tickTimer: ReturnType<typeof setInterval> | null = null

function startTimer() {
  if (tickTimer) return
  tickTimer = setInterval(tick, 1000)
}

function stopTimer() {
  if (tickTimer) {
    clearInterval(tickTimer)
    tickTimer = null
  }
  countdown.value = 0
}

watch(effectiveEnabled, (val) => {
  if (val) {
    lastBuyAt.value = 0
    startTimer()
  } else {
    stopTimer()
  }
}, { immediate: true })

onUnmounted(() => {
  stopTimer()
})

function tick() {
  if (!effectiveEnabled.value) {
    stopTimer()
    return
  }
  const nextRunAt = Number(getRuleRuntime()?.next_run_at ?? 0)
  if (nextRunAt > 0) {
    const remaining = Math.max(0, nextRunAt - Date.now() / 1000)
    countdown.value = Math.ceil(remaining)
    return
  }

  if (lastBuyAt.value > 0) {
    const elapsed = Date.now() / 1000 - lastBuyAt.value
    const remaining = Math.max(0, intervalSeconds.value - elapsed)
    countdown.value = Math.ceil(remaining)
  } else {
    countdown.value = 0
  }
}

function resetStats() {
  toastStore.showToast('统计由后端维护，重置功能待接入', 'info')
}

function formatCountdown(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
</script>

<template>
  <div class="border-t border-dashed border-base-300/50 pt-2 mt-2">
    <div class="flex items-center justify-between gap-2 text-xs">
      <span class="text-base-content/60 font-medium">定时买入</span>
      <div class="flex items-center gap-2">
        <button
          v-if="buyCount > 0"
          class="text-[10px] text-base-content/40 hover:text-base-content/70 underline"
          @click="resetStats"
        >
          重置
        </button>
        <label class="flex items-center gap-1">
          <input
            v-model="enabled"
            type="checkbox"
            class="toggle toggle-xs toggle-info"
            :disabled="requestPending || !currentTaskId"
            @change="onRuleChange"
          />
        </label>
      </div>
    </div>

    <div class="mt-1.5 grid grid-cols-3 gap-2 text-[11px]">
      <label>
        <div class="text-base-content/50">单笔金额</div>
        <input
          v-model.number="budgetUsdc"
          type="number"
          min="1"
          step="1"
          class="input input-bordered input-xs w-full"
          :disabled="requestPending || !currentTaskId"
          @change="onRuleChange"
        />
      </label>
      <label>
        <div class="text-base-content/50">间隔(秒)</div>
        <input
          v-model.number="intervalSeconds"
          type="number"
          min="5"
          step="5"
          class="input input-bordered input-xs w-full"
          :disabled="requestPending || !currentTaskId"
          @change="onRuleChange"
        />
      </label>
      <label>
        <div class="text-base-content/50">累计上限</div>
        <input
          v-model.number="maxTotalBudget"
          type="number"
          min="0"
          step="10"
          class="input input-bordered input-xs w-full"
          placeholder="0=无限"
          :disabled="requestPending || !currentTaskId"
          @change="onRuleChange"
        />
      </label>
    </div>

    <div
      v-if="effectiveEnabled || buyCount > 0"
      class="mt-1.5 flex items-center justify-between text-[10px] text-base-content/50"
    >
      <span v-if="effectiveEnabled">
        下次: {{ formatCountdown(countdown) }}
      </span>
      <span v-else>&nbsp;</span>
      <span>
        已买 {{ buyCount }}次 / ${{ totalSpent.toFixed(2) }}
        <template v-if="maxTotalBudget > 0">
          / 上限 ${{ maxTotalBudget }}
        </template>
      </span>
    </div>

    <div v-if="!currentTaskId" class="mt-1 text-[10px] text-amber-600/80">
      请先创建并订阅任务
    </div>
  </div>
</template>
