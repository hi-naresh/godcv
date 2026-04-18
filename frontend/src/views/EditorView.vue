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
const { startBatchAnalysis, startBatchTailoring } = useTailor()

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

const hasJobs = computed(() => store.jobs.size > 0)
const anyBusy = computed(() => [...store.jobs.values()].some(j => j.tailoringStatus === 'running' || j.tailoringStatus === 'analyzing'))
const hasAnalysis = computed(() => [...store.jobs.values()].some(j => j.analysis !== null))
const allIdle = computed(() => [...store.jobs.values()].every(j => j.tailoringStatus === 'idle'))
const canCheck = computed(() =>
  hasJobs.value &&
  [...store.jobs.values()].some(j => j.jobDescription.trim()) &&
  store.markdown.trim()
)

function addJob() { store.addJob() }
function removeJob(id: string) { store.removeJob(id) }

function checkAll() {
  if (!store.markdown.trim()) return alert('Load a resume first.')
  const key = props.apiKey || store.profile?.gemini_api_key || ''
  startBatchAnalysis(key, store.markdown)
  const firstJob = [...store.jobs.keys()][0]
  if (firstJob) store.activeJobId = firstJob
}

function tailorAll() {
  const key = props.apiKey || store.profile?.gemini_api_key || ''
  startBatchTailoring(key, store.markdown)
  const firstJob = [...store.jobs.keys()][0]
  if (firstJob) store.activeJobId = firstJob
}

function exportPdf() { window.print() }

