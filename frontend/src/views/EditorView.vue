<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useEditorStore } from '../stores/editor'
import { useProfile } from '../composables/useProfile'
import { useTailor } from '../composables/useTailor'
import { useSavedCVs } from '../composables/useSavedCVs'
import { useExport } from '../composables/useExport'
import ResumePreview from '../components/ResumePreview.vue'
import SectionEditor from '../components/SectionEditor.vue'
import JobCard from '../components/JobCard.vue'
import TabBar from '../components/TabBar.vue'
import ScorePanel from '../components/ScorePanel.vue'

const props = defineProps<{ apiKey?: string }>()

const store = useEditorStore()
const { fetchProfile } = useProfile()
const { analyzeJob, tailorJob } = useTailor()
const { saveCV } = useSavedCVs()
const { exportPdf: exportPdfBackend } = useExport()
const saveMsg = ref('')
const rawMode = ref(false)
const justified = ref(true)
const editorCollapsed = ref(true)

onMounted(async () => {
  const p = await fetchProfile()
  if (p) {
    store.profile = p
    if (!store.markdown) store.markdown = p.master_resume
    if (p.page_mode) store.pageMode = p.page_mode
  }
})

const jobList = computed(() => [...store.jobs.values()])
const activeJob = computed(() => store.activeJobId ? store.jobs.get(store.activeJobId) ?? null : null)

const activeMarkdown = computed(() => {
  if (!store.activeJobId) return store.markdown
  return activeJob.value?.result ?? store.markdown
})

function onSectionUpdate(md: string) {
  if (!store.activeJobId) {
    store.markdown = md
  } else if (activeJob.value?.result) {
    store.updateJob(store.activeJobId, { result: md })
  } else {
    store.markdown = md
  }
}

const currentPageMode = computed(() => {
  if (!store.activeJobId) return store.pageMode
  return activeJob.value?.pageMode ?? 'single'
})

const activeAgentStatuses = computed(() => {
  if (!activeJob.value || activeJob.value.tailoringStatus !== 'running') return undefined
  return activeJob.value.agentStatuses
})

const activeScoring = computed(() => activeJob.value?.scoring ?? null)
const activeAtsResult = computed(() => activeJob.value?.atsResult ?? null)

// Per-job status helpers
const jobIsAnalyzing = computed(() => activeJob.value?.tailoringStatus === 'analyzing')
const jobIsAnalyzed = computed(() => activeJob.value?.analysis !== null)
const jobIsTailoring = computed(() => activeJob.value?.tailoringStatus === 'running')
const jobIsBusy = computed(() => jobIsAnalyzing.value || jobIsTailoring.value)
const jobCanCheck = computed(() =>
  activeJob.value !== null &&
  activeJob.value.jobDescription.trim() !== '' &&
  store.markdown.trim() !== ''
)

function addJob() {
  const id = store.addJob()
  store.activeJobId = id
}

function removeJob(id: string) { store.removeJob(id) }

function getApiKey(): string {
  return props.apiKey || store.profile?.gemini_api_key || ''
}

function checkJob() {
  if (!activeJob.value || !store.markdown.trim()) return
  analyzeJob(activeJob.value.id, getApiKey(), store.markdown)
}

function tailorCurrentJob() {
  if (!activeJob.value) return
  tailorJob(activeJob.value.id, getApiKey(), store.markdown)
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
    if (isMulti) {
      document.documentElement.style.setProperty('--print-page-margin', '0')
    }
  }
  window.addEventListener('afterprint', cleanup, { once: true })
  setTimeout(cleanup, 2000)
}

function buildExportFilename(): string {
  const job = activeJob.value
  const name = store.profile?.master_resume?.match(/^name:\s*(.+)$/m)?.[1]?.trim()
  const jobPart = job?.analysis?.job_title || job?.title
  const companyPart = job?.analysis?.company
  const parts = [name, jobPart, companyPart].filter(Boolean)
  const base = parts.length ? parts.join('_') : 'resume'
  return base.replace(/\s+/g, '_').replace(/[^A-Za-z0-9._-]/g, '') + '.pdf'
}

async function exportPdf() {
  const md = activeMarkdown.value
  if (!md?.trim()) return
  await exportPdfBackend({
    markdown: md,
    pageMode: currentPageMode.value,
    filename: buildExportFilename(),
    documentTitle: 'Resume',
    onFallback: printViaBrowser,
  })
}

async function saveCurrent() {
  const job = activeJob.value
  const md = activeMarkdown.value
  if (!md?.trim()) return

  const jobTitle = job?.analysis?.job_title || job?.title || ''
  const company = job?.analysis?.company || ''
  const defaultName = jobTitle ? `${jobTitle}${company ? ' - ' + company : ''}` : 'Saved CV'
  const name = prompt('Name this CV:', defaultName)
  if (!name) return

  await saveCV(name, md, jobTitle, company)
  saveMsg.value = 'CV saved!'
  setTimeout(() => saveMsg.value = '', 2000)
}

