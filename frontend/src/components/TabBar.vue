<script setup lang="ts">
import type { JobState } from '../stores/editor'

defineProps<{
  jobs: JobState[]
  activeTab: string | null
}>()

defineEmits<{
  select: [id: string | null]
  add: []
  remove: [id: string]
}>()

function tabLabel(job: JobState): string {
  if (job.title) return job.title
  if (job.analysis) return job.analysis.job_title || job.id
  return 'New Job'
}

function statusIcon(status: JobState['tailoringStatus']): string {
  switch (status) {
    case 'analyzing': return '...'
    case 'analyzed': return ''
    case 'running': return '...'
    case 'done': return ''
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
      <span class="tab-label">{{ tabLabel(job) }}</span>
      <span v-if="statusIcon(job.tailoringStatus)" class="tab-status" :class="job.tailoringStatus">
        {{ statusIcon(job.tailoringStatus) }}
      </span>
      <span
        class="tab-close"
        @click.stop="$emit('remove', job.id)"
        title="Close tab"
      >&times;</span>
    </button>
    <button class="tab tab-add" @click="$emit('add')" title="Add job">+</button>
  </div>
</template>

<style scoped>
.tab-bar {
  display: flex; gap: 2px; background: #e8e8e8; border-radius: 10px;
  padding: 3px; overflow-x: auto; flex-shrink: 0;
}
.tab {
  display: flex; align-items: center; gap: 4px;
  padding: 7px 12px; border: none; background: transparent;
  border-radius: 8px; font-size: 0.82rem; font-weight: 600;
  cursor: pointer; white-space: nowrap; transition: all 0.15s;
  color: #666;
}
.tab:hover { background: #f0f0f0; color: #333; }
.tab.active { background: #fff; color: #111; box-shadow: 0 1px 4px rgba(0,0,0,.1); }
.tab-label { max-width: 140px; overflow: hidden; text-overflow: ellipsis; }
.tab-status {
  font-size: 0.7rem; padding: 1px 5px; border-radius: 4px;
}
.tab-status.analyzing, .tab-status.running { color: #667eea; animation: pulse 1s infinite; }
.tab-status.error { color: #dc3545; }
.tab-close {
  font-size: 0.85rem; color: #999; padding: 0 2px; border-radius: 3px;
  line-height: 1;
}
.tab-close:hover { color: #d00; background: #ffe0e0; }
.tab-add {
  font-size: 1.1rem; font-weight: 700; color: #999; padding: 5px 12px;
}
.tab-add:hover { color: #667eea; background: #f0f0f0; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