function acceptSuggestion(sugId: string) {
  const job = activeJob.value
  if (!job || !job.result) return
  const sug = job.suggestions.find(s => s.id === sugId)
  if (!sug) return

  // Merge content into the result markdown
  let md = job.result
  if (sug.type === 'remove') {
    // Remove the exact content from the markdown
    const textToRemove = sug.content.trim()
    // Try removing as a full line (bullet or text)
    const lineRegex = new RegExp(`^[ \\t]*${textToRemove.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[ \\t]*\\n?`, 'gm')
    md = md.replace(lineRegex, '')
  } else if (sug.type === 'replace' && sug.old_content) {
    // Replace old_content with new content
    md = md.replace(sug.old_content.trim(), sug.content.trim())
  } else if (sug.section === 'Skills' && sug.type === 'skill') {
    // Append skills to the Skills section
    const skillsMatch = md.match(/(# Skills\n)([\s\S]*?)(\n---|\n# |\n*$)/)
    if (skillsMatch) {
      const before = skillsMatch[1]
      const content = skillsMatch[2].trimEnd()
      const after = skillsMatch[3]
      md = md.replace(skillsMatch[0], before + content + ', ' + sug.content + after)
    }
  } else if (sug.type === 'project' && sug.section === 'Projects') {
    // Append new project entry at end of Projects section
    const projMatch = md.match(/(# Projects\n)([\s\S]*?)(\n---|\n# |\n*$)/)
    if (projMatch) {
      const before = projMatch[1]
      const content = projMatch[2].trimEnd()
      const after = projMatch[3]
      md = md.replace(projMatch[0], before + content + '\n\n' + sug.content + after)
    }
  } else if (sug.type === 'bullet') {
    // Append bullet to the matching entry
    const parts = sug.section.split(':')
    const entryKey = parts[1] || ''
    if (entryKey) {
      const keyEscaped = entryKey.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      const entryRegex = new RegExp(
        `(\\*\\*[^*]*${keyEscaped}[^*]*\\*\\*[\\s\\S]*?)(\\n(?=\\n\\*\\*|\\n---|\\n#|$))`,
        'i'
      )
      md = md.replace(entryRegex, (match, entryContent, trailing) => {
        return entryContent + '\n' + sug.content + trailing
      })
    }
  }

  // Update result and remove suggestion
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
    <!-- LEFT PANEL: Jobs Only -->
    <aside class="left-panel">
      <section class="panel-section">
        <div class="section-header">
          <h3>Jobs</h3>
          <button class="add-job-btn" @click="addJob">+ Add Job</button>
        </div>

        <div v-if="!hasJobs" class="empty-state">
          Add a job description to start tailoring your resume.
        </div>

        <div class="job-list">
          <JobCard
            v-for="job in jobList"
            :key="job.id"
            :job="job"
            @update:title="store.updateJob(job.id, { title: $event })"
            @update:job-description="store.updateJob(job.id, { jobDescription: $event })"
            @update:seniority-level="store.updateJob(job.id, { seniorityLevel: $event })"
            @remove="removeJob(job.id)"
          />
        </div>

        <div v-if="hasJobs" class="action-buttons">
          <button
            v-if="!hasAnalysis"
            class="check-all-btn"
            :disabled="!canCheck || anyBusy"
            @click="checkAll"
          >
            {{ anyBusy ? 'Analyzing...' : 'Check All' }}
          </button>
          <button
            v-if="hasAnalysis"
            class="tailor-all-btn"
            :disabled="anyBusy"
            @click="tailorAll"
          >
            {{ anyBusy ? 'Tailoring...' : 'Tailor All' }}
          </button>
          <button
            v-if="hasAnalysis && !anyBusy"
            class="recheck-btn"
            @click="checkAll"
          >
            Re-check
          </button>
        </div>
      </section>

      <!-- Section Editor in left panel -->
      <section v-if="store.markdown" class="panel-section sections-panel">
        <h3 class="sections-title">Edit Sections</h3>
        <SectionEditor
          :markdown="activeMarkdown"
          @update:markdown="onSectionUpdate"
        />
      </section>
    </aside>

    <!-- RIGHT PANEL: Preview Only -->
    <div class="right-panel">
      <TabBar
        v-if="hasJobs"
        :jobs="jobList"
        :activeTab="store.activeJobId"
        @select="store.activeJobId = $event"
      />

      <div class="preview-controls">
        <button class="export-btn" @click="exportPdf">Print / PDF</button>
      </div>

      <!-- Error banner -->
      <div v-if="activeJob && activeJob.tailoringStatus === 'error'" class="error-banner">
        <strong>Tailoring failed:</strong> {{ activeJob.error || 'Unknown error' }}
      </div>

      <!-- Empty state -->
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
          :pageMode="currentPageMode"
          :agentStatuses="activeAgentStatuses"
          :suggestions="activeSuggestions"
          @accept-suggestion="acceptSuggestion"
          @deny-suggestion="denySuggestion"
        />
      </div>

      <!-- Score Panel -->
      <ScorePanel
        v-if="activeJob"
        :scoring="activeScoring"
        :atsResult="activeAtsResult"
      />

      <!-- Step guide for new users -->
      <div v-if="!store.markdown && !hasJobs" class="step-guide">
        <div class="step"><span class="step-num">1</span> Set up resume in Profile</div>
        <div class="step-arrow">&rarr;</div>
        <div class="step"><span class="step-num">2</span> Add job descriptions</div>
        <div class="step-arrow">&rarr;</div>
        <div class="step"><span class="step-num">3</span> Tailor &amp; export</div>
      </div>
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

.section-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px;
}
.section-header h3 { margin: 0; font-size: 0.95rem; }
.add-job-btn {
  border: 1px solid #d0d0d0; background: #fafafa; border-radius: 8px;
  padding: 5px 12px; font-size: 0.8rem; font-weight: 600; cursor: pointer;
}
.add-job-btn:hover { background: #eee; }

.job-list { display: flex; flex-direction: column; gap: 8px; }

.empty-state {
  text-align: center; padding: 20px; color: #999; font-size: 0.85rem;
}

.action-buttons {
  display: flex; gap: 8px; margin-top: 8px;
}
.check-all-btn, .tailor-all-btn {
  flex: 1; padding: 11px; font-weight: 700; border-radius: 10px;
  border: none; color: white; cursor: pointer; font-size: 0.9rem;
}
.check-all-btn {
  background: linear-gradient(135deg, #28a745 0%, #218838 100%);
}
.tailor-all-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.recheck-btn {
  padding: 11px 14px; font-weight: 600; border-radius: 10px;
  border: 1px solid #d0d0d0; background: #fafafa; cursor: pointer;
  font-size: 0.8rem; color: #555;
}
.recheck-btn:hover { background: #eee; }
.check-all-btn:disabled, .tailor-all-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.check-all-btn:not(:disabled):hover, .tailor-all-btn:not(:disabled):hover { opacity: 0.9; }

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

.sections-panel {
  padding: 12px;
}
.sections-title {
  margin: 0 0 8px; font-size: 0.9rem; color: #555;
}
.preview-area {
  display: flex; justify-content: center;
}

.step-guide {
  display: flex; align-items: center; justify-content: center;
  gap: 12px; padding: 14px; color: #999; font-size: 0.82rem;
}
.step {
  display: flex; align-items: center; gap: 6px;
  background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
  padding: 8px 14px;
}
.step-num {
  width: 22px; height: 22px; border-radius: 50%; background: #667eea;
  color: #fff; font-weight: 700; font-size: 0.75rem;
  display: flex; align-items: center; justify-content: center;
}
.step-arrow { color: #ccc; font-size: 1.2rem; }

@media (max-width: 900px) {
  .editor-layout { flex-direction: column; align-items: stretch; }
  .left-panel {
    width: 100%; min-width: unset; position: static;
    max-height: unset;
  }
  .right-panel { max-width: 100%; }
}
</style>
