<script setup lang="ts">
import { ref } from 'vue'
import { RouterView, RouterLink } from 'vue-router'
import ApiKeyModal from './components/ApiKeyModal.vue'

const apiKey = ref('')
</script>

<template>
  <div class="app">
    <nav class="nav">
      <div class="nav-brand">GodCV</div>
      <div class="nav-links">
        <RouterLink to="/" class="nav-link">Editor</RouterLink>
        <RouterLink to="/profile" class="nav-link">Profile</RouterLink>
        <RouterLink to="/roles" class="nav-link">Roles</RouterLink>
        <RouterLink to="/saved" class="nav-link">Saved CVs</RouterLink>
        <RouterLink to="/history" class="nav-link">History</RouterLink>
        <RouterLink to="/preferences" class="nav-link">Preferences</RouterLink>
      </div>
      <div class="nav-right">
        <ApiKeyModal v-model="apiKey" />
      </div>
    </nav>
    <main class="main">
      <RouterView :apiKey="apiKey" />
    </main>
  </div>
</template>

<style scoped>
.app { min-height: 100vh; background: #f5f5f5; }
.nav {
  display: flex; align-items: center; gap: 24px;
  padding: 10px 24px; background: #111; color: #fff;
}
.nav-brand { font-weight: 800; font-size: 1.2rem; letter-spacing: 1px; }
.nav-links { display: flex; gap: 16px; flex: 1; }
.nav-link {
  color: #aaa; text-decoration: none; font-weight: 500;
  padding: 4px 8px; border-radius: 6px; transition: all 0.2s;
}
.nav-link:hover, .nav-link.router-link-active { color: #fff; background: #333; }
.nav-right { margin-left: auto; }
.main { padding: 18px; }
</style>
