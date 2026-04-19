<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSavedCVs, type SavedCV } from '../composables/useSavedCVs'
import { useEditorStore } from '../stores/editor'
import ResumePreview from '../components/ResumePreview.vue'

const store = useEditorStore()
const router = useRouter()
const { fetchSavedCVs, deleteCV } = useSavedCVs()

const cvs = ref<SavedCV[]>([])
const selectedCV = ref<SavedCV | null>(null)
const loading = ref(true)

onMounted(async () => {
  cvs.value = await fetchSavedCVs()
  loading.value = false
})

function selectCV(cv: SavedCV) {
  selectedCV.value = cv
}

async function loadInEditor(cv: SavedCV) {
  store.markdown = cv.markdown
  router.push('/')
}

async function removeCv(cv: SavedCV) {
  if (!confirm(`Delete "${cv.name}"?`)) return
  await deleteCV(cv.id)
  cvs.value = cvs.value.filter(c => c.id !== cv.id)
  if (selectedCV.value?.id === cv.id) selectedCV.value = null
}

function downloadPdf() {
  const sheet = document.querySelector('.sheet') as HTMLElement
  if (!sheet) return
  sheet.classList.add('export-mode')
  window.print()
  window.addEventListener('afterprint', () => sheet.classList.remove('export-mode'), { once: true })
  setTimeout(() => sheet.classList.remove('export-mode'), 2000)
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="saved-layout">
    <div class="saved-left">
      <h2>Saved CVs</h2>
      <div v-if="loading" class="empty">Loading...</div>
      <div v-else-if="cvs.length === 0" class="empty">
        <p>No saved CVs yet.</p>
        <p class="hint">After tailoring, click "Save CV" in the editor to store a version here.</p>
      </div>
      <div v-else class="cv-list">
        <div
          v-for="cv in cvs"
          :key="cv.id"
          :class="['cv-card', { active: selectedCV?.id === cv.id }]"
          @click="selectCV(cv)"
        >
          <div class="cv-card-header">
            <strong>{{ cv.name }}</strong>
            <button class="delete-btn" @click.stop="removeCv(cv)" title="Delete">&times;</button>
          </div>
          <div class="cv-card-meta">
            <span v-if="cv.job_title">{{ cv.job_title }}</span>
            <span v-if="cv.company"> at {{ cv.company }}</span>
          </div>
          <div class="cv-card-date">{{ formatDate(cv.created_at) }}</div>
          <button class="load-btn" @click.stop="loadInEditor(cv)">Load in Editor</button>
        </div>
      </div>
    </div>

    <div class="saved-right">
      <div v-if="selectedCV" class="preview-area">
        <div class="preview-controls">
          <div class="preview-label">Preview: {{ selectedCV.name }}</div>
          <button class="export-btn" @click="downloadPdf">Download PDF</button>
        </div>
        <ResumePreview :markdown="selectedCV.markdown" :pageMode="store.pageMode" />
      </div>
      <div v-else class="empty-preview">
        <p>Select a saved CV to preview</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.saved-layout {
  display: flex; gap: 18px; padding: 0 18px; max-width: 1400px; margin: 0 auto;
  align-items: flex-start;
}
.saved-left {
  width: min(420px, 35vw); min-width: 300px;
  position: sticky; top: 18px;
  display: flex; flex-direction: column; gap: 10px;
  max-height: calc(100vh - 36px); overflow-y: auto;
}
.saved-left h2 { margin: 0; }
.saved-right {
  flex: 1; max-width: 240mm;
  position: sticky; top: 18px;
  display: flex; flex-direction: column; gap: 8px;
}
.empty { color: #999; font-size: 0.9rem; padding: 20px 0; }
.hint { font-size: 0.8rem; color: #aaa; margin-top: 4px; }

.cv-list { display: flex; flex-direction: column; gap: 8px; }
.cv-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
  padding: 12px; cursor: pointer; transition: border-color 0.15s;
}
.cv-card:hover { border-color: #999; }
.cv-card.active { border-color: #111; background: #f9f9f9; }
.cv-card-header { display: flex; justify-content: space-between; align-items: center; }
.cv-card-header strong { font-size: 0.9rem; }
.cv-card-meta { font-size: 0.78rem; color: #666; margin-top: 2px; }
.cv-card-date { font-size: 0.72rem; color: #aaa; margin-top: 2px; }
.delete-btn {
  border: none; background: #f0f0f0; border-radius: 6px; width: 24px; height: 24px;
  font-size: 1rem; cursor: pointer; color: #999; display: flex; align-items: center; justify-content: center;
}
.delete-btn:hover { background: #ffe0e0; color: #d00; }
.load-btn {
  margin-top: 8px; padding: 6px 14px; border: 1px solid #d0d0d0; border-radius: 6px;
  background: #fff; font-size: 0.78rem; font-weight: 600; cursor: pointer;
}
.load-btn:hover { background: #f5f5f5; }

.preview-controls { display: flex; align-items: center; justify-content: space-between; }
.preview-label { font-size: 0.8rem; font-weight: 600; color: #999; text-transform: uppercase; letter-spacing: 0.5px; }
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
  .saved-layout { flex-direction: column; }
  .saved-left { width: 100%; min-width: unset; position: static; max-height: unset; }
  .saved-right { max-width: 100%; position: static; }
}
</style>
