import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ConnectionStatus } from '@/types/sse'

export const useConnectionStore = defineStore('connection', () => {
  // 状态
  const status = ref<ConnectionStatus>('disconnected')
  const lastHeartbeat = ref<string | null>(null)
  const retryCount = ref(0)

  // 计算属性
  const isConnected = computed(() => status.value === 'connected')
  const isConnecting = computed(() => status.value === 'connecting')
  const isError = computed(() => status.value === 'error')
  const isReconnecting = computed(() => status.value === 'connecting' && retryCount.value > 0)

  // Actions
  function setStatus(newStatus: ConnectionStatus) {
    status.value = newStatus
    // 连接成功时重置重试计数
    if (newStatus === 'connected') {
      retryCount.value = 0
    }
  }

  function setHeartbeat(timestamp: string) {
    lastHeartbeat.value = timestamp
  }

  function setRetryCount(count: number) {
    retryCount.value = count
  }

  function reset() {
    status.value = 'disconnected'
    lastHeartbeat.value = null
    retryCount.value = 0
  }

  return {
    // 状态
    status,
    lastHeartbeat,
    retryCount,
    // 计算属性
    isConnected,
    isConnecting,
    isError,
    isReconnecting,
    // Actions
    setStatus,
    setHeartbeat,
    setRetryCount,
    reset,
  }
})
