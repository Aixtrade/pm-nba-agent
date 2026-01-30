<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSSE } from '@/composables/useSSE'
import { useAuthStore, useConnectionStore } from '@/stores'
import type { LiveStreamRequest } from '@/types/sse'
import StreamConfig from '@/components/monitor/StreamConfig.vue'
import ConnectionStatus from './ConnectionStatus.vue'

const router = useRouter()
const { connect, disconnect, reconnect } = useSSE()
const connectionStore = useConnectionStore()
const isConfigOpen = ref(false)
const isPolymarketConfigOpen = ref(false)
const authStore = useAuthStore()
const polymarketPrivateKey = ref('')
const polymarketProxyAddress = ref('')

const POLYMARKET_PRIVATE_KEY = 'POLYMARKET_PRIVATE_KEY'
const POLYMARKET_PROXY_ADDRESS = 'POLYMARKET_PROXY_ADDRESS'

function handleConnect(request: LiveStreamRequest) {
  connect(request)
  isConfigOpen.value = false
}

function handleDisconnect() {
  disconnect()
}

function handleReconnect() {
  reconnect()
}

function handleLogout() {
  handleDisconnect()
  authStore.logout()
  router.push({ name: 'login' })
}

function loadPolymarketConfig() {
  polymarketPrivateKey.value = localStorage.getItem(POLYMARKET_PRIVATE_KEY) ?? ''
  polymarketProxyAddress.value = localStorage.getItem(POLYMARKET_PROXY_ADDRESS) ?? ''
}

function openPolymarketConfig() {
  loadPolymarketConfig()
  isPolymarketConfigOpen.value = true
}

function savePolymarketConfig() {
  const trimmedPrivateKey = polymarketPrivateKey.value.trim()
  const trimmedProxyAddress = polymarketProxyAddress.value.trim()

  if (trimmedPrivateKey) {
    localStorage.setItem(POLYMARKET_PRIVATE_KEY, trimmedPrivateKey)
  } else {
    localStorage.removeItem(POLYMARKET_PRIVATE_KEY)
  }

  if (trimmedProxyAddress) {
    localStorage.setItem(POLYMARKET_PROXY_ADDRESS, trimmedProxyAddress)
  } else {
    localStorage.removeItem(POLYMARKET_PROXY_ADDRESS)
  }

  isPolymarketConfigOpen.value = false
}

function clearPolymarketConfig() {
  polymarketPrivateKey.value = ''
  polymarketProxyAddress.value = ''
  localStorage.removeItem(POLYMARKET_PRIVATE_KEY)
  localStorage.removeItem(POLYMARKET_PROXY_ADDRESS)
}
</script>

<template>
  <header class="navbar app-header sticky top-0 z-50">
    <div class="w-full px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-4 flex-nowrap">
      <div class="flex-1 min-w-0 flex items-center gap-3 flex-nowrap">
        <RouterLink to="/" class="btn btn-ghost text-xl font-bold">
          NBA 实时监控
        </RouterLink>
        <ConnectionStatus />
        <button
          v-if="connectionStore.isError"
          class="btn btn-error btn-xs"
          @click="handleReconnect"
        >
          重新连接
        </button>
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
          class="btn btn-outline btn-sm"
          @click="openPolymarketConfig"
        >
          Polymarket 配置
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

  <dialog
    class="modal"
    :open="isPolymarketConfigOpen"
    @close="isPolymarketConfigOpen = false"
  >
    <div class="modal-box">
      <h3 class="text-lg font-semibold">Polymarket 配置</h3>
      <div class="mt-4 space-y-4">
        <label class="form-control w-full">
          <div class="label">
            <span class="label-text">POLYMARKET_PRIVATE_KEY</span>
          </div>
          <input
            v-model="polymarketPrivateKey"
            type="password"
            autocomplete="off"
            class="input input-bordered w-full"
            placeholder="输入私钥"
          />
        </label>
        <label class="form-control w-full">
          <div class="label">
            <span class="label-text">POLYMARKET_PROXY_ADDRESS</span>
          </div>
          <input
            v-model="polymarketProxyAddress"
            type="text"
            autocomplete="off"
            class="input input-bordered w-full"
            placeholder="输入代理地址"
          />
        </label>
      </div>
      <div class="mt-6 flex items-center justify-end gap-2">
        <button class="btn btn-ghost" @click="clearPolymarketConfig">
          清空
        </button>
        <button class="btn btn-primary" @click="savePolymarketConfig">
          保存
        </button>
      </div>
    </div>
    <form
      method="dialog"
      class="modal-backdrop"
      @click="isPolymarketConfigOpen = false"
    >
      <button>close</button>
    </form>
  </dialog>
</template>

<style scoped>
.app-header {
  background: rgba(255, 255, 255, 0.78);
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}
</style>
