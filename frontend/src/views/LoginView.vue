<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const passphrase = ref('')
const errorMessage = ref('')

async function handleSubmit() {
  errorMessage.value = ''

  const isSuccess = await authStore.login(passphrase.value)

  if (!isSuccess) {
    errorMessage.value = authStore.lastError || '登录失败'
    return
  }

  const redirect = (route.query.redirect as string) || '/monitor'
  passphrase.value = ''
  router.replace(redirect)
}
</script>

<template>
  <div class="min-h-[calc(100vh-6rem)] flex items-center justify-center">
    <div class="card w-full max-w-md bg-base-100 shadow-xl">
      <div class="card-body gap-4">
        <div class="space-y-1">
          <h2 class="text-2xl font-bold">登录监控台</h2>
          <p class="text-base-content/60 text-sm">请输入口令以进入 NBA 实时监控</p>
        </div>

        <form class="space-y-4" @submit.prevent="handleSubmit">
          <div class="form-control">
            <label class="label">
              <span class="label-text">口令</span>
            </label>
            <input
              v-model="passphrase"
              type="password"
              class="input input-bordered"
              placeholder="输入口令"
              autocomplete="current-password"
            >
          </div>

          <div v-if="errorMessage" class="alert alert-error text-sm">
            <span>{{ errorMessage }}</span>
          </div>

          <div class="card-actions justify-end">
            <button class="btn btn-primary" type="submit">登录</button>
          </div>
        </form>

        <div class="text-xs text-base-content/50">
          口令由后端环境变量配置
        </div>
      </div>
    </div>
  </div>
</template>
