<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAuthStore, useGameStore, useTaskStore, useToastStore } from '@/stores'
import { taskService } from '@/services/taskService'

const props = defineProps<{
  tokenId: string
  outcome: string
  bestAsk: number | null
}>()

const DEFAULT_TRIGGER_PRICE = 0.45
const DEFAULT_BUDGET = 10
const DEFAULT_COOLDOWN = 60

const authStore = useAuthStore()
const gameStore = useGameStore()
const taskStore = useTaskStore()
const toastStore = useToastStore()

const enabled = ref(false)
const triggerPrice = ref(DEFAULT_TRIGGER_PRICE.toFixed(3))
const budget = ref(DEFAULT_BUDGET.toString())
const cooldown = ref(DEFAULT_COOLDOWN.toString())
const requestPending = ref(false)

const autoTradeState = computed(() => gameStore.autoTradeState)
const currentTaskId = computed(() => taskStore.currentTaskId)
const ruleId = computed(() => `condition_buy_${normalizeRuleSuffix(props.outcome)}`)
const runtimeState = computed(() => {
  const runtime = autoTradeState.value?.runtime
  if (!runtime) return null
  return runtime[ruleId.value] ?? null
})
const backendBuyCount = computed(() => Number(runtimeState.value?.order_count ?? 0))
const backendTotalSpent = computed(() => Number(runtimeState.value?.total_spent ?? 0))

// --- localStorage persistence (full-map, backward compat) ---

interface AutoTradeRule {
  id?: string
  type?: string
  enabled?: boolean
  priority?: number
  scope?: Record<string, unknown>
  cooldown_seconds?: number
  config?: Record<string, unknown>
  risk?: Record<string, unknown>
}

watch(currentTaskId, () => {
  void loadRuleFromTaskConfig()
}, { immediate: true })

watch(autoTradeState, () => {
  syncFormFromState()
})

watch(() => props.outcome, () => {
  void loadRuleFromTaskConfig()
})

function normalizeRuleSuffix(value: string): string {
  const normalized = value.trim().toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')
  return normalized || 'unknown'
}

function getNumeric(input: string, fallback: number): number {
  const value = Number(input)
  if (!Number.isFinite(value)) return fallback
  return value
}

function parseRules(config: Record<string, unknown>): AutoTradeRule[] {
  const autoTrade = config.auto_trade
  if (!autoTrade || typeof autoTrade !== 'object') return []
  const rules = (autoTrade as Record<string, unknown>).rules
  return Array.isArray(rules) ? rules as AutoTradeRule[] : []
}

function createRule(): AutoTradeRule {
  const trigger = Math.min(0.999, Math.max(0.001, getNumeric(triggerPrice.value, DEFAULT_TRIGGER_PRICE)))
  const budgetValue = Math.max(1, getNumeric(budget.value, DEFAULT_BUDGET))
  const cooldownValue = Math.max(1, getNumeric(cooldown.value, DEFAULT_COOLDOWN))

  return {
    id: ruleId.value,
    type: 'condition_buy',
    enabled: enabled.value,
    priority: 200,
    scope: {
      outcome: props.outcome,
    },
    cooldown_seconds: cooldownValue,
    config: {
      trigger_price_lte: trigger,
      budget_usdc: budgetValue,
      order_type: 'GTC',
    },
    risk: {
      max_total_budget: 0,
      max_order_count: 0,
      max_slippage: 0,
    },
  }
}

function syncFormFromState() {
  const rules = autoTradeState.value?.rules
  if (!Array.isArray(rules)) return
  const found = rules.find((rule) => {
    if (!rule || typeof rule !== 'object') return false
    return (rule as Record<string, unknown>).id === ruleId.value
  })
  if (!found || typeof found !== 'object') return

  const rule = found as Record<string, unknown>
  enabled.value = !!rule.enabled
  const cooldownValue = Number(rule.cooldown_seconds)
  if (Number.isFinite(cooldownValue) && cooldownValue > 0) {
    cooldown.value = String(cooldownValue)
  }
  const config = rule.config
  if (config && typeof config === 'object') {
    const trigger = Number((config as Record<string, unknown>).trigger_price_lte)
    const budgetValue = Number((config as Record<string, unknown>).budget_usdc)
    if (Number.isFinite(trigger) && trigger > 0) {
      triggerPrice.value = trigger.toFixed(3)
    }
    if (Number.isFinite(budgetValue) && budgetValue > 0) {
      budget.value = String(budgetValue)
    }
  }
}

