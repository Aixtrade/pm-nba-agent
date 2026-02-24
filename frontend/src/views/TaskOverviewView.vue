<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue"
import { useRouter } from "vue-router"
import { taskOverviewSSEService } from "@/services/taskOverviewSSEService"
import { useAuthStore, useTaskOverviewStore, useToastStore } from "@/stores"
import type { TaskState } from "@/types/task"

const authStore = useAuthStore()
const toastStore = useToastStore()
const overviewStore = useTaskOverviewStore()
const router = useRouter()

const streamConnected = ref(false)

const activeTasks = computed(() => overviewStore.activeTasks)

function formatMatchup(item: { away_team?: string | null; home_team?: string | null; task_id: string }): string {
  if (item.away_team && item.home_team) {
    return `${item.away_team} @ ${item.home_team}`
  }
  return `任务 ${item.task_id.slice(0, 8)}`
}

function formatTime(value?: string | null): string {
  if (!value) return "--"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "--"
  return date.toLocaleTimeString("zh-CN", { hour12: false })
}

function formatDateTime(value?: string | null): string {
  if (!value) return "--"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "--"
  return `${date.toLocaleDateString("zh-CN")} ${date.toLocaleTimeString("zh-CN", { hour12: false })}`
}

function formatNumber(value?: number | null, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "--"
  return value.toFixed(digits)
}

function stateLabel(state: TaskState): string {
  switch (state) {
    case "pending":
      return "等待中"
    case "running":
      return "运行中"
    case "cancelling":
      return "取消中"
    case "completed":
      return "已完成"
    case "cancelled":
      return "已取消"
    case "failed":
      return "失败"
    default:
      return state
  }
}

function stateClass(state: TaskState): string {
  switch (state) {
    case "running":
      return "badge-success"
    case "pending":
      return "badge-warning"
    case "cancelling":
      return "badge-warning"
    case "failed":
      return "badge-error"
    default:
      return "badge-ghost"
  }
}

function executionClass(success: boolean): string {
  return success ? "text-emerald-600" : "text-rose-600"
}

function openTask(taskId: string) {
  void router.push({
    name: "monitor",
    query: { task_id: taskId },
  })
}

function refreshActiveTaskBindings() {
  const activeTaskIds = overviewStore.activeTasks.map((item) => item.task.task_id)
  overviewStore.setSubscribedTaskIds(activeTaskIds)
  overviewStore.setConnections(activeTaskIds, streamConnected.value ? "connected" : "disconnected")
}

async function connectStream(showLoader = false): Promise<void> {
  if (!authStore.token) return
  if (showLoader) {
    overviewStore.setLoading(true)
  }

  try {
    await taskOverviewSSEService.connect(authStore.token)
    overviewStore.setError(null)
    overviewStore.setLastSyncedNow()
  } catch (error) {
    const message = error instanceof Error ? error.message : "任务总览连接失败"
    overviewStore.setError(message)
    if (showLoader) {
      toastStore.showWarning(message)
    }
  } finally {
    overviewStore.setLoading(false)
  }
}

onMounted(() => {
  taskOverviewSSEService.setHandlers({
    onTaskStatus: (data) => {
      overviewStore.upsertTaskStatus(data)
      refreshActiveTaskBindings()
      overviewStore.setLastSyncedNow()
    },
    onTaskEnd: (data) => {
      overviewStore.updateTaskState(data.task_id, data.state)
      overviewStore.setTaskConnection(data.task_id, "disconnected")
      refreshActiveTaskBindings()
      overviewStore.setLastSyncedNow()
    },
    onTaskPositionState: (data) => {
      overviewStore.setTaskConnection(data.task_id, "connected")
      overviewStore.setPositionState(data.task_id, data)
      overviewStore.setLastSyncedNow()
    },
    onExecution: (event) => {
      overviewStore.setTaskConnection(event.task_id, "connected")
      overviewStore.addExecution(event)
      overviewStore.setLastSyncedNow()
    },
    onConnectionChange: (isConnected) => {
      streamConnected.value = isConnected
      refreshActiveTaskBindings()
      if (isConnected) {
        overviewStore.setError(null)
        overviewStore.setLastSyncedNow()
      }
      overviewStore.setLoading(false)
    },
    onError: (error) => {
      if (error?.message) {
        overviewStore.setError(error.message)
      }
    },
  })

  void connectStream(true)
})

onUnmounted(() => {
  taskOverviewSSEService.disconnect()
  overviewStore.reset()
})
</script>

