<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { marked } from 'marked'
import { useConnectionStore, useGameStore } from '@/stores'
import type { AnalysisChunkEventData } from '@/types/sse'

// 配置 marked：同步模式，性能更好
marked.setOptions({
  async: false,
  gfm: true,
  breaks: true,
})

interface AnalysisRoundGroup {
  round: number
  text: string
  html: string
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

// 缓存已完成轮次的渲染结果，避免重复渲染
const renderedCache = new Map<number, string>()

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
  const map = new Map<number, Omit<AnalysisRoundGroup, 'html'>>()

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

  // 转换为数组并添加 HTML 渲染
  return Array.from(map.values())
    .sort((a, b) => a.round - b.round)
    .map((group): AnalysisRoundGroup => {
      // 已完成的轮次：优先使用缓存
      if (group.isFinal && renderedCache.has(group.round)) {
        return {
          ...group,
          html: renderedCache.get(group.round)!,
        }
      }

      // 渲染 Markdown
      const html = marked.parse(group.text) as string

      // 完成后存入缓存
      if (group.isFinal) {
        renderedCache.set(group.round, html)
      }

      return { ...group, html }
    })
})

function formatTime(timestamp: string | null): string {
  if (!timestamp) return '-'
  // 后端返回的是 UTC 时间但不带 Z 后缀，需要手动添加以确保正确解析
  const normalizedTimestamp = timestamp.endsWith('Z') || timestamp.includes('+') || timestamp.includes('-', 10)
    ? timestamp
    : `${timestamp}Z`
  const date = new Date(normalizedTimestamp)
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
  renderedCache.clear()
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
  <div class="card glass-card h-full flex flex-col">
    <div class="card-body flex-1 min-h-0 flex flex-col">
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
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div class="analysis-prose text-sm leading-relaxed" v-html="group.html" />
        </div>
      </div>

      <div v-if="copyStatus === 'success'" class="mt-2 text-xs text-success">已复制到剪贴板</div>
      <div v-else-if="copyStatus === 'error'" class="mt-2 text-xs text-error">复制失败</div>
    </div>
  </div>
</template>

<style scoped>
/* Markdown 渲染样式 */
.analysis-prose :deep(p) {
  margin-bottom: 0.5em;
}

.analysis-prose :deep(p:last-child) {
  margin-bottom: 0;
}

.analysis-prose :deep(h1),
.analysis-prose :deep(h2),
.analysis-prose :deep(h3),
.analysis-prose :deep(h4) {
  font-weight: 600;
  margin-top: 1em;
  margin-bottom: 0.5em;
}

.analysis-prose :deep(h1) {
  font-size: 1.25em;
}

.analysis-prose :deep(h2) {
  font-size: 1.125em;
}

.analysis-prose :deep(h3),
.analysis-prose :deep(h4) {
  font-size: 1em;
}

.analysis-prose :deep(ul),
.analysis-prose :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

.analysis-prose :deep(ul) {
  list-style-type: disc;
}

.analysis-prose :deep(ol) {
  list-style-type: decimal;
}

.analysis-prose :deep(li) {
  margin: 0.25em 0;
}

.analysis-prose :deep(strong) {
  font-weight: 600;
}

.analysis-prose :deep(em) {
  font-style: italic;
}

.analysis-prose :deep(code) {
  background: oklch(var(--b2));
  padding: 0.125em 0.375em;
  border-radius: 0.25em;
  font-size: 0.875em;
  font-family: ui-monospace, monospace;
}

.analysis-prose :deep(pre) {
  background: oklch(var(--b2));
  padding: 0.75em 1em;
  border-radius: 0.5em;
  overflow-x: auto;
  margin: 0.5em 0;
}

.analysis-prose :deep(pre code) {
  background: none;
  padding: 0;
}

.analysis-prose :deep(blockquote) {
  border-left: 3px solid oklch(var(--bc) / 0.2);
  padding-left: 1em;
  margin: 0.5em 0;
  color: oklch(var(--bc) / 0.7);
}

.analysis-prose :deep(hr) {
  border: none;
  border-top: 1px solid oklch(var(--bc) / 0.1);
  margin: 1em 0;
}

.analysis-prose :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.5em 0;
  font-size: 0.875em;
}

.analysis-prose :deep(th),
.analysis-prose :deep(td) {
  border: 1px solid oklch(var(--bc) / 0.1);
  padding: 0.375em 0.75em;
  text-align: left;
}

.analysis-prose :deep(th) {
  background: oklch(var(--b2));
  font-weight: 600;
}

.analysis-prose :deep(a) {
  color: oklch(var(--p));
  text-decoration: underline;
}

.analysis-prose :deep(a:hover) {
  opacity: 0.8;
}
</style>
