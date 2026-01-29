import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ConnectionStatus } from '@/types/sse'

export const useConnectionStore = defineStore('connection', () => {
  // 状态
  const status = ref<ConnectionStatus>('disconnected')
  const lastHeartbeat = ref<string | null>(null)

  // 计算属性
  const isConnected = computed(() => status.value === 'connected')
  const isConnecting = computed(() => status.value === 'connecting')
  // Actions
  function setStatus(newStatus: ConnectionStatus) {
    status.value = newStatus
  }

  function setHeartbeat(timestamp: string) {
    lastHeartbeat.value = timestamp
  }

  function reset() {
    status.value = 'disconnected'
    lastHeartbeat.value = null
  }

  return {
    // 状态
    status,
    lastHeartbeat,
    // 计算属性
    isConnected,
    isConnecting,
    // Actions
    setStatus,
    setHeartbeat,
    reset,
  }
})
