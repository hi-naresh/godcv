# Editor Redesign + ATS Scoring — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Editor view (jobs left, editable section cards + preview right, score panel bottom) and add ATS scoring with before/after metrics and gap suggestions.

**Architecture:** Backend adds scoring to orchestrator output and a new ATS scorer agent that runs post-assembly. Frontend replaces the raw textarea with SectionEditor, adds a ScorePanel component, and handles new SSE events. Store gets scoring/ATS interfaces on JobState.

**Tech Stack:** Vue 3 (Composition API), Pinia, Python/FastAPI, Gemini API, SSE streaming.

---

## File Structure

### New Files
| File | Responsibility |
|---|---|
| `backend/agents/ats_scorer.py` | ATS scoring agent — rigorous per-category evaluation |
| `frontend/src/components/ScorePanel.vue` | Bottom floating panel with before/after metrics + ATS breakdown + gap suggestions |

### Modified Files
| File | What Changes |
|---|---|
| `frontend/src/stores/editor.ts` | Add `JobScoring`, `ATSResult` interfaces; add `scoring` and `atsResult` to `JobState` |
| `backend/agents/orchestrator.py` | Add scoring section to prompt and JSON output |
| `backend/routers/tailor.py` | Emit scoring in plan event, run ATS scorer after assembly, emit `ats_score` event |
| `frontend/src/composables/useTailor.ts` | Handle `ats_score` SSE event, extract scoring from plan |
| `frontend/src/views/EditorView.vue` | New layout: jobs-only left panel, section cards + preview + score panel right |

---

### Task 1: Add Scoring Interfaces to Frontend Store

**Files:**
- Modify: `frontend/src/stores/editor.ts`

- [ ] **Step 1: Add scoring and ATS interfaces**

Add these interfaces after the `ToolCall` interface (after line 12):

```typescript
export interface JobScoring {
  before: {
    keyword_match: number
    skills_coverage: number
    experience_fit: string
    overall_fit: number
  }
  predicted_after: {
    keyword_match: number
    skills_coverage: number
    experience_fit: string
    overall_fit: number
  }
  gap_suggestions: string[]
}

export interface ATSBreakdownItem {
  score: number
  detail: string
}

export interface ATSResult {
  ats_score: number
  breakdown: Record<string, ATSBreakdownItem>
  brutal_verdict: string
}
```

- [ ] **Step 2: Add scoring and atsResult to JobState**

Update the `JobState` interface to include:

```typescript
export interface JobState {
  id: string
  title: string
  jobDescription: string
  seniorityLevel: SeniorityLevel | null
  tailoringStatus: 'idle' | 'running' | 'done' | 'error'
  tailoringPlan: ToolCall[] | null
  agentStatuses: Record<string, 'pending' | 'running' | 'done'>
  result: string | null
  error: string | null
  pageMode: 'single' | 'multi'
  scoring: JobScoring | null
  atsResult: ATSResult | null
}
```

- [ ] **Step 3: Update addJob() defaults**

In the `addJob()` function, add to the initial state object:

```typescript
      scoring: null,
      atsResult: null,
```

- [ ] **Step 4: Update resetJobTailoring()**

Add `scoring: null, atsResult: null` to the reset:

```typescript
  function resetJobTailoring(id: string) {
    updateJob(id, {
      tailoringStatus: 'idle',
      tailoringPlan: null,
      agentStatuses: {},
      result: null,
      error: null,
      scoring: null,
      atsResult: null,
    })
  }
```

- [ ] **Step 5: Verify TypeScript compiles**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/stores/editor.ts
git commit -m "feat: add scoring and ATS interfaces to editor store"
```

---

### Task 2: Add Scoring to Orchestrator Prompt

**Files:**
- Modify: `backend/agents/orchestrator.py`

- [ ] **Step 1: Add scoring instructions to the prompt**

In `backend/agents/orchestrator.py`, add before the `CRITICAL: Keep your response CONCISE` line (line 84):

```python
SCORING: You MUST also evaluate the resume against the JD and provide scores.

