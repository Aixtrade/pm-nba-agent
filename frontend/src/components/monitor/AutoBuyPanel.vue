<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useAuthStore, useGameStore, useToastStore } from '@/stores'
import type { StrategySignalEventData } from '@/types/sse'

const BOTH_SIDE = '__BOTH__'

const authStore = useAuthStore()
const gameStore = useGameStore()
const toastStore = useToastStore()
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
const ORDER_TYPE = 'GTC'
const POLYMARKET_PRIVATE_KEY = 'POLYMARKET_PRIVATE_KEY'
const POLYMARKET_PROXY_ADDRESS = 'POLYMARKET_PROXY_ADDRESS'

// localStorage 持久化键
const STORAGE_PREFIX = 'AUTO_BUY_'
const getStorageKey = (key: string) => `${STORAGE_PREFIX}${key}`

// 从 localStorage 读取配置
function getStoredValue<T>(key: string, defaultValue: T): T {
  if (typeof window === 'undefined') return defaultValue
  const stored = localStorage.getItem(getStorageKey(key))
  if (stored === null) return defaultValue
  try {
    return JSON.parse(stored) as T
  } catch {
    return defaultValue
  }
}

function setStoredValue<T>(key: string, value: T) {
  if (typeof window === 'undefined') return
  localStorage.setItem(getStorageKey(key), JSON.stringify(value))
}

// 控制状态
const autoBuyEnabled = ref(false)
const orderSide = ref<string>(getStoredValue('SIDE', BOTH_SIDE)) // outcome 名称或 BOTH_SIDE
const orderAmount = ref(getStoredValue('AMOUNT', 10))

// 运行状态
const lastOrderTime = ref<Date | null>(null)
const lastSignalTimestamp = ref<number | null>(null) // 用于去重
// 使用 outcome 名称作为 key 的统计
const orderStats = reactive<Record<string, { count: number; amount: number }>>({})
const isOrdering = ref(false)

// 计算属性
const polymarketInfo = computed(() => gameStore.polymarketInfo)

// 可用的 outcome 列表（从市场信息中提取）
const availableOutcomes = computed(() => {
  const info = polymarketInfo.value
  if (!info) return []
  return info.tokens.map(token => token.outcome)
})

// 当前选中的 outcome 是否有效
const isValidSide = computed(() => {
  if (orderSide.value === BOTH_SIDE) return true
  return availableOutcomes.value.includes(orderSide.value)
})

// 当市场信息变化时，如果当前选择无效，重置为双边
watch(availableOutcomes, (outcomes) => {
  if (outcomes.length > 0 && !isValidSide.value) {
    orderSide.value = BOTH_SIDE
  }
})

const statusText = computed(() => {
  if (!autoBuyEnabled.value) return '已关闭'
  if (isOrdering.value) return '下单中...'
  return '等待信号'
})

