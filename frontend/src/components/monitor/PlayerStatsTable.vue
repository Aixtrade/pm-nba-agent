<script setup lang="ts">
import type { PlayerData } from '@/types'

defineProps<{
  title: string
  players: PlayerData[]
}>()
</script>

<template>
  <div class="card glass-card">
    <div class="card-body">
      <h3 class="card-title">{{ title }}</h3>

      <div v-if="players.length === 0" class="text-center text-base-content/50 py-4">
        暂无球员数据
      </div>

      <div v-else class="overflow-x-auto">
        <table class="table table-xs table-zebra">
          <thead>
            <tr>
              <th>球员</th>
              <th>位置</th>
              <th class="text-right">时间</th>
              <th class="text-right">得分</th>
              <th class="text-right">篮板</th>
              <th class="text-right">助攻</th>
              <th class="text-right">投篮</th>
              <th class="text-right">三分</th>
              <th class="text-right">罚球</th>
              <th class="text-right">抢断</th>
              <th class="text-right">盖帽</th>
              <th class="text-right">失误</th>
              <th class="text-right">+/-</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="player in players"
              :key="player.name"
              :class="{ 'bg-success/10': player.on_court }"
            >
              <td>
                <div class="flex items-center gap-1">
                  <span
                    v-if="player.on_court"
                    class="w-2 h-2 rounded-full bg-success"
                    title="场上"
                  ></span>
                  <span class="font-medium">{{ player.name }}</span>
                </div>
              </td>
              <td>{{ player.position || '-' }}</td>
              <td class="text-right">{{ player.stats.minutes }}</td>
              <td class="text-right font-bold">{{ player.stats.points }}</td>
              <td class="text-right">{{ player.stats.rebounds }}</td>
              <td class="text-right">{{ player.stats.assists }}</td>
              <td class="text-right">
                {{ player.stats.field_goals_made }}/{{ player.stats.field_goals_attempted }}
              </td>
              <td class="text-right">
                {{ player.stats.three_pointers_made }}/{{ player.stats.three_pointers_attempted }}
              </td>
              <td class="text-right">
                {{ player.stats.free_throws_made }}/{{ player.stats.free_throws_attempted }}
              </td>
              <td class="text-right">{{ player.stats.steals }}</td>
              <td class="text-right">{{ player.stats.blocks }}</td>
              <td class="text-right">{{ player.stats.turnovers }}</td>
              <td class="text-right" :class="{
                'text-success': player.stats.plus_minus > 0,
                'text-error': player.stats.plus_minus < 0
              }">
                {{ player.stats.plus_minus > 0 ? '+' : '' }}{{ player.stats.plus_minus }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
