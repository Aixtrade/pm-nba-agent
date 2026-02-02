<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore, useConnectionStore, useTaskStore, useToastStore } from '@/stores'
import { taskService } from '@/services/taskService'
import type { TaskStatus, TaskState } from '@/types/task'

const emit = defineEmits<{
  subscribe: [taskId: string]
  disconnect: []
}>()

const authStore = useAuthStore()
const connectionStore = useConnectionStore()
const taskStore = useTaskStore()
const toastStore = useToastStore()

// 刷新状态
const isRefreshing = ref(false)

const activeTasks = computed(() =>
  taskStore.tasks.filter((task) => task.state === 'running' || task.state === 'pending')
)

// 状态标签样式
function getStateBadgeClass(state: TaskState): string {
  switch (state) {
    case 'running':
      return 'badge-success'
    case 'pending':
      return 'badge-warning'
    case 'completed':
      return 'badge-info'
    case 'cancelled':
      return 'badge-neutral'
    case 'failed':
      return 'badge-error'
    default:
      return 'badge-ghost'
  }
}

function getStateLabel(state: TaskState): string {
  switch (state) {
    case 'running':
      return '运行中'
    case 'pending':
      return '等待中'
    case 'completed':
      return '已完成'
    case 'cancelled':
      return '已取消'
    case 'failed':
      return '失败'
    default:
      return state
  }
}

function formatTime(isoTime: string): string {
  const date = new Date(isoTime)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

async function refreshTasks() {
  if (!authStore.isAuthenticated) return

  isRefreshing.value = true
  try {
    const response = await taskService.listTasks(authStore.token)
    taskStore.setTasks(response.tasks)
  } catch (error) {
    console.error('刷新任务列表失败:', error)
    toastStore.showError('刷新任务列表失败')
  } finally {
    isRefreshing.value = false
  }
}

async function handleSubscribe(task: TaskStatus) {
  if (task.state !== 'running' && task.state !== 'pending') {
    toastStore.showWarning('只能订阅运行中或等待中的任务')
    return
  }

  taskStore.setCurrentTask(task.task_id)
  emit('subscribe', task.task_id)
}

async function handleCancelTask(taskId: string) {
  try {
    await taskService.cancelTask(taskId, authStore.token)
    taskStore.updateTaskState(taskId, 'cancelled')
    toastStore.showSuccess('任务已取消')

    // 如果是当前订阅的任务，断开连接
    if (taskStore.currentTaskId === taskId) {
      emit('disconnect')
    }
  } catch (error) {
    toastStore.showError(error instanceof Error ? error.message : '取消任务失败')
  }
}

function handleDisconnect() {
  emit('disconnect')
}

onMounted(() => {
  refreshTasks()
})
</script>

<template>
  <div class="card bg-base-100 shadow-md">
    <div class="card-body">
      <div class="flex items-center justify-between">
        <h2 class="card-title">任务管理</h2>
        <button
          class="btn btn-ghost btn-sm"
          :class="{ loading: isRefreshing }"
          :disabled="isRefreshing"
          @click="refreshTasks"
        >
          <svg
            v-if="!isRefreshing"
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          <span v-else>刷新中</span>
        </button>
      </div>

      <!-- 任务列表 -->
      <div class="divider my-2">运行中任务</div>

      <div v-if="activeTasks.length" class="space-y-2 max-h-80 overflow-y-auto">
        <div
          v-for="task in activeTasks"
          :key="task.task_id"
          class="flex items-start gap-3 p-3 rounded-lg border border-base-200"
          :class="{
            'bg-primary/5 border-primary/30': task.task_id === taskStore.currentTaskId,
          }"
        >
          <div class="flex-1 min-w-0 space-y-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-mono text-sm">{{ task.task_id }}</span>
              <span class="badge badge-sm" :class="getStateBadgeClass(task.state)">
                {{ getStateLabel(task.state) }}
              </span>
              <span
                v-if="task.task_id === taskStore.currentTaskId && connectionStore.isConnected"
                class="badge badge-sm badge-outline badge-success"
              >
                已订阅
              </span>
            </div>
            <div v-if="task.home_team && task.away_team" class="text-sm">
              {{ task.away_team }} @ {{ task.home_team }}
            </div>
            <div class="text-xs text-base-content/60">
              创建于 {{ formatTime(task.created_at) }}
            </div>
            <div v-if="task.error" class="text-xs text-error">
              {{ task.error }}
            </div>
          </div>

          <div class="flex gap-1">
            <button
              v-if="task.state === 'running' || task.state === 'pending'"
              class="btn btn-ghost btn-xs"
              :disabled="
                task.task_id === taskStore.currentTaskId && connectionStore.isConnected
              "
              @click="handleSubscribe(task)"
            >
              订阅
            </button>
            <button
              v-if="task.state === 'running' || task.state === 'pending'"
              class="btn btn-ghost btn-xs text-error"
              @click="handleCancelTask(task.task_id)"
            >
              取消
            </button>
          </div>
        </div>
      </div>
      <div v-else class="text-sm text-base-content/60 py-4 text-center">
        暂无运行中的任务
      </div>

      <!-- 断开当前订阅 -->
      <div v-if="connectionStore.isConnected && taskStore.currentTaskId" class="card-actions justify-end mt-4">
        <button class="btn btn-error btn-sm" @click="handleDisconnect">
          断开订阅
        </button>
      </div>
    </div>
  </div>
</template>
