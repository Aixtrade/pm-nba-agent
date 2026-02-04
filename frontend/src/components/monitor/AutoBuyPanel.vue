<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useAuthStore, useGameStore } from '@/stores'
import { autoBuyService, type AutoBuyState } from '@/services/autoBuyService'

const BOTH_SIDE = '__BOTH__'

const authStore = useAuthStore()
const gameStore = useGameStore()

// 服务状态（响应式）
const serviceState = ref<AutoBuyState>(autoBuyService.getState())

// 订阅服务状态变化
let unsubscribe: (() => void) | null = null

onMounted(() => {
  unsubscribe = autoBuyService.onStateChange((state) => {
    serviceState.value = state
  })
})

onUnmounted(() => {
  unsubscribe?.()
})

// 计算属性
const polymarketInfo = computed(() => gameStore.polymarketInfo)

// 可用的 outcome 列表
const availableOutcomes = computed(() => {
  const info = polymarketInfo.value
  if (!info) return []
  return info.tokens.map(token => token.outcome)
})

// 当前选中的 outcome 是否有效
const isValidSide = computed(() => {
  if (serviceState.value.config.side === BOTH_SIDE) return true
  return availableOutcomes.value.includes(serviceState.value.config.side)
})

// 当市场信息变化时，如果当前选择无效，重置为双边
watch(availableOutcomes, (outcomes) => {
  if (outcomes.length > 0 && !isValidSide.value) {
    autoBuyService.setConfig({ side: BOTH_SIDE })
  }
})

const statusText = computed(() => {
  if (!serviceState.value.enabled) return '已关闭'
  if (serviceState.value.isOrdering) return '下单中...'
  return '等待信号'
})

const statusClass = computed(() => {
  if (!serviceState.value.enabled) return 'text-base-content/50'
  if (serviceState.value.isOrdering) return 'text-warning'
  return 'text-success'
})

// 最新信号显示
const latestSignalText = computed(() => {
  const sig = gameStore.latestStrategySignal
  if (!sig?.signal) return '--'
  const type = sig.signal.type
  const labels: Record<string, string> = { BUY: '买入', SELL: '卖出', HOLD: '等待' }
  return labels[type] ?? '--'
})

const latestSignalClass = computed(() => {
  const type = gameStore.latestStrategySignal?.signal?.type
  if (type === 'BUY') return 'text-success'
  if (type === 'SELL') return 'text-error'
  return 'text-base-content/50'
})

