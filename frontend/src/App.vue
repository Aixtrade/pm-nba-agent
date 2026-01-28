<script setup lang="ts">
import AppHeader from '@/components/common/AppHeader.vue'
</script>

<template>
  <div class="min-h-screen bg-base-200 flex flex-col">
    <AppHeader />
    <main class="flex-1 w-full px-4 py-6">
      <RouterView />
    </main>
  </div>
</template>
