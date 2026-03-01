import { defineStore } from "pinia"
import { ref } from "vue"
import type { PolymarketInfoEventData } from "@/types/sse"
import { taskService } from "@/services/taskService"
import { updateGroupMemory } from "@/services/taskMemoryService"
import { useAuthStore } from "./authStore"
import { useGameStore } from "./gameStore"
import { useTaskStore } from "./taskStore"

type TaskMemorySyncStatus = "idle" | "syncing" | "synced" | "failed"

interface TaskMemoryState {
  status: TaskMemorySyncStatus
  lastHash: string | null
  lastSyncedAt: string | null
  error: string | null
}

type TaskMemoryStateMap = Record<string, TaskMemoryState>

type InflightMap = Record<string, Promise<void> | undefined>

function defaultTaskMemoryState(): TaskMemoryState {
  return {
    status: "idle",
    lastHash: null,
    lastSyncedAt: null,
    error: null,
  }
}

function toTaskMemoryGroupId(taskId: string): string {
  return `task-${taskId}`
}

function inferSide(outcome: string): string {
  const normalized = outcome.trim().toUpperCase()
  if (normalized === "YES" || normalized === "UP") return "YES"
  if (normalized === "NO" || normalized === "DOWN") return "NO"
  return "UNKNOWN"
}

function sanitizeNullableString(input: unknown): string {
  if (typeof input !== "string") return ""
  return input.trim()
}

function parseNbaEventFromUrl(url: string): {
  sport: string
  teams: string
  gameDate: string
  slug: string
} {
  const normalized = url.trim()
  if (!normalized) {
    return { sport: "NBA", teams: "(pending)", gameDate: "(pending)", slug: "(pending)" }
  }

  try {
    const pathname = new URL(normalized).pathname
    const slug = pathname.split("/").filter(Boolean).pop() || ""
    const match = slug.match(/^nba-([a-z]{2,4})-([a-z]{2,4})-(\d{4}-\d{2}-\d{2})$/i)
    if (!match) {
      return { sport: "NBA", teams: "(unknown)", gameDate: "(unknown)", slug: slug || "(unknown)" }
    }

    return {
      sport: "NBA",
      teams: `${match[1].toUpperCase()} vs ${match[2].toUpperCase()}`,
      gameDate: match[3],
      slug,
    }
  } catch {
    return { sport: "NBA", teams: "(unknown)", gameDate: "(unknown)", slug: "(unknown)" }
  }
}

function buildTaskMemoryContent(
  taskId: string,
  taskConfig: Record<string, unknown>,
  polymarketInfo: PolymarketInfoEventData | null,
): string {
  const privateKey = sanitizeNullableString(taskConfig.private_key)
  const proxyAddress = sanitizeNullableString(taskConfig.proxy_address)
  const taskUrl = sanitizeNullableString(taskConfig.url)
  const urlSummary = parseNbaEventFromUrl(taskUrl)
  const title = polymarketInfo?.title || ""
  const conditionId = polymarketInfo?.condition_id || polymarketInfo?.market_info?.condition_id || ""
  const marketSlug = polymarketInfo?.market_info?.slug || polymarketInfo?.tokens?.[0]?.market_slug || ""

  const tokenLines = (polymarketInfo?.tokens || []).map((token) => {
    const side = inferSide(token.outcome)
    return `- token_id: ${token.token_id}, outcome: ${token.outcome}, side: ${side}, market_slug: ${token.market_slug}`
  })

  return [
    "# Task Memory",
    "",
    "## Task",
    `- task_id: ${taskId}`,
    `- group_id: ${toTaskMemoryGroupId(taskId)}`,
    `- synced_at: ${new Date().toISOString()}`,
    "",
    "## Task Overview",
    `- domain: ${urlSummary.sport} sports match`,
    `- teams: ${urlSummary.teams}`,
    `- game_date: ${urlSummary.gameDate}`,
    `- event_slug: ${urlSummary.slug}`,
    `- task_url: ${taskUrl || "(pending)"}`,
    "",
    "## Credentials",
    `- private_key: ${privateKey || "(empty)"}`,
    `- proxy_address: ${proxyAddress || "(empty)"}`,
    "",
    "## Polymarket",
    `- title: ${title || "(pending)"}`,
    `- condition_id: ${conditionId || "(pending)"}`,
    `- market_slug: ${marketSlug || "(pending)"}`,
    "",
    "## Tokens",
    ...(tokenLines.length > 0 ? tokenLines : ["- (pending polymarket_info)"]),
  ].join("\n")
}

