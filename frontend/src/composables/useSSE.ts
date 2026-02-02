import { onMounted, onUnmounted, ref } from 'vue'
import { sseService } from '@/services/sseService'
import { useAuthStore, useConnectionStore, useGameStore, useToastStore } from '@/stores'
import type { LiveStreamRequest } from '@/types/sse'

export function useSSE() {
  const connectionStore = useConnectionStore()
  const gameStore = useGameStore()
  const authStore = useAuthStore()
  const toastStore = useToastStore()

  // 网络状态
  const isOnline = ref(navigator.onLine)

  // 设置状态变更回调
  sseService.setStateChangeCallback((state) => {
    if (state.isConnected) {
      connectionStore.setStatus('connected')
    } else if (state.isConnecting || state.retryCount > 0) {
      connectionStore.setStatus('connecting')
      connectionStore.setRetryCount(state.retryCount)
    } else {
      connectionStore.setStatus('disconnected')
    }
  })

  // 设置事件处理器
  sseService.setHandlers({
    onOpen: () => {
      connectionStore.setStatus('connected')
      connectionStore.setRetryCount(0)
      toastStore.showSuccess('连接已建立')
    },
    onClose: () => {
      // 状态由 stateChangeCallback 处理
    },
    onScoreboard: (data) => {
      gameStore.setScoreboard(data)
    },
    onBoxscore: (data) => {
      gameStore.setBoxscore(data)
    },
    onAnalysisChunk: (data) => {
      gameStore.appendAnalysisChunk(data)
    },
    onHeartbeat: (data) => {
      connectionStore.setHeartbeat(data.timestamp)
    },
    onPolymarketInfo: (data) => {
      gameStore.setPolymarketInfo(data)
    },
    onPolymarketBook: (data) => {
      gameStore.updatePolymarketBook(data)
    },
    onStrategySignal: (data) => {
      gameStore.addStrategySignal(data)
    },
    onError: (data) => {
      console.warn('SSE Error:', data)
      if (data?.code === 'MAX_RETRIES_EXCEEDED') {
        connectionStore.setStatus('error')
        toastStore.showError(data.message || '连接失败，请手动重试')
      } else if (data?.recoverable) {
        // 正在重连，显示提示
        const retryCount = sseService.getRetryCount()
        if (retryCount > 0) {
          toastStore.showWarning(`正在重连... (第 ${retryCount} 次)`)
        }
      } else {
        connectionStore.setStatus('error')
      }
    },
    onGameEnd: (data) => {
      gameStore.setGameEnd(data)
    },
  })

  // 网络状态监听
  function handleOnline() {
    isOnline.value = true
    console.log('SSE: 网络已恢复')
    toastStore.showInfo('网络已恢复')

    // 如果之前有连接，尝试重连
    if (sseService.canReconnect()) {
      console.log('SSE: 网络恢复后自动重连')
      sseService.reconnect()
    }
  }

  function handleOffline() {
    isOnline.value = false
    console.log('SSE: 网络已断开')
    toastStore.showWarning('网络已断开')
    connectionStore.setStatus('disconnected')
  }

  // 页面可见性监听
  function handleVisibilityChange() {
    if (document.visibilityState === 'visible') {
      console.log('SSE: 页面可见')

      // 检查连接状态，如果断开且有待恢复的连接，尝试重连
      if (!sseService.isConnected() && sseService.canReconnect() && isOnline.value) {
        console.log('SSE: 页面可见后检测到连接断开，尝试重连')
        sseService.reconnect()
      }
    }
  }

  async function connect(request: LiveStreamRequest) {
    if (!authStore.isAuthenticated) {
      connectionStore.setStatus('disconnected')
      toastStore.showError('请先登录')
      return
    }

    if (!isOnline.value) {
      connectionStore.setStatus('disconnected')
      toastStore.showError('网络不可用')
      return
    }

    connectionStore.setStatus('connecting')
    gameStore.reset()

    try {
      await sseService.connect(request, authStore.token)
    } catch (error) {
      console.warn('SSE connect failed:', error)
      // 状态由 sseService 的错误处理更新
    }
  }

  function disconnect() {
    sseService.disconnect()
    connectionStore.setStatus('disconnected')
  }

  // 手动重连
  async function reconnect() {
    if (!authStore.isAuthenticated) {
      toastStore.showError('请先登录')
      return
    }

    if (!isOnline.value) {
      toastStore.showError('网络不可用')
      return
    }

    connectionStore.setStatus('connecting')
    await sseService.reconnect()
  }

  // 注册事件监听
  onMounted(() => {
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    document.addEventListener('visibilitychange', handleVisibilityChange)
  })

  // 组件卸载时清理
  onUnmounted(() => {
    window.removeEventListener('online', handleOnline)
    window.removeEventListener('offline', handleOffline)
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    disconnect()
  })

  return {
    connect,
    disconnect,
    reconnect,
    isConnected: () => sseService.isConnected(),
    isOnline,
  }
}
