<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSSE } from '@/composables/useSSE'
import { useAuthStore } from '@/stores'
import type { LiveStreamRequest } from '@/types/sse'
import StreamConfig from '@/components/monitor/StreamConfig.vue'
import ConnectionStatus from './ConnectionStatus.vue'

const router = useRouter()
const { connect, disconnect } = useSSE()
const isConfigOpen = ref(false)
const authStore = useAuthStore()

function handleConnect(request: LiveStreamRequest) {
  connect(request)
  isConfigOpen.value = false
}

function handleDisconnect() {
  disconnect()
}

function handleLogout() {
  handleDisconnect()
  authStore.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <header class="navbar bg-base-100 shadow-md">
    <div class="w-full px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-4 flex-nowrap">
      <div class="flex-1 min-w-0 flex items-center gap-3 flex-nowrap">
        <RouterLink to="/" class="btn btn-ghost text-xl font-bold">
          NBA 实时监控
        </RouterLink>
        <ConnectionStatus />
      </div>
      <div class="flex-none flex items-center gap-2">
        <button
          v-if="authStore.isAuthenticated"
          class="btn btn-outline btn-sm"
          @click="isConfigOpen = true"
        >
          比赛列表
        </button>
        <button
          v-if="authStore.isAuthenticated"
          class="btn btn-ghost btn-sm"
          @click="handleLogout"
        >
          退出
        </button>
        <RouterLink
          v-else
          class="btn btn-primary btn-sm"
          to="/login"
        >
          登录
        </RouterLink>
      </div>
    </div>
  </header>

  <dialog class="modal" :open="isConfigOpen" @close="isConfigOpen = false">
    <div class="modal-box p-0 relative">
      <button
        class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2"
        @click="isConfigOpen = false"
      >
        ✕
      </button>
      <StreamConfig
        @connect="handleConnect"
        @disconnect="handleDisconnect"
      />
    </div>
    <form method="dialog" class="modal-backdrop" @click="isConfigOpen = false">
      <button>close</button>
    </form>
  </dialog>
</template>
