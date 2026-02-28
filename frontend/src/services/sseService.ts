import { fetchEventSource } from '@microsoft/fetch-event-source'
import type { SSEEventHandlers, SSEEventType, StrategySignalEventData } from '@/types/sse'
import type { TaskEndEventData, SubscribedEventData, TaskStatusEventData } from '@/types/task'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

// 任务订阅事件处理器
export interface TaskSSEEventHandlers extends SSEEventHandlers {
  onTaskEnd?: (data: TaskEndEventData) => void
  onTaskStatus?: (data: TaskStatusEventData) => void
  onSubscribed?: (data: SubscribedEventData) => void
}

// 重连配置
const RECONNECT_CONFIG = {
  maxRetries: 10, // 最大重试次数
  baseDelay: 1000, // 基础延迟 1 秒
  maxDelay: 30000, // 最大延迟 30 秒
  heartbeatTimeout: 60000, // 心跳超时 60 秒
}

export interface SSEConnectionState {
  isConnecting: boolean
  isConnected: boolean
  retryCount: number
  lastHeartbeat: number | null
}

export class SSEService {
  private abortController: AbortController | null = null
  private handlers: TaskSSEEventHandlers = {}

  // 策略信号订阅者
  private strategySignalListeners = new Set<(data: StrategySignalEventData) => void>()

  // 保活相关状态
  private lastToken: string | undefined = undefined
  private retryCount = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private heartbeatTimer: ReturnType<typeof setTimeout> | null = null
  private lastHeartbeatTime: number | null = null
  private isManualDisconnect = false // 标记是否为手动断开

  // 任务相关状态
  private currentTaskId: string | null = null

  // 状态变更回调
  private onStateChange: ((state: SSEConnectionState) => void) | null = null

  setHandlers(handlers: TaskSSEEventHandlers) {
    this.handlers = handlers
  }

  // 订阅策略信号（用于独立服务直接接收 SSE 信号）
  subscribeStrategySignal(listener: (data: StrategySignalEventData) => void): () => void {
    this.strategySignalListeners.add(listener)
    return () => this.strategySignalListeners.delete(listener)
  }

  getCurrentTaskId(): string | null {
    return this.currentTaskId
  }

  setStateChangeCallback(callback: (state: SSEConnectionState) => void) {
    this.onStateChange = callback
  }

  private notifyStateChange() {
    this.onStateChange?.({
      isConnecting: this.abortController !== null && !this.isConnected(),
      isConnected: this.isConnected(),
      retryCount: this.retryCount,
      lastHeartbeat: this.lastHeartbeatTime,
    })
  }

  private startHeartbeatMonitor() {
    this.stopHeartbeatMonitor()
    this.lastHeartbeatTime = Date.now()

    this.heartbeatTimer = setInterval(() => {
      if (this.lastHeartbeatTime) {
        const elapsed = Date.now() - this.lastHeartbeatTime
        if (elapsed > RECONNECT_CONFIG.heartbeatTimeout) {
          console.warn(`SSE: 心跳超时 (${elapsed}ms)，触发重连`)
          this.handleHeartbeatTimeout()
        }
      }
    }, 10000) // 每 10 秒检查一次
  }

  private stopHeartbeatMonitor() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private updateHeartbeat() {
    this.lastHeartbeatTime = Date.now()
  }

  private handleHeartbeatTimeout() {
    // 心跳超时，主动断开并重连
    this.cleanupConnection()
    this.scheduleTaskReconnect()
  }