For "before" scores — evaluate the ORIGINAL resume as-is:
- keyword_match: percentage of important JD keywords/phrases found in the resume (0-100)
- skills_coverage: percentage of JD required skills present in the Skills section (0-100)
- experience_fit: one sentence describing how experience level matches (years, seniority, domain)
- overall_fit: aggregated score considering all factors (0-100)

For "predicted_after" scores — predict what the tailored resume will score after your planned modifications.

For "gap_suggestions" — list specific weaknesses the candidate has for THIS job:
- Missing skills the JD requires but resume doesn't have at all
- Experience gaps (years, seniority level, domain mismatch)
- Missing project types or technologies
- Soft skill gaps (leadership, mentoring, etc.)
- Be brutally honest — these help the user understand what tailoring alone cannot fix
```

- [ ] **Step 2: Add scoring to the JSON output schema**

Update the JSON schema in the prompt. After `"section_order"`, add:

```python
  "scoring": {{
    "before": {{
      "keyword_match": "<0-100>",
      "skills_coverage": "<0-100>",
      "experience_fit": "<one sentence>",
      "overall_fit": "<0-100>"
    }},
    "predicted_after": {{
      "keyword_match": "<0-100>",
      "skills_coverage": "<0-100>",
      "experience_fit": "<one sentence>",
      "overall_fit": "<0-100>"
    }},
    "gap_suggestions": ["<specific weakness 1>", "<specific weakness 2>"]
  }}
```

Note: double braces `{{` `}}` because it's an f-string.

- [ ] **Step 3: Verify module loads**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -c "from backend.agents.orchestrator import OrchestratorAgent; print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add backend/agents/orchestrator.py
git commit -m "feat: orchestrator includes before/after scoring and gap suggestions"
```

---

### Task 3: Create ATS Scorer Agent

**Files:**
- Create: `backend/agents/ats_scorer.py`

- [ ] **Step 1: Create the ATS scorer agent**

Create `backend/agents/ats_scorer.py`:

```python
from backend.services.gemini import GeminiClient


class ATSScorerAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def score(self, resume_markdown: str, job_description: str) -> dict:
        """Run a rigorous ATS evaluation on a resume against a job description."""
        prompt = f"""You are a ruthless ATS (Applicant Tracking System) evaluator. Score this resume against the job description exactly how a real ATS would — no encouragement, no rounding up, brutally honest.

EVALUATION CATEGORIES (score each 0-100):

1. contact_info: Are name, email, phone, LinkedIn all present and clearly parseable? Missing any = penalty.

2. parsability: Is the format clean single-column? No tables, images, columns, fancy formatting that breaks ATS parsers? Standard markdown structure?

3. keyword_match: Count the EXACT important keywords/phrases from the JD that appear in the resume. ATS systems do NOT understand synonyms — "ML" and "Machine Learning" are different. Count exact matches only. Score = (matched keywords / total important JD keywords) * 100.

4. section_headers: Are section names standard (Experience, Education, Skills, Projects, Summary)? Creative names like "What I've Built" or "My Journey" get penalized — ATS can't parse them.

5. date_format: Are dates consistent and parseable? "Jan 2023 – Present" is good. "2023" alone, inconsistent formats, or missing dates get penalized.

6. title_match: Does any job title in the resume align with the JD title? Exact match = 100, close match = 70, no match = 30.

7. hard_skills: Are the JD's required hard skills EXPLICITLY listed in the Skills section? Skills buried only in bullet points get partial credit. Skills completely missing = 0 for each.

8. quantified_results: What percentage of experience/project bullets contain specific numbers, metrics, or percentages? "Improved performance by 30%" beats "Improved performance significantly."

9. experience_depth: Does the years of experience match what the JD asks? If JD says "5+ years" and resume shows 2 years, that's a major penalty.

RESUME:
{resume_markdown}

JOB DESCRIPTION:
{job_description}

Respond with JSON:
{{
  "ats_score": "<weighted average of all categories, integer 0-100>",
  "breakdown": {{
    "contact_info": {{"score": "<0-100>", "detail": "<one sentence explanation>"}},
    "parsability": {{"score": "<0-100>", "detail": "<one sentence>"}},
    "keyword_match": {{"score": "<0-100>", "detail": "<X/Y JD keywords found>"}},
    "section_headers": {{"score": "<0-100>", "detail": "<one sentence>"}},
    "date_format": {{"score": "<0-100>", "detail": "<one sentence>"}},
    "title_match": {{"score": "<0-100>", "detail": "<one sentence>"}},
    "hard_skills": {{"score": "<0-100>", "detail": "<X/Y required skills in Skills section>"}},
    "quantified_results": {{"score": "<0-100>", "detail": "<X/Y bullets have metrics>"}},
    "experience_depth": {{"score": "<0-100>", "detail": "<one sentence>"}}
  }},
  "brutal_verdict": "<2-3 sentences. Would this resume pass ATS screening? Where would it rank? What are the deal-breakers?>"
}}"""

        return await self.gemini.generate_json(prompt)
```

