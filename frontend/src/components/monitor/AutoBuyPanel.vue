<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAuthStore, useGameStore, useTaskStore, useToastStore } from '@/stores'
import { taskService } from '@/services/taskService'

const BOTH_SIDE = '__BOTH__'
const STRATEGY_ID = 'merge_long'
const POLYMARKET_PRIVATE_KEY = 'POLYMARKET_PRIVATE_KEY'
const POLYMARKET_PROXY_ADDRESS = 'POLYMARKET_PROXY_ADDRESS'

const authStore = useAuthStore()
const gameStore = useGameStore()
const taskStore = useTaskStore()
const toastStore = useToastStore()

const requestPending = ref(false)
const formSide = ref(BOTH_SIDE)
const formAmount = ref(10)
const formRoundSize = ref(false)
const formEnabled = ref(false)

const polymarketInfo = computed(() => gameStore.polymarketInfo)
const autoBuyState = computed(() => gameStore.autoBuyState)
const currentTaskId = computed(() => taskStore.currentTaskId)
const effectiveEnabled = computed(() => autoBuyState.value?.enabled ?? formEnabled.value)
const effectiveIsOrdering = computed(() => autoBuyState.value?.is_ordering ?? false)

const availableOutcomes = computed(() => {
  const info = polymarketInfo.value
  if (!info) return []
  return info.tokens.map((token) => token.outcome)
})

const statusText = computed(() => {
  if (!effectiveEnabled.value) return '已关闭'
  if (effectiveIsOrdering.value) return '下单中...'
  return '等待信号'
})

const statusClass = computed(() => {
  if (!effectiveEnabled.value) return 'text-base-content/50'
  if (effectiveIsOrdering.value) return 'text-warning'
  return 'text-success'
})

const latestSignalText = computed(() => {
  const sig = gameStore.getLatestSignalForStrategy(STRATEGY_ID)
  if (!sig?.signal) return '--'
  const type = sig.signal.type
  const labels: Record<string, string> = { BUY: '买入', SELL: '卖出', HOLD: '等待' }
  return labels[type] ?? '--'
})

const latestSignalClass = computed(() => {
  const type = gameStore.getLatestSignalForStrategy(STRATEGY_ID)?.signal?.type
  if (type === 'BUY') return 'text-success'
  if (type === 'SELL') return 'text-error'
  return 'text-base-content/50'
})

const latestOrderExecution = computed(() => {
  const execution = gameStore.getLatestSignalForStrategy(STRATEGY_ID)?.execution
  if (!execution || execution.source !== 'task_auto_buy') return null
  return execution
})

const latestOrderExecutionText = computed(() => {
  const execution = latestOrderExecution.value
  if (!execution) return '--'
  if (execution.success) {
    const count = Array.isArray(execution.orders) ? execution.orders.length : 0
    return `成功 (${count} 笔)`
  }
  return execution.error || '失败'
})

const latestOrderExecutionClass = computed(() => {
  const execution = latestOrderExecution.value
  if (!execution) return 'text-base-content/50'
  return execution.success ? 'text-success' : 'text-error'
})

const hasStats = computed(() => {
  return Object.keys(autoBuyState.value?.stats ?? {}).length > 0
})

const statsDisplay = computed(() => {
  const stats = autoBuyState.value?.stats ?? {}
  const entries = Object.entries(stats)
  if (entries.length === 0) return '--'
  return entries
    .map(([outcome, stat]) => `${outcome} x${stat.count} ($${stat.amount.toFixed(0)})`)
    .join(', ')
})