<template>
  <section class="mx-auto w-full max-w-[1500px] space-y-5">
    <div class="overview-hero rounded-2xl p-5 md:p-6">
      <div class="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 class="text-xl md:text-2xl font-semibold tracking-tight">任务总览</h1>
          <p class="mt-1 text-sm text-base-content/70">
            点击任务卡可进入原任务监控界面。
          </p>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-xs text-base-content/60">更新 {{ formatDateTime(overviewStore.lastSyncedAt) }}</span>
          <button class="btn btn-sm btn-primary" :disabled="overviewStore.isLoading" @click="connectStream(true)">
            {{ overviewStore.isLoading ? "连接中..." : streamConnected ? "刷新连接" : "连接" }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="overviewStore.error" class="alert alert-warning">
      <span>{{ overviewStore.error }}</span>
    </div>

    <div class="task-grid">
      <article
        v-for="item in activeTasks"
        :key="item.task.task_id"
        class="task-card rounded-2xl p-4 md:p-5"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <h2
              class="text-base font-semibold truncate cursor-pointer hover:text-primary transition-colors"
              role="button"
              tabindex="0"
              @click="openTask(item.task.task_id)"
              @keydown.enter="openTask(item.task.task_id)"
              @keydown.space.prevent="openTask(item.task.task_id)"
            >
              {{ formatMatchup(item.task) }}
            </h2>
            <p class="mt-1 text-[11px] text-base-content/55">更新于 {{ formatDateTime(item.task.updated_at) }}</p>
          </div>
          <span class="badge badge-sm" :class="stateClass(item.task.state)">{{ stateLabel(item.task.state) }}</span>
        </div>

        <div class="mt-4 rounded-xl bg-base-100/75 p-3">
          <div class="mb-2 flex items-center justify-between text-xs text-base-content/60">
            <span>持仓</span>
            <span>{{ item.position?.loading ? "刷新中..." : formatTime(item.position?.updated_at ?? item.position?.timestamp) }}</span>
          </div>
          <div v-if="item.position?.sides?.length" class="flex flex-nowrap gap-2 overflow-x-auto pb-1">
            <div
              v-for="side in item.position.sides"
              :key="`${item.task.task_id}-${side.outcome}`"
              class="min-w-[240px] flex-1 rounded-lg border border-base-200/80 bg-base-100 px-3 py-2"
            >
              <div class="flex items-center justify-between text-sm font-semibold">
                <span>{{ side.outcome }}</span>
                <span>{{ formatNumber(side.size) }}</span>
              </div>
              <div class="mt-1 flex items-center justify-between text-[11px] text-base-content/60">
                <span>成本 {{ formatNumber(side.initial_value) }}</span>
                <span>{{ formatNumber(side.avg_price, 3) }} / {{ formatNumber(side.cur_price, 3) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="py-3 text-center text-sm text-base-content/45">暂无持仓</div>
        </div>

        <div class="mt-3 rounded-xl bg-base-100/75 p-3">
          <div class="mb-2 text-xs text-base-content/60">最近执行</div>
          <div v-if="item.executions.length" class="space-y-2">
            <div
              v-for="exec in item.executions.slice(0, 3)"
              :key="`${item.task.task_id}-${exec.timestamp}-${exec.source}`"
              class="flex items-center justify-between rounded-lg border border-base-200/80 bg-base-100 px-3 py-2 text-xs"
            >
              <div class="min-w-0">
                <div class="font-semibold truncate">{{ exec.source }}</div>
                <div class="text-base-content/60">{{ formatTime(exec.timestamp) }} · {{ exec.orders.length }} 笔</div>
              </div>
              <div :class="executionClass(exec.success)">{{ exec.success ? "成功" : "失败" }}</div>
            </div>
          </div>
          <div v-else class="py-2 text-center text-sm text-base-content/45">暂无执行</div>
        </div>
      </article>

      <div v-if="activeTasks.length === 0" class="task-card rounded-2xl p-10 text-center text-base-content/55">
        当前没有运行中的任务
      </div>
    </div>
  </section>
</template>

<style scoped>
.overview-hero {
  background:
    radial-gradient(140% 140% at 0% 0%, rgba(14, 165, 233, 0.16), transparent 62%),
    radial-gradient(140% 140% at 100% 0%, rgba(16, 185, 129, 0.12), transparent 58%),
    rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
}

.task-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

@media (min-width: 1100px) {
  .task-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.task-card {
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.07);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.task-card:hover {
  transform: translateY(-2px);
  border-color: rgba(14, 165, 233, 0.35);
  box-shadow: 0 18px 34px rgba(14, 165, 233, 0.12);
}
</style>