- [ ] **Step 2: Verify module loads**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -c "from backend.agents.ats_scorer import ATSScorerAgent; print('OK')"`

- [ ] **Step 3: Commit**

```bash
git add backend/agents/ats_scorer.py
git commit -m "feat: add ATS scorer agent with rigorous per-category evaluation"
```

---

### Task 4: Update Tailor Router to Emit Scoring and Run ATS Scorer

**Files:**
- Modify: `backend/routers/tailor.py`

- [ ] **Step 1: Add ATS scorer import**

Add at the top of `backend/routers/tailor.py`, after the ProfileLearnerAgent import:

```python
from backend.agents.ats_scorer import ATSScorerAgent
```

- [ ] **Step 2: Include scoring in the plan SSE event**

Update the `yield _sse_event("plan", ...)` call (line 68-72) to include scoring:

```python
            yield _sse_event("plan", {
                "analysis": plan.get("analysis", {}),
                "tool_calls": tool_calls,
                "sections_unchanged": sections_unchanged,
                "scoring": plan.get("scoring"),
            })
```

- [ ] **Step 3: Run ATS scorer after assembly, before learning**

After the `yield _sse_event("complete", ...)` block (after line 115) and before Phase 5 (learning), add:

```python
            # Phase 4.5: ATS Scoring
            try:
                yield _sse_event("status", {"phase": "ats_scoring", "message": "Running ATS analysis..."})
                ats_agent = ATSScorerAgent(gemini)
                ats_result = await ats_agent.score(tailored_md, job_description)
                yield _sse_event("ats_score", ats_result)
            except Exception as e:
                logger.error("ATS scoring failed: %s", e)
                yield _sse_event("ats_score", {"ats_score": 0, "breakdown": {}, "brutal_verdict": f"ATS scoring failed: {str(e)}"})
```

- [ ] **Step 4: Verify module loads**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -c "from backend.routers.tailor import router; print('OK')"`

- [ ] **Step 5: Commit**

```bash
git add backend/routers/tailor.py
git commit -m "feat: tailor endpoint emits scoring and ATS score events"
```

---

### Task 5: Update useTailor Composable for New SSE Events

**Files:**
- Modify: `frontend/src/composables/useTailor.ts`

- [ ] **Step 1: Handle scoring data from plan event**

In the `handleEvent` function, update the `case 'plan':` block. After the existing `store.updateJob(jobId, updates)` line, add scoring extraction. Replace the full `case 'plan':` block:

