<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useEditorStore } from '../stores/editor'
import { useProfile } from '../composables/useProfile'
import { useTailor } from '../composables/useTailor'
import ResumePreview from '../components/ResumePreview.vue'
import SectionEditor from '../components/SectionEditor.vue'
import JobCard from '../components/JobCard.vue'
import TabBar from '../components/TabBar.vue'
import ScorePanel from '../components/ScorePanel.vue'

const props = defineProps<{ apiKey?: string }>()

const store = useEditorStore()
const { fetchProfile } = useProfile()
const { analyzeJob, tailorJob } = useTailor()

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
const activeSuggestions = computed(() => activeJob.value?.suggestions ?? [])

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

async function exportPdf() {
  const sheet = document.querySelector('.sheet') as HTMLElement
  if (!sheet) return

  const { default: html2canvas } = await import('html2canvas')
  const { default: jsPDF } = await import('jspdf')

  const origShadow = sheet.style.boxShadow
  sheet.style.boxShadow = 'none'

  try {
    const canvas = await html2canvas(sheet, { scale: 2, useCORS: true })
    const imgData = canvas.toDataURL('image/jpeg', 0.98)
    const pdf = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' })
    pdf.addImage(imgData, 'JPEG', 0, 0, 210, 297)
    pdf.save('resume.pdf')
  } finally {
    sheet.style.boxShadow = origShadow
  }
}

function acceptSuggestion(sugId: string) {
  const job = activeJob.value
  if (!job || !job.result) return
  const sug = job.suggestions.find(s => s.id === sugId)
  if (!sug) return

  let md = job.result
  if (sug.type === 'remove') {
    const textToRemove = sug.content.trim()
    const lineRegex = new RegExp(`^[ \\t]*${textToRemove.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[ \\t]*\\n?`, 'gm')
    md = md.replace(lineRegex, '')
  } else if (sug.type === 'replace' && sug.old_content) {
    md = md.replace(sug.old_content.trim(), sug.content.trim())
  } else if (sug.section === 'Skills' && sug.type === 'skill') {
    const skillsMatch = md.match(/(# Skills\n)([\s\S]*?)(\n---|\n# |\n*$)/)
    if (skillsMatch) {
      const before = skillsMatch[1]
      const content = skillsMatch[2].trimEnd()
      const after = skillsMatch[3]
      md = md.replace(skillsMatch[0], before + content + ', ' + sug.content + after)
    }
  } else if (sug.type === 'project' && sug.section === 'Projects') {
    const projMatch = md.match(/(# Projects\n)([\s\S]*?)(\n---|\n# |\n*$)/)
    if (projMatch) {
      const before = projMatch[1]
      const content = projMatch[2].trimEnd()
      const after = projMatch[3]
      md = md.replace(projMatch[0], before + content + '\n\n' + sug.content + after)
    }
  } else if (sug.type === 'bullet') {
    const parts = sug.section.split(':')
    const entryKey = parts[1] || ''
    if (entryKey) {
      const keyEscaped = entryKey.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      const entryRegex = new RegExp(
        `(\\*\\*[^*]*${keyEscaped}[^*]*\\*\\*[\\s\\S]*?)(\\n(?=\\n\\*\\*|\\n---|\\n#|$))`,
        'i'
      )
      md = md.replace(entryRegex, (_match, entryContent, trailing) => {
        return entryContent + '\n' + sug.content + trailing
      })
    }
  }

  store.updateJob(job.id, {
    result: md,
    suggestions: job.suggestions.filter(s => s.id !== sugId),
  })
}

function denySuggestion(sugId: string) {
  const job = activeJob.value
  if (!job) return
  store.updateJob(job.id, {
    suggestions: job.suggestions.filter(s => s.id !== sugId),
  })
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
          @update:seniority-level="store.updateJob(activeJob!.id, { seniorityLevel: $event })"
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
        <h3 class="sections-title">Edit Sections</h3>
        <SectionEditor
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

      <div v-else class="preview-area">
        <ResumePreview
          :markdown="activeMarkdown"
          :originalMarkdown="activeJob?.result ? store.markdown : undefined"
          :pageMode="currentPageMode"
          :agentStatuses="activeAgentStatuses"
          :suggestions="activeSuggestions"
          @accept-suggestion="acceptSuggestion"
          @deny-suggestion="denySuggestion"
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
  position: sticky; top: 60px; align-self: flex-start;
  display: flex; flex-direction: column; gap: 12px;
  max-height: calc(100vh - 80px); overflow-y: auto;
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
.export-btn {
  margin-left: auto; border: 1px solid #d0d0d0; background: #fafafa;
  border-radius: 8px; padding: 6px 14px; font-weight: 600;
  font-size: 0.8rem; cursor: pointer;
}
.export-btn:hover { background: #eee; }

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
.sections-title { margin: 0 0 8px; font-size: 0.9rem; color: #555; }
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
