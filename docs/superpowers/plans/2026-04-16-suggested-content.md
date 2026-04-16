# Suggested Content from Gap Analysis — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After tailoring, generate concrete resume content from gap suggestions and display inline with green highlights, accept/deny on hover, invisible in print.

**Architecture:** A new `SuggestionAgent` takes gap_suggestions + tailored resume + JD and generates actionable content items (skills, bullets) targeting specific sections. The frontend stores suggestions separately from the result markdown, injects them as highlighted spans during HTML rendering, and merges/removes them on accept/deny.

**Tech Stack:** Python/FastAPI backend, Vue 3 + TypeScript frontend, Gemini API, marked.js

---

### Task 1: Create SuggestionAgent backend

**Files:**
- Create: `backend/agents/suggestion_agent.py`

- [ ] **Step 1: Create the SuggestionAgent class**

```python
from backend.services.gemini import GeminiClient


class SuggestionAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def generate(
        self,
        gap_suggestions: list[str],
        tailored_resume: str,
        job_description: str,
    ) -> list[dict]:
        """Generate concrete content suggestions from gap analysis."""
        if not gap_suggestions:
            return []

        gaps_text = "\n".join(f"- {g}" for g in gap_suggestions)

        prompt = f"""You are a resume content advisor. Given a tailored resume, a job description, and a list of profile gaps, generate CONCRETE content that could be added to the resume to address each gap.

RULES:
- Only generate suggestions for gaps that the candidate could PLAUSIBLY have (skill gaps they might know but didn't list, bullet rewording)
- Do NOT fabricate experience the candidate clearly doesn't have (e.g., don't add "5 years of Go" if resume shows no Go at all)
- Do NOT suggest content for experience-level gaps (e.g., "needs 5 more years") — these can't be fixed with text
- Each suggestion targets a specific existing section of the resume
- Skills: comma-separated items to append to the Skills section
- Bullets: a single bullet point for the most relevant experience or project entry

TAILORED RESUME:
{tailored_resume}

JOB DESCRIPTION:
{job_description}

GAPS TO ADDRESS:
{gaps_text}

Respond with a JSON array (may be empty if no actionable gaps):
[
  {{
    "id": "sug-1",
    "section": "<Skills|experience:CompanyKey|projects:ProjectKey>",
    "type": "<skill|bullet>",
    "content": "<the actual text to add>",
    "context": "<which gap this addresses, 1 short sentence>"
  }}
]"""

        result = await self.gemini.generate_json(prompt)
        if isinstance(result, list):
            return result
        return result.get("suggestions", [])
```

- [ ] **Step 2: Verify the file is importable**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -c "from backend.agents.suggestion_agent import SuggestionAgent; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/agents/suggestion_agent.py
git commit -m "feat: add SuggestionAgent for generating content from gap analysis"
```

---

### Task 2: Wire SuggestionAgent into tailor endpoint

**Files:**
- Modify: `backend/routers/tailor.py:1-15` (imports) and `backend/routers/tailor.py:119-128` (after scoring_after, before ATS)

- [ ] **Step 1: Add import**

Add to imports at line 15:
```python
from backend.agents.suggestion_agent import SuggestionAgent
```

- [ ] **Step 2: Add suggestion generation phase**

Insert after the `scoring_after` phase (after line 127) and before the ATS scoring phase (current line 129):

```python
            # Phase 4.6: Generate content suggestions from gaps
            gap_suggestions = plan.get("scoring", {}).get("gap_suggestions", [])
            if gap_suggestions:
                try:
                    yield _sse_event("status", {"phase": "suggestions", "message": "Generating content suggestions..."})
                    sug_agent = SuggestionAgent(gemini)
                    suggestions = await sug_agent.generate(gap_suggestions, tailored_md, job_description)
                    if suggestions:
                        yield _sse_event("suggestions", {"items": suggestions})
                except Exception as e:
                    logger.error("Suggestion generation failed: %s", e)
```

Update the ATS scoring comment from `Phase 4.6` to `Phase 4.7`.

- [ ] **Step 3: Verify backend starts without errors**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -c "from backend.routers.tailor import router; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/routers/tailor.py
git commit -m "feat: emit suggestions SSE event after scoring"
```

---

### Task 3: Add Suggestion type and state to frontend store

**Files:**
- Modify: `frontend/src/stores/editor.ts:14-59` (interfaces and JobState)

- [ ] **Step 1: Add Suggestion interface after ATSResult**

Insert after the `ATSResult` interface (after line 36):

```typescript
export interface Suggestion {
  id: string
  section: string
  type: 'skill' | 'bullet'
  content: string
  context: string
}
```

- [ ] **Step 2: Add `suggestions` field to JobState**

Add `suggestions: Suggestion[]` after the `atsResult` field in `JobState` (line 58):

```typescript
  suggestions: Suggestion[]
```

- [ ] **Step 3: Initialize suggestions in addJob**

In the `addJob` function, add `suggestions: []` to the initial state object (after `atsResult: null` at line 84):

```typescript
      suggestions: [],
```

