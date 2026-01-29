import { fetchEventSource } from '@microsoft/fetch-event-source'
import type { LiveStreamRequest, SSEEventHandlers, SSEEventType } from '@/types/sse'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export class SSEService {
  private abortController: AbortController | null = null
  private handlers: SSEEventHandlers = {}

  setHandlers(handlers: SSEEventHandlers) {
    this.handlers = handlers
  }

  async connect(request: LiveStreamRequest, token?: string): Promise<void> {
    // 先断开已有连接
    this.disconnect()

    this.abortController = new AbortController()

    const url = `${API_BASE_URL}/api/v1/live/stream`

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    if (token) {
      headers.Authorization = `Bearer ${token}`
    }

    await fetchEventSource(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        url: request.url,
        poll_interval: request.poll_interval ?? 10,
        include_scoreboard: request.include_scoreboard ?? true,
        include_boxscore: request.include_boxscore ?? true,
        include_playbyplay: request.include_playbyplay ?? true,
        playbyplay_limit: request.playbyplay_limit ?? 20,
      }),
      signal: this.abortController.signal,
      openWhenHidden: true,
      onopen: async (response) => {
        if (response.ok) {
          this.handlers.onOpen?.()
        } else {
          const errorText = await response.text()
          throw new Error(`Failed to connect: ${response.status} ${errorText}`)
        }
      },
      onmessage: (event) => {
        this.handleEvent(event.event as SSEEventType, event.data)
      },
      onclose: () => {
        this.handlers.onClose?.()
      },
      onerror: (err) => {
        console.error('SSE Error:', err)
        this.handlers.onError?.({
          code: 'CONNECTION_ERROR',
          message: err instanceof Error ? err.message : 'Unknown error',
          recoverable: false,
          timestamp: new Date().toISOString(),
        })
        // 停止重试
        throw err
      },
    })
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
        case 'playbyplay':
          this.handlers.onPlayByPlay?.(parsed)
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
    if (this.abortController) {
      this.abortController.abort()
      this.abortController = null
    }
  }

  isConnected(): boolean {
    return this.abortController !== null && !this.abortController.signal.aborted
  }
}

// 导出单例
export const sseService = new SSEService()
