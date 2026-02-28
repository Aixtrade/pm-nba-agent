import { fetchEventSource } from "@microsoft/fetch-event-source"

const NANOCLAW_BASE_URL = import.meta.env.VITE_NANOCLAW_BASE_URL || "http://localhost:3100"

interface SendChatStreamParams {
  prompt: string
  groupId: string
  token: string
  signal?: AbortSignal
  onMessage: (text: string) => void
  onDone: (sessionId: string | null) => void
  onErrorEvent: (message: string) => void
}

interface MessageEventPayload {
  text?: string
}

interface ErrorEventPayload {
  error?: string
}

interface DoneEventPayload {
  sessionId?: string
}

function parseJSONPayload<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

function mapHttpError(status: number): string {
  if (status === 400) return "请求格式错误，请检查输入"
  if (status === 401) return "认证失败，请重新登录"
  if (status === 409) return "该任务已有进行中的对话"
  if (status === 413) return "消息过长，请精简后重试"
  return `请求失败 (${status})`
}

export async function sendChatStream(params: SendChatStreamParams): Promise<void> {
  const { prompt, groupId, token, signal, onMessage, onDone, onErrorEvent } = params

  await fetchEventSource(`${NANOCLAW_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ prompt, groupId }),
    signal,
    openWhenHidden: true,
    async onopen(response) {
      if (response.ok) return
      throw new Error(mapHttpError(response.status))
    },
    onmessage(event) {
      if (event.event === "message") {
        const payload = parseJSONPayload<MessageEventPayload>(event.data)
        if (payload?.text) {
          onMessage(payload.text)
        }
        return
      }

      if (event.event === "error") {
        const payload = parseJSONPayload<ErrorEventPayload>(event.data)
        const message = payload?.error || "Agent 返回错误"
        onErrorEvent(message)
        throw new Error(message)
      }

      if (event.event === "done") {
        const payload = parseJSONPayload<DoneEventPayload>(event.data)
        onDone(payload?.sessionId || null)
      }
    },
    onerror(err) {
      throw err
    },
  })
}
