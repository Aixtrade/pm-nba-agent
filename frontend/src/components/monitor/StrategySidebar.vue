<script setup lang="ts">
/**
 * 策略边栏组件
 *
 * 整合策略相关内容：
 * - 策略信号（顶部，紧凑型）
 * - Agent 分析（下方，流式文字）
 */
import { computed } from 'vue'
import { useGameStore } from '@/stores'
import StrategySignalPanel from './StrategySignalPanel.vue'
import AgentAnalysisPanel from './AgentAnalysisPanel.vue'

const gameStore = useGameStore()

// 格式化信号数据
function formatSignal(sig: typeof gameStore.latestStrategySignal.value) {
  if (!sig) return null
  return {
    event_type: 'signal' as const,
    timestamp: sig.timestamp ? new Date(sig.timestamp).getTime() : Date.now(),
    signal: sig.signal,
    market: sig.market,
    position: sig.position,
    execution: sig.execution,
    strategy: sig.strategy,
    error: null,
  }
}

// 策略信号（从 store 获取）
const strategySignals = computed(() => {
  const latest = formatSignal(gameStore.latestStrategySignal)
  const history = gameStore.strategySignals.map(formatSignal).filter(Boolean)

  if (latest) {
    const latestTimestamp = latest.timestamp
    const filteredHistory = history.filter(h => h && h.timestamp !== latestTimestamp)
    return [latest, ...filteredHistory] as NonNullable<ReturnType<typeof formatSignal>>[]
  }

  return history as NonNullable<ReturnType<typeof formatSignal>>[]
})
</script>

<template>
  <div class="strategy-sidebar">
    <!-- 策略信号（顶部） -->
    <StrategySignalPanel
      :signals="strategySignals"
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
}
</style>
