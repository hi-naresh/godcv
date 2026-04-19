<script setup lang="ts">
import { ref } from 'vue'
import { RouterView, RouterLink } from 'vue-router'
import ApiKeyModal from './components/ApiKeyModal.vue'
import ToastContainer from './components/ToastContainer.vue'

const apiKey = ref('')
const sidebarOpen = ref(true)
</script>

<template>
  <div class="app">
    <aside :class="['sidebar', { collapsed: !sidebarOpen }]">
      <div class="sidebar-top">
        <div class="brand" v-show="sidebarOpen">GodCV</div>
        <button class="toggle-btn" @click="sidebarOpen = !sidebarOpen" :title="sidebarOpen ? 'Collapse' : 'Expand'">
          {{ sidebarOpen ? '\u2039' : '\u203A' }}
        </button>
      </div>
      <nav class="sidebar-nav">
        <RouterLink to="/" class="nav-item">
          <span class="nav-icon">&#9998;</span>
          <span v-show="sidebarOpen" class="nav-label">Editor</span>
        </RouterLink>
        <RouterLink to="/profile" class="nav-item">
          <span class="nav-icon">&#9787;</span>
          <span v-show="sidebarOpen" class="nav-label">Profile</span>
        </RouterLink>
        <RouterLink to="/saved" class="nav-item">
          <span class="nav-icon">&#9744;</span>
          <span v-show="sidebarOpen" class="nav-label">Saved CVs</span>
        </RouterLink>
        <RouterLink to="/roles" class="nav-item">
          <span class="nav-icon">&#9881;</span>
          <span v-show="sidebarOpen" class="nav-label">Roles</span>
        </RouterLink>
        <RouterLink to="/history" class="nav-item">
          <span class="nav-icon">&#8634;</span>
          <span v-show="sidebarOpen" class="nav-label">History</span>
        </RouterLink>
        <RouterLink to="/preferences" class="nav-item">
          <span class="nav-icon">&#9881;</span>
          <span v-show="sidebarOpen" class="nav-label">Preferences</span>
        </RouterLink>
      </nav>
      <div class="sidebar-bottom" v-show="sidebarOpen">
        <ApiKeyModal v-model="apiKey" />
      </div>
    </aside>
    <main class="main">
      <RouterView :apiKey="apiKey" />
    </main>
    <ToastContainer />
  </div>
</template>

<style scoped>
.app { display: flex; min-height: 100vh; background: #f5f5f5; }

.sidebar {
  width: 180px; min-height: 100vh;
  background: #111; color: #fff;
  display: flex; flex-direction: column;
  transition: width 0.2s ease;
  position: sticky; top: 0; align-self: flex-start;
  height: 100vh; overflow: hidden;
  z-index: 10;
}
.sidebar.collapsed { width: 48px; }

.sidebar-top {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 12px 10px;
  min-height: 48px;
}
.brand { font-weight: 800; font-size: 1.1rem; letter-spacing: 1px; white-space: nowrap; }
.toggle-btn {
  border: none; background: #333; color: #aaa;
  width: 24px; height: 24px; border-radius: 6px;
  font-size: 1rem; cursor: pointer; display: flex;
  align-items: center; justify-content: center;
  flex-shrink: 0;
}
.toggle-btn:hover { background: #444; color: #fff; }

.sidebar-nav {
  flex: 1; display: flex; flex-direction: column;
  gap: 2px; padding: 4px 8px;
}
.collapsed .sidebar-nav { padding: 4px 6px; }

.nav-item {
  display: flex; align-items: center; gap: 10px;
  color: #999; text-decoration: none; font-weight: 500; font-size: 0.85rem;
  padding: 8px 10px; border-radius: 8px;
  transition: all 0.15s; white-space: nowrap;
}
.nav-item:hover { color: #fff; background: #222; }
.nav-item.router-link-exact-active { color: #fff; background: #333; }
.collapsed .nav-item { justify-content: center; padding: 8px; }

.nav-icon { font-size: 1rem; width: 20px; text-align: center; flex-shrink: 0; }
.nav-label { overflow: hidden; }

.sidebar-bottom {
  padding: 10px 12px 14px;
  border-top: 1px solid #222;
}

.main { flex: 1; padding: 18px; min-width: 0; }

@media (max-width: 900px) {
  .sidebar { position: fixed; left: 0; top: 0; z-index: 100; }
  .sidebar.collapsed { width: 48px; }
  .main { margin-left: 48px; }
}
</style>
