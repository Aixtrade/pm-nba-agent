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
      console.warn('SSE Error:', data)
      connectionStore.setStatus('disconnected')
    },
    onGameEnd: (data) => {
      gameStore.setGameEnd(data)
    },
  })

  async function connect(request: LiveStreamRequest) {
    if (!authStore.isAuthenticated) {
      connectionStore.setStatus('disconnected')
      return
    }

    connectionStore.setStatus('connecting')
    gameStore.reset()

    try {
      await sseService.connect(request, authStore.token)
    } catch (error) {
      console.warn('SSE connect failed:', error)
      connectionStore.setStatus('disconnected')
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
