<script setup lang="ts">
import { computed } from "vue"
import { useGameStore } from "@/stores"
import { requestPositionRefresh } from "@/composables/usePolymarketOrder"

const gameStore = useGameStore()

const positionSides = computed(() => gameStore.positionSides)
const positionsLoading = computed(() => gameStore.positionsLoading)

function formatPrice(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "--"
  return value.toFixed(3)
}

function formatSize(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "--"
  return value.toFixed(2)
}
</script>

<template>
  <div class="card glass-card ring-1 ring-base-content/30 ring-offset-2 ring-offset-base-100">
    <div class="card-body">
      <div class="flex items-center justify-between gap-3">
        <div class="text-sm font-semibold">当前持仓</div>
        <div class="flex items-center gap-2 text-xs text-base-content/60">
          <span>{{ positionsLoading ? "刷新中..." : "双边份额" }}</span>
          <button
            class="btn btn-ghost btn-xs"
            :disabled="positionsLoading"
            title="刷新持仓"
            @click="requestPositionRefresh()"
          >
            ↻
          </button>
        </div>
      </div>

      <div class="mt-2 grid grid-cols-2 gap-2 text-xs">
        <div
          v-for="side in positionSides"
          :key="side.outcome"
          class="rounded-md bg-base-100/60 px-2 py-2"
        >
          <div class="flex items-baseline justify-between">
            <span class="text-sm font-semibold text-base-content">{{ side.outcome }}</span>
            <span class="text-sm font-semibold text-base-content">{{ formatSize(side.size) }}</span>
          </div>
          <div class="mt-0.5 flex items-center justify-between text-[10px] text-base-content/50">
            <span>成本</span>
            <span class="text-base-content/70">{{ formatSize(side.initial_value ?? null) }}</span>
          </div>
          <div class="mt-0.5 flex items-center justify-between text-[10px] text-base-content/50">
            <span>均价 / 现价</span>
            <span class="text-base-content/70">{{ side.avg_price != null ? formatPrice(side.avg_price) : "-" }} / {{ side.cur_price != null ? formatPrice(side.cur_price) : "-" }}</span>
          </div>
        </div>
        <div v-if="positionSides.length === 0" class="col-span-2 text-center text-base-content/50">
          暂无持仓数据
        </div>
      </div>
    </div>
  </div>
</template>
