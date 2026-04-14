<script setup lang="ts">
import type { JobState } from '../stores/editor'

defineProps<{
  jobs: JobState[]
  activeTab: string | null
}>()

defineEmits<{
  select: [id: string | null]
}>()

function statusIcon(status: JobState['tailoringStatus']): string {
  switch (status) {
    case 'running': return '...'
    case 'done': return 'done'
    case 'error': return '!'
    default: return ''
  }
}
</script>

<template>
  <div class="tab-bar">
    <button
      class="tab"
      :class="{ active: activeTab === null }"
      @click="$emit('select', null)"
    >Original</button>
    <button
      v-for="job in jobs"
      :key="job.id"
      class="tab"
      :class="{ active: activeTab === job.id, [job.tailoringStatus]: true }"
      @click="$emit('select', job.id)"
    >
      <span class="tab-label">{{ job.title || job.id }}</span>
      <span v-if="job.tailoringStatus !== 'idle'" class="tab-status" :class="job.tailoringStatus">
        {{ statusIcon(job.tailoringStatus) }}
      </span>
    </button>
  </div>
</template>

<style scoped>
.tab-bar {
  display: flex; gap: 2px; background: #e8e8e8; border-radius: 10px;
  padding: 3px; overflow-x: auto; flex-shrink: 0;
}
.tab {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 14px; border: none; background: transparent;
  border-radius: 8px; font-size: 0.82rem; font-weight: 600;
  cursor: pointer; white-space: nowrap; transition: all 0.15s;
  color: #666;
}
.tab:hover { background: #f0f0f0; color: #333; }
.tab.active { background: #fff; color: #111; box-shadow: 0 1px 4px rgba(0,0,0,.1); }
.tab-label { max-width: 160px; overflow: hidden; text-overflow: ellipsis; }
.tab-status {
  font-size: 0.7rem; padding: 1px 5px; border-radius: 4px;
}
.tab-status.running { color: #667eea; animation: pulse 1s infinite; }
.tab-status.done { color: #28a745; }
.tab-status.error { color: #dc3545; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
