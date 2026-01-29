<script setup lang="ts">
import { computed } from 'vue'
import { useGameStore } from '@/stores'

const gameStore = useGameStore()

const periodDisplay = computed(() => {
  const scoreboard = gameStore.scoreboard
  if (!scoreboard) return ''

  const period = scoreboard.period
  if (period <= 4) {
    return `第 ${period} 节`
  }
  return `加时 ${period - 4}`
})

const statusClass = computed(() => {
  const status = gameStore.gameStatus.toLowerCase()
  if (status.includes('live') || status.includes('进行中')) {
    return 'badge-success'
  }
  if (status.includes('final') || status.includes('结束')) {
    return 'badge-neutral'
  }
  return 'badge-info'
})

const statusMessage = computed(() => gameStore.scoreboard?.status_message?.trim() || '')
</script>

<template>
  <div v-if="gameStore.homeTeam && gameStore.awayTeam" class="card glass-card">
    <div class="card-body">
      <!-- 比赛状态 -->
      <div class="flex justify-center items-center gap-4 mb-4">
        <span class="badge" :class="statusClass">{{ gameStore.gameStatus }}</span>
        <span v-if="gameStore.scoreboard" class="text-sm text-base-content/70">
          {{ periodDisplay }} | {{ gameStore.scoreboard.game_clock }}
        </span>
      </div>

      <!-- 比分 -->
      <div class="grid grid-cols-3 gap-4 items-center text-center">
        <!-- 客队 -->
        <div class="space-y-2">
          <div class="text-lg font-bold">{{ gameStore.awayTeam.abbreviation }}</div>
          <div class="text-sm text-base-content/70">{{ gameStore.awayTeam.name }}</div>
        </div>

        <!-- 比分显示 -->
        <div class="flex items-center justify-center gap-4">
          <span class="text-5xl font-bold tabular-nums">{{ gameStore.awayTeam.score }}</span>
          <span class="text-2xl text-base-content/50">-</span>
          <span class="text-5xl font-bold tabular-nums">{{ gameStore.homeTeam.score }}</span>
        </div>

        <!-- 主队 -->
        <div class="space-y-2">
          <div class="text-lg font-bold">{{ gameStore.homeTeam.abbreviation }}</div>
          <div class="text-sm text-base-content/70">{{ gameStore.homeTeam.name }}</div>
        </div>
      </div>

      <!-- 比赛结束提示 -->
      <div v-if="gameStore.isGameEnded" class="alert alert-info mt-4">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>比赛已结束</span>
      </div>

      <div v-else-if="statusMessage" class="alert alert-info mt-4">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>{{ statusMessage }}</span>
      </div>
    </div>
  </div>

  <!-- 无数据占位 -->
  <div v-else class="card glass-card">
    <div class="card-body items-center text-center text-base-content/50">
      <p>等待比赛数据...</p>
    </div>
  </div>
</template>
