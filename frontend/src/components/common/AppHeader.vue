<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSSE } from '@/composables/useSSE'
import { useAuthStore, useConnectionStore, useTaskStore, useToastStore } from '@/stores'
import { taskService } from '@/services/taskService'
import type { CreateTaskRequest, TaskState } from '@/types/task'
import ConnectionStatus from './ConnectionStatus.vue'
import GameCommandBar from './GameCommandBar.vue'
import ActiveGamesDropdown from './ActiveGamesDropdown.vue'
import UserMenu from './UserMenu.vue'

const router = useRouter()
const { disconnect, reconnect, subscribeTask, createAndSubscribe } = useSSE()
const authStore = useAuthStore()
const connectionStore = useConnectionStore()
const taskStore = useTaskStore()
const toastStore = useToastStore()
const gameCommandBarKey = ref(0)

type CreateTaskCallbacks = {
  onSuccess?: () => void
  onError?: () => void
  onFinally?: () => void
}

const TERMINAL_STATES: TaskState[] = ['completed', 'cancelled', 'failed']

async function handleCreateAndSubscribe(request: CreateTaskRequest, callbacks?: CreateTaskCallbacks) {
  try {
    await createAndSubscribe(request)
    callbacks?.onSuccess?.()
  } catch {
    callbacks?.onError?.()
  } finally {
    callbacks?.onFinally?.()
  }
}

function handleSubscribeTask(taskId: string) {
  subscribeTask(taskId)
}

async function handleCancelTask(taskId: string) {
  const isCurrentTask = taskStore.currentTaskId === taskId
  const task = taskStore.tasks.find((item) => item.task_id === taskId)
  if (!task) {
    toastStore.showError('任务不存在')
    return
  }

  try {
    if (!TERMINAL_STATES.includes(task.state)) {
      if (task.state !== 'cancelling') {
        await taskService.cancelTask(taskId, authStore.token)
        taskStore.updateTaskState(taskId, 'cancelling')
      }
      await waitForTaskTerminal(taskId)
    }

    await taskService.deleteTask(taskId, authStore.token)
    taskStore.removeTask(taskId)
    toastStore.showSuccess('任务已删除')

    if (isCurrentTask) {
      disconnect()
      gameCommandBarKey.value += 1
    }
  } catch (error) {
    toastStore.showError(error instanceof Error ? error.message : '删除任务失败')
  }
}

async function waitForTaskTerminal(taskId: string): Promise<void> {
  const maxAttempts = 20
  const intervalMs = 800

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const status = await taskService.getTask(taskId, authStore.token)
    taskStore.addTask(status)
    if (TERMINAL_STATES.includes(status.state)) {
      return
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
  }

  throw new Error('任务取消超时，请稍后重试删除')
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
</script>

<template>
  <header class="navbar app-header sticky top-0 z-50">
    <div class="w-full px-4 sm:px-6 lg:px-8 grid grid-cols-[auto_1fr_auto] items-center gap-4">
      <!-- 左侧：Logo + 活跃任务 + 连接状态 -->
      <div class="flex items-center gap-2 flex-nowrap">
        <RouterLink to="/" class="btn btn-ghost text-xl font-bold px-2">
          NBA
        </RouterLink>
        <ActiveGamesDropdown
          @subscribe="handleSubscribeTask"
          @cancel="handleCancelTask"
        />
        <ConnectionStatus />
        <button
          v-if="connectionStore.isError"
          class="btn btn-error btn-xs"
          @click="handleReconnect"
        >
          重新连接
        </button>
      </div>

      <!-- 中间：GameCommandBar -->
      <div class="flex justify-center">
        <GameCommandBar
          :key="gameCommandBarKey"
          v-if="authStore.isAuthenticated"
          @submit="handleCreateAndSubscribe"
          @stop="handleDisconnect"
        />
      </div>

      <!-- 右侧：UserMenu 或登录按钮 -->
      <div class="flex items-center justify-end">
        <UserMenu
          v-if="authStore.isAuthenticated"
          @logout="handleLogout"
        />
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
