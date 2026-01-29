<script setup lang="ts">
import { computed } from 'vue'
import { useToastStore } from '@/stores'

const toastStore = useToastStore()
const hasToasts = computed(() => toastStore.toasts.length > 0)

function closeToast(id: number) {
  toastStore.removeToast(id)
}
</script>

<template>
  <div class="toast-layer" :class="{ 'toast-layer--active': hasToasts }" aria-live="polite">
    <TransitionGroup name="toast" tag="div" class="toast-stack">
      <div
        v-for="toast in toastStore.toasts"
        :key="toast.id"
        class="toast-card"
        :class="`toast-card--${toast.type}`"
        role="status"
        @click="closeToast(toast.id)"
      >
        <span class="toast-message">{{ toast.message }}</span>
        <button class="toast-close" type="button" aria-label="关闭" @click.stop="closeToast(toast.id)">
          ×
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-layer {
  position: fixed;
  top: 12px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  pointer-events: none;
  z-index: 50;
}

.toast-layer--active {
  pointer-events: auto;
}

.toast-stack {
  display: grid;
  gap: 8px;
  width: min(520px, 92vw);
}

.toast-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid transparent;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.12);
  font-size: 13px;
  font-weight: 600;
  pointer-events: auto;
  backdrop-filter: blur(10px);
  cursor: pointer;
}

.toast-card--success {
  background: rgba(240, 253, 244, 0.92);
  color: #15803d;
  border-color: rgba(22, 163, 74, 0.25);
}

.toast-card--error {
  background: rgba(254, 242, 242, 0.94);
  color: #b91c1c;
  border-color: rgba(239, 68, 68, 0.35);
}

.toast-card--info {
  background: rgba(248, 250, 252, 0.95);
  color: #334155;
  border-color: rgba(148, 163, 184, 0.35);
}

.toast-message {
  flex: 1;
}

.toast-close {
  border: none;
  background: transparent;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  color: currentColor;
  opacity: 0.7;
}

.toast-close:hover {
  opacity: 1;
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active {
    transition: opacity 0.01s linear;
  }
}
</style>
