<script setup lang="ts">
import { computed } from 'vue'
import type { RoleLevel } from '../composables/useRoleLevel'
import type { JobState } from '../stores/editor'
import { useEditorStore } from '../stores/editor'

const store = useEditorStore()

const props = defineProps<{ job: JobState }>()

const emit = defineEmits<{
  'update:title': [value: string]
  'update:jobDescription': [value: string]
  'update:roleLevel': [value: RoleLevel | null]
  'update:stealthOverride': [value: boolean]
  remove: []
}>()

function onJdInput(value: string) {
  emit('update:jobDescription', value)
}

const fitLevel = computed(() => {
  if (!props.job.scoring?.before) return null
  const score = props.job.scoring.before.overall_fit
  if (score >= 70) return 'good'
  if (score >= 45) return 'moderate'
  return 'poor'
})

const fitWarning = computed(() => {
  if (!props.job.analysis || !props.job.scoring?.before) return null
  const score = props.job.scoring.before.overall_fit
  const fit = props.job.scoring.before.experience_fit
  if (score < 40) {
    return `Low fit (${score}/100) — review the gap list before tailoring. ${fit}`
  }
  return null
})
</script>

<template>
  <div class="job-card" :class="job.tailoringStatus">
    <div class="job-card-header">
      <span v-if="job.tailoringStatus === 'done'" class="status-badge done">Done</span>
      <span v-else-if="job.tailoringStatus === 'analyzed'" class="status-badge analyzed">Analyzed</span>
      <span v-else-if="job.tailoringStatus === 'analyzing'" class="status-badge running">Analyzing...</span>
      <span v-else-if="job.tailoringStatus === 'running'" class="status-badge running">Tailoring...</span>
      <span v-else-if="job.tailoringStatus === 'error'" class="status-badge error">Error</span>
      <button class="remove-btn" @click="$emit('remove')" title="Remove job">&times;</button>
    </div>
    <!-- Live status message -->
    <div v-if="job.statusMessage" class="status-message">
      {{ job.statusMessage }}
    </div>
    <textarea
      class="jd-textarea"
      :value="job.jobDescription"
      @input="onJdInput(($event.target as HTMLTextAreaElement).value)"
      placeholder="Paste job description here..."
    />
    <div v-if="job.tailoringStatus === 'error' && job.error" class="error-message">
      {{ job.error }}
    </div>

    <!-- Job Analysis Card — shown after orchestrator responds -->
    <div v-if="job.analysis" class="analysis-card">
      <div class="analysis-header">
        <span class="analysis-company">{{ job.analysis.company }}</span>
        <span class="analysis-level" :class="job.analysis.role_level">{{ job.analysis.role_level === 'graduate' ? 'Graduate' : 'Non-Graduate' }}</span>
      </div>
      <div class="analysis-role">{{ job.analysis.job_title }}</div>
      <div v-if="job.scoring?.before" class="analysis-fit" :class="fitLevel">
        <span class="fit-score">{{ job.scoring.before.overall_fit }}% fit</span>
        <span class="fit-detail">{{ job.scoring.before.experience_fit }}</span>
      </div>
      <div v-if="fitWarning" class="fit-warning">
        {{ fitWarning }}
      </div>
      <div v-if="job.analysis.matched_strengths.length" class="analysis-tags">
        <span v-for="s in job.analysis.matched_strengths.slice(0, 4)" :key="s" class="tag match">{{ s }}</span>
      </div>
      <div v-if="job.scoring?.gap_suggestions?.length" class="analysis-gaps">
        <span class="gaps-label">Gaps:</span>
        <ul class="gaps-list">
          <li v-for="(gap, i) in job.scoring.gap_suggestions" :key="i">{{ gap }}</li>
        </ul>
      </div>
    </div>

    <div v-if="job.roleLevel" class="role-level-chip">
      <button
        type="button"
        :class="{ active: job.roleLevel === 'graduate' }"
        @click="$emit('update:roleLevel', 'graduate')"
      >Graduate</button>
      <button
        type="button"
        :class="{ active: job.roleLevel === 'non-graduate' }"
        @click="$emit('update:roleLevel', 'non-graduate')"
      >Non-Graduate</button>
    </div>

    <label v-if="job.analysis" class="stealth-toggle">
      <input
        type="checkbox"
        :checked="job.stealthOverride ?? store.profile?.stealth_mode ?? false"
        @change="$emit('update:stealthOverride', ($event.target as HTMLInputElement).checked)"
      />
      <span>Stealth: {{ (job.stealthOverride ?? store.profile?.stealth_mode) ? 'ON' : 'OFF' }}</span>
    </label>
  </div>
</template>

