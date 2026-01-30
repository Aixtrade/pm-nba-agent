<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useConnectionStore, useGameStore } from '@/stores'
import type { AnalysisChunkEventData } from '@/types/sse'

interface AnalysisRoundGroup {
  round: number
  text: string
  isFinal: boolean
  lastTimestamp: string | null
  chunks: AnalysisChunkEventData[]
}

const gameStore = useGameStore()
const connectionStore = useConnectionStore()

const autoScroll = ref(true)
const panelRef = ref<HTMLElement | null>(null)
const copyStatus = ref<'idle' | 'success' | 'error'>('idle')

const analysisChunks = computed(() => gameStore.analysisChunks)

const statusLabel = computed(() => {
  if (connectionStore.isConnecting) return '连接中'
  if (connectionStore.isConnected) return '已连接'
  return '未连接'
})

const statusClass = computed(() => {
  if (connectionStore.isConnected) return 'badge-success'
  if (connectionStore.isConnecting) return 'badge-warning'
  return 'badge-ghost'
})

const lastAnalysisTime = computed(() => {
  const last = analysisChunks.value[analysisChunks.value.length - 1]
  return last?.timestamp ?? null
})

const groupedRounds = computed<AnalysisRoundGroup[]>(() => {
  const map = new Map<number, AnalysisRoundGroup>()

  for (const chunk of analysisChunks.value) {
    const roundNumber = typeof chunk.round === 'number' ? chunk.round : 0
    if (!map.has(roundNumber)) {
      map.set(roundNumber, {
        round: roundNumber,
        text: '',
        isFinal: false,
        lastTimestamp: null,
        chunks: [],
      })
    }
    const group = map.get(roundNumber)
    if (!group) continue
    group.chunks.push(chunk)
    group.text += chunk.chunk
    group.isFinal = group.isFinal || chunk.is_final
    group.lastTimestamp = chunk.timestamp
  }

  return Array.from(map.values()).sort((a, b) => a.round - b.round)
})

function formatTime(timestamp: string | null): string {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return timestamp
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatRoundLabel(round: number): string {
  if (round <= 0) return '未编号'
  return `第 ${round} 轮`
}

function scrollToBottom() {
  if (!panelRef.value) return
  panelRef.value.scrollTop = panelRef.value.scrollHeight
}

async function handleCopy() {
  if (groupedRounds.value.length === 0) return
  const content = groupedRounds.value
    .map(group => `${formatRoundLabel(group.round)}\n${group.text}`)
    .join('\n\n')

  try {
    await navigator.clipboard.writeText(content)
    copyStatus.value = 'success'
  } catch (error) {
    console.error('复制失败:', error)
    copyStatus.value = 'error'
  } finally {
    window.setTimeout(() => {
      copyStatus.value = 'idle'
    }, 1500)
  }
}

function handleClear() {
  gameStore.clearAnalysis()
}

watch(
  () => analysisChunks.value.length,
  async () => {
    if (!autoScroll.value) return
    await nextTick()
    scrollToBottom()
  }
)
</script>

<template>
  <div class="card glass-card h-full">
    <div class="card-body flex min-h-0 flex-col">
      <div class="flex items-start justify-between gap-4">
        <div class="flex flex-wrap items-center gap-2">
          <h3 class="card-title">Agent 分析</h3>
          <span class="badge badge-sm" :class="statusClass">{{ statusLabel }}</span>
          <span class="badge badge-sm badge-outline">{{ analysisChunks.length }}</span>
        </div>
        <div class="flex items-center gap-2">
          <button
            class="btn btn-xs btn-outline"
            :disabled="analysisChunks.length === 0"
            @click="handleCopy"
          >
            复制
          </button>
          <button
            class="btn btn-xs btn-ghost"
            :disabled="analysisChunks.length === 0"
            @click="handleClear"
          >
            清空
          </button>
        </div>
      </div>

      <div class="mt-1 flex items-center justify-between text-xs text-base-content/60">
        <span>最近更新：{{ formatTime(lastAnalysisTime) }}</span>
        <label class="label cursor-pointer gap-2 py-0">
          <span class="label-text text-xs">自动滚动</span>
          <input v-model="autoScroll" type="checkbox" class="toggle toggle-xs" />
        </label>
      </div>

      <div v-if="analysisChunks.length === 0" class="flex-1 py-6 text-center text-base-content/50">
        <span v-if="connectionStore.isConnected">等待分析输出...</span>
        <span v-else>未连接，暂无分析</span>
      </div>

      <div
        v-else
        ref="panelRef"
        class="mt-3 flex-1 min-h-0 space-y-4 overflow-y-auto pr-1"
      >
        <div
          v-for="group in groupedRounds"
          :key="group.round"
          class="rounded-lg border border-base-200 p-3"
        >
          <div class="mb-2 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-sm font-semibold">{{ formatRoundLabel(group.round) }}</span>
              <span v-if="group.isFinal" class="badge badge-success badge-xs">完成</span>
            </div>
            <span class="text-xs text-base-content/60">{{ formatTime(group.lastTimestamp) }}</span>
          </div>
          <div class="text-sm leading-relaxed whitespace-pre-wrap">
            {{ group.text }}
          </div>
        </div>
      </div>

      <div v-if="copyStatus === 'success'" class="mt-2 text-xs text-success">已复制到剪贴板</div>
      <div v-else-if="copyStatus === 'error'" class="mt-2 text-xs text-error">复制失败</div>
    </div>
  </div>
</template>