watch(autoBuyState, (next) => {
  if (!next) return

  formEnabled.value = !!next.enabled
  const defaultCfg = (next.default ?? {}) as Record<string, unknown>
  if (typeof defaultCfg.amount === 'number') {
    formAmount.value = defaultCfg.amount
  }
  if (typeof defaultCfg.round_size === 'boolean') {
    formRoundSize.value = defaultCfg.round_size
  }

  const rule = next.strategy_rules?.[STRATEGY_ID] as Record<string, unknown> | undefined
  if (!rule) return

  const side = typeof rule.side === 'string' ? rule.side : BOTH_SIDE
  const amount = typeof rule.amount === 'number' ? rule.amount : formAmount.value
  const roundSize = typeof rule.round_size === 'boolean' ? rule.round_size : formRoundSize.value

  formSide.value = side
  formAmount.value = amount
  formRoundSize.value = roundSize
}, { immediate: true })

watch(availableOutcomes, (outcomes) => {
  if (formSide.value === BOTH_SIDE) return
  if (outcomes.includes(formSide.value)) return
  formSide.value = BOTH_SIDE
  void pushConfigPatch()
})

watch(currentTaskId, () => {
  void loadTaskConfig()
}, { immediate: true })

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

function getSideButtonClass(side: string): string {
  if (formSide.value !== side) return 'btn-ghost'
  if (side === BOTH_SIDE) return 'btn-primary'
  const index = availableOutcomes.value.indexOf(side)
  return index === 0 ? 'btn-success' : 'btn-error'
}