// 格式化时间
function formatTime(date: Date | null): string {
  if (!date) return '--'
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// 统计是否有数据
const hasStats = computed(() => {
  return Object.keys(serviceState.value.stats).length > 0
})

// 格式化统计显示
const statsDisplay = computed(() => {
  const entries = Object.entries(serviceState.value.stats)
  if (entries.length === 0) return '--'
  return entries
    .map(([outcome, stat]) => `${outcome} x${stat.count} ($${stat.amount.toFixed(0)})`)
    .join(', ')
})

// 操作方法
function toggleEnabled(event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  autoBuyService.setEnabled(checked)
}

function selectSide(side: string) {
  if (!serviceState.value.enabled) {
    autoBuyService.setConfig({ side })
  }
}

function updateAmount(event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  if (value > 0) {
    autoBuyService.setConfig({ amount: value })
  }
}

function toggleRoundSize(event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  autoBuyService.setConfig({ roundSize: checked })
}

function resetStats() {
  autoBuyService.resetStats()
}

// 获取按钮样式
function getSideButtonClass(side: string): string {
  if (serviceState.value.config.side !== side) return 'btn-ghost'
  if (side === BOTH_SIDE) return 'btn-primary'
  const index = availableOutcomes.value.indexOf(side)
  return index === 0 ? 'btn-success' : 'btn-error'
}
</script>

<template>
  <div class="card glass-card ring-1 ring-base-content/30 ring-offset-2 ring-offset-base-100">
    <div class="card-body">
      <!-- 标题与开关 -->
      <div class="flex items-center justify-between">
        <h3 class="card-title text-base">自动买入</h3>
        <input
          type="checkbox"
          class="toggle toggle-success"
          :checked="serviceState.enabled"
          :disabled="!polymarketInfo"
          @change="toggleEnabled"
        />
      </div>

      <!-- 配置区域 -->
      <div class="mt-4 space-y-3">
        <!-- 下单方向 -->
        <div class="flex items-center gap-3">
          <span class="text-sm text-base-content/70 w-16">方向</span>
          <div class="join">
            <!-- 第一个 outcome -->
            <button
              v-if="availableOutcomes[0]"
              class="btn btn-sm join-item"
              :class="getSideButtonClass(availableOutcomes[0])"
              :disabled="serviceState.enabled"
              @click="selectSide(availableOutcomes[0])"
            >
              {{ availableOutcomes[0] }}
            </button>
            <!-- 双边按钮（中间） -->
            <button
              class="btn btn-sm join-item"
              :class="getSideButtonClass(BOTH_SIDE)"
              :disabled="serviceState.enabled"
              @click="selectSide(BOTH_SIDE)"
            >
              双边
            </button>
            <!-- 第二个 outcome -->
            <button
              v-if="availableOutcomes[1]"
              class="btn btn-sm join-item"
              :class="getSideButtonClass(availableOutcomes[1])"
              :disabled="serviceState.enabled"
              @click="selectSide(availableOutcomes[1])"
            >
              {{ availableOutcomes[1] }}
            </button>
          </div>
        </div>

        <!-- 下单金额 -->
        <div class="flex items-center gap-3">
          <span class="text-sm text-base-content/70 w-16">金额</span>
          <input
            type="number"
            min="1"
            step="1"
            class="input input-bordered input-sm w-24"
            :value="serviceState.config.amount"
            :disabled="serviceState.enabled"
            @change="updateAmount"
          />
          <span class="text-sm text-base-content/60">USDC</span>
        </div>

        <!-- Size 取整 -->
        <div class="flex items-center gap-3">
          <span class="text-sm text-base-content/70 w-16">取整</span>
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              class="checkbox checkbox-sm"
              :checked="serviceState.config.roundSize"
              :disabled="serviceState.enabled"
              @change="toggleRoundSize"
            />
            <span class="text-sm text-base-content/60">Size 取整数</span>
          </label>
        </div>
      </div>

      <!-- 状态区域 -->
      <div class="mt-4 rounded-lg border border-base-200/70 px-3 py-2 ring-1 ring-base-content/20">
        <div class="grid grid-cols-2 gap-2 text-xs">
          <!-- 状态 -->
          <div>
            <div class="text-base-content/50">状态</div>
            <div class="font-medium" :class="statusClass">{{ statusText }}</div>
          </div>

          <!-- 最新信号 -->
          <div>
            <div class="text-base-content/50">最新信号</div>
            <div class="font-medium" :class="latestSignalClass">
              {{ latestSignalText }}
            </div>
          </div>

          <!-- 上次下单 -->
          <div>
            <div class="text-base-content/50">上次下单</div>
            <div class="font-medium text-base-content">{{ formatTime(serviceState.lastOrderTime) }}</div>
          </div>

          <!-- 累计统计 -->
          <div>
            <div class="text-base-content/50">累计</div>
            <div class="font-medium text-base-content text-[11px]">
              {{ statsDisplay }}
            </div>
          </div>
        </div>

        <!-- 重置按钮 -->
        <div v-if="hasStats" class="mt-2 text-right">
          <button
            class="btn btn-ghost btn-xs text-base-content/50"
            @click="resetStats"
          >
            重置统计
          </button>
        </div>
      </div>

      <!-- 未连接提示 -->
      <div v-if="!polymarketInfo" class="mt-3 text-xs text-amber-600/80">
        请先连接到 Polymarket 比赛
      </div>

      <!-- 未登录提示 -->
      <div v-else-if="!authStore.isAuthenticated" class="mt-3 text-xs text-amber-600/80">
        请先登录
      </div>
    </div>
  </div>
</template>
