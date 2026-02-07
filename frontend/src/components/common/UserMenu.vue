<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores'

const emit = defineEmits<{
  logout: []
}>()

const authStore = useAuthStore()

const POLYMARKET_PRIVATE_KEY = 'POLYMARKET_PRIVATE_KEY'
const POLYMARKET_PROXY_ADDRESS = 'POLYMARKET_PROXY_ADDRESS'

const isOpen = ref(false)
const showPolymarketConfig = ref(false)
const polymarketPrivateKey = ref('')
const polymarketProxyAddress = ref('')
const rootRef = ref<HTMLElement | null>(null)

const userInitial = () => {
  const name = authStore.username
  return name ? name.charAt(0).toUpperCase() : '?'
}

function toggle() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    loadPolymarketConfig()
  }
}

function close() {
  isOpen.value = false
}

function loadPolymarketConfig() {
  polymarketPrivateKey.value = localStorage.getItem(POLYMARKET_PRIVATE_KEY) ?? ''
  polymarketProxyAddress.value = localStorage.getItem(POLYMARKET_PROXY_ADDRESS) ?? ''
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

  showPolymarketConfig.value = false
}

function clearPolymarketConfig() {
  polymarketPrivateKey.value = ''
  polymarketProxyAddress.value = ''
  localStorage.removeItem(POLYMARKET_PRIVATE_KEY)
  localStorage.removeItem(POLYMARKET_PROXY_ADDRESS)
}

function handleLogout() {
  close()
  emit('logout')
}

function handleDocumentClick(event: MouseEvent) {
  const target = event.target as Node | null
  if (!target || !rootRef.value) return
  if (!rootRef.value.contains(target)) {
    close()
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleDocumentClick)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', handleDocumentClick)
})
</script>

<template>
  <div ref="rootRef" class="relative">
    <button
      class="btn btn-ghost btn-sm btn-circle avatar placeholder"
      @click="toggle"
    >
      <div class="bg-neutral text-neutral-content w-8 rounded-full flex items-center justify-center overflow-hidden">
        <span class="text-xs">{{ userInitial() }}</span>
      </div>
    </button>

    <div
      v-if="isOpen"
      class="absolute top-full right-0 mt-1 z-50 bg-base-100 rounded-box shadow-lg border border-base-200 w-72 p-3"
    >
      <!-- 用户信息 -->
      <div class="flex items-center gap-2 pb-2 border-b border-base-200">
        <div class="avatar placeholder">
          <div class="bg-neutral text-neutral-content w-8 rounded-full flex items-center justify-center overflow-hidden">
            <span class="text-xs">{{ userInitial() }}</span>
          </div>
        </div>
        <span class="text-sm font-medium">{{ authStore.username }}</span>
      </div>

      <!-- Polymarket 配置 -->
      <div class="py-2 border-b border-base-200">
        <button
          class="btn btn-ghost btn-sm btn-block justify-between font-normal"
          @click="showPolymarketConfig = !showPolymarketConfig"
        >
          <span class="text-sm">Polymarket 配置</span>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4 transition-transform"
            :class="{ 'rotate-180': showPolymarketConfig }"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <div v-if="showPolymarketConfig" class="mt-2 space-y-3 px-1">
          <div>
            <label class="text-xs text-base-content/60 block mb-1">Private Key</label>
            <input
              v-model="polymarketPrivateKey"
              type="password"
              autocomplete="off"
              class="input input-bordered input-xs w-full"
              placeholder="输入私钥"
            />
          </div>
          <div>
            <label class="text-xs text-base-content/60 block mb-1">Proxy Address</label>
            <input
              v-model="polymarketProxyAddress"
              type="text"
              autocomplete="off"
              class="input input-bordered input-xs w-full"
              placeholder="输入代理地址"
            />
          </div>
          <div class="flex justify-end gap-1">
            <button class="btn btn-ghost btn-xs" @click="clearPolymarketConfig">
              清空
            </button>
            <button class="btn btn-primary btn-xs" @click="savePolymarketConfig">
              保存
            </button>
          </div>
        </div>
      </div>

      <!-- 退出按钮 -->
      <div class="pt-2">
        <button
          class="btn btn-ghost btn-sm btn-block justify-start font-normal text-error"
          @click="handleLogout"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          退出
        </button>
      </div>
    </div>
  </div>
</template>
