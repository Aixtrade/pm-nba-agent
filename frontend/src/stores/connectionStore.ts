import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ConnectionStatus, ErrorEventData } from '@/types/sse'

export const useConnectionStore = defineStore('connection', () => {
  // 状态
  const status = ref<ConnectionStatus>('disconnected')
  const lastError = ref<ErrorEventData | null>(null)
  const lastHeartbeat = ref<string | null>(null)

  // 计算属性
  const isConnected = computed(() => status.value === 'connected')
  const isConnecting = computed(() => status.value === 'connecting')
  const hasError = computed(() => status.value === 'error' || lastError.value !== null)

  // Actions
  function setStatus(newStatus: ConnectionStatus) {
    status.value = newStatus
    if (newStatus === 'connected' || newStatus === 'connecting') {
      lastError.value = null
    }
  }

  function setError(error: ErrorEventData) {
    lastError.value = error
    if (!error.recoverable) {
      status.value = 'error'
    }
  }

  function setHeartbeat(timestamp: string) {
    lastHeartbeat.value = timestamp
  }

  function clearError() {
    lastError.value = null
    if (status.value === 'error') {
      status.value = 'disconnected'
    }
  }

  function reset() {
    status.value = 'disconnected'
    lastError.value = null
    lastHeartbeat.value = null
  }

  return {
    // 状态
    status,
    lastError,
    lastHeartbeat,
    // 计算属性
    isConnected,
    isConnecting,
    hasError,
    // Actions
    setStatus,
    setError,
    setHeartbeat,
    clearError,
    reset,
  }
})