const statusClass = computed(() => {
  if (!autoBuyEnabled.value) return 'text-base-content/50'
  if (isOrdering.value) return 'text-warning'
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

// 获取目标 token
function getTargetTokens() {
  const info = polymarketInfo.value
  if (!info) return []

  if (orderSide.value === BOTH_SIDE) {
    return info.tokens
  }

  return info.tokens.filter(token => token.outcome === orderSide.value)
}

// 获取价格 (bestAsk)
function getBestAsk(tokenId: string): number | null {
  const snapshot = gameStore.polymarketBook[tokenId]
  return snapshot?.bestAsk ?? null
}

// 计算 size: amount / price
function calculateSize(amount: number, price: number): number {
  if (price <= 0 || price >= 1) return 0
  return Math.floor((amount / price) * 100) / 100
}

// 获取配置
function getPrivateKey(): string {
  return localStorage.getItem(POLYMARKET_PRIVATE_KEY)?.trim() ?? ''
}

function getProxyAddress(): string {
  return localStorage.getItem(POLYMARKET_PROXY_ADDRESS)?.trim() ?? ''
}

// 下单条件检查
function canPlaceOrder(): { ok: boolean; reason?: string } {
  if (isOrdering.value) return { ok: false, reason: '下单中' }
  if (!authStore.isAuthenticated) return { ok: false, reason: '未登录' }
  if (!getPrivateKey()) return { ok: false, reason: '未配置私钥' }
  if (!getProxyAddress()) return { ok: false, reason: '未配置代理地址' }
  if (orderAmount.value <= 0) return { ok: false, reason: '金额无效' }
  if (!polymarketInfo.value) return { ok: false, reason: '无市场信息' }

  const tokens = getTargetTokens()
  if (tokens.length === 0) return { ok: false, reason: '无目标token' }

  for (const token of tokens) {
    const bestAsk = getBestAsk(token.token_id)
    if (!bestAsk || bestAsk <= 0 || bestAsk >= 1) {
      return { ok: false, reason: `${token.outcome} 无有效卖价` }
    }
  }
  return { ok: true }
}

// 执行单边下单
async function placeSingleOrder(tokenId: string, price: number, size: number): Promise<boolean> {
  const privateKey = getPrivateKey()
  const proxyAddress = getProxyAddress()

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/polymarket/orders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authStore.token}`,
      },
      body: JSON.stringify({
        token_id: tokenId,
        side: 'BUY',
        price,
        size,
        order_type: ORDER_TYPE,
        private_key: privateKey,
        proxy_address: proxyAddress,
      }),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => null)
      throw new Error(data?.detail || '下单失败')
    }

    await response.json().catch(() => null)
    return true
  } catch (error) {
    toastStore.showError(error instanceof Error ? error.message : '下单失败')
    return false
  }
}

// 监听策略信号
watch(
  () => gameStore.latestStrategySignal,
  (newSignal: StrategySignalEventData | null) => {
    if (!autoBuyEnabled.value || !newSignal) return

    // 只处理 BUY 信号
    if (newSignal.signal?.type !== 'BUY') return

    // 用 timestamp 去重，避免重复处理同一信号
    const signalTs = newSignal.timestamp ? new Date(newSignal.timestamp).getTime() : Date.now()
    if (lastSignalTimestamp.value === signalTs) return
    lastSignalTimestamp.value = signalTs

    // 执行信号驱动的下单
    executeSignalOrder(newSignal)
  }
)

// 执行信号驱动的下单（使用原有下单逻辑：金额/bestAsk）
async function executeSignalOrder(_signalData: StrategySignalEventData) {
  const check = canPlaceOrder()
  if (!check.ok) {
    toastStore.showWarning(`无法下单: ${check.reason}`)
    return
  }

  isOrdering.value = true
  const tokens = getTargetTokens()
  let successCount = 0

  try {
    for (const token of tokens) {
      const bestAsk = getBestAsk(token.token_id)
      if (!bestAsk || bestAsk <= 0 || bestAsk >= 1) continue

      const size = calculateSize(orderAmount.value, bestAsk)
      if (size <= 0) continue

      const success = await placeSingleOrder(token.token_id, bestAsk, size)
      if (success) {
        successCount++
        // 更新统计（使用 outcome 作为 key）
        const outcome = token.outcome
        if (!orderStats[outcome]) {
          orderStats[outcome] = { count: 0, amount: 0 }
        }
        orderStats[outcome].count++
        orderStats[outcome].amount += orderAmount.value
      }
    }

    if (successCount > 0) {
      lastOrderTime.value = new Date()
      toastStore.showSuccess(`信号买入成功 (${successCount}笔)`)
    }
  } finally {
    isOrdering.value = false
  }
}

// 配置变化时持久化
watch(orderSide, (value) => setStoredValue('SIDE', value))
watch(orderAmount, (value) => setStoredValue('AMOUNT', value))

// 格式化时间
function formatTime(date: Date | null): string {
  if (!date) return '--'
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// 重置统计
function resetStats() {
  Object.keys(orderStats).forEach(key => {
    delete orderStats[key]
  })
}

// 统计是否有数据
const hasStats = computed(() => {
  return Object.keys(orderStats).length > 0
})

// 格式化统计显示
const statsDisplay = computed(() => {
  const entries = Object.entries(orderStats)
  if (entries.length === 0) return '--'
  return entries
    .map(([outcome, stat]) => `${outcome} x${stat.count} ($${stat.amount.toFixed(0)})`)
    .join(', ')
})

// 选择方向
function selectSide(side: string) {
  if (!autoBuyEnabled.value) {
    orderSide.value = side
  }
}

// 获取按钮样式
function getSideButtonClass(side: string): string {
  if (orderSide.value !== side) return 'btn-ghost'
  if (side === BOTH_SIDE) return 'btn-primary'
  // 第一个 outcome 用绿色，第二个用红色
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
          v-model="autoBuyEnabled"
          type="checkbox"
          class="toggle toggle-success"
          :disabled="!polymarketInfo"
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
              :disabled="autoBuyEnabled"
              @click="selectSide(availableOutcomes[0])"
            >
              {{ availableOutcomes[0] }}
            </button>
            <!-- 双边按钮（中间） -->
            <button
              class="btn btn-sm join-item"
              :class="getSideButtonClass(BOTH_SIDE)"
              :disabled="autoBuyEnabled"
              @click="selectSide(BOTH_SIDE)"
            >
              双边
            </button>
            <!-- 第二个 outcome -->
            <button
              v-if="availableOutcomes[1]"
              class="btn btn-sm join-item"
              :class="getSideButtonClass(availableOutcomes[1])"
              :disabled="autoBuyEnabled"
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
            v-model.number="orderAmount"
            type="number"
            min="1"
            step="1"
            class="input input-bordered input-sm w-24"
            :disabled="autoBuyEnabled"
          />
          <span class="text-sm text-base-content/60">USDC</span>
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
            <div class="font-medium text-base-content">{{ formatTime(lastOrderTime) }}</div>
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
