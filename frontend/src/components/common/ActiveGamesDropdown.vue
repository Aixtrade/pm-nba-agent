<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore, useConnectionStore, useTaskStore, useToastStore } from '@/stores'
import { taskService } from '@/services/taskService'
import type { TaskState, TaskStatus } from '@/types/task'

const emit = defineEmits<{
  subscribe: [taskId: string]
  cancel: [taskId: string]
}>()

const authStore = useAuthStore()
const connectionStore = useConnectionStore()
const taskStore = useTaskStore()
const toastStore = useToastStore()

const isOpen = ref(false)
const isRefreshing = ref(false)
const rootRef = ref<HTMLElement | null>(null)

const activeTasks = computed(() =>
  taskStore.tasks.filter((t) => t.state === 'running' || t.state === 'pending' || t.state === 'cancelling'),
)

const activeCount = computed(() => activeTasks.value.length)

function getStateLabel(state: TaskState): string {
  switch (state) {
    case 'pending':
      return '等待中'
    case 'cancelling':
      return '取消中'
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

function getStateDotClass(state: TaskState): string {
  switch (state) {
    case 'running':
      return 'bg-emerald-500'
    case 'pending':
      return 'bg-amber-500'
    case 'cancelling':
      return 'bg-orange-500'
    default:
      return 'bg-slate-400'
  }
}

function getTaskDisplayName(task: TaskStatus): string {
  if (task.away_team && task.home_team) {
    return `${task.away_team} @ ${task.home_team}`
  }
  return task.task_id.slice(0, 8)
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

function handleSubscribe(task: TaskStatus) {
  if (task.state !== 'running' && task.state !== 'pending') {
    toastStore.showWarning('只能订阅运行中或等待中的任务')
    return
  }
  taskStore.setCurrentTask(task.task_id)
  emit('subscribe', task.task_id)
  isOpen.value = false
}

function handleCancel(taskId: string) {
  emit('cancel', taskId)
}

function toggle() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    void refreshTasks()
  }
}

function close() {
  isOpen.value = false
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
  if (authStore.isAuthenticated) {
    void refreshTasks()
  }
})

onUnmounted(() => {
  document.removeEventListener('mousedown', handleDocumentClick)
})
</script>

<template>
  <div v-if="authStore.isAuthenticated" ref="rootRef" class="relative">
    <button
      class="btn btn-ghost btn-sm gap-1"
      :class="{ 'btn-active': isOpen }"
      @click="toggle"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
      </svg>
      <span v-if="activeCount > 0" class="badge badge-sm badge-primary">
        {{ activeCount }}
      </span>
    </button>

    <!-- 下拉内容 -->
    <div
      v-if="isOpen"
      class="absolute top-full left-0 mt-1 z-50 bg-base-100 rounded-2xl shadow-xl border border-base-200 w-[360px] p-3"
    >
      <div class="flex items-center justify-between">
        <div class="text-base font-semibold tracking-tight">活跃任务</div>
        <button
          class="btn btn-ghost btn-xs text-base-content/60 hover:text-base-content"
          :disabled="isRefreshing"
          @click="refreshTasks"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-3.5 w-3.5"
            :class="{ 'animate-spin': isRefreshing }"
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
        </button>
      </div>

      <RouterLink
        to="/task-overview"
        class="mt-3 block rounded-xl border border-sky-200/70 bg-linear-to-r from-sky-50 to-cyan-50 px-3 py-2.5 hover:from-sky-100 hover:to-cyan-100 transition-colors"
        @click="close"
      >
        <div class="flex items-center justify-between gap-2">
          <div class="min-w-0">
            <div class="text-sm font-semibold text-sky-900">任务总览</div>
            <div class="text-[11px] text-sky-800/70 truncate">查看全部任务持仓与执行</div>
          </div>
          <span class="text-sky-700 text-sm">→</span>
        </div>
      </RouterLink>

      <div class="my-3 h-px bg-base-200"></div>

      <div v-if="activeTasks.length" class="space-y-1.5 max-h-72 overflow-y-auto pr-1">
        <div
          v-for="task in activeTasks"
          :key="task.task_id"
          class="flex items-center gap-2 rounded-lg border border-base-200/70 bg-base-100 px-2.5 py-2 hover:border-base-300 hover:bg-base-200/35 transition-colors"
          :class="{
            'border-primary/35 bg-primary/5': task.task_id === taskStore.currentTaskId && connectionStore.isConnected,
          }"
        >
          <div class="flex-1 min-w-0 pl-0.5">
            <div
              class="flex items-center gap-2 text-sm font-semibold truncate cursor-pointer hover:text-primary transition-colors"
              @click="handleSubscribe(task)"
            >
              <span class="h-2 w-2 rounded-full shrink-0" :class="getStateDotClass(task.state)"></span>
              <span class="truncate">{{ getTaskDisplayName(task) }}</span>
            </div>
            <div class="mt-0.5 flex items-center gap-1.5 text-[11px] text-base-content/55">
              <span>{{ getStateLabel(task.state) }}</span>
              <span>·</span>
              <span>#{{ task.task_id.slice(-4) }}</span>
              <span
                v-if="task.task_id === taskStore.currentTaskId && connectionStore.isConnected"
                class="badge badge-xs badge-outline badge-success ml-1"
              >
                正在观看
              </span>
            </div>
          </div>

          <div class="flex gap-1 shrink-0">
            <button
              class="btn btn-ghost btn-xs text-base-content/70 hover:text-base-content"
              :disabled="task.task_id === taskStore.currentTaskId && connectionStore.isConnected"
              title="查看"
              @click="handleSubscribe(task)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </button>
            <button
              class="btn btn-ghost btn-xs text-error/80 hover:text-error"
              title="停止"
              :disabled="task.state === 'cancelling'"
              @click="handleCancel(task.task_id)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <div v-else class="py-7 text-center">
        <div class="text-sm text-base-content/55">暂无活跃任务</div>
      </div>
    </div>

  </div>
</template>
