<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useEditorStore } from '../stores/editor'
import { useExport } from '../composables/useExport'
import ResumePreview from '../components/ResumePreview.vue'

const store = useEditorStore()
const router = useRouter()
const { exportPdf: exportPdfBackend } = useExport()
const history = ref<any[]>([])
const selected = ref<any>(null)

onMounted(async () => {
  const res = await fetch('/api/jobs')
  if (res.ok) history.value = await res.json()
})

async function deleteJob(id: number) {
  await fetch(`/api/jobs/${id}`, { method: 'DELETE' })
  history.value = history.value.filter(j => j.id !== id)
  if (selected.value?.id === id) selected.value = null
}

function loadInEditor(job: any) {
  if (job.tailored_resume) {
    store.markdown = job.tailored_resume
    router.push('/')
  }
}

function printViaBrowser() {
  const sheet = document.querySelector('.sheet') as HTMLElement
  if (!sheet) return
  sheet.classList.add('export-mode')
  const isMulti = store.pageMode === 'multi'
  if (isMulti) {
    document.documentElement.style.setProperty('--base-font-size', '11px')
    document.documentElement.style.setProperty('--line-height', '1.4')
    document.documentElement.style.setProperty('--print-page-margin', 'var(--page-margin)')
  }
  window.print()
  const cleanup = () => {
    sheet.classList.remove('export-mode')
    if (isMulti) document.documentElement.style.setProperty('--print-page-margin', '0')
  }
  window.addEventListener('afterprint', cleanup, { once: true })
  setTimeout(cleanup, 2000)
}

async function downloadPdf() {
  const job = selected.value
  if (!job?.tailored_resume) return
  const parts = [job.job_title, job.company].filter(Boolean)
  const filename = (parts.join('_') || 'tailored_resume').replace(/\s+/g, '_').replace(/[^A-Za-z0-9._-]/g, '') + '.pdf'
  await exportPdfBackend({
    markdown: job.tailored_resume,
    pageMode: store.pageMode,
    filename,
    documentTitle: job.job_title || 'Resume',
    onFallback: printViaBrowser,
  })
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="history-layout">
    <div class="history-left">
      <h2>Tailoring History</h2>
      <div v-if="!history.length" class="empty-state">
        <p>No tailoring history yet.</p>
        <p class="hint">Tailor a resume from the Editor tab to see history here.</p>
      </div>
      <div v-else class="job-list">
        <div
          v-for="job in history"
          :key="job.id"
          :class="['job-card', { active: selected?.id === job.id }]"
          @click="selected = job"
        >
          <div class="job-header">
            <strong>{{ job.job_title || 'Untitled' }}</strong>
            <button class="delete-btn" @click.stop="deleteJob(job.id)" title="Delete">&times;</button>
          </div>
          <div class="job-meta">
            <span v-if="job.company">{{ job.company }}</span>
            <span class="badge">{{ job.role_type || 'general' }}</span>
            <span>{{ (job.sections_modified || []).length }} sections</span>
          </div>
          <div class="job-date">{{ formatDate(job.created_at) }}</div>
          <button class="load-btn" @click.stop="loadInEditor(job)">Load in Editor</button>
        </div>
      </div>
    </div>

    <div class="history-right">
      <div v-if="selected" class="preview-area">
        <div class="preview-controls">
          <div class="preview-label">{{ selected.job_title || 'Tailored Resume' }}<span v-if="selected.company"> at {{ selected.company }}</span></div>
          <button class="export-btn" @click="downloadPdf">Download PDF</button>
        </div>
        <ResumePreview v-if="selected.tailored_resume" :markdown="selected.tailored_resume" :pageMode="store.pageMode" />
      </div>
      <div v-else class="empty-preview">
        <p>Select a history item to preview</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-layout {
  display: flex; gap: 18px; max-width: 1400px; margin: 0 auto;
  align-items: flex-start;
}
.history-left {
  width: min(400px, 35vw); min-width: 280px;
  position: sticky; top: 18px;
  display: flex; flex-direction: column; gap: 8px;
  max-height: calc(100vh - 36px); overflow-y: auto;
}
.history-left h2 { margin: 0; }
.history-right {
  flex: 1; max-width: 240mm;
  position: sticky; top: 18px;
  display: flex; flex-direction: column; gap: 8px;
}
.empty-state {
  color: #999; font-size: 0.9rem; padding: 30px;
  background: #fff; border: 2px dashed #e0e0e0; border-radius: 12px; text-align: center;
}
.hint { font-size: 0.8rem; color: #aaa; margin-top: 4px; }

.job-list { display: flex; flex-direction: column; gap: 6px; }
.job-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
  padding: 12px; cursor: pointer; transition: border-color 0.15s;
}
.job-card:hover { border-color: #999; }
.job-card.active { border-color: #111; background: #f9f9f9; }
.job-header { display: flex; justify-content: space-between; align-items: center; }
.job-header strong { font-size: 0.88rem; }
.job-meta { display: flex; gap: 8px; font-size: 0.78rem; color: #666; margin-top: 3px; align-items: center; }
.badge { background: #f0f0f0; padding: 1px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 600; }
.job-date { font-size: 0.72rem; color: #aaa; margin-top: 2px; }
.delete-btn {
  border: none; background: #f0f0f0; border-radius: 6px; width: 24px; height: 24px;
  font-size: 1rem; cursor: pointer; color: #999; display: flex; align-items: center; justify-content: center;
}
.delete-btn:hover { background: #ffe0e0; color: #d00; }
.load-btn {
  margin-top: 8px; padding: 5px 12px; border: 1px solid #d0d0d0; border-radius: 6px;
  background: #fff; font-size: 0.76rem; font-weight: 600; cursor: pointer;
}
.load-btn:hover { background: #f5f5f5; }

.preview-controls { display: flex; align-items: center; justify-content: space-between; }
.preview-label { font-size: 0.8rem; font-weight: 600; color: #999; }
.export-btn {
  border: 1px solid #d0d0d0; background: #fafafa; border-radius: 8px;
  padding: 6px 14px; font-weight: 600; font-size: 0.8rem; cursor: pointer;
}
.export-btn:hover { background: #eee; }
.empty-preview {
  width: var(--page-w); min-height: 300px;
  background: #fff; border: 2px dashed #d9d9d9; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  color: #999; font-size: 0.85rem;
}

@media (max-width: 900px) {
  .history-layout { flex-direction: column; }
  .history-left { width: 100%; min-width: unset; position: static; max-height: unset; }
  .history-right { max-width: 100%; position: static; }
}
</style>