function discardChanges() {
  const job = activeJob.value
  if (!job) return
  if (!confirm('Discard tailored changes and revert to original resume?')) return
  store.updateJob(job.id, { result: undefined })
}


</script>

<template>
  <div class="editor-layout">
    <!-- LEFT PANEL: Active job controls + section editor -->
    <aside class="left-panel">
      <!-- Active job's JD and analysis -->
      <section v-if="activeJob" class="panel-section">
        <JobCard
          :job="activeJob"
          @update:title="store.updateJob(activeJob!.id, { title: $event })"
          @update:job-description="store.updateJob(activeJob!.id, { jobDescription: $event })"
          @update:role-level="store.updateJob(activeJob!.id, { roleLevel: $event })"
          @update:stealth-override="store.updateJob(activeJob!.id, { stealthOverride: $event })"
          @remove="removeJob(activeJob!.id)"
        />

        <div class="action-buttons">
          <button
            v-if="!jobIsAnalyzed && !jobIsAnalyzing"
            class="check-btn"
            :disabled="!jobCanCheck"
            @click="checkJob"
          >
            Check
          </button>
          <button v-if="jobIsAnalyzing" class="check-btn" disabled>
            Analyzing...
          </button>
          <button
            v-if="jobIsAnalyzed && !jobIsAnalyzing && !jobIsTailoring"
            class="tailor-btn"
            @click="tailorCurrentJob"
          >
            Tailor
          </button>
          <button v-if="jobIsTailoring" class="tailor-btn" disabled>
            Tailoring...
          </button>
          <button
            v-if="jobIsAnalyzed && !jobIsBusy"
            class="recheck-btn"
            @click="checkJob"
          >
            Re-check
          </button>
        </div>
      </section>

      <!-- No job selected -->
      <section v-else class="panel-section">
        <div class="empty-state">
          <p>Select a job tab or add a new one.</p>
          <button class="add-job-btn" @click="addJob">+ New Job</button>
        </div>
      </section>

      <!-- Section Editor -->
      <section v-if="store.markdown" class="panel-section sections-panel">
        <div class="sections-header" @click="editorCollapsed = !editorCollapsed">
          <h3 class="sections-title">Edit Sections</h3>
          <span class="collapse-icon">{{ editorCollapsed ? '+' : '-' }}</span>
        </div>
        <SectionEditor
          v-show="!editorCollapsed"
          :markdown="activeMarkdown"
          @update:markdown="onSectionUpdate"
        />
      </section>
    </aside>

    <!-- RIGHT PANEL: Tabs + Preview -->
    <div class="right-panel">
      <TabBar
        :jobs="jobList"
        :activeTab="store.activeJobId"
        @select="store.activeJobId = $event"
        @add="addJob"
        @remove="removeJob"
      />

      <div class="preview-controls">
        <div class="mode-toggle">
          <button :class="{ active: !rawMode }" @click="rawMode = false">Preview</button>
          <button :class="{ active: rawMode }" @click="rawMode = true">Markdown</button>
        </div>
        <button v-if="activeJob?.result" class="save-cv-btn" @click="saveCurrent">Save CV</button>
        <button v-if="activeJob?.result" class="discard-btn" @click="discardChanges">Discard</button>
        <button :class="['justify-btn', { active: justified }]" @click="justified = !justified" title="Toggle justified text">J</button>
        <span v-if="saveMsg" class="save-msg">{{ saveMsg }}</span>
        <button class="export-btn" @click="exportPdf">Download PDF</button>
      </div>

      <div v-if="activeJob && activeJob.tailoringStatus === 'error'" class="error-banner">
        <strong>Tailoring failed:</strong> {{ activeJob.error || 'Unknown error' }}
      </div>

      <div v-if="!store.markdown" class="empty-preview">
        <div class="empty-preview-content">
          <div class="empty-preview-icon">&#128196;</div>
          <p>Set up your resume in the Profile tab</p>
          <small>Add your experiences, projects, and skills there first</small>
        </div>
      </div>

      <div v-else :class="['preview-area', { justified }]">
        <ResumePreview
          :markdown="activeMarkdown"
          :originalMarkdown="activeJob?.result ? store.markdown : undefined"
          :pageMode="currentPageMode"
          :rawMode="rawMode"
          :agentStatuses="activeAgentStatuses"
          @update:markdown="onSectionUpdate"
        />
      </div>

      <ScorePanel
        v-if="activeJob"
        :scoring="activeScoring"
        :atsResult="activeAtsResult"
      />
    </div>
  </div>
</template>

<style scoped>
.editor-layout {
  display: flex; align-items: flex-start; justify-content: center;
  gap: 14px; padding: 0 14px; max-width: 1600px; margin: 0 auto;
}

