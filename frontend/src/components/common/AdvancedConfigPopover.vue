<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

export interface AdvancedConfig {
  pollInterval: number
  analysisInterval: number
  includeScoreboard: boolean
  includeBoxscore: boolean
  strategyIds: string[]
}

const config = defineModel<AdvancedConfig>({ required: true })

const isOpen = ref(false)
const rootRef = ref<HTMLElement | null>(null)

const availableStrategies = [
  { id: 'merge_long', label: 'Merge Long' },
  { id: 'locked_profit', label: 'Locked Profit' },
]

function toggleStrategy(id: string) {
  const ids = config.value.strategyIds
  const index = ids.indexOf(id)
  if (index >= 0) {
    ids.splice(index, 1)
  } else {
    ids.push(id)
  }
}

function close() {
  isOpen.value = false
}

function handleDocumentClick(event: MouseEvent) {
  const target = event.target as Node | null
  if (!target || !rootRef.value) return
  if (!rootRef.value.contains(target)) {
    close()
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleDocumentClick)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', handleDocumentClick)
})
</script>

<template>
  <div ref="rootRef" class="relative">
    <button
      class="btn btn-ghost btn-sm btn-square"
      title="高级配置"
      @click.stop="isOpen = !isOpen"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    </button>

    <div
      v-if="isOpen"
      class="absolute top-full right-0 mt-1 z-50 bg-base-100 rounded-box w-72 p-4 shadow-lg border border-base-200 space-y-4"
    >
      <div class="flex items-center justify-between mb-1">
        <span class="text-sm font-semibold">高级配置</span>
        <button class="btn btn-ghost btn-xs btn-square" @click="close">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- 数据开关 -->
      <div class="flex flex-wrap gap-3">
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            v-model="config.includeScoreboard"
            type="checkbox"
            class="checkbox checkbox-xs"
          />
          <span class="text-xs">比分板</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            v-model="config.includeBoxscore"
            type="checkbox"
            class="checkbox checkbox-xs"
          />
          <span class="text-xs">技术统计</span>
        </label>
      </div>

      <!-- 轮询间隔 -->
      <div>
        <div class="flex justify-between text-xs mb-1">
          <span>轮询间隔</span>
          <span class="tabular-nums">{{ config.pollInterval }}s</span>
        </div>
        <input
          v-model.number="config.pollInterval"
          type="range"
          min="5"
          max="60"
          step="5"
          class="range range-xs w-full"
        />
      </div>

      <!-- AI 分析间隔 -->
      <div>
        <div class="flex justify-between text-xs mb-1">
          <span>AI 分析间隔</span>
          <span class="tabular-nums">{{ config.analysisInterval }}s</span>
        </div>
        <input
          v-model.number="config.analysisInterval"
          type="range"
          min="10"
          max="120"
          step="5"
          class="range range-xs w-full"
        />
      </div>

      <!-- 策略选择 -->
      <div>
        <div class="text-xs mb-2">策略选择</div>
        <div class="flex flex-wrap gap-3">
          <label
            v-for="strat in availableStrategies"
            :key="strat.id"
            class="flex items-center gap-2 cursor-pointer"
          >
            <input
              type="checkbox"
              class="checkbox checkbox-xs"
              :checked="config.strategyIds.includes(strat.id)"
              @change="toggleStrategy(strat.id)"
            />
            <span class="text-xs">{{ strat.label }}</span>
          </label>
        </div>
      </div>
    </div>
  </div>

</template>
