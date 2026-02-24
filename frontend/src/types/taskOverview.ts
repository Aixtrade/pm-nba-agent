import type { PositionStateEventData } from "./sse"
import type { TaskStatus } from "./task"

export type TaskConnectionState = "connecting" | "connected" | "disconnected"

export interface TaskExecutionEvent {
  task_id: string
  source: string
  success: boolean
  orders: Array<Record<string, unknown>>
  error?: string | null
  timestamp: string
}

export interface TaskOverviewItem {
  task: TaskStatus
  position: PositionStateEventData | null
  executions: TaskExecutionEvent[]
  connection: TaskConnectionState
  last_event_at: string | null
}
