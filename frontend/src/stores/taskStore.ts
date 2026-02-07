import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { TaskStatus, TaskState } from '@/types/task'

export const useTaskStore = defineStore('task', () => {
  // 状态
  const tasks = ref<TaskStatus[]>([])
  const currentTaskId = ref<string | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // 计算属性
  const currentTask = computed(() =>
    tasks.value.find((t) => t.task_id === currentTaskId.value) ?? null
  )

  const activeTasks = computed(() =>
    tasks.value.filter((t) => t.state === 'pending' || t.state === 'running' || t.state === 'cancelling')
  )

  const hasActiveTasks = computed(() => activeTasks.value.length > 0)

  // Actions
  function setTasks(newTasks: TaskStatus[]) {
    tasks.value = newTasks
  }

  function addTask(task: TaskStatus) {
    const index = tasks.value.findIndex((t) => t.task_id === task.task_id)
    if (index >= 0) {
      tasks.value[index] = task
    } else {
      tasks.value.unshift(task)
    }
  }

  function updateTaskState(taskId: string, state: TaskState) {
    const task = tasks.value.find((t) => t.task_id === taskId)
    if (task) {
      task.state = state
      task.updated_at = new Date().toISOString()
    }
  }

  function removeTask(taskId: string) {
    const index = tasks.value.findIndex((t) => t.task_id === taskId)
    if (index >= 0) {
      tasks.value.splice(index, 1)
    }
    if (currentTaskId.value === taskId) {
      currentTaskId.value = null
    }
  }

  function setCurrentTask(taskId: string | null) {
    currentTaskId.value = taskId
  }

  function setLoading(loading: boolean) {
    isLoading.value = loading
  }

  function setError(err: string | null) {
    error.value = err
  }

  function reset() {
    tasks.value = []
    currentTaskId.value = null
    isLoading.value = false
    error.value = null
  }

  return {
    // 状态
    tasks,
    currentTaskId,
    isLoading,
    error,
    // 计算属性
    currentTask,
    activeTasks,
    hasActiveTasks,
    // Actions
    setTasks,
    addTask,
    updateTaskState,
    removeTask,
    setCurrentTask,
    setLoading,
    setError,
    reset,
  }
})
