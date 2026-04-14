<script setup lang="ts">
import { RouterView, RouterLink } from 'vue-router'
</script>

<template>
  <div class="app">
    <nav class="nav">
      <div class="nav-brand">GodCV</div>
      <div class="nav-links">
        <RouterLink to="/" class="nav-link">Editor</RouterLink>
        <RouterLink to="/profile" class="nav-link">Profile</RouterLink>
        <RouterLink to="/history" class="nav-link">History</RouterLink>
      </div>
    </nav>
    <main class="main">
      <RouterView />
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
.nav-links { display: flex; gap: 16px; }
.nav-link {
  color: #aaa; text-decoration: none; font-weight: 500;
  padding: 4px 8px; border-radius: 6px; transition: all 0.2s;
}
.nav-link:hover, .nav-link.router-link-active { color: #fff; background: #333; }
.main { padding: 18px; }
</style>
