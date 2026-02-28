<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue"
import { useAuthStore, useChatStore, useToastStore } from "@/stores"
import { sendChatStream } from "@/services/agentChatService"
import nanoClawAvatar from "@/assets/avatar/nanoclaw.jpeg"

const props = defineProps<{
  taskId: string
}>()

const authStore = useAuthStore()
const toastStore = useToastStore()
const chatStore = useChatStore()

const draft = ref("")
const messagesRef = ref<HTMLElement | null>(null)
const currentAbortController = ref<AbortController | null>(null)
const currentAssistantMessageId = ref<string | null>(null)

const groupId = computed(() => `task:${props.taskId}`)
const isOpen = computed(() => chatStore.isOpen)
const isSending = computed(() => chatStore.sendingGroupId === groupId.value)
const session = computed(() => chatStore.sessions[groupId.value] || null)
const messages = computed(() => session.value?.messages || [])

function formatTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "--"
  return date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  })
}

function messageClass(role: string): string {
  if (role === "user") return "chat-bubble chat-bubble-primary"
  if (role === "error") return "chat-bubble chat-bubble-error"
  return "chat-bubble chat-bubble-neutral"
}

function senderLabel(role: string): string {
  if (role === "user") return "我"
  if (role === "error") return "系统"
  return "NanoClaw"
}

function scrollToBottom() {
  if (!messagesRef.value) return
  messagesRef.value.scrollTop = messagesRef.value.scrollHeight
}

function stopStreaming() {
  if (currentAbortController.value) {
    currentAbortController.value.abort()
    currentAbortController.value = null
  }
}

async function handleSend() {
  const prompt = draft.value.trim()
  if (!prompt || isSending.value) return

  if (!authStore.token) {
    toastStore.showError("请先登录")
    return
  }

  chatStore.setActiveGroup(groupId.value, props.taskId)
  chatStore.addMessage(groupId.value, props.taskId, "user", prompt)
  const assistantMessageId = chatStore.addMessage(groupId.value, props.taskId, "assistant", "", true)

  draft.value = ""
  currentAssistantMessageId.value = assistantMessageId
  chatStore.setSending(groupId.value, true)

  const abortController = new AbortController()
  currentAbortController.value = abortController

  try {
    await sendChatStream({
      prompt,
      groupId: groupId.value,
      token: authStore.token,
      signal: abortController.signal,
      onMessage: (chunk) => {
        chatStore.appendMessage(groupId.value, assistantMessageId, chunk)
      },
      onDone: (sessionId) => {
        chatStore.setSessionId(groupId.value, sessionId)
      },
      onErrorEvent: (message) => {
        toastStore.showError(message)
      },
    })
  } catch (error) {
    if (abortController.signal.aborted) {
      toastStore.showInfo("已停止回复")
    } else {
      const message = error instanceof Error ? error.message : "聊天请求失败"
      chatStore.addMessage(groupId.value, props.taskId, "error", message)
      toastStore.showError(message)
    }
  } finally {
    if (currentAssistantMessageId.value) {
      chatStore.finishMessage(groupId.value, currentAssistantMessageId.value)
    }
    currentAssistantMessageId.value = null
    currentAbortController.value = null
    chatStore.setSending(groupId.value, false)
  }
}

function handleToggle() {
  const nextState = !chatStore.isOpen
  chatStore.setOpen(nextState)
}

function handleClearSession() {
  if (isSending.value) {
    stopStreaming()
  }
  chatStore.clearSession(groupId.value, props.taskId)
}

watch(
  () => props.taskId,
  (taskId) => {
    chatStore.setActiveGroup(`task:${taskId}`, taskId)
  },
  { immediate: true },
)

watch([messages, isOpen], async () => {
  if (!isOpen.value) return
  await nextTick()
  scrollToBottom()
})

onBeforeUnmount(() => {
  stopStreaming()
  if (currentAssistantMessageId.value) {
    chatStore.finishMessage(groupId.value, currentAssistantMessageId.value)
  }
  chatStore.setSending(groupId.value, false)
})
</script>

