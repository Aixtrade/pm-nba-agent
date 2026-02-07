<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { CreateTaskRequest } from '@/types/task'

type CreateTaskCallbacks = {
  onSuccess?: () => void
  onError?: (message: string) => void
  onFinally?: () => void
}

type MonitorSource = {
  id: string
  name: string
  url: string
  lastUsedAt?: number
}

type ParseResponse = {
  ok: boolean
  event?: {
    team1_abbr: string
    team2_abbr: string
    game_date: string
    url: string
    display_name: string
  }
}

const emit = defineEmits<{
  createAndSubscribe: [request: CreateTaskRequest, callbacks?: CreateTaskCallbacks]
}>()

const STORAGE_KEY = 'pm_nba_agent_sources'
const SELECTED_KEY = 'pm_nba_agent_selected_source'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
const POLYMARKET_PRIVATE_KEY = 'POLYMARKET_PRIVATE_KEY'
const POLYMARKET_PROXY_ADDRESS = 'POLYMARKET_PROXY_ADDRESS'

const sources = ref<MonitorSource[]>([])
const selectedSourceId = ref<string | null>(null)
const newUrl = ref('')
const addError = ref<string | null>(null)
const isAdding = ref(false)

const isCreating = ref(false)
const createError = ref<string | null>(null)

const pollInterval = ref(10)
const includeScoreboard = ref(true)
const includeBoxscore = ref(true)
const analysisInterval = ref(60)
const showAdvanced = ref(false)

const availableStrategies = [
  { id: 'merge_long', label: 'Merge Long' },
  { id: 'locked_profit', label: 'Locked Profit' },
]
const selectedStrategyIds = ref<string[]>(['merge_long'])

const currentSource = computed(() => {
  return sources.value.find((item) => item.id === selectedSourceId.value) || null
})

const isValidUrl = computed(() => {
  return newUrl.value.startsWith('http') && newUrl.value.includes('polymarket.com')
})

const canAdd = computed(() => {
  return isValidUrl.value && !isAdding.value
})

const canCreate = computed(() => {
  return currentSource.value !== null && !isCreating.value
})

