<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useEditorStore } from '../stores/editor'
import { useProfile } from '../composables/useProfile'
import { useTailor } from '../composables/useTailor'
import MarkdownEditor from '../components/MarkdownEditor.vue'
import ResumePreview from '../components/ResumePreview.vue'
import JobCard from '../components/JobCard.vue'
import AgentProgress from '../components/AgentProgress.vue'
import TabBar from '../components/TabBar.vue'
import PageModeToggle from '../components/PageModeToggle.vue'

const props = defineProps<{ apiKey?: string }>()

const store = useEditorStore()
const { fetchProfile } = useProfile()
const { startTailoring, startBatchTailoring } = useTailor()

onMounted(async () => {
  const p = await fetchProfile()
  if (p) {
    store.profile = p
    if (!store.markdown) store.markdown = p.master_resume
  }
})

const jobList = computed(() => [...store.jobs.values()])
const activeJob = computed(() => store.activeJobId ? store.jobs.get(store.activeJobId) ?? null : null)
const previewMarkdown = computed(() => {
  if (!store.activeJobId) return store.markdown
  return activeJob.value?.result ?? store.markdown
})

const currentPageMode = computed({
  get: () => {
    if (!store.activeJobId) return store.pageMode
    return activeJob.value?.pageMode ?? 'single'
  },
  set: (val: 'single' | 'multi') => {
    if (!store.activeJobId) {
      store.pageMode = val
    } else {
      store.updateJob(store.activeJobId, { pageMode: val })
    }
  },
})

const hasJobs = computed(() => store.jobs.size > 0)
const anyRunning = computed(() => [...store.jobs.values()].some(j => j.tailoringStatus === 'running'))
const canTailor = computed(() =>
  hasJobs.value &&
  [...store.jobs.values()].some(j => j.jobDescription.trim()) &&
  store.markdown.trim()
)

function addJob() {
  store.addJob()
}

function removeJob(id: string) {
  store.removeJob(id)
}

function tailorAll() {
  if (!store.markdown.trim()) return alert('Load a resume first.')
  const key = props.apiKey || store.profile?.gemini_api_key || ''
  startBatchTailoring(key, store.markdown)
  // Auto-switch to the first job tab
  const firstJob = [...store.jobs.keys()][0]
  if (firstJob) store.activeJobId = firstJob
}

function exportPdf() { window.print() }
</script>

<template>
  <div class="editor-layout">
    <!-- LEFT PANEL -->
    <aside class="left-panel">
      <section class="panel-section">
        <MarkdownEditor v-model="store.markdown" />
      </section>

      <section class="panel-section jobs-section">
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

        <button
          v-if="hasJobs"
          class="tailor-all-btn"
          :disabled="!canTailor || anyRunning"
          @click="tailorAll"
        >
          {{ anyRunning ? 'Tailoring...' : 'Tailor All' }}
        </button>
      </section>
    </aside>

    <!-- RIGHT PANEL -->
    <div class="right-panel">
      <TabBar
        v-if="hasJobs"
        :jobs="jobList"
        :activeTab="store.activeJobId"
        @select="store.activeJobId = $event"
      />

      <div class="preview-controls">
        <PageModeToggle v-model="currentPageMode" />
        <button class="export-btn" @click="exportPdf">Print / PDF</button>
      </div>

      <AgentProgress v-if="activeJob && activeJob.tailoringStatus === 'running'" :job="activeJob" />

      <div v-if="!store.markdown" class="empty-preview">
        <div class="empty-preview-content">
          <div class="empty-preview-icon">&#128196;</div>
          <p>Load a resume to see preview</p>
          <small>Paste markdown in the editor or drag a .md file</small>
        </div>
      </div>
      <ResumePreview
        v-else
        :markdown="previewMarkdown"
        :pageMode="currentPageMode"
      />

      <div v-if="!store.markdown && !hasJobs" class="step-guide">
        <div class="step"><span class="step-num">1</span> Load your resume</div>
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
  gap: 18px; padding: 0 18px; max-width: 1400px; margin: 0 auto;
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

.tailor-all-btn {
  width: 100%; padding: 11px; font-weight: 700; border-radius: 10px;
  border: none; color: white; cursor: pointer; font-size: 0.9rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  margin-top: 8px;
}
.tailor-all-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.tailor-all-btn:not(:disabled):hover { opacity: 0.9; }

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

.empty-preview {
  width: var(--page-w); min-height: 300px;
  background: #fff; border: 2px dashed #d9d9d9; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
}
.empty-preview-content { text-align: center; color: #999; }
.empty-preview-icon { font-size: 3rem; margin-bottom: 8px; }
.empty-preview-content p { margin: 0; font-weight: 600; }
.empty-preview-content small { font-size: 0.8rem; }

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
