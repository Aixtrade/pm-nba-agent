<script setup lang="ts">
import { computed } from 'vue'
import { useConnectionStore } from '@/stores'

const connectionStore = useConnectionStore()

const statusConfig = computed(() => {
  switch (connectionStore.status) {
    case 'connected':
      return { text: '已连接', class: 'badge-success' }
    case 'connecting':
      return { text: '连接中...', class: 'badge-warning' }
    default:
      return { text: '未连接', class: 'badge-neutral' }
  }
})
</script>

<template>
  <div class="flex items-center gap-2">
    <span class="badge" :class="statusConfig.class">
      <span
        v-if="connectionStore.isConnecting"
        class="loading loading-spinner loading-xs mr-1"
      ></span>
      {{ statusConfig.text }}
    </span>
  </div>
</template>