function generateId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `source_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

function loadSources() {
  const rawSources = localStorage.getItem(STORAGE_KEY)
  if (rawSources) {
    try {
      const parsed = JSON.parse(rawSources) as MonitorSource[]
      sources.value = Array.isArray(parsed) ? parsed : []
    } catch {
      sources.value = []
    }
  }

  const savedSelected = localStorage.getItem(SELECTED_KEY)
  if (savedSelected) {
    selectedSourceId.value = savedSelected
  }

  if (!selectedSourceId.value && sources.value.length > 0) {
    selectedSourceId.value = sources.value[0].id
  }
}

function persistSources() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sources.value))
  if (selectedSourceId.value) {
    localStorage.setItem(SELECTED_KEY, selectedSourceId.value)
  } else {
    localStorage.removeItem(SELECTED_KEY)
  }
}

function selectSource(id: string) {
  selectedSourceId.value = id
  const target = sources.value.find((item) => item.id === id)
  if (target) {
    target.lastUsedAt = Date.now()
  }
  persistSources()
}

function removeSource(id: string) {
  const nextSources = sources.value.filter((item) => item.id !== id)
  sources.value = nextSources

  if (selectedSourceId.value === id) {
    selectedSourceId.value = nextSources[0]?.id ?? null
  }

  persistSources()
}

function updateSourceName(source: MonitorSource) {
  const trimmed = source.name.trim()
  source.name = trimmed || source.url
  persistSources()
}

async function parsePolymarketUrl(url: string) {
  const response = await fetch(`${API_BASE_URL}/api/v1/parse/polymarket`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url }),
  })

  if (!response.ok) {
    return null
  }

  const data = (await response.json()) as ParseResponse
  return data.ok ? data.event ?? null : null
}

async function handleAddSource() {
  if (!canAdd.value) return

  const trimmedUrl = newUrl.value.trim()
  addError.value = null

  if (!trimmedUrl) {
    addError.value = '请输入有效的 Polymarket URL'
    return
  }

  const existing = sources.value.find((item) => item.url === trimmedUrl)
  if (existing) {
    selectSource(existing.id)
    addError.value = '该 URL 已存在，已切换到对应比赛'
    return
  }

  isAdding.value = true

  try {
    const event = await parsePolymarketUrl(trimmedUrl)
    if (!event) {
      addError.value = 'URL 解析失败，请检查地址是否正确'
      return
    }

    const fallbackName = `${event.team1_abbr} ${event.team2_abbr} - ${event.game_date}`
    const name = event.display_name || fallbackName

    const source: MonitorSource = {
      id: generateId(),
      name,
      url: trimmedUrl,
      lastUsedAt: Date.now(),
    }

    sources.value = [source, ...sources.value]
    selectedSourceId.value = source.id
    newUrl.value = ''
    persistSources()
  } catch {
    addError.value = '解析失败，请检查 URL 是否正确'
  } finally {
    isAdding.value = false
  }
}

function handleCreateTask() {
  if (!canCreate.value || !currentSource.value) return

  const privateKey = localStorage.getItem(POLYMARKET_PRIVATE_KEY)?.trim() || null
  const proxyAddress = localStorage.getItem(POLYMARKET_PROXY_ADDRESS)?.trim() || null

  createError.value = null
  isCreating.value = true

  const request: CreateTaskRequest = {
    url: currentSource.value.url,
    poll_interval: pollInterval.value,
    include_scoreboard: includeScoreboard.value,
    include_boxscore: includeBoxscore.value,
    analysis_interval: analysisInterval.value,
    strategy_ids: selectedStrategyIds.value.length > 0 ? selectedStrategyIds.value : undefined,
    strategy_params_map: {},
    private_key: privateKey,
    proxy_address: proxyAddress,
  }

  emit('createAndSubscribe', request, {
    onSuccess: () => {
      createError.value = null
    },
    onError: (message) => {
      createError.value = message
    },
    onFinally: () => {
      isCreating.value = false
    },
  })
}

onMounted(() => {
  loadSources()
})
</script>

<template>
  <div class="card bg-base-100 shadow-md">
    <div class="card-body">
      <h2 class="card-title">创建任务</h2>

      <div class="space-y-4">
        <div class="grid gap-3 md:grid-cols-[1fr_auto] items-end">
          <div class="form-control">
            <label class="label">
              <span class="label-text">比赛 URL</span>
            </label>
            <input
              v-model="newUrl"
              type="url"
              placeholder="https://polymarket.com/event/nba-xxx-xxx-2026-01-27"
              class="input input-bordered w-full"
              :class="{ 'input-error': newUrl && !isValidUrl }"
            />
          </div>
          <div class="form-control">
            <button
              class="btn btn-primary"
              :class="{ loading: isAdding }"
              :disabled="!canAdd"
              @click="handleAddSource"
            >
              <span v-if="isAdding">解析中...</span>
              <span v-else>添加</span>
            </button>
          </div>
        </div>

        <label v-if="newUrl && !isValidUrl" class="label">
          <span class="label-text-alt text-error">
            请输入有效的 Polymarket URL
          </span>
        </label>
        <label v-else-if="addError" class="label">
          <span class="label-text-alt text-error">
            {{ addError }}
          </span>
        </label>

        <div v-if="sources.length" class="space-y-2">
          <div
            v-for="source in sources"
            :key="source.id"
            class="flex items-start gap-3 p-3 rounded-lg border border-base-200"
            :class="{ 'bg-base-200/50': source.id === selectedSourceId }"
          >
            <input
              v-model="selectedSourceId"
              type="radio"
              class="radio radio-sm mt-2"
              :value="source.id"
              @change="selectSource(source.id)"
            />
            <div class="flex-1 space-y-2">
              <input
                v-model="source.name"
                type="text"
                class="input input-ghost input-sm w-full"
                @blur="updateSourceName(source)"
              />
              <div class="text-xs text-base-content/60 break-all">
                {{ source.url }}
              </div>
            </div>
            <button
              class="btn btn-ghost btn-sm"
              @click="removeSource(source.id)"
            >
              删除
            </button>
          </div>
        </div>
        <div v-else class="text-sm text-base-content/60">
          暂无比赛 URL，请先添加。
        </div>
      </div>

      <div class="form-control mt-2">
        <label class="label cursor-pointer justify-start gap-2">
          <input
            v-model="showAdvanced"
            type="checkbox"
            class="checkbox checkbox-sm"
          />
          <span class="label-text">显示高级选项</span>
        </label>
      </div>

      <div
        v-if="showAdvanced"
        class="space-y-4 mt-2 p-4 bg-base-100/80 border border-base-200 rounded-lg"
      >
        <div class="flex flex-wrap gap-4">
          <label class="label cursor-pointer gap-2">
            <input
              v-model="includeScoreboard"
              type="checkbox"
              class="checkbox checkbox-sm"
            />
            <span class="label-text">包含比分板</span>
          </label>
          <label class="label cursor-pointer gap-2">
            <input
              v-model="includeBoxscore"
              type="checkbox"
              class="checkbox checkbox-sm"
            />
            <span class="label-text">包含技术统计</span>
          </label>
        </div>

        <div class="form-control">
          <label class="label">
            <span class="label-text">轮询间隔 (秒)</span>
            <span class="label-text-alt">{{ pollInterval }}s</span>
          </label>
          <input
            v-model.number="pollInterval"
            type="range"
            min="5"
            max="60"
            step="5"
            class="range range-sm w-full"
          />
          <div class="flex justify-between text-xs px-2 mt-1">
            <span>5s</span>
            <span>60s</span>
          </div>
        </div>

        <div class="form-control">
          <label class="label">
            <span class="label-text">AI 分析间隔 (秒)</span>
            <span class="label-text-alt">{{ analysisInterval }}s</span>
          </label>
          <input
            v-model.number="analysisInterval"
            type="range"
            min="10"
            max="120"
            step="5"
            class="range range-sm w-full"
          />
          <div class="flex justify-between text-xs px-2 mt-1">
            <span>10s</span>
            <span>120s</span>
          </div>
        </div>

        <div class="form-control">
          <label class="label">
            <span class="label-text">策略选择</span>
          </label>
          <div class="flex flex-wrap gap-3">
            <label
              v-for="strat in availableStrategies"
              :key="strat.id"
              class="flex items-center gap-2 cursor-pointer"
            >
              <input
                v-model="selectedStrategyIds"
                type="checkbox"
                class="checkbox checkbox-sm"
                :value="strat.id"
              />
              <span class="label-text">{{ strat.label }}</span>
            </label>
          </div>
        </div>
      </div>

      <label v-if="createError" class="label pt-0">
        <span class="label-text-alt text-error">
          {{ createError }}
        </span>
      </label>

      <div class="card-actions justify-end mt-4">
        <button
          class="btn btn-primary"
          :class="{ loading: isCreating }"
          :disabled="!canCreate"
          @click="handleCreateTask"
        >
          <span v-if="isCreating">创建中...</span>
          <span v-else>创建并订阅</span>
        </button>
      </div>
    </div>
  </div>
</template>