<template>
  <div class="task-chat fixed right-4 bottom-4 z-40 md:right-6 md:bottom-6">
    <button
      v-if="!isOpen"
      class="btn btn-primary rounded-full shadow-lg task-chat__fab"
      @click="handleToggle"
      aria-label="打开 NanoClaw 聊天"
    >
      <img :src="nanoClawAvatar" alt="NanoClaw" class="task-chat__fab-avatar" />
    </button>

    <section v-else class="task-chat__panel card border border-base-200 bg-base-100 shadow-2xl">
      <header class="task-chat__header">
        <div>
          <h3 class="text-sm font-semibold">任务聊天</h3>
          <p class="text-xs text-base-content/60">NanoClaw · {{ props.taskId.slice(0, 8) }}</p>
        </div>
        <div class="flex items-center gap-2">
          <button class="btn btn-ghost btn-xs" :disabled="messages.length === 0" @click="handleClearSession">
            清空
          </button>
          <button class="btn btn-ghost btn-xs" @click="handleToggle">收起</button>
        </div>
      </header>

      <div ref="messagesRef" class="task-chat__messages">
        <div v-if="messages.length === 0" class="text-sm text-base-content/55 text-center py-8">
          发送问题，获取该任务的 NanoClaw 回复
        </div>

        <div
          v-for="message in messages"
          :key="message.id"
          class="chat"
          :class="message.role === 'user' ? 'chat-end' : 'chat-start'"
        >
          <div class="chat-header mb-1 text-[11px] text-base-content/55">
            {{ senderLabel(message.role) }} · {{ formatTime(message.createdAt) }}
          </div>
          <div class="chat-bubble task-chat__bubble" :class="messageClass(message.role)">
            <span class="whitespace-pre-wrap break-words">{{ message.content || (message.isStreaming ? '...' : '') }}</span>
          </div>
        </div>
      </div>

      <footer class="task-chat__footer">
        <textarea
          v-model="draft"
          class="textarea textarea-bordered w-full min-h-[68px] max-h-[160px]"
          placeholder="输入要问 NanoClaw 的内容..."
          :disabled="isSending"
          @keydown.enter.exact.prevent="handleSend"
        />

        <div class="flex items-center justify-between gap-2">
          <span class="text-xs text-base-content/50">Enter 发送，Shift+Enter 换行</span>
          <div class="flex items-center gap-2">
            <button v-if="isSending" class="btn btn-outline btn-sm" @click="stopStreaming">停止</button>
            <button class="btn btn-primary btn-sm" :disabled="!draft.trim() || isSending" @click="handleSend">
              {{ isSending ? "发送中..." : "发送" }}
            </button>
          </div>
        </div>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.task-chat__fab {
  min-width: 64px;
  height: 64px;
  padding: 0;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.96);
  box-shadow:
    0 18px 34px rgba(2, 6, 23, 0.28),
    0 6px 14px rgba(14, 165, 233, 0.32);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.task-chat__fab:hover {
  transform: translateY(-2px);
  box-shadow:
    0 24px 40px rgba(2, 6, 23, 0.34),
    0 8px 16px rgba(14, 165, 233, 0.38);
}

.task-chat__fab-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.task-chat__panel {
  width: min(390px, calc(100vw - 1rem));
  height: min(560px, calc(100vh - 1rem));
  display: grid;
  grid-template-rows: auto 1fr auto;
  border: 1px solid rgba(15, 23, 42, 0.16);
  box-shadow:
    0 38px 64px rgba(2, 6, 23, 0.34),
    0 14px 26px rgba(2, 6, 23, 0.2);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.task-chat__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.75rem 0.875rem;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  background:
    radial-gradient(120% 140% at 0% 0%, rgba(14, 165, 233, 0.18), transparent 60%),
    rgba(255, 255, 255, 0.92);
}

.task-chat__messages {
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background: rgba(248, 250, 252, 0.65);
}

.task-chat__bubble {
  max-width: 90%;
}

.task-chat__footer {
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  padding: 0.75rem;
  display: grid;
  gap: 0.5rem;
  background: rgba(255, 255, 255, 0.94);
}

@media (max-width: 640px) {
  .task-chat {
    right: 0.5rem;
    bottom: 0.5rem;
  }

  .task-chat__panel {
    width: calc(100vw - 1rem);
    height: min(620px, calc(100vh - 1rem));
  }
}
</style>
