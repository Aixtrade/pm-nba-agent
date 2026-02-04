import { sseService } from './sseService'
import { useAuthStore, useGameStore, useToastStore } from '@/stores'
import type { StrategySignalEventData } from '@/types/sse'

const BOTH_SIDE = '__BOTH__'
const ORDER_TYPE = 'GTC'
const POLYMARKET_PRIVATE_KEY = 'POLYMARKET_PRIVATE_KEY'
const POLYMARKET_PROXY_ADDRESS = 'POLYMARKET_PROXY_ADDRESS'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

// localStorage 持久化键
const STORAGE_PREFIX = 'AUTO_BUY_'
const getStorageKey = (key: string) => `${STORAGE_PREFIX}${key}`

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

export interface AutoBuyConfig {
  side: string // outcome 名称或 BOTH_SIDE
  amount: number
  roundSize: boolean // size 是否取整数
}

export interface AutoBuyStats {
  [outcome: string]: { count: number; amount: number }
}

export interface AutoBuyState {
  enabled: boolean
  config: AutoBuyConfig
  stats: AutoBuyStats
  lastOrderTime: Date | null
  isOrdering: boolean
}

type StateChangeCallback = (state: AutoBuyState) => void

class AutoBuyService {
  private enabled = false
  private config: AutoBuyConfig = {
    side: getStoredValue('SIDE', BOTH_SIDE),
    amount: getStoredValue('AMOUNT', 10),
    roundSize: getStoredValue('ROUND_SIZE', false),
  }
  private stats: AutoBuyStats = {}
  private lastOrderTime: Date | null = null
  private isOrdering = false

  private unsubscribe: (() => void) | null = null
  private stateChangeCallbacks = new Set<StateChangeCallback>()

  constructor() {
    // 初始化时订阅 SSE 策略信号
    this.unsubscribe = sseService.subscribeStrategySignal(this.handleSignal)
  }

  // 订阅状态变化（供 UI 组件使用）
  onStateChange(callback: StateChangeCallback): () => void {
    this.stateChangeCallbacks.add(callback)
    // 立即通知当前状态
    callback(this.getState())
    return () => this.stateChangeCallbacks.delete(callback)
  }

  private notifyStateChange() {
    const state = this.getState()
    this.stateChangeCallbacks.forEach(cb => cb(state))
  }

  getState(): AutoBuyState {
    return {
      enabled: this.enabled,
      config: { ...this.config },
      stats: { ...this.stats },
      lastOrderTime: this.lastOrderTime,
      isOrdering: this.isOrdering,
    }
  }

  // 开启/关闭
  setEnabled(enabled: boolean) {
    this.enabled = enabled
    console.log(`[AutoBuyService] ${enabled ? '已开启' : '已关闭'}`)
    this.notifyStateChange()
  }

  isEnabled(): boolean {
    return this.enabled
  }

  // 配置
  setConfig(config: Partial<AutoBuyConfig>) {
    if (config.side !== undefined) {
      this.config.side = config.side
      setStoredValue('SIDE', config.side)
    }
    if (config.amount !== undefined) {
      this.config.amount = config.amount
      setStoredValue('AMOUNT', config.amount)
    }
    if (config.roundSize !== undefined) {
      this.config.roundSize = config.roundSize
      setStoredValue('ROUND_SIZE', config.roundSize)
    }
    this.notifyStateChange()
  }

  getConfig(): AutoBuyConfig {
    return { ...this.config }
  }

  // 重置统计
  resetStats() {
    this.stats = {}
    this.notifyStateChange()
  }

  // 处理策略信号
  private handleSignal = (signal: StrategySignalEventData) => {
    if (!this.enabled) return
    if (signal.signal?.type !== 'BUY') return

    console.log('[AutoBuyService] 收到 BUY 信号，执行下单', signal.timestamp)
    this.executeOrder(signal)
  }