```typescript
      case 'plan': {
        const plan = data.tool_calls as any[]
        const analysis = data.analysis as Record<string, unknown> | undefined
        const scoring = data.scoring as any | undefined
        const statuses: Record<string, 'pending' | 'running' | 'done'> = {}
        for (const call of plan || []) {
          const key = call.entry ? `${call.agent}:${call.entry}` : call.agent
          if (call.action === 'keep' || call.action === 'include') {
            statuses[key] = 'done'
          } else if (call.action === 'exclude') {
            // Don't show excluded entries in status
          } else {
            statuses[key] = 'pending'
          }
        }
        const updates: Partial<typeof job> = { tailoringPlan: plan, agentStatuses: statuses }
        if (scoring) {
          updates.scoring = scoring
        }
        // Use AI-extracted job info if available and user hasn't manually set them
        if (analysis) {
          const aiTitle = analysis.job_title as string
          const aiCompany = analysis.company as string
          const aiPosition = analysis.position_level as string
          if (aiTitle && aiCompany && !job.title) {
            updates.title = `${aiTitle} @ ${aiCompany}`
          } else if (aiTitle && !job.title) {
            updates.title = aiTitle
          }
          if (aiPosition && !job.seniorityLevel) {
            updates.seniorityLevel = aiPosition as any
          }
        }
        store.updateJob(jobId, updates)
        break
      }
```

- [ ] **Step 2: Add ats_score event handler**

Add a new case in the switch statement, before the `case 'error':` block:

```typescript
      case 'ats_score':
        store.updateJob(jobId, { atsResult: data as any })
        break
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/composables/useTailor.ts
git commit -m "feat: handle scoring and ATS score SSE events in useTailor"
```

---

### Task 6: Create ScorePanel Component

**Files:**
- Create: `frontend/src/components/ScorePanel.vue`

- [ ] **Step 1: Create the ScorePanel component**

