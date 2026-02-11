<script setup lang="ts">
import { ref, watch } from 'vue'
import { useTaskStore, useToastStore } from '@/stores'
import { submitOrder, requestPositionRefresh, canPlaceOrder } from '@/composables/usePolymarketOrder'

const props = defineProps<{
  tokenId: string
  outcome: string
  bestAsk: number | null
}>()

const AUTO_BUY_CONFIG_KEY = 'POLYMARKET_LOCAL_AUTO_BUY_CONFIG_V1'
const DEFAULT_TRIGGER_PRICE = 0.45
const DEFAULT_BUDGET = 10
const DEFAULT_COOLDOWN = 60

const taskStore = useTaskStore()
const toastStore = useToastStore()

const enabled = ref(false)
const triggerPrice = ref(DEFAULT_TRIGGER_PRICE.toFixed(3))
const budget = ref(DEFAULT_BUDGET.toString())
const cooldown = ref(DEFAULT_COOLDOWN.toString())
const submitting = ref(false)
const lastBuyAt = ref(0)

// --- localStorage persistence (full-map, backward compat) ---

interface StoredRule {
  enabled?: boolean
  trigger?: string
  budget?: string
  cooldown?: string
}

function loadConfig() {
  try {
    const raw = localStorage.getItem(AUTO_BUY_CONFIG_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw) as { rules?: Record<string, StoredRule> }
    const rule = parsed.rules?.[props.outcome]
    if (!rule) return
    enabled.value = !!rule.enabled
    if (rule.trigger !== undefined) triggerPrice.value = rule.trigger
    if (rule.budget !== undefined) budget.value = rule.budget
    if (rule.cooldown !== undefined) cooldown.value = rule.cooldown
  } catch {
    // ignore
  }
}

function saveConfig() {
  try {
    const raw = localStorage.getItem(AUTO_BUY_CONFIG_KEY)
    const parsed = raw ? (JSON.parse(raw) as { rules?: Record<string, StoredRule> }) : {}
    const rules = parsed.rules ?? {}
    rules[props.outcome] = {
      enabled: enabled.value,
      trigger: triggerPrice.value,
      budget: budget.value,
      cooldown: cooldown.value,
    }
    localStorage.setItem(AUTO_BUY_CONFIG_KEY, JSON.stringify({ rules }))
  } catch {
    // ignore
  }
}

loadConfig()

// If triggerPrice was never set (fresh outcome), seed from bestAsk
if (triggerPrice.value === DEFAULT_TRIGGER_PRICE.toFixed(3) && props.bestAsk !== null) {
  triggerPrice.value = props.bestAsk.toFixed(3)
}

function onRuleChange() {
  saveConfig()
  void runAutoBuy()
}

function parsePositiveNumber(value: string): number | null {
  const num = Number(value)
  if (Number.isNaN(num) || num <= 0) return null
  return num
}

// --- auto-buy sweep on bestAsk change ---

watch(() => props.bestAsk, () => {
  void runAutoBuy()
})

async function runAutoBuy() {
  if (!enabled.value) return
  if (submitting.value) return

  const check = canPlaceOrder()
  if (!check.ok) return

  const ask = props.bestAsk
  if (ask === null || Number.isNaN(ask) || ask <= 0 || ask >= 1) return

  const trigger = parsePositiveNumber(triggerPrice.value)
  const budgetVal = parsePositiveNumber(budget.value)
  const cooldownVal = parsePositiveNumber(cooldown.value) ?? DEFAULT_COOLDOWN
  if (trigger === null || budgetVal === null) return
  if (trigger >= 1) return
  if (ask > trigger) return

  const now = Date.now()
  if (now - lastBuyAt.value < cooldownVal * 1000) return

  const size = Number((budgetVal / ask).toFixed(2))
  if (!size || Number.isNaN(size) || size <= 0) return

  submitting.value = true
  try {
    lastBuyAt.value = now
    await submitOrder({
      tokenId: props.tokenId,
      side: 'BUY',
      price: ask,
      size,
    })
    toastStore.showToast(`触价买入成功 ${props.outcome} @ ${ask.toFixed(3)} (${size})`, 'success')
    if (taskStore.currentTaskId) {
      void requestPositionRefresh()
    }
  } catch (error) {
    toastStore.showToast(error instanceof Error ? error.message : '触价买入失败', 'error')
  } finally {
    submitting.value = false
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
          @change="onRuleChange"
        />
      </label>
    </div>
  </div>
</template>
