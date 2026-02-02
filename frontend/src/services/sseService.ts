import { fetchEventSource } from '@microsoft/fetch-event-source'
import type { LiveStreamRequest, SSEEventHandlers, SSEEventType } from '@/types/sse'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

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
  private handlers: SSEEventHandlers = {}

  // 保活相关状态
  private lastRequest: LiveStreamRequest | null = null
  private lastToken: string | undefined = undefined
  private retryCount = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private heartbeatTimer: ReturnType<typeof setTimeout> | null = null
  private lastHeartbeatTime: number | null = null
  private isManualDisconnect = false // 标记是否为手动断开

  // 状态变更回调
  private onStateChange: ((state: SSEConnectionState) => void) | null = null

  setHandlers(handlers: SSEEventHandlers) {
    this.handlers = handlers
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

  async connect(request: LiveStreamRequest, token?: string): Promise<void> {
    // 保存请求参数以便重连
    this.lastRequest = request
    this.lastToken = token
    this.isManualDisconnect = false
    this.retryCount = 0

    await this.doConnect()
  }

  private async doConnect(): Promise<void> {
    if (!this.lastRequest) return

    // 先断开已有连接
    this.cleanupConnection()

    this.abortController = new AbortController()
    this.notifyStateChange()

    const url = `${API_BASE_URL}/api/v1/live/stream`

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    if (this.lastToken) {
      headers.Authorization = `Bearer ${this.lastToken}`
    }

    try {
      await fetchEventSource(url, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          url: this.lastRequest.url,
          poll_interval: this.lastRequest.poll_interval ?? 10,
          include_scoreboard: this.lastRequest.include_scoreboard ?? true,
          include_boxscore: this.lastRequest.include_boxscore ?? true,
          analysis_interval: this.lastRequest.analysis_interval ?? 30,
        }),
        signal: this.abortController.signal,
        openWhenHidden: true,
        onopen: async (response) => {
          if (response.ok) {
            // 连接成功，重置重试计数
            this.retryCount = 0
            this.startHeartbeatMonitor()
            this.handlers.onOpen?.()
            this.notifyStateChange()
          } else {
            const errorText = await response.text()
            throw new Error(`Failed to connect: ${response.status} ${errorText}`)
          }
        },
        onmessage: (event) => {
          // 收到任何消息都更新心跳时间
          this.updateHeartbeat()
          this.handleEvent(event.event as SSEEventType, event.data)
        },
        onclose: () => {
          this.stopHeartbeatMonitor()
          this.handlers.onClose?.()
          this.notifyStateChange()

          // 如果不是手动断开，尝试重连
          if (!this.isManualDisconnect) {
            this.scheduleReconnect()
          }
        },
        onerror: (err) => {
          console.error('SSE Error:', err)
          this.stopHeartbeatMonitor()

          // 通知错误但标记为可恢复（将尝试重连）
          const willRetry = !this.isManualDisconnect && this.retryCount < RECONNECT_CONFIG.maxRetries
          this.handlers.onError?.({
            code: 'CONNECTION_ERROR',
            message: err instanceof Error ? err.message : 'Unknown error',
            recoverable: willRetry,
            timestamp: new Date().toISOString(),
          })

          this.notifyStateChange()

          // 如果不是手动断开且未超过最大重试次数，抛出错误触发 fetchEventSource 的重试
          // 但我们使用自己的重连逻辑，所以抛出错误停止内部重试
          throw err
        },
      })
    } catch (error) {
      // fetchEventSource 抛出错误后，如果不是手动断开，安排重连
      if (!this.isManualDisconnect) {
        this.scheduleReconnect()
      }
    }
  }

  private scheduleReconnect() {
    if (this.isManualDisconnect) return
    if (this.retryCount >= RECONNECT_CONFIG.maxRetries) {
      console.warn(`SSE: 已达到最大重试次数 (${RECONNECT_CONFIG.maxRetries})，停止重连`)
      this.handlers.onError?.({
        code: 'MAX_RETRIES_EXCEEDED',
        message: `连接失败，已重试 ${RECONNECT_CONFIG.maxRetries} 次`,
        recoverable: false,
        timestamp: new Date().toISOString(),
      })
      return
    }

    // 指数退避计算延迟
    const delay = Math.min(
      RECONNECT_CONFIG.baseDelay * Math.pow(2, this.retryCount),
      RECONNECT_CONFIG.maxDelay,
    )

    this.retryCount++
    console.log(`SSE: 将在 ${delay}ms 后进行第 ${this.retryCount} 次重连...`)

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      if (!this.isManualDisconnect) {
        this.doConnect()
      }
    }, delay)

    this.notifyStateChange()
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
    this.scheduleReconnect()
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
        case 'playbyplay':
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
          break
        case 'error':
          this.handlers.onError?.(parsed)
          break
        case 'game_end':
          this.handlers.onGameEnd?.(parsed)
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
    this.lastRequest = null
    this.lastToken = undefined
    this.retryCount = 0
    this.lastHeartbeatTime = null
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
    if (!this.lastRequest) {
      console.warn('SSE: 没有可用的连接参数，无法重连')
      return
    }

    this.isManualDisconnect = false
    this.retryCount = 0
    await this.doConnect()
  }

  // 检查是否有待恢复的连接
  canReconnect(): boolean {
    return this.lastRequest !== null && this.isManualDisconnect === false
  }
}

// 导出单例
export const sseService = new SSEService()
