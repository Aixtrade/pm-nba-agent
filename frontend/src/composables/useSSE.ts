import { onUnmounted } from 'vue'
import { sseService } from '@/services/sseService'
import { useAuthStore, useConnectionStore, useGameStore } from '@/stores'
import type { LiveStreamRequest } from '@/types/sse'

export function useSSE() {
  const connectionStore = useConnectionStore()
  const gameStore = useGameStore()
  const authStore = useAuthStore()

  // 设置事件处理器
  sseService.setHandlers({
    onOpen: () => {
      connectionStore.setStatus('connected')
    },
    onClose: () => {
      connectionStore.setStatus('disconnected')
    },
    onScoreboard: (data) => {
      gameStore.setScoreboard(data)
    },
    onBoxscore: (data) => {
      gameStore.setBoxscore(data)
    },
    onPlayByPlay: (data) => {
      gameStore.setPlayByPlay(data)
    },
    onAnalysisChunk: (data) => {
      gameStore.appendAnalysisChunk(data)
    },
    onHeartbeat: (data) => {
      connectionStore.setHeartbeat(data.timestamp)
    },
    onError: (data) => {
      connectionStore.setError(data)
    },
    onGameEnd: (data) => {
      gameStore.setGameEnd(data)
    },
  })

  async function connect(request: LiveStreamRequest) {
    if (!authStore.isAuthenticated) {
      connectionStore.setError({
        code: 'AUTH_REQUIRED',
        message: '请先登录再连接数据流',
        recoverable: false,
        timestamp: new Date().toISOString(),
      })
      connectionStore.setStatus('error')
      return
    }

    connectionStore.setStatus('connecting')
    gameStore.reset()
    connectionStore.clearError()

    try {
      await sseService.connect(request, authStore.token)
    } catch (error) {
      connectionStore.setStatus('error')
      connectionStore.setError({
        code: 'CONNECTION_FAILED',
        message: error instanceof Error ? error.message : 'Failed to connect',
        recoverable: false,
        timestamp: new Date().toISOString(),
      })
    }
  }

  function disconnect() {
    sseService.disconnect()
    connectionStore.setStatus('disconnected')
  }

  // 组件卸载时自动断开连接
  onUnmounted(() => {
    disconnect()
  })

  return {
    connect,
    disconnect,
    isConnected: () => sseService.isConnected(),
  }
}
