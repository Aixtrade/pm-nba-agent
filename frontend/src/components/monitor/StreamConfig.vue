<script setup lang="ts">
import { ref, computed } from 'vue'
import { useConnectionStore } from '@/stores'
import type { LiveStreamRequest } from '@/types/sse'

const emit = defineEmits<{
  connect: [request: LiveStreamRequest]
  disconnect: []
}>()

const connectionStore = useConnectionStore()

// 表单数据
const url = ref('')
const pollInterval = ref(10)
const includeScoreboard = ref(true)
const includeBoxscore = ref(true)
const includePlaybyplay = ref(true)
const playbyplayLimit = ref(20)

// 是否显示高级选项
const showAdvanced = ref(false)

// 表单验证
const isValidUrl = computed(() => {
  return url.value.startsWith('http') && url.value.includes('polymarket.com')
})

const canConnect = computed(() => {
  return isValidUrl.value && !connectionStore.isConnecting
})

function handleConnect() {
  if (!canConnect.value) return

  emit('connect', {
    url: url.value,
    poll_interval: pollInterval.value,
    include_scoreboard: includeScoreboard.value,
    include_boxscore: includeBoxscore.value,
    include_playbyplay: includePlaybyplay.value,
    playbyplay_limit: playbyplayLimit.value,
  })
}

function handleDisconnect() {
  emit('disconnect')
}
</script>

<template>
  <div class="card bg-base-100 shadow-md">
    <div class="card-body">
      <h2 class="card-title">监控配置</h2>

      <div class="form-control">
        <label class="label">
          <span class="label-text">Polymarket URL</span>
        </label>
        <input
          v-model="url"
          type="url"
          placeholder="https://polymarket.com/event/nba-xxx-xxx-2026-01-27"
          class="input input-bordered w-full"
          :class="{ 'input-error': url && !isValidUrl }"
          :disabled="connectionStore.isConnected"
        />
        <label v-if="url && !isValidUrl" class="label">
          <span class="label-text-alt text-error">
            请输入有效的 Polymarket URL
          </span>
        </label>
      </div>

      <!-- 高级选项切换 -->
      <div class="form-control mt-2">
        <label class="label cursor-pointer justify-start gap-2">
          <input
            v-model="showAdvanced"
            type="checkbox"
            class="checkbox checkbox-sm"
            :disabled="connectionStore.isConnected"
          />
          <span class="label-text">显示高级选项</span>
        </label>
      </div>

      <!-- 高级选项 -->
      <div v-if="showAdvanced" class="space-y-4 mt-2 p-4 bg-base-200 rounded-lg">
        <div class="form-control">
          <label class="label">
            <span class="label-text">轮询间隔 (秒)</span>
            <span class="label-text-alt">{{ pollInterval }}s</span>
          </label>
          <input
            v-model.number="pollInterval"
            type="range"
            min="5"
            max="60"
            step="5"
            class="range range-sm"
            :disabled="connectionStore.isConnected"
          />
          <div class="flex justify-between text-xs px-2 mt-1">
            <span>5s</span>
            <span>60s</span>
          </div>
        </div>

        <div class="divider my-2">数据选项</div>

        <div class="flex flex-wrap gap-4">
          <label class="label cursor-pointer gap-2">
            <input
              v-model="includeScoreboard"
              type="checkbox"
              class="checkbox checkbox-sm"
              :disabled="connectionStore.isConnected"
            />
            <span class="label-text">比分板</span>
          </label>
          <label class="label cursor-pointer gap-2">
            <input
              v-model="includeBoxscore"
              type="checkbox"
              class="checkbox checkbox-sm"
              :disabled="connectionStore.isConnected"
            />
            <span class="label-text">详细统计</span>
          </label>
          <label class="label cursor-pointer gap-2">
            <input
              v-model="includePlaybyplay"
              type="checkbox"
              class="checkbox checkbox-sm"
              :disabled="connectionStore.isConnected"
            />
            <span class="label-text">逐回合</span>
          </label>
        </div>

        <div v-if="includePlaybyplay" class="form-control">
          <label class="label">
            <span class="label-text">首次逐回合条数</span>
            <span class="label-text-alt">{{ playbyplayLimit }}</span>
          </label>
          <input
            v-model.number="playbyplayLimit"
            type="range"
            min="1"
            max="100"
            class="range range-sm"
            :disabled="connectionStore.isConnected"
          />
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="card-actions justify-end mt-4">
        <button
          v-if="!connectionStore.isConnected"
          class="btn btn-primary"
          :class="{ 'loading': connectionStore.isConnecting }"
          :disabled="!canConnect"
          @click="handleConnect"
        >
          <span v-if="connectionStore.isConnecting">连接中...</span>
          <span v-else>开始监控</span>
        </button>
        <button
          v-else
          class="btn btn-error"
          @click="handleDisconnect"
        >
          停止监控
        </button>
      </div>
    </div>
  </div>
</template>
