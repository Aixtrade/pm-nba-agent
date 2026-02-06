<script setup lang="ts">
/**
 * 策略边栏组件
 *
 * 整合策略相关内容：
 * - 策略信号（顶部，按策略分组显示）
 * - Agent 分析（下方，流式文字）
 */
import { computed } from 'vue'
import { useGameStore } from '@/stores'
import type { StrategySignalEventData } from '@/types/sse'
import StrategySignalPanel from './StrategySignalPanel.vue'
import AgentAnalysisPanel from './AgentAnalysisPanel.vue'

const gameStore = useGameStore()

// 格式化信号数据
function formatSignal(sig: StrategySignalEventData | null | undefined) {
  if (!sig) return null
  return {
    event_type: 'signal' as const,
    timestamp: sig.timestamp ?? new Date().toISOString(),
    signal: sig.signal,
    market: sig.market,
    position: sig.position,
    execution: sig.execution,
    strategy: sig.strategy,
    error: null,
  }
}

// 动态策略 ID 列表
const activeStrategyIds = computed(() => gameStore.activeStrategyIds)

// 按策略 ID 获取格式化后的信号列表
function getFormattedSignals(sid: string) {
  const latest = formatSignal(gameStore.getLatestSignalForStrategy(sid))
  const history = gameStore.getSignalsForStrategy(sid).map(formatSignal).filter(Boolean)

  if (latest) {
    const latestTimestamp = latest.timestamp
    const filteredHistory = history.filter(h => h && h.timestamp !== latestTimestamp)
    return [latest, ...filteredHistory] as NonNullable<ReturnType<typeof formatSignal>>[]
  }

  return history as NonNullable<ReturnType<typeof formatSignal>>[]
}
</script>

<template>
  <div class="strategy-sidebar">
    <!-- 策略信号（按策略分组，动态渲染） -->
    <StrategySignalPanel
      v-for="sid in activeStrategyIds"
      :key="sid"
      :signals="getFormattedSignals(sid)"
      :strategy-id="sid"
      class="shrink-0"
    />

    <!-- 无策略信号时的占位 -->
    <StrategySignalPanel
      v-if="activeStrategyIds.length === 0"
      :signals="[]"
      strategy-id="merge_long"
      class="shrink-0"
    />

    <!-- Agent 分析（下方，填充剩余空间） -->
    <AgentAnalysisPanel class="flex-1 min-h-0" />
  </div>
</template>

<style scoped>
.strategy-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  min-height: 0;
}
</style>
