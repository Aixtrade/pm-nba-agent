<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useConnectionStore, useGameStore } from '@/stores'
import type { CreateTaskRequest } from '@/types/task'
import AdvancedConfigPopover, { type AdvancedConfig } from './AdvancedConfigPopover.vue'

type SubmitCallbacks = {
  onSuccess?: () => void
  onError?: () => void
  onFinally?: () => void
}

const emit = defineEmits<{
  submit: [request: CreateTaskRequest, callbacks?: SubmitCallbacks]
  stop: []
}>()

const connectionStore = useConnectionStore()
const gameStore = useGameStore()

const HISTORY_KEY = 'pm_nba_agent_url_history'
const POLYMARKET_PRIVATE_KEY = 'POLYMARKET_PRIVATE_KEY'
const POLYMARKET_PROXY_ADDRESS = 'POLYMARKET_PROXY_ADDRESS'
const MAX_HISTORY = 10

const url = ref('')
const isSubmitting = ref(false)
const showHistory = ref(false)
const urlHistory = ref<string[]>(loadHistory())

const advancedConfig = ref<AdvancedConfig>({
  pollInterval: 10,
  analysisInterval: 60,
  includeScoreboard: true,
  includeBoxscore: true,
  strategyIds: ['merge_long'],
})

// 比分板相关计算属性（迁移自 AppHeader）
const hasScoreData = computed(() => gameStore.homeTeam && gameStore.awayTeam)

const periodDisplay = computed(() => {
  const scoreboard = gameStore.scoreboard
  if (!scoreboard) return ''
  const period = scoreboard.period
  if (period <= 4) return `Q${period}`
  return `OT${period - 4}`
})

const statusBadgeClass = computed(() => {
  const status = gameStore.gameStatus.toLowerCase()
  if (status.includes('live') || status.includes('进行中')) return 'badge-success'
  if (status.includes('final') || status.includes('结束')) return 'badge-neutral'
  return 'badge-info'
})

const isConnected = computed(() => connectionStore.isConnected)
const isConnecting = computed(() => connectionStore.isConnecting)

const isValidUrl = computed(() => {
  return url.value.startsWith('http') && url.value.includes('polymarket.com')
})

const canSubmit = computed(() => isValidUrl.value && !isSubmitting.value)

// 从 URL slug 解析显示名
const parsedDisplay = computed(() => {
  if (!url.value) return ''
  try {
    const urlObj = new URL(url.value)
    const slug = urlObj.pathname.split('/').pop() || ''
    // nba-lal-bos-2026-01-27 → LAL vs BOS - 2026-01-27
    const match = slug.match(/^nba-([a-z]{2,4})-([a-z]{2,4})-(\d{4}-\d{2}-\d{2})$/i)
    if (match) {
      return `${match[1].toUpperCase()} vs ${match[2].toUpperCase()} - ${match[3]}`
    }
    return ''
  } catch {
    return ''
  }
})

function loadHistory(): string[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      return Array.isArray(parsed) ? parsed.slice(0, MAX_HISTORY) : []
    }
  } catch { /* ignore */ }
  return []
}

function saveHistory(newUrl: string) {
  const trimmed = newUrl.trim()
  if (!trimmed) return
  const filtered = urlHistory.value.filter((u) => u !== trimmed)
  urlHistory.value = [trimmed, ...filtered].slice(0, MAX_HISTORY)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(urlHistory.value))
}

function selectHistory(historyUrl: string) {
  url.value = historyUrl
  showHistory.value = false
}

function handleBlur() {
  window.setTimeout(() => { showHistory.value = false }, 200)
}

function handleSubmit() {
  if (!canSubmit.value) return

  const trimmedUrl = url.value.trim()
  const privateKey = localStorage.getItem(POLYMARKET_PRIVATE_KEY)?.trim() || null
  const proxyAddress = localStorage.getItem(POLYMARKET_PROXY_ADDRESS)?.trim() || null

  const request: CreateTaskRequest = {
    url: trimmedUrl,
    poll_interval: advancedConfig.value.pollInterval,
    include_scoreboard: advancedConfig.value.includeScoreboard,
    include_boxscore: advancedConfig.value.includeBoxscore,
    analysis_interval: advancedConfig.value.analysisInterval,
    strategy_ids: advancedConfig.value.strategyIds.length > 0
      ? advancedConfig.value.strategyIds
      : undefined,
    strategy_params_map: {},
    private_key: privateKey,
    proxy_address: proxyAddress,
  }

  isSubmitting.value = true
  saveHistory(trimmedUrl)
  emit('submit', request, {
    onError: () => {
      isSubmitting.value = false
    },
    onFinally: () => {
      if (!connectionStore.isConnected) {
        isSubmitting.value = false
      }
    },
  })
}

