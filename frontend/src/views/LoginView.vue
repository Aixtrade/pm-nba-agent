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
  <div class="login-view">
    <div class="login-shell">
      <div class="login-grid">
        <section class="login-brand">
          <div class="login-tag">Live NBA Monitor</div>
          <h1>NBA 实时监控</h1>
          <p>
            追踪即时比分、球员表现与回合走势。安全口令登录后，直达完整比赛控制台。
          </p>
          <div class="login-highlights">
            <div class="highlight-card">
              <span>秒级推送</span>
              <strong>实时事件</strong>
            </div>
            <div class="highlight-card">
              <span>多维看板</span>
              <strong>数据解读</strong>
            </div>
            <div class="highlight-card">
              <span>稳定连接</span>
              <strong>快速切换</strong>
            </div>
          </div>
        </section>

        <section class="login-card">
          <div class="login-card-inner">
            <div class="login-card-title">登录监控台</div>
            <p class="login-card-subtitle">使用安全口令进入实时比赛看板</p>

            <form class="login-form" @submit.prevent="handleSubmit">
              <label class="login-label" for="login-passphrase">口令</label>
              <input
                id="login-passphrase"
                v-model="passphrase"
                type="password"
                class="login-input"
                placeholder="输入口令"
                autocomplete="current-password"
                :aria-invalid="Boolean(errorMessage)"
              >

              <div v-if="errorMessage" class="login-error">
                {{ errorMessage }}
              </div>

              <button class="login-button" type="submit">进入控制台</button>
            </form>

            <div class="login-hint">口令由后端环境变量配置</div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&display=swap');

.login-view {
  --login-ink: #0f172a;
  --login-muted: rgba(15, 23, 42, 0.6);
  --login-accent: #0ea5e9;
  --login-accent-2: #14b8a6;
  --login-card: rgba(255, 255, 255, 0.78);
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(1200px 800px at 12% 18%, rgba(20, 184, 166, 0.18), transparent 60%),
    radial-gradient(1000px 700px at 88% 10%, rgba(14, 165, 233, 0.18), transparent 55%),
    linear-gradient(135deg, #f8fafc 0%, #eef2f7 52%, #f8fafc 100%);
  font-family: "Manrope", "SF Pro Display", "SF Pro Text", "Segoe UI", sans-serif;
  color: var(--login-ink);
}

.login-view::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(15, 23, 42, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, 0.04) 1px, transparent 1px);
  background-size: 32px 32px;
  opacity: 0.35;
  pointer-events: none;
}

.login-view::after {
  content: "";
  position: absolute;
  width: 520px;
  height: 520px;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(14, 165, 233, 0.22), transparent 65%);
  right: -160px;
  bottom: -180px;
  filter: blur(10px);
  animation: float 18s ease-in-out infinite;
  pointer-events: none;
}

.login-shell {
  width: min(1120px, 100%);
  padding: 48px 24px;
  position: relative;
  z-index: 1;
}

.login-grid {
  display: grid;
  gap: 40px;
  align-items: center;
}

.login-brand {
  animation: fade-up 0.8s ease forwards;
}

.login-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  background: rgba(14, 165, 233, 0.12);
  color: #0f766e;
  font-weight: 600;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.login-brand h1 {
  margin-top: 16px;
  font-size: clamp(32px, 4.2vw, 52px);
  line-height: 1.1;
  font-weight: 700;
}

.login-brand p {
  margin-top: 12px;
  max-width: 520px;
  font-size: 16px;
  line-height: 1.7;
  color: var(--login-muted);
}

.login-highlights {
  margin-top: 24px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.highlight-card {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  display: grid;
  gap: 6px;
}

.highlight-card span {
  font-size: 12px;
  color: var(--login-muted);
}

.highlight-card strong {
  font-size: 15px;
  font-weight: 600;
}

.login-card {
  animation: fade-up 0.9s ease 0.1s forwards;
}

.login-card-inner {
  background: var(--login-card);
  border-radius: 24px;
  padding: 32px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.login-card-title {
  font-size: 22px;
  font-weight: 700;
}

.login-card-subtitle {
  margin-top: 6px;
  color: var(--login-muted);
  font-size: 14px;
}

.login-form {
  margin-top: 20px;
  display: grid;
  gap: 14px;
}

.login-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--login-ink);
}

.login-input {
  width: 100%;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.14);
  padding: 12px 14px;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.9);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.login-input:focus {
  outline: none;
  border-color: var(--login-accent);
  box-shadow: 0 0 0 4px rgba(14, 165, 233, 0.18);
}

.login-error {
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
  font-size: 13px;
}

.login-button {
  width: 100%;
  border-radius: 14px;
  border: none;
  padding: 12px 16px;
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  background: linear-gradient(120deg, var(--login-accent), var(--login-accent-2));
  box-shadow: 0 16px 32px rgba(14, 165, 233, 0.28);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.login-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 20px 40px rgba(14, 165, 233, 0.3);
}

.login-hint {
  margin-top: 18px;
  font-size: 12px;
  color: var(--login-muted);
}

@keyframes float {
  0%, 100% { transform: translate3d(0, 0, 0); }
  50% { transform: translate3d(-20px, -18px, 0); }
}

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (min-width: 1024px) {
  .login-grid {
    grid-template-columns: 1.1fr 0.9fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-view::after,
  .login-brand,
  .login-card {
    animation: none;
  }
}
</style>
