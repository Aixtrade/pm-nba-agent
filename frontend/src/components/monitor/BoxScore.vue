<script setup lang="ts">
import { computed } from 'vue'
import { useGameStore } from '@/stores'
import type { TeamData } from '@/types'

const gameStore = useGameStore()

interface TeamBoxStats {
  team: TeamData
  label: string
}

const teams = computed<TeamBoxStats[]>(() => {
  const result: TeamBoxStats[] = []
  if (gameStore.awayTeam) {
    result.push({ team: gameStore.awayTeam, label: '客队' })
  }
  if (gameStore.homeTeam) {
    result.push({ team: gameStore.homeTeam, label: '主队' })
  }
  return result
})

function formatPct(value: number): string {
  if (typeof value !== 'number') return '-'
  return (value * 100).toFixed(1) + '%'
}
</script>

<template>
  <div v-if="gameStore.boxscore" class="card bg-base-100 shadow-md">
    <div class="card-body">
      <h3 class="card-title">球队统计</h3>

      <div class="overflow-x-auto">
        <table class="table table-zebra">
          <thead>
            <tr>
              <th>球队</th>
              <th class="text-right">得分</th>
              <th class="text-right">篮板</th>
              <th class="text-right">助攻</th>
              <th class="text-right">抢断</th>
              <th class="text-right">盖帽</th>
              <th class="text-right">失误</th>
              <th class="text-right">投篮%</th>
              <th class="text-right">三分%</th>
              <th class="text-right">罚球%</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="{ team, label } in teams" :key="team.abbreviation">
              <td>
                <div class="font-bold">{{ team.abbreviation }}</div>
                <div class="text-xs text-base-content/60">{{ label }}</div>
              </td>
              <td class="text-right font-bold">{{ team.score }}</td>
              <td class="text-right">{{ team.statistics?.rebounds ?? '-' }}</td>
              <td class="text-right">{{ team.statistics?.assists ?? '-' }}</td>
              <td class="text-right">{{ team.statistics?.steals ?? '-' }}</td>
              <td class="text-right">{{ team.statistics?.blocks ?? '-' }}</td>
              <td class="text-right">{{ team.statistics?.turnovers ?? '-' }}</td>
              <td class="text-right">{{ formatPct(team.statistics?.field_goal_pct) }}</td>
              <td class="text-right">{{ formatPct(team.statistics?.three_point_pct) }}</td>
              <td class="text-right">{{ formatPct(team.statistics?.free_throw_pct) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
