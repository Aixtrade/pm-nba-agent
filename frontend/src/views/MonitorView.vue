<script setup lang="ts">
import { useConnectionStore, useGameStore } from '@/stores'
import ScoreBoard from '@/components/monitor/ScoreBoard.vue'
import BoxScore from '@/components/monitor/BoxScore.vue'
import PlayerStatsTable from '@/components/monitor/PlayerStatsTable.vue'
import PlayByPlay from '@/components/monitor/PlayByPlay.vue'
import AgentAnalysisPanel from '@/components/monitor/AgentAnalysisPanel.vue'
import PolymarketBookPanel from '@/components/monitor/PolymarketBookPanel.vue'

const connectionStore = useConnectionStore()
const gameStore = useGameStore()
</script>

<template>
  <div class="space-y-6">
    <!-- 数据展示区域 -->
    <div
      v-if="connectionStore.isConnected || gameStore.scoreboard || gameStore.boxscore"
      class="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_440px] gap-6 items-start"
    >
      <div class="space-y-6">
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
      </div>

      <!-- Agent 分析侧边栏 -->
      <div class="space-y-6">
        <PolymarketBookPanel />
        <AgentAnalysisPanel />
      </div>
    </div>

    <!-- 未连接时的占位提示 -->
    <div
      v-else-if="!connectionStore.isConnecting"
      class="card empty-card"
    >
      <div class="card-body items-center text-center py-12 empty-card__body">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 empty-card__icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        <h2 class="text-xl font-semibold empty-card__title">NBA 实时监控</h2>
        <p class="empty-card__subtitle">
          在比赛列表中添加 Polymarket 比赛 URL，开始实时监控 NBA 比赛数据。
          系统将自动获取比分、球队统计、球员数据和逐回合信息。
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.empty-card {
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.empty-card__body {
  gap: 12px;
}

.empty-card__icon {
  color: rgba(15, 23, 42, 0.32);
}

.empty-card__title {
  color: rgba(15, 23, 42, 0.72);
}

.empty-card__subtitle {
  max-width: 520px;
  color: rgba(15, 23, 42, 0.48);
}
</style>
