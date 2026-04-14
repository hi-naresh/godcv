<script setup lang="ts">
import { ref, onMounted } from 'vue'

const history = ref<any[]>([])
const selected = ref<any>(null)

onMounted(async () => {
  const res = await fetch('/api/jobs')
  history.value = await res.json()
})

async function deleteJob(id: number) {
  await fetch(`/api/jobs/${id}`, { method: 'DELETE' })
  history.value = history.value.filter(j => j.id !== id)
  if (selected.value?.id === id) selected.value = null
}
</script>

<template>
  <div class="history-page">
    <h2>Tailoring History</h2>
    <div v-if="!history.length" class="empty">No tailoring history yet.</div>
    <div v-for="job in history" :key="job.id" class="history-card" @click="selected = job">
      <div class="history-header">
        <strong>{{ job.job_title || 'Untitled' }}</strong>
        <span v-if="job.company"> at {{ job.company }}</span>
        <span class="date">{{ new Date(job.created_at).toLocaleDateString() }}</span>
        <button class="delete-btn" @click.stop="deleteJob(job.id)">Delete</button>
      </div>
      <div class="history-meta">
        <span class="badge">{{ job.role_type || 'general' }}</span>
        <span>{{ job.sections_modified?.length || 0 }} sections modified</span>
      </div>
    </div>

    <div v-if="selected" class="detail-panel">
      <h3>Tailored Resume</h3>
      <pre class="resume-preview">{{ selected.tailored_resume }}</pre>
      <button @click="selected = null" class="close-btn">Close</button>
    </div>
  </div>
</template>

<style scoped>
.history-page { max-width: 800px; margin: 0 auto; }
h2 { margin-bottom: 12px; }
.empty { color: #666; }
.history-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
  padding: 12px; margin-bottom: 8px; cursor: pointer;
}
.history-card:hover { border-color: #667eea; }
.history-header { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.date { margin-left: auto; color: #999; font-size: 0.8rem; }
.delete-btn {
  font-size: 0.75rem; background: none; border: 1px solid #ddd;
  border-radius: 6px; padding: 2px 8px; cursor: pointer; color: #dc3545;
}
.history-meta { margin-top: 4px; font-size: 0.8rem; color: #666; display: flex; gap: 10px; }
.badge {
  background: #f0f0f0; padding: 1px 8px; border-radius: 4px;
  font-size: 0.75rem; font-weight: 600;
}
.detail-panel {
  margin-top: 16px; background: #fff; border: 1px solid #d9d9d9;
  border-radius: 12px; padding: 16px;
}
.resume-preview {
  white-space: pre-wrap; font-size: 0.8rem; max-height: 400px;
  overflow-y: auto; background: #f9f9f9; padding: 10px; border-radius: 8px;
}
.close-btn {
  margin-top: 10px; padding: 6px 16px; border: 1px solid #ccc;
  border-radius: 8px; background: #fafafa; cursor: pointer;
}
</style>
