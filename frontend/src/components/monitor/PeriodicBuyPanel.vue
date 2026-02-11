<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import { useTaskStore, useToastStore } from '@/stores'
import { submitOrder, canPlaceOrder, requestPositionRefresh } from '@/composables/usePolymarketOrder'

const props = defineProps<{
  tokenId: string
  outcome: string
  bestAsk: number | null
}>()

const STORAGE_KEY = 'POLYMARKET_PERIODIC_BUY_CONFIG_V1'
const DEFAULT_BUDGET = 10
const DEFAULT_INTERVAL = 120
const DEFAULT_MAX_TOTAL = 0

const taskStore = useTaskStore()
const toastStore = useToastStore()

const enabled = ref(false)
const budgetUsdc = ref(DEFAULT_BUDGET)
const intervalSeconds = ref(DEFAULT_INTERVAL)
const maxTotalBudget = ref(DEFAULT_MAX_TOTAL)

const buyCount = ref(0)
const totalSpent = ref(0)
const lastBuyAt = ref(0)
const submitting = ref(false)
const countdown = ref(0)

// --- localStorage persistence (full-map, backward compat) ---

interface StoredRule {
  enabled: boolean
  budgetUsdc: number
  intervalSeconds: number
  maxTotalBudget: number
}

interface StoredStats {
  buyCount: number
  totalSpent: number
  lastBuyAt: number
}

function loadConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw) as {
      rules?: Record<string, StoredRule>
      stats?: Record<string, StoredStats>
    }
    const rule = parsed.rules?.[props.outcome]
    if (rule) {
      enabled.value = false // never auto-resume on reload
      budgetUsdc.value = rule.budgetUsdc
      intervalSeconds.value = rule.intervalSeconds
      maxTotalBudget.value = rule.maxTotalBudget
    }
    const stats = parsed.stats?.[props.outcome]
    if (stats) {
      buyCount.value = stats.buyCount
      totalSpent.value = stats.totalSpent
      lastBuyAt.value = stats.lastBuyAt
    }
  } catch {
    // ignore
  }
}

function saveConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const parsed = raw
      ? (JSON.parse(raw) as { rules?: Record<string, StoredRule>; stats?: Record<string, StoredStats> })
      : {}
    const rules = parsed.rules ?? {}
    const stats = parsed.stats ?? {}
    rules[props.outcome] = {
      enabled: enabled.value,
      budgetUsdc: budgetUsdc.value,
      intervalSeconds: intervalSeconds.value,
      maxTotalBudget: maxTotalBudget.value,
    }
    stats[props.outcome] = {
      buyCount: buyCount.value,
      totalSpent: totalSpent.value,
      lastBuyAt: lastBuyAt.value,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ rules, stats }))
  } catch {
    // ignore
  }
}

loadConfig()

function onRuleChange() {
  saveConfig()
}

// --- Timer (per-instance) ---

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

watch(enabled, (val) => {
  if (val) {
    lastBuyAt.value = 0
    startTimer()
  } else {
    stopTimer()
  }
  saveConfig()
}, { immediate: true })

onUnmounted(() => {
  stopTimer()
})

function tick() {
  if (!enabled.value) {
    stopTimer()
    return
  }
  const now = Date.now()
  const elapsed = (now - lastBuyAt.value) / 1000
  const remaining = Math.max(0, intervalSeconds.value - elapsed)
  countdown.value = Math.ceil(remaining)

  if (remaining <= 0) {
    void runPeriodicBuy()
  }
}

async function runPeriodicBuy() {
  if (!enabled.value) return
  if (submitting.value) return

  const check = canPlaceOrder()
  if (!check.ok) return

  const ask = props.bestAsk
  if (ask === null || Number.isNaN(ask) || ask <= 0 || ask >= 1) return

  // Check max total budget cap
  if (maxTotalBudget.value > 0 && totalSpent.value >= maxTotalBudget.value) {
    enabled.value = false
    saveConfig()
    toastStore.showToast(`${props.outcome} 定时买入已达上限 $${maxTotalBudget.value}，已自动停止`, 'warning')
    return
  }

  // Calculate effective budget (don't exceed remaining cap)
  let effectiveBudget = budgetUsdc.value
  if (maxTotalBudget.value > 0) {
    const remaining = maxTotalBudget.value - totalSpent.value
    effectiveBudget = Math.min(effectiveBudget, remaining)
  }

  const size = Number((effectiveBudget / ask).toFixed(2))
  if (!size || Number.isNaN(size) || size <= 0) return

  submitting.value = true
  lastBuyAt.value = Date.now()
  try {
    await submitOrder({
      tokenId: props.tokenId,
      side: 'BUY',
      price: ask,
      size,
    })
    buyCount.value++
    totalSpent.value += effectiveBudget
    saveConfig()
    toastStore.showToast(`定时买入成功 ${props.outcome} @ ${ask.toFixed(3)} (${size})`, 'success')
    if (taskStore.currentTaskId) {
      void requestPositionRefresh()
    }
  } catch (error) {
    toastStore.showToast(error instanceof Error ? error.message : '定时买入失败', 'error')
  } finally {
    submitting.value = false
  }
}

function resetStats() {
  buyCount.value = 0
  totalSpent.value = 0
  lastBuyAt.value = 0
  saveConfig()
  toastStore.showToast(`${props.outcome} 定时买入统计已重置`, 'success')
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
          @change="onRuleChange"
        />
      </label>
    </div>

    <div
      v-if="enabled || buyCount > 0"
      class="mt-1.5 flex items-center justify-between text-[10px] text-base-content/50"
    >
      <span v-if="enabled">
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
  </div>
</template>