function createHash(content: string): string {
  let hash = 0
  for (let i = 0; i < content.length; i += 1) {
    hash = (hash << 5) - hash + content.charCodeAt(i)
    hash |= 0
  }
  return String(hash)
}

async function retryUpdateGroupMemory(
  groupId: string,
  content: string,
  token: string,
  maxAttempts = 3,
): Promise<void> {
  let lastError: unknown = null

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      await updateGroupMemory({ groupId, content, token })
      return
    } catch (error) {
      lastError = error
      if (attempt >= maxAttempts) break
      const backoffMs = attempt * 300
      await new Promise((resolve) => setTimeout(resolve, backoffMs))
    }
  }

  throw lastError instanceof Error ? lastError : new Error("任务记忆同步失败")
}

export const useTaskMemoryStore = defineStore("taskMemory", () => {
  const taskMemoryStates = ref<TaskMemoryStateMap>({})
  const inflightByTask = ref<InflightMap>({})

  function ensureState(taskId: string): TaskMemoryState {
    const existing = taskMemoryStates.value[taskId]
    if (existing) return existing
    const created = defaultTaskMemoryState()
    taskMemoryStates.value = { ...taskMemoryStates.value, [taskId]: created }
    return created
  }

  function markSyncing(taskId: string) {
    const state = ensureState(taskId)
    state.status = "syncing"
    state.error = null
  }

  function markSynced(taskId: string, hash: string) {
    const state = ensureState(taskId)
    state.status = "synced"
    state.lastHash = hash
    state.lastSyncedAt = new Date().toISOString()
    state.error = null
  }

  function markFailed(taskId: string, message: string) {
    const state = ensureState(taskId)
    state.status = "failed"
    state.error = message
  }

  async function syncTaskMemory(taskId: string, force = false): Promise<void> {
    const authStore = useAuthStore()
    const gameStore = useGameStore()
    const taskStore = useTaskStore()
    const state = ensureState(taskId)

    if (!authStore.token) {
      markFailed(taskId, "未登录，无法同步任务记忆")
      return
    }

    const configResponse = await taskService.getTaskConfig(taskId, authStore.token)
    const config = (configResponse.config || {}) as Record<string, unknown>
    const shouldUseLivePolymarket = taskStore.currentTaskId === taskId
    const polymarketInfo = shouldUseLivePolymarket ? gameStore.polymarketInfo : null
    const content = buildTaskMemoryContent(taskId, config, polymarketInfo)
    const hash = createHash(content)

    if (!force && state.status === "synced" && state.lastHash === hash) {
      return
    }

    markSyncing(taskId)
    await retryUpdateGroupMemory(toTaskMemoryGroupId(taskId), content, authStore.token)
    markSynced(taskId, hash)
  }

  async function ensureTaskMemorySynced(taskId: string, force = false): Promise<void> {
    const inflight = inflightByTask.value[taskId]
    if (inflight) {
      await inflight
      return
    }

    const job = syncTaskMemory(taskId, force).catch((error) => {
      const message = error instanceof Error ? error.message : "同步任务记忆失败"
      markFailed(taskId, message)
      throw error
    }).finally(() => {
      inflightByTask.value = { ...inflightByTask.value, [taskId]: undefined }
    })

    inflightByTask.value = { ...inflightByTask.value, [taskId]: job }
    await job
  }

  function resetTaskMemory(taskId: string) {
    taskMemoryStates.value = {
      ...taskMemoryStates.value,
      [taskId]: defaultTaskMemoryState(),
    }
    inflightByTask.value = {
      ...inflightByTask.value,
      [taskId]: undefined,
    }
  }

  return {
    taskMemoryStates,
    ensureTaskMemorySynced,
    resetTaskMemory,
  }
})