Create `frontend/src/components/ScorePanel.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import type { JobScoring, ATSResult } from '../stores/editor'

defineProps<{
  scoring: JobScoring | null
  atsResult: ATSResult | null
}>()

const expanded = ref(false)
const atsExpanded = ref(false)

function scoreColor(score: number): string {
  if (score >= 75) return '#28a745'
  if (score >= 50) return '#f0ad4e'
  return '#dc3545'
}

const categoryLabels: Record<string, string> = {
  contact_info: 'Contact Info',
  parsability: 'Parsability',
  keyword_match: 'Keyword Match',
  section_headers: 'Section Headers',
  date_format: 'Date Format',
  title_match: 'Title Match',
  hard_skills: 'Hard Skills',
  quantified_results: 'Quantified Results',
  experience_depth: 'Experience Depth',
}
</script>

<template>
  <div v-if="scoring || atsResult" class="score-panel">
    <div class="panel-header" @click="expanded = !expanded">
      <span class="panel-toggle">{{ expanded ? '-' : '+' }}</span>
      <span class="panel-title">Resume Scoring</span>
      <template v-if="scoring">
        <span class="quick-score" :style="{ color: scoreColor(scoring.before.overall_fit) }">
          Before: {{ scoring.before.overall_fit }}%
        </span>
        <span class="score-arrow">-></span>
        <span class="quick-score" :style="{ color: scoreColor(scoring.predicted_after.overall_fit) }">
          After: {{ scoring.predicted_after.overall_fit }}%
        </span>
      </template>
      <span v-if="atsResult" class="ats-badge" :style="{ background: scoreColor(atsResult.ats_score) }">
        ATS: {{ atsResult.ats_score }}
      </span>
    </div>

    <div v-show="expanded" class="panel-body">
      <!-- Before / After Comparison -->
      <div v-if="scoring" class="scores-grid">
        <div class="score-column">
          <h4>Before Tailoring</h4>
          <div class="score-row">
            <span class="score-label">Keyword Match</span>
            <span class="score-value" :style="{ color: scoreColor(scoring.before.keyword_match) }">{{ scoring.before.keyword_match }}%</span>
          </div>
          <div class="score-row">
            <span class="score-label">Skills Coverage</span>
            <span class="score-value" :style="{ color: scoreColor(scoring.before.skills_coverage) }">{{ scoring.before.skills_coverage }}%</span>
          </div>
          <div class="score-row">
            <span class="score-label">Experience Fit</span>
            <span class="score-detail">{{ scoring.before.experience_fit }}</span>
          </div>
          <div class="score-row">
            <span class="score-label">Overall Fit</span>
            <span class="score-value big" :style="{ color: scoreColor(scoring.before.overall_fit) }">{{ scoring.before.overall_fit }}%</span>
          </div>
        </div>

        <div class="score-column">
          <h4>After Tailoring</h4>
          <div class="score-row">
            <span class="score-label">Keyword Match</span>
            <span class="score-value" :style="{ color: scoreColor(scoring.predicted_after.keyword_match) }">{{ scoring.predicted_after.keyword_match }}%</span>
          </div>
          <div class="score-row">
            <span class="score-label">Skills Coverage</span>
            <span class="score-value" :style="{ color: scoreColor(scoring.predicted_after.skills_coverage) }">{{ scoring.predicted_after.skills_coverage }}%</span>
          </div>
          <div class="score-row">
            <span class="score-label">Experience Fit</span>
            <span class="score-detail">{{ scoring.predicted_after.experience_fit }}</span>
          </div>
          <div class="score-row">
            <span class="score-label">Overall Fit</span>
            <span class="score-value big" :style="{ color: scoreColor(scoring.predicted_after.overall_fit) }">{{ scoring.predicted_after.overall_fit }}%</span>
          </div>
        </div>
      </div>

      <!-- ATS Score Breakdown -->
      <div v-if="atsResult" class="ats-section">
        <div class="ats-header" @click="atsExpanded = !atsExpanded">
          <span class="ats-toggle">{{ atsExpanded ? '-' : '+' }}</span>
          <span class="ats-title">ATS Score: {{ atsResult.ats_score }}/100</span>
        </div>
        <div v-show="atsExpanded" class="ats-breakdown">
          <div v-for="(item, key) in atsResult.breakdown" :key="key" class="ats-row">
            <span class="ats-cat">{{ categoryLabels[key as string] || key }}</span>
            <div class="ats-bar-wrap">
              <div class="ats-bar" :style="{ width: item.score + '%', background: scoreColor(item.score) }"></div>
            </div>
            <span class="ats-score-num">{{ item.score }}</span>
            <span class="ats-detail">{{ item.detail }}</span>
          </div>
        </div>
        <p class="ats-verdict">{{ atsResult.brutal_verdict }}</p>
      </div>

      <!-- Gap Suggestions -->
      <div v-if="scoring && scoring.gap_suggestions.length" class="gaps-section">
        <h4>Profile Gaps</h4>
        <ul>
          <li v-for="(gap, i) in scoring.gap_suggestions" :key="i">{{ gap }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.score-panel {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px;
  box-shadow: 0 -2px 12px rgba(0,0,0,.08);
  position: sticky; bottom: 0; z-index: 10;
}
.panel-header {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px; cursor: pointer; user-select: none;
}
.panel-header:hover { background: #f8f8f8; border-radius: 12px; }
.panel-toggle { font-weight: 700; color: #666; width: 16px; }
.panel-title { font-weight: 700; font-size: 0.85rem; }
.quick-score { font-weight: 700; font-size: 0.85rem; }
.score-arrow { color: #999; font-size: 0.8rem; }
.ats-badge {
  margin-left: auto; color: #fff; font-weight: 700; font-size: 0.75rem;
  padding: 2px 10px; border-radius: 10px;
}

.panel-body { padding: 0 16px 14px; }

.scores-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 12px; }
.score-column h4 { margin: 0 0 8px; font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
.score-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.score-label { font-size: 0.78rem; color: #555; flex: 1; }
.score-value { font-weight: 700; font-size: 0.85rem; }
.score-value.big { font-size: 1.1rem; }
.score-detail { font-size: 0.75rem; color: #777; flex: 2; }

.ats-section { border-top: 1px solid #eee; padding-top: 10px; margin-bottom: 10px; }
.ats-header { display: flex; align-items: center; gap: 8px; cursor: pointer; margin-bottom: 6px; }
.ats-toggle { font-weight: 700; color: #666; width: 16px; }
.ats-title { font-weight: 700; font-size: 0.85rem; }
.ats-breakdown { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
.ats-row { display: flex; align-items: center; gap: 8px; font-size: 0.78rem; }
.ats-cat { width: 110px; color: #555; flex-shrink: 0; }
.ats-bar-wrap { flex: 1; height: 6px; background: #eee; border-radius: 3px; overflow: hidden; }
.ats-bar { height: 100%; border-radius: 3px; transition: width 0.3s; }
.ats-score-num { width: 28px; text-align: right; font-weight: 600; }
.ats-detail { color: #777; font-size: 0.72rem; flex: 2; }
.ats-verdict { font-size: 0.8rem; color: #444; font-style: italic; margin: 6px 0 0; line-height: 1.4; }

.gaps-section { border-top: 1px solid #eee; padding-top: 10px; }
.gaps-section h4 { margin: 0 0 6px; font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
.gaps-section ul { margin: 0; padding-left: 18px; }
.gaps-section li { font-size: 0.8rem; color: #c00; margin-bottom: 3px; line-height: 1.3; }
</style>
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ScorePanel.vue
git commit -m "feat: add ScorePanel component with before/after metrics and ATS breakdown"
```

