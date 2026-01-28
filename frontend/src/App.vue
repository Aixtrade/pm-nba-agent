<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/common/AppHeader.vue'

const route = useRoute()
const showHeader = computed(() => route.name !== 'login')
</script>

<template>
  <div
    class="min-h-screen flex flex-col app-shell"
    :class="showHeader ? 'app-shell--default' : 'app-shell--plain'"
  >
    <AppHeader v-if="showHeader" />
    <main class="flex-1 w-full app-main" :class="showHeader ? 'px-4 py-6' : 'p-0'">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  position: relative;
}

.app-shell--default {
  background:
    radial-gradient(900px 600px at 8% 12%, rgba(20, 184, 166, 0.08), transparent 58%),
    radial-gradient(900px 600px at 88% 18%, rgba(14, 165, 233, 0.1), transparent 60%),
    linear-gradient(135deg, #f4f6fb 0%, #eef2f7 50%, #f6f8fc 100%);
}

.app-shell--plain {
  background: transparent;
}

.app-shell--default::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(15, 23, 42, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 23, 42, 0.035) 1px, transparent 1px);
  background-size: 40px 40px;
  opacity: 0.5;
  pointer-events: none;
}

.app-main {
  position: relative;
  z-index: 1;
}

@media (prefers-reduced-motion: reduce) {
  .app-shell--default::before {
    opacity: 0.35;
  }
}
</style>