.left-panel {
  width: min(440px, 34vw); min-width: 320px;
  position: sticky; top: 18px; align-self: flex-start;
  display: flex; flex-direction: column; gap: 12px;
  max-height: calc(100vh - 36px); overflow-y: auto;
}

.panel-section {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.05); padding: 14px;
}

.empty-state {
  text-align: center; padding: 20px; color: #999; font-size: 0.85rem;
  display: flex; flex-direction: column; align-items: center; gap: 10px;
}
.add-job-btn {
  border: 1px solid #d0d0d0; background: #fafafa; border-radius: 8px;
  padding: 8px 16px; font-size: 0.82rem; font-weight: 600; cursor: pointer;
}
.add-job-btn:hover { background: #eee; }

.action-buttons {
  display: flex; gap: 8px; margin-top: 10px;
}
.check-btn, .tailor-btn {
  flex: 1; padding: 10px; font-weight: 700; border-radius: 10px;
  border: none; color: white; cursor: pointer; font-size: 0.88rem;
}
.check-btn {
  background: linear-gradient(135deg, #28a745 0%, #218838 100%);
}
.tailor-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.recheck-btn {
  padding: 10px 14px; font-weight: 600; border-radius: 10px;
  border: 1px solid #d0d0d0; background: #fafafa; cursor: pointer;
  font-size: 0.8rem; color: #555;
}
.recheck-btn:hover { background: #eee; }
.check-btn:disabled, .tailor-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.check-btn:not(:disabled):hover, .tailor-btn:not(:disabled):hover { opacity: 0.9; }

.right-panel {
  flex: 1; max-width: 240mm;
  display: flex; flex-direction: column; gap: 10px;
}

.preview-controls {
  display: flex; align-items: center; gap: 10px;
}
.mode-toggle {
  display: flex; border: 1px solid #d0d0d0; border-radius: 6px; overflow: hidden;
}
.mode-toggle button {
  padding: 4px 14px; border: none; background: #fff; font-size: 0.75rem;
  font-weight: 600; cursor: pointer; color: #666;
}
.mode-toggle button.active { background: #111; color: #fff; }
.mode-toggle button:not(.active):hover { background: #f5f5f5; }
.justify-btn {
  width: 28px; height: 28px; border: 1px solid #d0d0d0; border-radius: 6px;
  background: #fff; font-size: 0.8rem; font-weight: 800; cursor: pointer;
  color: #999; font-family: Georgia, serif;
}
.justify-btn.active { background: #111; color: #fff; border-color: #111; }
.justify-btn:not(.active):hover { background: #f5f5f5; }
.export-btn {
  margin-left: auto; border: 1px solid #d0d0d0; background: #fafafa;
  border-radius: 8px; padding: 6px 14px; font-weight: 600;
  font-size: 0.8rem; cursor: pointer;
}
.export-btn:hover { background: #eee; }
.save-cv-btn {
  border: 1px solid #28a745; background: #28a745; color: #fff;
  border-radius: 8px; padding: 6px 14px; font-weight: 600;
  font-size: 0.8rem; cursor: pointer;
}
.save-cv-btn:hover { background: #218838; }
.discard-btn {
  border: 1px solid #d0d0d0; background: #fff;
  border-radius: 8px; padding: 6px 14px; font-weight: 600;
  font-size: 0.8rem; cursor: pointer; color: #d00;
}
.discard-btn:hover { background: #fff0f0; }
.save-msg { color: #28a745; font-size: 0.8rem; font-weight: 600; }

.error-banner {
  background: #fff0f0; border: 1px solid #fcc; border-radius: 10px;
  padding: 10px 14px; font-size: 0.82rem; color: #c00; line-height: 1.4;
  word-break: break-word;
}
.error-banner strong { font-weight: 700; }

.empty-preview {
  min-height: 300px;
  background: #fff; border: 2px dashed #d9d9d9; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
}
.empty-preview-content { text-align: center; color: #999; }
.empty-preview-icon { font-size: 3rem; margin-bottom: 8px; }
.empty-preview-content p { margin: 0; font-weight: 600; }
.empty-preview-content small { font-size: 0.8rem; }

.sections-panel { padding: 12px; }
.sections-header {
  display: flex; align-items: center; justify-content: space-between;
  cursor: pointer; user-select: none;
}
.sections-header .collapse-icon { font-size: 1.1rem; font-weight: 700; color: #888; }
.sections-title { margin: 0; font-size: 0.9rem; color: #555; }
.preview-area { display: flex; justify-content: center; }

@media (max-width: 900px) {
  .editor-layout { flex-direction: column; align-items: stretch; }
  .left-panel {
    width: 100%; min-width: unset; position: static;
    max-height: unset;
  }
  .right-panel { max-width: 100%; }
}
</style>
