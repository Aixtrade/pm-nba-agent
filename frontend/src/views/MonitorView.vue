<script setup lang="ts">
import { useSSE } from '@/composables/useSSE'
import { useConnectionStore, useGameStore } from '@/stores'
import type { LiveStreamRequest } from '@/types/sse'
import StreamConfig from '@/components/monitor/StreamConfig.vue'
import ScoreBoard from '@/components/monitor/ScoreBoard.vue'
import BoxScore from '@/components/monitor/BoxScore.vue'
import PlayerStatsTable from '@/components/monitor/PlayerStatsTable.vue'
import PlayByPlay from '@/components/monitor/PlayByPlay.vue'

const { connect, disconnect } = useSSE()
const connectionStore = useConnectionStore()
const gameStore = useGameStore()

function handleConnect(request: LiveStreamRequest) {
  connect(request)
}

function handleDisconnect() {
  disconnect()
}
</script>

<template>
  <div class="space-y-6">
    <!-- 配置区域 -->
    <StreamConfig
      @connect="handleConnect"
      @disconnect="handleDisconnect"
    />

    <!-- 错误提示 -->
    <div
      v-if="connectionStore.lastError"
      class="alert alert-error"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <div>
        <h3 class="font-bold">{{ connectionStore.lastError.code }}</h3>
        <p class="text-sm">{{ connectionStore.lastError.message }}</p>
      </div>
      <button class="btn btn-sm btn-ghost" @click="connectionStore.clearError">
        关闭
      </button>
    </div>

    <!-- 数据展示区域 -->
    <template v-if="connectionStore.isConnected || gameStore.scoreboard || gameStore.boxscore">
      <!-- 比分板 -->
      <ScoreBoard />

      <!-- 球队统计 -->
      <BoxScore />

      <!-- 球员统计 -->
      <div v-if="gameStore.boxscore" class="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <PlayerStatsTable
          :title="`${gameStore.awayTeam?.name ?? '客队'} 球员统计`"
          :players="gameStore.awayPlayers"
        />
        <PlayerStatsTable
          :title="`${gameStore.homeTeam?.name ?? '主队'} 球员统计`"
          :players="gameStore.homePlayers"
        />
      </div>

      <!-- 逐回合 -->
      <PlayByPlay />
    </template>

    <!-- 未连接时的占位提示 -->
    <div
      v-else-if="!connectionStore.isConnecting"
      class="card bg-base-100 shadow-md"
    >
      <div class="card-body items-center text-center py-12">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 text-base-content/30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        <h2 class="text-xl font-semibold text-base-content/60 mt-4">NBA 实时监控</h2>
        <p class="text-base-content/40 max-w-md">
          输入 Polymarket 比赛 URL 开始实时监控 NBA 比赛数据。
          系统将自动获取比分、球队统计、球员数据和逐回合信息。
        </p>
      </div>
    </div>
  </div>
</template>