function handleStop() {
  emit('stop')
}

// 连接成功后重置 submitting 状态
watch(isConnected, (connected) => {
  if (connected) {
    isSubmitting.value = false
  }
})

// 连接失败时也重置
watch(
  () => connectionStore.isError,
  (error) => {
    if (error) {
      isSubmitting.value = false
    }
  },
)
</script>

<template>
  <!-- 已连接态：比分显示 + 停止按钮 -->
  <div v-if="isConnected && hasScoreData" class="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-base-200/50">
    <span class="badge badge-sm" :class="statusBadgeClass">{{ gameStore.gameStatus }}</span>
    <div class="flex items-center gap-2 text-sm font-semibold">
      <span class="text-base-content/70">{{ gameStore.awayTeam!.abbreviation }}</span>
      <span class="text-lg tabular-nums">{{ gameStore.awayTeam!.score }}</span>
      <span class="text-base-content/40">-</span>
      <span class="text-lg tabular-nums">{{ gameStore.homeTeam!.score }}</span>
      <span class="text-base-content/70">{{ gameStore.homeTeam!.abbreviation }}</span>
    </div>
    <span v-if="gameStore.scoreboard" class="text-xs text-base-content/50">
      {{ periodDisplay }} {{ gameStore.scoreboard.game_clock }}
    </span>
    <button
      class="btn btn-ghost btn-xs text-error ml-2"
      title="停止监控"
      @click="handleStop"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
      </svg>
    </button>
  </div>

  <!-- 已连接但无比分数据 -->
  <div v-else-if="isConnected" class="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-base-200/50">
    <span class="text-sm text-base-content/60">已连接，等待数据...</span>
    <button
      class="btn btn-ghost btn-xs text-error ml-2"
      title="停止监控"
      @click="handleStop"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
      </svg>
    </button>
  </div>

  <!-- 连接中态 -->
  <div v-else-if="isConnecting || isSubmitting" class="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-base-200/50">
    <span class="loading loading-spinner loading-sm"></span>
    <span class="text-sm text-base-content/60">连接中...</span>
  </div>

  <!-- 未连接态：URL 输入框 -->
  <div v-else class="flex items-center gap-2 w-full max-w-2xl relative">
    <div class="relative flex-1">
      <input
        v-model="url"
        type="url"
        class="input input-sm input-bordered w-full pr-8"
        :class="{ 'input-error': url && !isValidUrl }"
        placeholder="粘贴 Polymarket 比赛 URL..."
        @keydown.enter="handleSubmit"
        @focus="showHistory = urlHistory.length > 0 && !url"
        @blur="handleBlur"
      />
      <!-- URL 解析预览 -->
      <span
        v-if="parsedDisplay"
        class="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-base-content/40 pointer-events-none"
      >
        {{ parsedDisplay }}
      </span>

      <!-- URL 历史下拉 -->
      <ul
        v-if="showHistory && urlHistory.length > 0"
        class="absolute top-full left-0 right-0 mt-1 z-50 menu bg-base-100 rounded-box shadow-lg border border-base-200 max-h-48 overflow-y-auto p-1"
      >
        <li v-for="historyUrl in urlHistory" :key="historyUrl">
          <a
            class="text-xs truncate"
            @mousedown.prevent="selectHistory(historyUrl)"
          >
            {{ historyUrl }}
          </a>
        </li>
      </ul>
    </div>

    <AdvancedConfigPopover v-model="advancedConfig" />

    <button
      class="btn btn-primary btn-sm"
      :disabled="!canSubmit"
      @click="handleSubmit"
    >
      开始
    </button>
  </div>
</template>