<style scoped>
.job-card {
  border: 1px solid #e0e0e0; border-radius: 10px; padding: 10px;
  display: flex; flex-direction: column; gap: 6px;
  transition: border-color 0.2s;
}
.job-card.analyzing { border-color: #667eea; }
.job-card.analyzed { border-color: #28a745; }
.job-card.running { border-color: #667eea; }
.job-card.done { border-color: #28a745; }
.job-card.error { border-color: #dc3545; }
.job-card-header { display: flex; align-items: center; justify-content: flex-end; gap: 6px; }
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
.role-level-chip {
  display: inline-flex; border: 1px solid #d9d9d9; border-radius: 6px; overflow: hidden;
  align-self: flex-start;
}
.role-level-chip button {
  border: none; background: #fff; padding: 4px 10px; font-size: 0.75rem;
  font-weight: 600; cursor: pointer; color: #666; line-height: 1.4;
}
.role-level-chip button:not(:last-child) {
  border-right: 1px solid #d9d9d9;
}
.role-level-chip button:hover:not(.active) { background: #f5f5f5; }
.role-level-chip button.active { background: #111; color: #fff; }
.status-badge {
  font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 4px;
}
.status-badge.done { background: #e6f9e6; color: #28a745; }
.status-badge.analyzed { background: #e6f9e6; color: #1a7f37; }
.status-badge.running { background: #eef0ff; color: #667eea; }
.status-badge.error { background: #ffe6e6; color: #dc3545; }
.jd-textarea {
  width: 100%; min-height: 60px; resize: vertical; padding: 8px;
  border: 1px dashed #c9c9c9; border-radius: 8px; font-size: 0.8rem;
}
.jd-textarea:focus { outline: none; border-color: #667eea; }
.status-message {
  background: #eef0ff; border: 1px solid #d0d5f0; border-radius: 6px;
  padding: 5px 8px; font-size: 0.75rem; color: #667eea; font-weight: 500;
  animation: pulse-status 1.5s ease-in-out infinite;
}
@keyframes pulse-status { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.error-message {
  background: #fff0f0; border: 1px solid #fcc; border-radius: 6px;
  padding: 6px 8px; font-size: 0.78rem; color: #c00; line-height: 1.3;
  word-break: break-word;
}

/* Analysis card */
.analysis-card {
  background: #f8f9fb; border: 1px solid #e4e7ec; border-radius: 8px;
  padding: 8px 10px; display: flex; flex-direction: column; gap: 4px;
}
.analysis-header {
  display: flex; align-items: center; justify-content: space-between;
}
.analysis-company {
  font-weight: 700; font-size: 0.82rem; color: #333;
}
.analysis-level {
  font-size: 0.68rem; font-weight: 700; padding: 1px 7px; border-radius: 4px;
  text-transform: uppercase; letter-spacing: 0.3px;
}
.analysis-level.graduate { background: #e6f4ea; color: #1a7f37; }
.analysis-level.non-graduate { background: #e8f0fe; color: #1a73e8; }
.analysis-role {
  font-size: 0.8rem; color: #555; font-weight: 500;
}
.analysis-fit {
  display: flex; align-items: center; gap: 6px; font-size: 0.78rem;
}
.fit-score {
  font-weight: 700; padding: 1px 6px; border-radius: 4px;
}
.analysis-fit.good .fit-score { background: #e6f4ea; color: #1a7f37; }
.analysis-fit.moderate .fit-score { background: #fef3e2; color: #b45309; }
.analysis-fit.poor .fit-score { background: #fce8e6; color: #c5221f; }
.fit-detail {
  color: #777; font-size: 0.72rem; flex: 1;
}
.fit-warning {
  background: #fce8e6; border: 1px solid #f5c6cb; border-radius: 6px;
  padding: 5px 8px; font-size: 0.75rem; color: #c5221f; font-weight: 500;
  line-height: 1.3;
}
.analysis-tags {
  display: flex; flex-wrap: wrap; gap: 4px;
}
.tag {
  font-size: 0.68rem; padding: 1px 6px; border-radius: 3px;
}
.tag.match { background: #e8f0fe; color: #1a73e8; }

.analysis-gaps {
  border-top: 1px solid #e4e7ec; padding-top: 4px; margin-top: 2px;
}
.gaps-label {
  font-size: 0.72rem; font-weight: 700; color: #b45309; text-transform: uppercase; letter-spacing: 0.3px;
}
.gaps-list {
  margin: 2px 0 0 14px; padding: 0;
}
.gaps-list li {
  font-size: 0.72rem; color: #8b5e34; line-height: 1.35; margin-bottom: 1px;
}

.stealth-toggle {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 0.75rem; color: #666; cursor: pointer;
  align-self: flex-start;
}
.stealth-toggle input { margin: 0; cursor: pointer; }
</style>
