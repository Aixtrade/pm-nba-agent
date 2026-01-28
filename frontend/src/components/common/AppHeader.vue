<script setup lang="ts">
import ConnectionStatus from './ConnectionStatus.vue'
</script>

<template>
  <header class="navbar bg-base-100 shadow-md">
    <div class="container mx-auto">
      <div class="flex-1">
        <RouterLink to="/" class="btn btn-ghost text-xl font-bold">
          NBA 实时监控
        </RouterLink>
      </div>
      <div class="flex-none">
        <ConnectionStatus />
      </div>
    </div>
  </header>
</template>
