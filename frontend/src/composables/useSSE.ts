import { onMounted, onUnmounted, ref } from 'vue'
import { sseService } from '@/services/sseService'
import { taskService } from '@/services/taskService'
import { useAuthStore, useConnectionStore, useGameStore, useTaskStore, useToastStore } from '@/stores'
import type { LiveStreamRequest } from '@/types/sse'
import type { CreateTaskRequest } from '@/types/task'

export function useSSE() {
  const connectionStore = useConnectionStore()
  const gameStore = useGameStore()
  const authStore = useAuthStore()
  const taskStore = useTaskStore()
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

      const execution = data.execution
      if (execution?.source === 'task_auto_buy') {
        const orderCount = Array.isArray(execution.orders) ? execution.orders.length : 0
        if (execution.success) {
          toastStore.showSuccess(`自动买入下单成功 (${orderCount} 笔)`)
        } else {
          toastStore.showError(execution.error || '自动买入下单失败')
        }
      }
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
    onAutoBuyState: (data) => {
      gameStore.setAutoBuyState(data)
    },
    onAutoSellState: (data) => {
      gameStore.setAutoSellState(data)
    },
    onPositionState: (data) => {
      gameStore.setPositionState(data)
    },
    onTaskEnd: (data) => {
      taskStore.updateTaskState(data.task_id, data.state)
      if (data.task_id === taskStore.currentTaskId) {
        toastStore.showInfo(`任务已结束: ${data.state}`)
      }
    },
    onTaskStatus: (data) => {
      taskStore.addTask(data)
    },
    onSubscribed: (data) => {
      taskStore.setCurrentTask(data.task_id)
      toastStore.showSuccess(`已订阅任务: ${data.task_id}`)
      void refreshTaskStatus(data.task_id)
    },
  })

  // 网络状态监听
  function handleOnline() {
    isOnline.value = true
    console.log('SSE: 网络已恢复')
    toastStore.showInfo('网络已恢复')

    if (!sseService.isConnected() && taskStore.currentTaskId) {
      console.log('SSE: 网络恢复后重新订阅任务')
      void subscribeTask(taskStore.currentTaskId)
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

      if (!sseService.isConnected() && isOnline.value && taskStore.currentTaskId) {
        console.log('SSE: 页面可见后检测到连接断开，重新订阅任务')
        void subscribeTask(taskStore.currentTaskId)
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
    taskStore.setCurrentTask(null)
  }

  /**
   * 订阅后台任务
   */
  async function subscribeTask(taskId: string) {
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
    taskStore.setCurrentTask(taskId)

    try {
      await sseService.subscribeTask(taskId, authStore.token)
    } catch (error) {
      console.warn('Task subscribe failed:', error)
    }
  }

  async function refreshTaskStatus(taskId: string, maxRetries = 3): Promise<void> {
    if (!authStore.isAuthenticated) return

    for (let attempt = 0; attempt < maxRetries; attempt += 1) {
      try {
        const status = await taskService.getTask(taskId, authStore.token)
        taskStore.addTask(status)

        if (status.state !== 'pending') {
          return
        }
      } catch (error) {
        console.warn('Task status refresh failed:', error)
        return
      }

      if (attempt < maxRetries - 1) {
        await new Promise((resolve) => setTimeout(resolve, 800))
      }
    }
  }

  /**
   * 创建任务并订阅
   */
  async function createAndSubscribe(request: CreateTaskRequest): Promise<string> {
    if (!authStore.isAuthenticated) {
      const error = new Error('请先登录')
      toastStore.showError(error.message)
      throw error
    }

    try {
      const response = await taskService.createTask(request, authStore.token)
      toastStore.showSuccess(`任务已创建: ${response.task_id}`)

      // 添加到任务列表
      taskStore.addTask({
        task_id: response.task_id,
        state: response.status,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })

      // 订阅新任务
      void subscribeTask(response.task_id)
      void refreshTaskStatus(response.task_id)

      return response.task_id
    } catch (error) {
      const message = error instanceof Error ? error.message : '创建任务失败'
      toastStore.showError(message)
      throw error instanceof Error ? error : new Error(message)
    }
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

    if (taskStore.currentTaskId) {
      await subscribeTask(taskStore.currentTaskId)
      return
    }

    toastStore.showWarning('暂无可重连的任务')
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
    subscribeTask,
    createAndSubscribe,
    isConnected: () => sseService.isConnected(),
    isOnline,
  }
}