  // 下单条件检查
  private canPlaceOrder(): { ok: boolean; reason?: string } {
    const authStore = useAuthStore()
    const gameStore = useGameStore()

    if (this.isOrdering) return { ok: false, reason: '下单中' }
    if (!authStore.isAuthenticated) return { ok: false, reason: '未登录' }
    if (!this.getPrivateKey()) return { ok: false, reason: '未配置私钥' }
    if (!this.getProxyAddress()) return { ok: false, reason: '未配置代理地址' }
    if (this.config.amount <= 0) return { ok: false, reason: '金额无效' }
    if (!gameStore.polymarketInfo) return { ok: false, reason: '无市场信息' }

    const tokens = this.getTargetTokens()
    if (tokens.length === 0) return { ok: false, reason: '无目标token' }

    for (const token of tokens) {
      const bestAsk = this.getBestAsk(token.token_id)
      if (!bestAsk || bestAsk <= 0 || bestAsk >= 1) {
        return { ok: false, reason: `${token.outcome} 无有效卖价` }
      }
    }
    return { ok: true }
  }

  private getPrivateKey(): string {
    return localStorage.getItem(POLYMARKET_PRIVATE_KEY)?.trim() ?? ''
  }

  private getProxyAddress(): string {
    return localStorage.getItem(POLYMARKET_PROXY_ADDRESS)?.trim() ?? ''
  }

  private getTargetTokens() {
    const gameStore = useGameStore()
    const info = gameStore.polymarketInfo
    if (!info) return []

    if (this.config.side === BOTH_SIDE) {
      return info.tokens
    }

    return info.tokens.filter(token => token.outcome === this.config.side)
  }

  private getBestAsk(tokenId: string): number | null {
    const gameStore = useGameStore()
    const snapshot = gameStore.polymarketBook[tokenId]
    return snapshot?.bestAsk ?? null
  }

  private calculateSize(amount: number, price: number): number {
    if (price <= 0 || price >= 1) return 0
    const rawSize = amount / price
    if (this.config.roundSize) {
      return Math.floor(rawSize)
    }
    return Math.floor(rawSize * 100) / 100
  }

  // 执行下单
  private async executeOrder(_signalData: StrategySignalEventData) {
    const toastStore = useToastStore()

    const check = this.canPlaceOrder()
    if (!check.ok) {
      console.warn('[AutoBuyService] 无法下单:', check.reason)
      toastStore.showWarning(`无法下单: ${check.reason}`)
      return
    }

    this.isOrdering = true
    this.notifyStateChange()

    const tokens = this.getTargetTokens()
    let successCount = 0

    try {
      for (const token of tokens) {
        const bestAsk = this.getBestAsk(token.token_id)
        if (!bestAsk || bestAsk <= 0 || bestAsk >= 1) continue

        const size = this.calculateSize(this.config.amount, bestAsk)
        if (size <= 0) continue

        const success = await this.placeSingleOrder(token.token_id, bestAsk, size)
        if (success) {
          successCount++
          // 更新统计
          const outcome = token.outcome
          if (!this.stats[outcome]) {
            this.stats[outcome] = { count: 0, amount: 0 }
          }
          this.stats[outcome].count++
          this.stats[outcome].amount += this.config.amount
        }
      }

      if (successCount > 0) {
        this.lastOrderTime = new Date()
        toastStore.showSuccess(`信号买入成功 (${successCount}笔)`)
      }
    } finally {
      this.isOrdering = false
      this.notifyStateChange()
    }
  }

  private async placeSingleOrder(tokenId: string, price: number, size: number): Promise<boolean> {
    const authStore = useAuthStore()
    const toastStore = useToastStore()
    const privateKey = this.getPrivateKey()
    const proxyAddress = this.getProxyAddress()

    const requestBody = {
      token_id: tokenId,
      side: 'BUY',
      price,
      size,
      order_type: ORDER_TYPE,
      private_key: privateKey,
      proxy_address: proxyAddress,
    }

    console.log('[AutoBuyService] 发起下单请求:', { tokenId, price, size })

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/polymarket/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authStore.token}`,
        },
        body: JSON.stringify(requestBody),
      })

      const data = await response.json().catch(() => null)

      if (!response.ok) {
        console.error('[AutoBuyService] 下单失败:', {
          status: response.status,
          statusText: response.statusText,
          response: data,
          request: { tokenId, price, size },
        })
        toastStore.showError(data?.detail || `下单失败: ${response.status}`)
        return false
      }

      console.log('[AutoBuyService] 下单成功:', data)
      return true
    } catch (error) {
      console.error('[AutoBuyService] 下单异常:', error)
      toastStore.showError(error instanceof Error ? error.message : '下单失败')
      return false
    }
  }

  // 清理（应用退出时调用）
  destroy() {
    this.unsubscribe?.()
    this.unsubscribe = null
  }
}

// 导出单例
export const autoBuyService = new AutoBuyService()
