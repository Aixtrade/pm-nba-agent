import { computed, ref } from "vue"
import { defineStore } from "pinia"
import type { PositionStateEventData } from "@/types/sse"
import type { TaskStatus, TaskState } from "@/types/task"
import type { TaskConnectionState, TaskExecutionEvent, TaskOverviewItem } from "@/types/taskOverview"

const ACTIVE_STATES: TaskState[] = ["pending", "running", "cancelling"]
const PER_TASK_EXECUTIONS_LIMIT = 20
const GLOBAL_EXECUTIONS_LIMIT = 200

export const useTaskOverviewStore = defineStore("taskOverview", () => {
  const items = ref<Record<string, TaskOverviewItem>>({})
  const subscribedTaskIds = ref<string[]>([])
  const globalExecutions = ref<TaskExecutionEvent[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const lastSyncedAt = ref<string | null>(null)

  const allTasks = computed(() =>
    Object.values(items.value).sort((a, b) => b.task.updated_at.localeCompare(a.task.updated_at)),
  )

  const activeTasks = computed(() =>
    allTasks.value.filter((item) => ACTIVE_STATES.includes(item.task.state)),
  )

  const activeTaskCount = computed(() => activeTasks.value.length)

  const connectedTaskCount = computed(
    () => activeTasks.value.filter((item) => item.connection === "connected").length,
  )

  const loadingPositionCount = computed(
    () => activeTasks.value.filter((item) => item.position?.loading).length,
  )

  function ensureItem(task: TaskStatus): TaskOverviewItem {
    const existing = items.value[task.task_id]
    if (existing) {
      existing.task = task
      return existing
    }

    const created: TaskOverviewItem = {
      task,
      position: null,
      executions: [],
      connection: "disconnected",
      last_event_at: null,
    }
    items.value[task.task_id] = created
    return created
  }

  function setTasks(tasks: TaskStatus[]) {
    const next: Record<string, TaskOverviewItem> = {}
    for (const task of tasks) {
      const prev = items.value[task.task_id]
      next[task.task_id] = {
        task,
        position: prev?.position ?? null,
        executions: prev?.executions ?? [],
        connection: prev?.connection ?? "disconnected",
        last_event_at: prev?.last_event_at ?? null,
      }
    }
    items.value = next
  }

  function upsertTaskStatus(task: TaskStatus) {
    ensureItem(task)
  }

  function updateTaskState(taskId: string, state: TaskState) {
    const item = items.value[taskId]
    if (!item) return
    item.task.state = state
    item.task.updated_at = new Date().toISOString()
  }

  function setTaskConnection(taskId: string, state: TaskConnectionState) {
    const item = items.value[taskId]
    if (!item) return
    item.connection = state
    if (state === "connected") {
      item.last_event_at = new Date().toISOString()
    }
  }

  function setConnections(taskIds: string[], state: TaskConnectionState) {
    for (const taskId of taskIds) {
      setTaskConnection(taskId, state)
    }
  }

  function setPositionState(taskId: string, data: PositionStateEventData) {
    const item = items.value[taskId]
    if (!item) return
    item.position = data
    item.last_event_at = data.timestamp ?? new Date().toISOString()
  }

  function addExecution(execution: TaskExecutionEvent) {
    const item = items.value[execution.task_id]
    if (!item) return

    item.executions = [execution, ...item.executions].slice(0, PER_TASK_EXECUTIONS_LIMIT)
    item.last_event_at = execution.timestamp
    globalExecutions.value = [execution, ...globalExecutions.value].slice(0, GLOBAL_EXECUTIONS_LIMIT)
  }

  function setSubscribedTaskIds(taskIds: string[]) {
    subscribedTaskIds.value = taskIds
  }

  function setLoading(loading: boolean) {
    isLoading.value = loading
  }

  function setError(message: string | null) {
    error.value = message
  }

  function setLastSyncedNow() {
    lastSyncedAt.value = new Date().toISOString()
  }

  function reset() {
    items.value = {}
    subscribedTaskIds.value = []
    globalExecutions.value = []
    isLoading.value = false
    error.value = null
    lastSyncedAt.value = null
  }

  return {
    items,
    subscribedTaskIds,
    globalExecutions,
    isLoading,
    error,
    lastSyncedAt,
    allTasks,
    activeTasks,
    activeTaskCount,
    connectedTaskCount,
    loadingPositionCount,
    setTasks,
    upsertTaskStatus,
    updateTaskState,
    setTaskConnection,
    setConnections,
    setPositionState,
    addExecution,
    setSubscribedTaskIds,
    setLoading,
    setError,
    setLastSyncedNow,
    reset,
  }
})
