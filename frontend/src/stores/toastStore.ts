import { defineStore } from 'pinia'
import { ref } from 'vue'

type ToastType = 'success' | 'error' | 'info' | 'warning'

type ToastItem = {
  id: number
  message: string
  type: ToastType
}

const DEFAULT_DURATION = 3200
let toastSeed = 0

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<ToastItem[]>([])
  const timeouts = new Map<number, number>()

  function removeToast(id: number) {
    const index = toasts.value.findIndex(item => item.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
    const timeout = timeouts.get(id)
    if (timeout) {
      window.clearTimeout(timeout)
      timeouts.delete(id)
    }
  }

  function showToast(message: string, type: ToastType = 'info', duration = DEFAULT_DURATION) {
    if (!message) return
    const id = toastSeed++
    toasts.value.push({ id, message, type })

    if (duration > 0) {
      const timeout = window.setTimeout(() => removeToast(id), duration)
      timeouts.set(id, timeout)
    }
  }

  // 便捷方法
  function showSuccess(message: string, duration = DEFAULT_DURATION) {
    showToast(message, 'success', duration)
  }

  function showError(message: string, duration = DEFAULT_DURATION) {
    showToast(message, 'error', duration)
  }

  function showInfo(message: string, duration = DEFAULT_DURATION) {
    showToast(message, 'info', duration)
  }

  function showWarning(message: string, duration = DEFAULT_DURATION) {
    showToast(message, 'warning', duration)
  }

  function clearAll() {
    toasts.value = []
    timeouts.forEach(timeout => window.clearTimeout(timeout))
    timeouts.clear()
  }

  return {
    toasts,
    showToast,
    showSuccess,
    showError,
    showInfo,
    showWarning,
    removeToast,
    clearAll,
  }
})