async function loadTaskConfig() {
  if (!currentTaskId.value || !authStore.token) return

  try {
    const response = await taskService.getTaskConfig(currentTaskId.value, authStore.token)
    const config = (response.config ?? {}) as Record<string, unknown>
    const autoBuy = (config.auto_buy ?? {}) as Record<string, unknown>
    const defaultCfg = (autoBuy.default ?? {}) as Record<string, unknown>
    const strategyRules = (autoBuy.strategy_rules ?? {}) as Record<string, unknown>
    const rule = (strategyRules[STRATEGY_ID] ?? {}) as Record<string, unknown>

    if (typeof autoBuy.enabled === 'boolean') {
      formEnabled.value = autoBuy.enabled
    }
    if (typeof defaultCfg.amount === 'number') {
      formAmount.value = defaultCfg.amount
    }
    if (typeof defaultCfg.round_size === 'boolean') {
      formRoundSize.value = defaultCfg.round_size
    }
    if (typeof rule.side === 'string') {
      formSide.value = rule.side
    }
    if (typeof rule.amount === 'number') {
      formAmount.value = rule.amount
    }
    if (typeof rule.round_size === 'boolean') {
      formRoundSize.value = rule.round_size
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : '加载自动买入配置失败'
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

    await taskService.updateTaskConfig(
      currentTaskId.value,
      {
        patch: {
          private_key: privateKey,
          proxy_address: proxyAddress,
          auto_buy: {
            enabled: formEnabled.value,
            strategy_rules: {
              [STRATEGY_ID]: {
                enabled: formEnabled.value,
                side: formSide.value,
                amount: formAmount.value,
                round_size: formRoundSize.value,
                signal_types: ['BUY'],
              },
            },
          },
        },
      },
      authStore.token,
    )
  } catch (error) {
    const message = error instanceof Error ? error.message : '更新自动买入配置失败'
    toastStore.showError(message)
  } finally {
    requestPending.value = false
  }
}

function toggleEnabled(event: Event) {
  formEnabled.value = (event.target as HTMLInputElement).checked
  void pushConfigPatch()
}

function selectSide(side: string) {
  formSide.value = side
  void pushConfigPatch()
}

function updateAmount(event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  if (value <= 0) return
  formAmount.value = value
  void pushConfigPatch()
}

function toggleRoundSize(event: Event) {
  formRoundSize.value = (event.target as HTMLInputElement).checked
  void pushConfigPatch()
}

function resetStats() {
  toastStore.showInfo('统计由后台维护，重置功能待接入')
}
</script>

<template>
  <div class="card glass-card ring-1 ring-base-content/30 ring-offset-2 ring-offset-base-100">
    <div class="card-body">
      <div class="flex items-center justify-between">
        <h3 class="card-title text-base">自动买入</h3>
        <input
          type="checkbox"
          class="toggle toggle-success"
          :checked="formEnabled"
          :disabled="!polymarketInfo || !currentTaskId || requestPending"
          @change="toggleEnabled"
        />
      </div>

      <div class="mt-4 space-y-3">
        <div class="flex items-center gap-3">
          <span class="text-sm text-base-content/70 w-16">方向</span>
          <div class="join">
            <button
              v-if="availableOutcomes[0]"
              class="btn btn-sm join-item"
              :class="getSideButtonClass(availableOutcomes[0])"
              :disabled="requestPending || !currentTaskId"
              @click="selectSide(availableOutcomes[0])"
            >
              {{ availableOutcomes[0] }}
            </button>
            <button
              class="btn btn-sm join-item"
              :class="getSideButtonClass(BOTH_SIDE)"
              :disabled="requestPending || !currentTaskId"
              @click="selectSide(BOTH_SIDE)"
            >
              双边
            </button>
            <button
              v-if="availableOutcomes[1]"
              class="btn btn-sm join-item"
              :class="getSideButtonClass(availableOutcomes[1])"
              :disabled="requestPending || !currentTaskId"
              @click="selectSide(availableOutcomes[1])"
            >
              {{ availableOutcomes[1] }}
            </button>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <span class="text-sm text-base-content/70 w-16">金额</span>
          <input
            type="number"
            min="1"
            step="1"
            class="input input-bordered input-sm w-24"
            :value="formAmount"
            :disabled="requestPending || !currentTaskId"
            @change="updateAmount"
          />
          <span class="text-sm text-base-content/60">USDC</span>
        </div>

        <div class="flex items-center gap-3">
          <span class="text-sm text-base-content/70 w-16">取整</span>
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              class="checkbox checkbox-sm"
              :checked="formRoundSize"
              :disabled="requestPending || !currentTaskId"
              @change="toggleRoundSize"
            />
            <span class="text-sm text-base-content/60">Size 取整数</span>
          </label>
        </div>
      </div>

      <div class="mt-4 rounded-lg border border-base-200/70 px-3 py-2 ring-1 ring-base-content/20">
        <div class="grid grid-cols-2 gap-2 text-xs">
          <div>
            <div class="text-base-content/50">状态</div>
            <div class="font-medium" :class="statusClass">{{ statusText }}</div>
          </div>

          <div>
            <div class="text-base-content/50">最新信号</div>
            <div class="font-medium" :class="latestSignalClass">
              {{ latestSignalText }}
            </div>
          </div>

          <div>
            <div class="text-base-content/50">上次下单</div>
            <div class="font-medium text-base-content">{{ formatTime(autoBuyState?.last_order_time) }}</div>
          </div>

          <div>
            <div class="text-base-content/50">累计</div>
            <div class="font-medium text-base-content text-[11px]">
              {{ statsDisplay }}
            </div>
          </div>

          <div class="col-span-2">
            <div class="text-base-content/50">下单结果</div>
            <div class="font-medium" :class="latestOrderExecutionClass">
              {{ latestOrderExecutionText }}
            </div>
          </div>
        </div>

        <div v-if="hasStats" class="mt-2 text-right">
          <button
            class="btn btn-ghost btn-xs text-base-content/50"
            @click="resetStats"
          >
            重置统计
          </button>
        </div>
      </div>

      <div v-if="!currentTaskId" class="mt-3 text-xs text-amber-600/80">
        请先创建并订阅任务
      </div>
      <div v-else-if="!polymarketInfo" class="mt-3 text-xs text-amber-600/80">
        请先连接到 Polymarket 比赛
      </div>
      <div v-else-if="!authStore.isAuthenticated" class="mt-3 text-xs text-amber-600/80">
        请先登录
      </div>
    </div>
  </div>
</template>
