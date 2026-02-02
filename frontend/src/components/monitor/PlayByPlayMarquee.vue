<script setup lang="ts">
/**
 * 逐回合跑马灯组件
 *
 * 在比分板下方显示最新的比赛动作，横向滚动效果
 */
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useGameStore } from '@/stores'

const gameStore = useGameStore()

const marqueeRef = ref<HTMLElement | null>(null)
const isPaused = ref(false)

// 获取最新的动作（最多显示 5 条用于滚动）
const recentActions = computed(() => {
  return gameStore.playByPlayActions.slice(0, 5)
})

const latestAction = computed(() => {
  return gameStore.playByPlayActions[0] ?? null
})

const totalActions = computed(() => gameStore.playByPlayActions.length)

function getPeriodLabel(period: number): string {
  if (period <= 4) return `Q${period}`
  return `OT${period - 4}`
}

function formatAction(action: typeof latestAction.value): string {
  if (!action) return ''
  const parts: string[] = []
  if (action.teamTricode) {
    parts.push(`[${action.teamTricode}]`)
  }
  if (action.playerNameI) {
    parts.push(action.playerNameI + ':')
  }
  parts.push(action.description)
  return parts.join(' ')
}

// 暂停/恢复滚动
function togglePause() {
  isPaused.value = !isPaused.value
}
</script>

<template>
  <div
    v-if="latestAction"
    class="marquee-container"
    @mouseenter="isPaused = true"
    @mouseleave="isPaused = false"
  >
    <!-- 左侧固定信息 -->
    <div class="marquee-info">
      <span class="badge badge-sm badge-ghost">
        {{ getPeriodLabel(latestAction.period) }}
      </span>
      <span class="marquee-clock">{{ latestAction.clock }}</span>
      <span class="marquee-score">
        {{ latestAction.scoreAway }} - {{ latestAction.scoreHome }}
      </span>
    </div>

    <!-- 跑马灯内容 -->
    <div class="marquee-content" ref="marqueeRef">
      <div class="marquee-track" :class="{ paused: isPaused }">
        <span
          v-for="(action, index) in recentActions"
          :key="action.actionNumber"
          class="marquee-item"
        >
          <span class="marquee-dot" :class="index === 0 ? 'dot-active' : 'dot-dim'" />
          {{ formatAction(action) }}
        </span>
        <!-- 复制一份实现无缝滚动 -->
        <span
          v-for="action in recentActions"
          :key="'dup-' + action.actionNumber"
          class="marquee-item"
        >
          <span class="marquee-dot dot-dim" />
          {{ formatAction(action) }}
        </span>
      </div>
    </div>

    <!-- 右侧动作计数 -->
    <div class="marquee-count">
      <span class="text-xs text-base-content/50">{{ totalActions }} 条</span>
    </div>
  </div>

  <!-- 无数据时的占位 -->
  <div v-else class="marquee-placeholder">
    <span class="text-xs text-base-content/40">等待比赛动作...</span>
  </div>
</template>

<style scoped>
.marquee-container {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: linear-gradient(
    90deg,
    rgba(15, 23, 42, 0.03) 0%,
    rgba(15, 23, 42, 0.06) 50%,
    rgba(15, 23, 42, 0.03) 100%
  );
  border-radius: 8px;
  overflow: hidden;
}

.marquee-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  padding-right: 12px;
  border-right: 1px solid rgba(15, 23, 42, 0.1);
}

.marquee-clock {
  font-size: 12px;
  font-weight: 500;
  color: rgba(15, 23, 42, 0.6);
  font-variant-numeric: tabular-nums;
}

.marquee-score {
  font-size: 12px;
  font-weight: 600;
  color: rgba(15, 23, 42, 0.8);
  font-variant-numeric: tabular-nums;
}

.marquee-content {
  flex: 1;
  overflow: hidden;
  mask-image: linear-gradient(
    90deg,
    transparent 0%,
    black 5%,
    black 95%,
    transparent 100%
  );
}

.marquee-track {
  display: flex;
  gap: 48px;
  white-space: nowrap;
  animation: marquee 30s linear infinite;
}

.marquee-track.paused {
  animation-play-state: paused;
}

.marquee-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: rgba(15, 23, 42, 0.7);
}

.marquee-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-active {
  background: #10b981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.5);
}

.dot-dim {
  background: rgba(15, 23, 42, 0.2);
}

.marquee-count {
  flex-shrink: 0;
  padding-left: 12px;
  border-left: 1px solid rgba(15, 23, 42, 0.1);
}

.marquee-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  background: rgba(15, 23, 42, 0.02);
  border-radius: 8px;
}

@keyframes marquee {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-50%);
  }
}
</style>