async function loadRuleFromTaskConfig() {
  if (!currentTaskId.value || !authStore.token) return
  try {
    const response = await taskService.getTaskConfig(currentTaskId.value, authStore.token)
    const rules = parseRules(response.config)
    const found = rules.find((item) => item.id === ruleId.value)
    if (!found) {
      if (triggerPrice.value === DEFAULT_TRIGGER_PRICE.toFixed(3) && props.bestAsk !== null) {
        triggerPrice.value = props.bestAsk.toFixed(3)
      }
      return
    }

    enabled.value = !!found.enabled
    const cooldownValue = Number(found.cooldown_seconds)
    if (Number.isFinite(cooldownValue) && cooldownValue > 0) {
      cooldown.value = String(cooldownValue)
    }

    const config = found.config
    if (config && typeof config === 'object') {
      const cfg = config as Record<string, unknown>
      const trigger = Number(cfg.trigger_price_lte)
      const budgetValue = Number(cfg.budget_usdc)
      if (Number.isFinite(trigger) && trigger > 0) {
        triggerPrice.value = trigger.toFixed(3)
      }
      if (Number.isFinite(budgetValue) && budgetValue > 0) {
        budget.value = String(budgetValue)
      }
    }
  } catch {
    // ignore load failures for panel resilience
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
  } catch (error) {
    toastStore.showError(error instanceof Error ? error.message : '更新触价买入配置失败')
  } finally {
    requestPending.value = false
  }
}
</script>

<template>
  <div class="border-t border-dashed border-base-300/50 pt-2 mt-2">
    <div class="flex items-center justify-between gap-2 text-xs">
      <span class="text-base-content/60 font-medium">触价买入</span>
      <label class="flex items-center gap-1">
        <input
          v-model="enabled"
          type="checkbox"
          class="toggle toggle-xs toggle-success"
          :disabled="requestPending || !currentTaskId"
          @change="onRuleChange"
        />
      </label>
    </div>
    <div class="mt-1.5 grid grid-cols-3 gap-2 text-[11px]">
      <label>
        <div class="text-base-content/50">触发价 ≤</div>
        <input
          v-model="triggerPrice"
          type="number"
          min="0"
          max="1"
          step="0.001"
          class="input input-bordered input-xs w-full"
          :disabled="requestPending || !currentTaskId"
          @change="onRuleChange"
        />
      </label>
      <label>
        <div class="text-base-content/50">单笔金额</div>
        <input
          v-model="budget"
          type="number"
          min="1"
          step="1"
          class="input input-bordered input-xs w-full"
          :disabled="requestPending || !currentTaskId"
          @change="onRuleChange"
        />
      </label>
      <label>
        <div class="text-base-content/50">冷却(秒)</div>
        <input
          v-model="cooldown"
          type="number"
          min="1"
          step="1"
          class="input input-bordered input-xs w-full"
          :disabled="requestPending || !currentTaskId"
          @change="onRuleChange"
        />
      </label>
    </div>

    <div v-if="enabled || backendBuyCount > 0" class="mt-1.5 flex items-center justify-between text-[10px] text-base-content/50">
      <span>后端执行中</span>
      <span>已买 {{ backendBuyCount }}次 / ${{ backendTotalSpent.toFixed(2) }}</span>
    </div>

    <div v-if="!currentTaskId" class="mt-1 text-[10px] text-amber-600/80">
      请先创建并订阅任务
    </div>
  </div>
</template>
