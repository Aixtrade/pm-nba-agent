export type ChatRole = "user" | "assistant" | "error"

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  createdAt: string
  isStreaming?: boolean
  sourceEventId?: string
}

export interface ChatSession {
  groupId: string
  taskId: string
  messages: ChatMessage[]
  unreadCount: number
  lastSessionId: string | null
  updatedAt: string
}
