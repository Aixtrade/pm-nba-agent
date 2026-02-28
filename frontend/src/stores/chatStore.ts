import { defineStore } from "pinia"
import { computed, ref } from "vue"
import type { ChatMessage, ChatRole, ChatSession } from "@/types/chat"

type SessionMap = Record<string, ChatSession>

function createMessage(role: ChatRole, content: string, isStreaming = false): ChatMessage {
  const random = Math.random().toString(36).slice(2, 8)
  return {
    id: `${Date.now()}-${random}`,
    role,
    content,
    createdAt: new Date().toISOString(),
    isStreaming,
  }
}

export const useChatStore = defineStore("chat", () => {
  const isOpen = ref(false)
  const activeGroupId = ref<string | null>(null)
  const sendingGroupId = ref<string | null>(null)
  const sessions = ref<SessionMap>({})

  const activeSession = computed(() => {
    if (!activeGroupId.value) return null
    return sessions.value[activeGroupId.value] || null
  })

  function ensureSession(groupId: string, taskId: string): ChatSession {
    const existing = sessions.value[groupId]
    if (existing) {
      existing.taskId = taskId
      existing.updatedAt = new Date().toISOString()
      return existing
    }

    const created: ChatSession = {
      groupId,
      taskId,
      messages: [],
      lastSessionId: null,
      updatedAt: new Date().toISOString(),
    }

    sessions.value[groupId] = created
    return created
  }

  function setOpen(value: boolean) {
    isOpen.value = value
  }

  function setActiveGroup(groupId: string, taskId: string) {
    activeGroupId.value = groupId
    ensureSession(groupId, taskId)
  }

  function setSending(groupId: string, sending: boolean) {
    if (sending) {
      sendingGroupId.value = groupId
      return
    }

    if (sendingGroupId.value === groupId) {
      sendingGroupId.value = null
    }
  }

  function addMessage(
    groupId: string,
    taskId: string,
    role: ChatRole,
    content: string,
    isStreaming = false,
  ): string {
    const session = ensureSession(groupId, taskId)
    const message = createMessage(role, content, isStreaming)
    session.messages.push(message)
    session.updatedAt = new Date().toISOString()
    return message.id
  }

  function appendMessage(groupId: string, messageId: string, chunk: string) {
    const session = sessions.value[groupId]
    if (!session) return

    const target = session.messages.find((message) => message.id === messageId)
    if (!target) return

    target.content += chunk
    session.updatedAt = new Date().toISOString()
  }

  function finishMessage(groupId: string, messageId: string) {
    const session = sessions.value[groupId]
    if (!session) return

    const target = session.messages.find((message) => message.id === messageId)
    if (!target) return

    target.isStreaming = false
    session.updatedAt = new Date().toISOString()
  }

  function setSessionId(groupId: string, sessionId: string | null) {
    const session = sessions.value[groupId]
    if (!session) return

    session.lastSessionId = sessionId
    session.updatedAt = new Date().toISOString()
  }

  function clearSession(groupId: string, taskId: string) {
    sessions.value[groupId] = {
      groupId,
      taskId,
      messages: [],
      lastSessionId: null,
      updatedAt: new Date().toISOString(),
    }
  }

  return {
    isOpen,
    activeGroupId,
    sendingGroupId,
    sessions,
    activeSession,
    ensureSession,
    setOpen,
    setActiveGroup,
    setSending,
    addMessage,
    appendMessage,
    finishMessage,
    setSessionId,
    clearSession,
  }
})
