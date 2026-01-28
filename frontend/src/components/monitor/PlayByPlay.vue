<script setup lang="ts">
import { computed } from 'vue'
import { useGameStore } from '@/stores'

const gameStore = useGameStore()

const actions = computed(() => gameStore.playByPlayActions)

function getPeriodLabel(period: number): string {
  if (period <= 4) return `Q${period}`
  return `OT${period - 4}`
}
</script>

<template>
  <div class="card bg-base-100 shadow-md">
    <div class="card-body">
      <h3 class="card-title">
        逐回合
        <span class="badge badge-neutral badge-sm">{{ actions.length }}</span>
      </h3>

      <div v-if="actions.length === 0" class="text-center text-base-content/50 py-4">
        暂无逐回合数据
      </div>

      <div v-else class="overflow-y-auto max-h-96 space-y-1">
        <div
          v-for="action in actions"
          :key="action.actionNumber"
          class="flex items-start gap-3 p-2 rounded hover:bg-base-200 transition-colors"
        >
          <!-- 时间和节数 -->
          <div class="flex-none w-20 text-right">
            <span class="badge badge-sm badge-ghost">{{ getPeriodLabel(action.period) }}</span>
            <span class="text-xs text-base-content/60 ml-1">{{ action.clock }}</span>
          </div>

          <!-- 球队标识 -->
          <div class="flex-none w-12 text-center">
            <span
              v-if="action.teamTricode"
              class="badge badge-sm badge-outline"
            >
              {{ action.teamTricode }}
            </span>
          </div>

          <!-- 描述 -->
          <div class="flex-1 text-sm">
            <span v-if="action.playerNameI" class="font-medium">{{ action.playerNameI }}: </span>
            <span>{{ action.description }}</span>
          </div>

          <!-- 比分 -->
          <div class="flex-none w-16 text-right text-sm tabular-nums">
            <span class="text-base-content/60">
              {{ action.scoreAway }} - {{ action.scoreHome }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