- [ ] **Step 4: Reset suggestions in resetJobTailoring**

In `resetJobTailoring`, add `suggestions: []` to the reset object (after `atsResult: null` at line 113):

```typescript
      suggestions: [],
```

- [ ] **Step 5: Verify types compile**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`
Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/stores/editor.ts
git commit -m "feat: add Suggestion type and state to editor store"
```

---

### Task 4: Handle suggestions SSE event in useTailor

**Files:**
- Modify: `frontend/src/composables/useTailor.ts:155-161` (add case before ats_score)

- [ ] **Step 1: Add suggestions event handler**

Add a new case before the `scoring_after` case (before line 155):

```typescript
      case 'suggestions':
        store.updateJob(jobId, {
          suggestions: (data.items as any[]) || [],
        })
        break
```

- [ ] **Step 2: Verify types compile**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useTailor.ts
git commit -m "feat: handle suggestions SSE event in useTailor"
```

---

### Task 5: Inject suggestions into ResumePreview with green highlights

**Files:**
- Modify: `frontend/src/components/ResumePreview.vue` (add props, emit, injection logic)

- [ ] **Step 1: Add props and emits**

Update the script setup to add the new prop and emits. Replace the props definition (lines 5-9):

```typescript
import type { Suggestion } from '../stores/editor'

const props = defineProps<{
  markdown: string
  pageMode: 'single' | 'multi'
  agentStatuses?: Record<string, 'pending' | 'running' | 'done'>
  suggestions?: Suggestion[]
}>()

const emit = defineEmits<{
  'accept-suggestion': [id: string]
  'deny-suggestion': [id: string]
}>()
```

- [ ] **Step 2: Add suggestion injection into renderedHtml**

After the refining badge injection in `renderedHtml` computed (line 41), add suggestion injection:

```typescript
  // Inject suggestion content as green-highlighted spans
  if (props.suggestions?.length) {
    for (const sug of props.suggestions) {
      html = injectSuggestion(html, sug)
    }
  }
```

- [ ] **Step 3: Add the injectSuggestion function**

Add this function before the `renderedHtml` computed:

```typescript
function injectSuggestion(html: string, sug: Suggestion): string {
  const escaped = sug.content
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const sugHtml = `<span class="suggestion" data-sug-id="${sug.id}" title="${sug.context.replace(/"/g, '&quot;')}">${sug.type === 'bullet' ? '<li>' + escaped + '</li>' : escaped}</span>`

  if (sug.section === 'Skills') {
    // Append after the Skills section content (find Skills h1, then append after next content)
    const skillsRegex = /(<h1>Skills<\/h1>)([\s\S]*?)(<h1>|<hr|$)/i
    html = html.replace(skillsRegex, (match, h1, content, next) => {
      return h1 + content.replace(/<\/p>(?![\s\S]*<\/p>)/, ', ' + sugHtml + '</p>') + next
    })
  } else {
    // For experience:Key or projects:Key, find the entry and append bullet
    const parts = sug.section.split(':')
    const entryKey = parts[1] || ''
    if (entryKey) {
      // Find the bold entry header containing the key, then find its <ul> and append
      const keyEscaped = entryKey.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      const entryRegex = new RegExp(
        `(<strong>[^<]*${keyEscaped}[^<]*<\\/strong>[\\s\\S]*?<ul>)([\\s\\S]*?)(<\\/ul>)`,
        'i'
      )
      html = html.replace(entryRegex, (match, before, items, close) => {
        return before + items + sugHtml + close
      })
    }
  }
  return html
}
```

- [ ] **Step 4: Add click handler for accept/deny via event delegation**

Add an `onMounted` handler for click events on suggestion tooltips. Add after the `applyMultiPageStyles` function:

```typescript
import { onMounted, onUnmounted } from 'vue'

function handleSuggestionClick(e: Event) {
  const target = e.target as HTMLElement
  if (target.classList.contains('sug-accept')) {
    const id = target.closest('.suggestion')?.getAttribute('data-sug-id')
    if (id) emit('accept-suggestion', id)
  } else if (target.classList.contains('sug-deny')) {
    const id = target.closest('.suggestion')?.getAttribute('data-sug-id')
    if (id) emit('deny-suggestion', id)
  }
}

onMounted(() => {
  contentRef.value?.addEventListener('click', handleSuggestionClick)
})

onUnmounted(() => {
  contentRef.value?.removeEventListener('click', handleSuggestionClick)
})
```

- [ ] **Step 5: Inject hover tooltip HTML into suggestion spans**

Update the `injectSuggestion` function to include the tooltip buttons in each suggestion span. Change the `sugHtml` construction:

```typescript
  const tooltip = `<span class="sug-tooltip"><button class="sug-accept" title="Accept">&#10003;</button><button class="sug-deny" title="Deny">&#10005;</button></span>`
  const innerContent = sug.type === 'bullet' ? '<li>' + escaped + tooltip + '</li>' : escaped + tooltip
  const sugHtml = `<span class="suggestion" data-sug-id="${sug.id}" title="${sug.context.replace(/"/g, '&quot;')}">${innerContent}</span>`
