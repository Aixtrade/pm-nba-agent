<script setup lang="ts">
import { useConnectionStore, useGameStore } from '@/stores'
import BoxScore from '@/components/monitor/BoxScore.vue'
import PlayerStatsTable from '@/components/monitor/PlayerStatsTable.vue'
import StrategySidebar from '@/components/monitor/StrategySidebar.vue'
import PolymarketBookPanel from '@/components/monitor/PolymarketBookPanel.vue'
import AutoBuyPanel from '@/components/monitor/AutoBuyPanel.vue'
import AutoSellPanel from '@/components/monitor/AutoSellPanel.vue'

const connectionStore = useConnectionStore()
const gameStore = useGameStore()
</script>

<template>
  <div class="space-y-6">
    <!-- 数据展示区域 -->
    <div
      v-if="connectionStore.isConnected || gameStore.scoreboard || gameStore.boxscore"
      class="monitor-layout grid grid-cols-1 lg:grid-cols-[420px_minmax(0,1fr)] xl:grid-cols-[420px_minmax(0,1fr)_400px] gap-4 lg:gap-6 items-start"
    >
      <!-- 左侧策略边栏 -->
      <div class="lg:sticky lg:top-(--sidebar-top) lg:h-(--sidebar-height) lg:overflow-hidden">
        <StrategySidebar class="h-full" />
      </div>

      <!-- 中间主内容区 -->
      <div class="space-y-4 min-w-0">
        <!-- 自动买入面板 -->
        <AutoBuyPanel />

        <!-- 自动卖出面板 -->
        <AutoSellPanel />

        <!-- 球队统计 -->
        <BoxScore />

        <!-- 球员统计 -->
        <div v-if="gameStore.boxscore" class="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <PlayerStatsTable
            :title="`${gameStore.awayTeam?.name ?? '客队'} 球员统计`"
            :players="gameStore.awayPlayers"
          />
          <PlayerStatsTable
            :title="`${gameStore.homeTeam?.name ?? '主队'} 球员统计`"
            :players="gameStore.homePlayers"
          />
        </div>
      </div>

      <!-- Polymarket 右侧边栏 -->
      <div class="lg:col-span-2 xl:col-span-1 lg:sticky lg:top-(--sidebar-top) lg:max-h-(--sidebar-height) lg:overflow-y-auto pr-1">
        <PolymarketBookPanel :show-position-cost="true" />
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
          点击右上角“创建任务”，选择 Polymarket 比赛 URL 并创建任务后即可订阅。
          系统将自动获取比分、球队统计和球员数据。
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

.monitor-layout {
  --app-header-h: 4rem;
  --app-main-pad-y: 1.5rem;
  --sidebar-top: calc(var(--app-header-h) + var(--app-main-pad-y));
  --sidebar-height: calc(100dvh - var(--app-header-h) - (var(--app-main-pad-y) * 2));
}
</style>
