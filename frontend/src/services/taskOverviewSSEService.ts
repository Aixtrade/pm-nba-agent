import { fetchEventSource } from "@microsoft/fetch-event-source"
import type { PositionStateEventData } from "@/types/sse"
import type { TaskEndEventData, TaskStatusEventData } from "@/types/task"
import type { TaskExecutionEvent } from "@/types/taskOverview"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""

type UserTaskPositionStateEventData = PositionStateEventData & { task_id: string }
type UserTaskErrorEventData = { code?: string; message?: string; recoverable?: boolean; timestamp?: string }

interface TaskOverviewSSEHandlers {
  onTaskStatus?: (data: TaskStatusEventData) => void
  onTaskEnd?: (data: TaskEndEventData) => void
  onTaskPositionState?: (data: UserTaskPositionStateEventData) => void
  onExecution?: (event: TaskExecutionEvent) => void
  onConnectionChange?: (isConnected: boolean) => void
  onError?: (error: UserTaskErrorEventData) => void
}

export class TaskOverviewSSEService {
  private handlers: TaskOverviewSSEHandlers = {}
  private abortController: AbortController | null = null
  private manualDisconnect = false
  private connected = false

  setHandlers(handlers: TaskOverviewSSEHandlers) {
    this.handlers = handlers
  }

  isConnected(): boolean {
    return this.connected
  }

  async connect(token?: string): Promise<void> {
    this.disconnect()
    this.manualDisconnect = false
    this.connected = false

    const headers: Record<string, string> = {
      Accept: "text/event-stream",
    }
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }

    this.abortController = new AbortController()
    this.handlers.onConnectionChange?.(false)

    try {
      await fetchEventSource(`${API_BASE_URL}/api/v1/live/subscribe/user/tasks`, {
        method: "GET",
        headers,
        signal: this.abortController.signal,
        openWhenHidden: true,
        onopen: async (response) => {
          if (!response.ok) {
            const text = await response.text()
            throw new Error(`任务总览订阅失败: ${response.status} ${text}`)
          }
          this.connected = true
          this.handlers.onConnectionChange?.(true)
        },
        onmessage: (message) => {
          if (!message.data) return
          this.handleEvent(message.event, message.data)
        },
        onclose: () => {
          this.connected = false
          this.handlers.onConnectionChange?.(false)
        },
        onerror: (err) => {
          console.error("TaskOverview SSE error:", err)
          this.connected = false
          this.handlers.onConnectionChange?.(false)
        },
      })
    } catch (error) {
      this.connected = false
      if (!this.manualDisconnect) {
        console.warn("TaskOverview SSE disconnected:", error)
      }
      this.handlers.onConnectionChange?.(false)
    } finally {
      if (this.abortController?.signal.aborted || !this.connected) {
        this.abortController = null
      }
    }
  }

  disconnect() {
    this.manualDisconnect = true
    this.connected = false
    if (this.abortController) {
      this.abortController.abort()
      this.abortController = null
    }
    this.handlers.onConnectionChange?.(false)
  }

  private handleEvent(eventType: string, rawData: string) {
    let parsed: unknown
    try {
      parsed = JSON.parse(rawData)
    } catch {
      return
    }

    switch (eventType) {
      case "task_status":
        this.handlers.onTaskStatus?.(parsed as TaskStatusEventData)
        return
      case "task_end":
        this.handlers.onTaskEnd?.(parsed as TaskEndEventData)
        return
      case "task_position_state":
        this.handlers.onTaskPositionState?.(parsed as UserTaskPositionStateEventData)
        return
      case "task_execution":
        this.handlers.onExecution?.(parsed as TaskExecutionEvent)
        return
      case "error":
        this.handlers.onError?.(parsed as UserTaskErrorEventData)
        return
      default:
        return
    }
  }
}

export const taskOverviewSSEService = new TaskOverviewSSEService()
