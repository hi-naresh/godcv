<script setup lang="ts">
import { SENIORITY_OPTIONS, detectSeniority, detectJobTitle, type SeniorityLevel } from '../composables/useSeniority'
import type { JobState } from '../stores/editor'

const props = defineProps<{ job: JobState }>()

const emit = defineEmits<{
  'update:title': [value: string]
  'update:jobDescription': [value: string]
  'update:seniorityLevel': [value: SeniorityLevel | null]
  remove: []
}>()

function onJdInput(value: string) {
  emit('update:jobDescription', value)
  const detected = detectSeniority(value)
  if (detected) {
    emit('update:seniorityLevel', detected)
  }
  // Auto-detect title if user hasn't manually typed one
  if (!props.job.title) {
    const title = detectJobTitle(value)
    if (title) emit('update:title', title)
  }
}
</script>

<template>
  <div class="job-card" :class="job.tailoringStatus">
    <div class="job-card-header">
      <input
        class="job-title-input"
        :value="job.title"
        @input="$emit('update:title', ($event.target as HTMLInputElement).value)"
        placeholder="Job title (e.g., ML Engineer @ Google)"
      />
      <button class="remove-btn" @click="$emit('remove')" title="Remove job">&times;</button>
    </div>
    <div class="job-card-row">
      <select
        class="seniority-select"
        :value="job.seniorityLevel || ''"
        @change="$emit('update:seniorityLevel', ($event.target as HTMLSelectElement).value as SeniorityLevel || null)"
      >
        <option value="">Auto-detect level</option>
        <option v-for="level in SENIORITY_OPTIONS" :key="level" :value="level">
          {{ level.charAt(0).toUpperCase() + level.slice(1) }}
        </option>
      </select>
      <span v-if="job.tailoringStatus === 'done'" class="status-badge done">Done</span>
      <span v-else-if="job.tailoringStatus === 'running'" class="status-badge running">Running...</span>
      <span v-else-if="job.tailoringStatus === 'error'" class="status-badge error">Error</span>
    </div>
    <textarea
      class="jd-textarea"
      :value="job.jobDescription"
      @input="onJdInput(($event.target as HTMLTextAreaElement).value)"
      placeholder="Paste job description here..."
    />
  </div>
</template>

<style scoped>
.job-card {
  border: 1px solid #e0e0e0; border-radius: 10px; padding: 10px;
  display: flex; flex-direction: column; gap: 6px;
  transition: border-color 0.2s;
}
.job-card.running { border-color: #667eea; }
.job-card.done { border-color: #28a745; }
.job-card.error { border-color: #dc3545; }
.job-card-header { display: flex; align-items: center; gap: 6px; }
.job-title-input {
  flex: 1; border: 1px solid #d9d9d9; border-radius: 6px;
  padding: 6px 8px; font-size: 0.85rem; font-weight: 600;
}
.job-title-input:focus { outline: none; border-color: #667eea; }
.remove-btn {
  width: 28px; height: 28px; border: none; background: #f5f5f5;
  border-radius: 6px; font-size: 1.1rem; cursor: pointer; color: #999;
  display: flex; align-items: center; justify-content: center;
}
.remove-btn:hover { background: #ffe0e0; color: #d00; }
.job-card-row { display: flex; align-items: center; gap: 8px; }
.seniority-select {
  flex: 1; border: 1px solid #d9d9d9; border-radius: 6px;
  padding: 5px 8px; font-size: 0.8rem; background: #fff;
}
.status-badge {
  font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 4px;
}
.status-badge.done { background: #e6f9e6; color: #28a745; }
.status-badge.running { background: #eef0ff; color: #667eea; }
.status-badge.error { background: #ffe6e6; color: #dc3545; }
.jd-textarea {
  width: 100%; min-height: 60px; resize: vertical; padding: 8px;
  border: 1px dashed #c9c9c9; border-radius: 8px; font-size: 0.8rem;
}
.jd-textarea:focus { outline: none; border-color: #667eea; }
</style>
