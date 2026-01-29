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
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.2);
  font-size: 13px;
  font-weight: 600;
  pointer-events: auto;
  backdrop-filter: blur(10px);
  cursor: pointer;
}

.toast-card--success {
  background: rgba(22, 163, 74, 0.18);
  color: #166534;
  border-color: rgba(22, 163, 74, 0.55);
}

.toast-card--error {
  background: rgba(239, 68, 68, 0.18);
  color: #991b1b;
  border-color: rgba(239, 68, 68, 0.55);
}

.toast-card--info {
  background: rgba(148, 163, 184, 0.22);
  color: #1f2937;
  border-color: rgba(148, 163, 184, 0.55);
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
  transition: opacity 0.34s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.34s cubic-bezier(0.22, 1, 0.36, 1);
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-12px) scale(0.96);
}

.toast-leave-active {
  transition: opacity 0.24s ease-in, transform 0.24s ease-in;
}

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active {
    transition: opacity 0.01s linear;
  }
}
</style>