```

- [ ] **Step 6: Verify types compile**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`
Expected: no errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ResumePreview.vue
git commit -m "feat: inject suggestion content with green highlights and accept/deny"
```

---

### Task 6: Wire accept/deny in EditorView

**Files:**
- Modify: `frontend/src/views/EditorView.vue` (add computed, handlers, pass props)

- [ ] **Step 1: Add activeSuggestions computed**

After `activeAtsResult` (line 56), add:

```typescript
const activeSuggestions = computed(() => activeJob.value?.suggestions ?? [])
```

- [ ] **Step 2: Add accept and deny handler functions**

After the `exportPdf` function (line 77), add:

```typescript
function acceptSuggestion(sugId: string) {
  const job = activeJob.value
  if (!job || !job.result) return
  const sug = job.suggestions.find(s => s.id === sugId)
  if (!sug) return

  // Merge content into the result markdown
  let md = job.result
  if (sug.section === 'Skills' && sug.type === 'skill') {
    // Append skills to the Skills section — find last non-empty line in Skills
    const skillsMatch = md.match(/(# Skills\n)([\s\S]*?)(\n---|\n# |\n*$)/)
    if (skillsMatch) {
      const before = skillsMatch[1]
      const content = skillsMatch[2].trimEnd()
      const after = skillsMatch[3]
      md = md.replace(skillsMatch[0], before + content + ', ' + sug.content + after)
    }
  } else if (sug.type === 'bullet') {
    // Append bullet to the matching entry
    const parts = sug.section.split(':')
    const entryKey = parts[1] || ''
    if (entryKey) {
      // Find the entry by its bold title containing the key
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
```

- [ ] **Step 3: Pass suggestions prop and wire events on ResumePreview**

Update the ResumePreview usage (lines 154-158):

```vue
        <ResumePreview
          :markdown="activeMarkdown"
          :pageMode="currentPageMode"
          :agentStatuses="activeAgentStatuses"
          :suggestions="activeSuggestions"
          @accept-suggestion="acceptSuggestion"
          @deny-suggestion="denySuggestion"
        />
```

- [ ] **Step 4: Verify types compile**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/EditorView.vue
git commit -m "feat: wire accept/deny suggestion handlers in EditorView"
```

---

### Task 7: Add CSS for suggestion highlights, tooltip, and print override

**Files:**
- Modify: `frontend/src/style.css` (add suggestion styles before `@page` rule at line 78)

- [ ] **Step 1: Add suggestion styles**

Insert before the `@page { size: A4; margin: 0; }` line (line 78):

```css
/* Suggested content highlights */
.sheet-content .suggestion {
  background: #e6ffe6;
  border-left: 2px solid #28a745;
  padding: 0 3px;
  border-radius: 2px;
  position: relative;
  transition: background 0.2s;
}
.sheet-content .suggestion:hover {
  background: #d0f5d0;
}
.sheet-content .suggestion li {
  list-style: disc;
}

/* Accept/Deny tooltip */
.sheet-content .sug-tooltip {
  display: none;
  position: absolute;
  top: -28px;
  left: 0;
  background: #fff;
  border: 1px solid #ccc;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,.15);
  padding: 2px 4px;
  gap: 2px;
  z-index: 20;
  white-space: nowrap;
}
.sheet-content .suggestion:hover .sug-tooltip {
  display: inline-flex;
}
.sheet-content .sug-accept,
.sheet-content .sug-deny {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 0.85rem;
  padding: 2px 6px;
  border-radius: 4px;
  line-height: 1;
}
.sheet-content .sug-accept { color: #28a745; }
.sheet-content .sug-accept:hover { background: #e6ffe6; }
.sheet-content .sug-deny { color: #dc3545; }
.sheet-content .sug-deny:hover { background: #ffe6e6; }
```

- [ ] **Step 2: Add print overrides**

Inside the existing `@media print` block (after line 85), add to the list of hidden elements:

```css
  .sug-tooltip { display: none !important; }
```

And add a rule to make suggestion text look normal when printed:

```css
  .suggestion {
    background: none !important;
    border-left: none !important;
    padding: 0 !important;
  }
```

- [ ] **Step 3: Verify the app loads in browser**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vite build --mode development 2>&1 | tail -5`
Expected: build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/style.css
git commit -m "feat: add CSS for suggestion highlights, tooltip, and print-safe overrides"
```

---

### Task 8: End-to-end verification

- [ ] **Step 1: Start the backend and frontend dev servers**

Start backend and frontend and test a tailoring flow with a job that produces gap_suggestions.

- [ ] **Step 2: Verify the flow**

1. Add a job description and tailor
2. After tailoring completes, verify `suggestions` SSE event arrives in browser devtools Network tab
3. Verify green-highlighted content appears in the resume preview at the correct sections
4. Hover over a suggestion — verify accept/deny tooltip appears
5. Click accept — verify content merges into the resume and green highlight disappears
6. Click deny on another — verify it's removed from the preview
7. Use Print/PDF — verify no green highlights in the print preview

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: end-to-end adjustments for suggested content feature"
```
