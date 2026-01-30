<script setup lang="ts">
import { computed } from 'vue'
import { useConnectionStore } from '@/stores'

const connectionStore = useConnectionStore()

const statusConfig = computed(() => {
  switch (connectionStore.status) {
    case 'connected':
      return { text: '已连接', class: 'badge-success', showSpinner: false }
    case 'connecting':
      if (connectionStore.retryCount > 0) {
        return {
          text: `重连中 (${connectionStore.retryCount})`,
          class: 'badge-warning',
          showSpinner: true,
        }
      }
      return { text: '连接中...', class: 'badge-warning', showSpinner: true }
    case 'error':
      return { text: '连接失败', class: 'badge-error', showSpinner: false }
    default:
      return { text: '未连接', class: 'badge-neutral', showSpinner: false }
  }
})
</script>

<template>
  <div class="flex items-center gap-2">
    <span class="badge" :class="statusConfig.class">
      <span v-if="statusConfig.showSpinner" class="loading loading-spinner loading-xs mr-1"></span>
      {{ statusConfig.text }}
    </span>
  </div>
</template>