  // 清理连接但不清理重连参数
  private cleanupConnection() {
    this.stopHeartbeatMonitor()

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.abortController) {
      this.abortController.abort()
      this.abortController = null
    }
  }

  private handleEvent(eventType: SSEEventType, data: string) {
    try {
      const parsed = JSON.parse(data)

      switch (eventType) {
        case 'scoreboard':
          this.handlers.onScoreboard?.(parsed)
          break
        case 'boxscore':
          this.handlers.onBoxscore?.(parsed)
          break
        case 'analysis_chunk':
          this.handlers.onAnalysisChunk?.(parsed)
          break
        case 'heartbeat':
          this.handlers.onHeartbeat?.(parsed)
          break
        case 'polymarket_info':
          this.handlers.onPolymarketInfo?.(parsed)
          break
        case 'polymarket_book':
          this.handlers.onPolymarketBook?.(parsed)
          break
        case 'strategy_signal':
          this.handlers.onStrategySignal?.(parsed)
          // 通知所有直接订阅的服务
          this.strategySignalListeners.forEach(listener => listener(parsed))
          break
        case 'error':
          this.handlers.onError?.(parsed)
          break
        case 'game_end':
          this.handlers.onGameEnd?.(parsed)
          break
        case 'task_end':
          this.handlers.onTaskEnd?.(parsed)
          break
        case 'task_status':
          this.handlers.onTaskStatus?.(parsed)
          break
        case 'task_chat_output':
          this.handlers.onTaskChatOutput?.(parsed)
          break
        case 'subscribed':
          this.handlers.onSubscribed?.(parsed)
          break
        case 'auto_buy_state':
          this.handlers.onAutoBuyState?.(parsed)
          break
        case 'auto_trade_state':
          this.handlers.onAutoTradeState?.(parsed)
          break
        case 'auto_trade_execution':
          this.handlers.onAutoTradeExecution?.(parsed)
          break
        case 'auto_sell_state':
          this.handlers.onAutoSellState?.(parsed)
          break
        case 'auto_sell_execution':
          this.handlers.onAutoSellExecution?.(parsed)
          break
        case 'position_state':
          this.handlers.onPositionState?.(parsed)
          break
        default:
          console.warn('Unknown event type:', eventType)
      }
    } catch (e) {
      console.error('Failed to parse SSE event data:', e)
    }
  }

  disconnect() {
    this.isManualDisconnect = true
    this.cleanupConnection()
    this.lastToken = undefined
    this.retryCount = 0
    this.lastHeartbeatTime = null
    this.currentTaskId = null
    this.notifyStateChange()
  }

  /**
   * 订阅后台任务事件流
   */
  async subscribeTask(taskId: string, token?: string): Promise<void> {
    this.currentTaskId = taskId
    this.lastToken = token
    this.isManualDisconnect = false
    this.retryCount = 0

    await this.doSubscribeTask()
  }

  private async doSubscribeTask(): Promise<void> {
    if (!this.currentTaskId) return

    // 先断开已有连接
    this.cleanupConnection()

    this.abortController = new AbortController()
    this.notifyStateChange()

    const url = `${API_BASE_URL}/api/v1/live/subscribe/${this.currentTaskId}`

    const headers: Record<string, string> = {
      Accept: 'text/event-stream',
    }

    if (this.lastToken) {
      headers.Authorization = `Bearer ${this.lastToken}`
    }

    try {
      await fetchEventSource(url, {
        method: 'GET',
        headers,
        signal: this.abortController.signal,
        openWhenHidden: true,
        onopen: async (response) => {
          if (response.ok) {
            this.retryCount = 0
            this.startHeartbeatMonitor()
            this.handlers.onOpen?.()
            this.notifyStateChange()
          } else {
            const errorText = await response.text()
            // 任务不存在/无权限/请求错误时，不应自动重连
            if ([400, 401, 403, 404].includes(response.status)) {
              this.isManualDisconnect = true
              this.currentTaskId = null
              this.cleanupConnection()
              this.notifyStateChange()
              this.handlers.onError?.({
                code: 'TASK_SUBSCRIBE_FAILED',
                message: `订阅失败(${response.status})，请检查任务是否存在`,
                recoverable: false,
                timestamp: new Date().toISOString(),
              })
            }
            throw new Error(`Failed to subscribe: ${response.status} ${errorText}`)
          }
        },
        onmessage: (event) => {
          this.updateHeartbeat()
          this.handleEvent(event.event as SSEEventType, event.data)

          // 任务结束时自动断开
          if (event.event === 'task_end' || event.event === 'game_end') {
            this.isManualDisconnect = true
          }
        },
        onclose: () => {
          this.stopHeartbeatMonitor()
          this.handlers.onClose?.()
          this.notifyStateChange()

          // 如果不是手动断开且是任务模式，尝试重连
          if (!this.isManualDisconnect && this.currentTaskId) {
            this.scheduleTaskReconnect()
          }
        },
        onerror: (err) => {
          console.error('Task SSE Error:', err)
          this.stopHeartbeatMonitor()

          if (this.isManualDisconnect && !this.currentTaskId) {
            this.notifyStateChange()
            return
          }

          const willRetry =
            !this.isManualDisconnect && this.retryCount < RECONNECT_CONFIG.maxRetries
          this.handlers.onError?.({
            code: 'CONNECTION_ERROR',
            message: err instanceof Error ? err.message : 'Unknown error',
            recoverable: willRetry,
            timestamp: new Date().toISOString(),
          })

          this.notifyStateChange()
          throw err
        },
      })
    } catch {
      if (!this.isManualDisconnect && this.currentTaskId) {
        this.scheduleTaskReconnect()
      }
    }
  }

  private scheduleTaskReconnect() {
    if (this.isManualDisconnect) return
    if (this.retryCount >= RECONNECT_CONFIG.maxRetries) {
      console.warn(`Task SSE: 已达到最大重试次数 (${RECONNECT_CONFIG.maxRetries})`)
      this.handlers.onError?.({
        code: 'MAX_RETRIES_EXCEEDED',
        message: `订阅任务失败，已重试 ${RECONNECT_CONFIG.maxRetries} 次`,
        recoverable: false,
        timestamp: new Date().toISOString(),
      })
      return
    }

    const delay = Math.min(
      RECONNECT_CONFIG.baseDelay * Math.pow(2, this.retryCount),
      RECONNECT_CONFIG.maxDelay
    )

    this.retryCount++
    console.log(`Task SSE: 将在 ${delay}ms 后进行第 ${this.retryCount} 次重连...`)

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      if (!this.isManualDisconnect && this.currentTaskId) {
        this.doSubscribeTask()
      }
    }, delay)

    this.notifyStateChange()
  }

  isConnected(): boolean {
    return this.abortController !== null && !this.abortController.signal.aborted
  }

  getRetryCount(): number {
    return this.retryCount
  }

  getLastHeartbeat(): number | null {
    return this.lastHeartbeatTime
  }

  // 手动触发重连（如网络恢复时调用）
  async reconnect(): Promise<void> {
    if (!this.currentTaskId) {
      console.warn('SSE: 没有可用的任务 ID，无法重连')
      return
    }

    this.isManualDisconnect = false
    this.retryCount = 0
    await this.doSubscribeTask()
  }

  // 检查是否有待恢复的连接
  canReconnect(): boolean {
    return this.currentTaskId !== null && this.isManualDisconnect === false
  }
}

// 导出单例
export const sseService = new SSEService()
