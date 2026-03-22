<template>
  <div id="app" class="flex h-screen">
    <!-- Sidebar -->
    <Sidebar v-if="authStore.isAuthenticated" />
    
    <!-- Main Content -->
    <div class="flex-1 flex flex-col">
      <Navigation v-if="authStore.isAuthenticated" />
      <main class="flex-1 overflow-y-auto">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from './stores/auth'
import Sidebar from './components/shared/Sidebar.vue'
import Navigation from './components/shared/Navigation.vue'

const authStore = useAuthStore()
</script>

<style scoped>
#app {
  background-color: #f9fafb;
}
</style>
