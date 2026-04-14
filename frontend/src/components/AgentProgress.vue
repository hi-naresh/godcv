<script setup lang="ts">
import { computed } from 'vue'
import type { JobState } from '../stores/editor'

const props = defineProps<{ job: JobState }>()

const agents = computed(() => {
  const entries = Object.entries(props.job.agentStatuses)
  return entries.map(([key, status]) => ({
    key,
    label: key.includes(':') ? key.split(':')[1] : key,
    type: key.includes(':') ? 'experience' : key,
    status,
  }))
})
</script>

<template>
  <div class="progress-panel">
    <div class="progress-header">
      <span class="progress-status running">Tailoring in progress...</span>
    </div>
    <div class="agent-list">
      <div v-for="agent in agents" :key="agent.key" class="agent-item" :class="agent.status">
        <span class="agent-dot" />
        <span class="agent-name">{{ agent.label }}</span>
        <span class="agent-badge">{{ agent.status }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.progress-panel {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
  padding: 12px;
}
.progress-header { margin-bottom: 8px; font-weight: 600; }
.progress-status.running { color: #667eea; }
.agent-list { display: flex; flex-direction: column; gap: 4px; }
.agent-item {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 8px; border-radius: 6px; font-size: 0.85rem;
}
.agent-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.agent-item.pending .agent-dot { background: #ccc; }
.agent-item.running .agent-dot { background: #667eea; animation: pulse 1s infinite; }
.agent-item.done .agent-dot { background: #28a745; }
.agent-badge { margin-left: auto; font-size: 0.75rem; color: #999; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