---

### Task 7: Redesign EditorView Layout

**Files:**
- Modify: `frontend/src/views/EditorView.vue`

This is the main UI redesign. Replace the entire file.

- [ ] **Step 1: Replace EditorView.vue**

Replace the full content of `frontend/src/views/EditorView.vue` with:

```vue
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
const { startBatchTailoring } = useTailor()

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

// The markdown for the active view (master resume or tailored result)
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

const hasJobs = computed(() => store.jobs.size > 0)
const anyRunning = computed(() => [...store.jobs.values()].some(j => j.tailoringStatus === 'running'))
const canTailor = computed(() =>
  hasJobs.value &&
  [...store.jobs.values()].some(j => j.jobDescription.trim()) &&
  store.markdown.trim()
)

function addJob() { store.addJob() }
function removeJob(id: string) { store.removeJob(id) }

function tailorAll() {
  if (!store.markdown.trim()) return alert('Load a resume first.')
  const key = props.apiKey || store.profile?.gemini_api_key || ''
  startBatchTailoring(key, store.markdown)
  const firstJob = [...store.jobs.keys()][0]
  if (firstJob) store.activeJobId = firstJob
}

function exportPdf() { window.print() }
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

      <!-- Main content: Section Cards + Preview side by side -->
      <div v-else class="content-area">
        <div class="sections-col">
          <SectionEditor
            :markdown="activeMarkdown"
            @update:markdown="onSectionUpdate"
          />
        </div>
        <div class="preview-col">
          <ResumePreview
            :markdown="activeMarkdown"
            :pageMode="currentPageMode"
            :agentStatuses="activeAgentStatuses"
          />
        </div>
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
  width: min(340px, 26vw); min-width: 280px;
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
  flex: 1; min-width: 0;
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

.content-area {
  display: flex; gap: 14px; align-items: flex-start;
}
.sections-col {
  width: min(420px, 35%); min-width: 300px;
  max-height: calc(100vh - 140px); overflow-y: auto;
}
.preview-col {
  flex: 1;
  display: flex; flex-direction: column; align-items: center;
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

@media (max-width: 1100px) {
  .content-area { flex-direction: column; }
  .sections-col { width: 100%; min-width: unset; max-height: unset; }
}

@media (max-width: 900px) {
  .editor-layout { flex-direction: column; align-items: stretch; }
  .left-panel {
    width: 100%; min-width: unset; position: static;
    max-height: unset;
  }
  .right-panel { max-width: 100%; }
}
</style>
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/EditorView.vue
git commit -m "feat: redesign Editor — jobs left, section cards + preview right, score panel bottom"
```

---

### Task 8: End-to-End Verification

**Files:** None (testing only)

- [ ] **Step 1: Run all backend tests**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -m pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 2: Run frontend type check**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Verify all backend modules load**

Run:
```bash
cd /Users/naresh/Documents/resume_editor/godcv
python -c "from backend.agents.ats_scorer import ATSScorerAgent; print('ATS OK')"
python -c "from backend.agents.orchestrator import OrchestratorAgent; print('Orch OK')"
python -c "from backend.routers.tailor import router; print('Router OK')"
```

- [ ] **Step 4: Commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address verification issues"
```
