<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSSE } from '@/composables/useSSE'
import { useAuthStore, useConnectionStore, useGameStore, useTaskStore } from '@/stores'
import type { CreateTaskRequest } from '@/types/task'
import TaskCreateForm from '@/components/monitor/TaskCreateForm.vue'
import TaskListPanel from '@/components/monitor/TaskListPanel.vue'
import ConnectionStatus from './ConnectionStatus.vue'

const router = useRouter()
const { disconnect, reconnect, subscribeTask, createAndSubscribe } = useSSE()
const connectionStore = useConnectionStore()
const gameStore = useGameStore()
const taskStore = useTaskStore()
const isCreateTaskOpen = ref(false)
const isTaskListOpen = ref(false)
const isPolymarketConfigOpen = ref(false)
const authStore = useAuthStore()
const polymarketPrivateKey = ref('')
const polymarketProxyAddress = ref('')

// 比分板相关计算属性
const hasScoreData = computed(() => gameStore.homeTeam && gameStore.awayTeam)

const periodDisplay = computed(() => {
  const scoreboard = gameStore.scoreboard
  if (!scoreboard) return ''
  const period = scoreboard.period
  if (period <= 4) return `Q${period}`
  return `OT${period - 4}`
})

const statusBadgeClass = computed(() => {
  const status = gameStore.gameStatus.toLowerCase()
  if (status.includes('live') || status.includes('进行中')) return 'badge-success'
  if (status.includes('final') || status.includes('结束')) return 'badge-neutral'
  return 'badge-info'
})

const POLYMARKET_PRIVATE_KEY = 'POLYMARKET_PRIVATE_KEY'
const POLYMARKET_PROXY_ADDRESS = 'POLYMARKET_PROXY_ADDRESS'

type CreateTaskCallbacks = {
  onSuccess?: () => void
  onError?: (message: string) => void
  onFinally?: () => void
}

function handleDisconnect() {
  disconnect()
}

function handleReconnect() {
  reconnect()
}

function handleSubscribeTask(taskId: string) {
  subscribeTask(taskId)
  isTaskListOpen.value = false
}

async function handleCreateAndSubscribe(
  request: CreateTaskRequest,
  callbacks?: CreateTaskCallbacks,
) {
  try {
    await createAndSubscribe(request)
    callbacks?.onSuccess?.()
    isCreateTaskOpen.value = false
  } catch (error) {
    const message = error instanceof Error ? error.message : '创建任务失败'
    callbacks?.onError?.(message)
  } finally {
    callbacks?.onFinally?.()
  }
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
    <div class="w-full px-4 sm:px-6 lg:px-8 grid grid-cols-[1fr_auto_1fr] items-center gap-4">
      <!-- 左侧：标题和连接状态 -->
      <div class="flex items-center gap-3 flex-nowrap">
        <RouterLink to="/" class="btn btn-ghost text-xl font-bold px-2">
          NBA
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

      <!-- 中间：比分显示（居中） -->
      <div v-if="hasScoreData" class="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-base-200/50">
        <span class="badge badge-sm" :class="statusBadgeClass">{{ gameStore.gameStatus }}</span>
        <div class="flex items-center gap-2 text-sm font-semibold">
          <span class="text-base-content/70">{{ gameStore.awayTeam!.abbreviation }}</span>
          <span class="text-lg tabular-nums">{{ gameStore.awayTeam!.score }}</span>
          <span class="text-base-content/40">-</span>
          <span class="text-lg tabular-nums">{{ gameStore.homeTeam!.score }}</span>
          <span class="text-base-content/70">{{ gameStore.homeTeam!.abbreviation }}</span>
        </div>
        <span v-if="gameStore.scoreboard" class="text-xs text-base-content/50">
          {{ periodDisplay }} {{ gameStore.scoreboard.game_clock }}
        </span>
      </div>
      <div v-else></div>

      <!-- 右侧：操作按钮 -->
      <div class="flex items-center justify-end gap-2">
        <button
          v-if="authStore.isAuthenticated"
          class="btn btn-primary btn-sm"
          @click="isCreateTaskOpen = true"
        >
          创建任务
        </button>
        <button
          v-if="authStore.isAuthenticated"
          class="btn btn-outline btn-sm"
          :class="{ 'btn-primary': taskStore.hasActiveTasks }"
          @click="isTaskListOpen = true"
        >
          任务管理
          <span v-if="taskStore.activeTasks.length" class="badge badge-sm">
            {{ taskStore.activeTasks.length }}
          </span>
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

  <dialog class="modal" :open="isCreateTaskOpen" @close="isCreateTaskOpen = false">
    <div class="modal-box p-0 relative max-w-2xl">
      <button
        class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2 z-10"
        @click="isCreateTaskOpen = false"
      >
        ✕
      </button>
      <TaskCreateForm @create-and-subscribe="handleCreateAndSubscribe" />
    </div>
    <form method="dialog" class="modal-backdrop" @click="isCreateTaskOpen = false">
      <button>close</button>
    </form>
  </dialog>

  <dialog class="modal" :open="isTaskListOpen" @close="isTaskListOpen = false">
    <div class="modal-box p-0 relative max-w-xl">
      <button
        class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2 z-10"
        @click="isTaskListOpen = false"
      >
        ✕
      </button>
      <TaskListPanel
        @subscribe="handleSubscribeTask"
        @disconnect="handleDisconnect"
      />
    </div>
    <form method="dialog" class="modal-backdrop" @click="isTaskListOpen = false">
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
