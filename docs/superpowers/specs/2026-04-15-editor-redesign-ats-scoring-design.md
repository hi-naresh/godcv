# Editor View Redesign + ATS Scoring Panel

## Problem

The Editor view shows raw markdown in a textarea which is hard to read and edit. Users can't see structured sections of their tailored resume, and there's no feedback on how well their resume matches the JD — no ATS score, no keyword match, no gap analysis.

## Solution

Redesign the Editor view: left panel for job cards, right panel splits into editable section cards + live A4 preview. Add a bottom floating panel with before/after scoring (keyword match, skills coverage, experience fit, overall fit) plus a rigorous ATS score with brutal honest feedback. The orchestrator provides before scores and gap suggestions at analysis time; a new ATS scoring agent runs after tailoring for the real after scores.

## Editor View Layout

```
Editor Tab
├── Left Panel (sticky, narrow)
│   ├── Job Cards (add/remove JDs, seniority)
│   └── Tailor All button
│
├── Right Panel (wide)
│   ├── Tab Bar (Original / Job1 / Job2...)
│   ├── Content Area (two columns):
│   │   ├── Section Cards (editable, collapsible — reuses SectionCard/EntryCard)
│   │   └── A4 Resume Preview (ResumePreview component)
│   │
│   └── Score Panel (bottom, floating/sticky)
│       ├── Before → After comparison:
│       │   ├── ATS Score (0-100, rigorous breakdown)
│       │   ├── Keyword Match %
│       │   ├── Skills Coverage %
│       │   ├── Experience Fit (text)
│       │   └── Overall Job Fit Score (0-100)
│       └── Gap Suggestions (list of weaknesses/missing requirements)
```

### Left Panel

Contains only job cards and the tailor button. The raw markdown textarea is removed entirely. The left panel becomes narrower since it only has job descriptions.

### Right Panel — Section Cards

When viewing the "Original" tab, the section cards show the master resume parsed into editable sections (same as Profile page — reuses SectionEditor component in read/edit mode).

When viewing a tailored job tab, the section cards show the tailored result parsed into editable sections. Edits update the tailored result markdown and the preview re-renders live.

### Right Panel — A4 Preview

The existing ResumePreview component, displayed alongside section cards. Updates live as section cards are edited.

### Score Panel

A sticky/floating panel at the bottom of the right panel. Only visible when a job tab is active and has scores. Shows before/after metrics side by side.

## Orchestrator Changes

The orchestrator prompt adds a `scoring` section to its JSON output. This runs during the analysis phase (before agents execute), so it scores the ORIGINAL resume against the JD and predicts post-tailoring improvement.

### Added to orchestrator output schema:

```json
{
  "analysis": { "..." },
  "tool_calls": [ "..." ],
  "scoring": {
    "before": {
      "keyword_match": 45,
      "skills_coverage": 60,
      "experience_fit": "JD asks 5+ years, resume shows 3 years",
      "overall_fit": 52
    },
    "predicted_after": {
      "keyword_match": 82,
      "skills_coverage": 85,
      "experience_fit": "Reworded to emphasize depth over duration",
      "overall_fit": 78
    },
    "gap_suggestions": [
      "JD requires Kubernetes — not in your skills or experience",
      "JD asks for 5+ years — your resume shows ~3 years",
      "No team leadership examples — JD emphasizes managing 3+ engineers"
    ]
  }
}
```

### Scoring prompt additions:

```
SCORING: You MUST also evaluate the resume against the JD and provide scores.

For "before" scores — evaluate the ORIGINAL resume as-is:
- keyword_match: percentage of important JD keywords/phrases found in the resume (0-100)
- skills_coverage: percentage of JD required skills present in the Skills section (0-100)
- experience_fit: text describing how the experience level matches (years, seniority, domain)
- overall_fit: aggregated score considering all factors (0-100)

For "predicted_after" scores — predict what the tailored resume will score after your planned modifications.

For "gap_suggestions" — list specific weaknesses in the candidate's profile for THIS job:
- Missing skills that the JD requires but the resume doesn't have at all
- Experience gaps (years, seniority level, domain mismatch)
- Missing project types or technologies
- Soft skill gaps (leadership, mentoring, etc.)
- Be brutally honest — these help the user understand what they can't fix with tailoring alone
```

## ATS Scoring Agent (New)

A new backend agent (`backend/agents/ats_scorer.py`) that runs AFTER the tailored resume is assembled. It performs a rigorous ATS evaluation — not a feel-good score, but what an actual ATS would flag.

### What it checks:

| Category | What ATS Systems Check |
|---|---|
| contact_info | Name, email, phone, LinkedIn all present and parseable |
| parsability | Clean single-column format, no tables/images, standard markdown |
| keyword_match | Exact JD keywords found in resume (ATS don't understand synonyms) |
| section_headers | Standard names (Experience, Education, Skills) vs creative names |
| date_format | Consistent, parseable date ranges (Mon YYYY – Mon YYYY) |
| title_match | Resume job titles align with JD title |
| hard_skills | Required skills explicitly listed in Skills section, not just buried in bullets |
| quantified_results | Bullets with numbers, metrics, percentages vs vague statements |
| experience_depth | Years of experience match JD requirements |

### Output schema:

```json
{
  "ats_score": 71,
  "breakdown": {
    "contact_info": { "score": 100, "detail": "All fields present" },
    "parsability": { "score": 90, "detail": "Clean markdown, single column" },
    "keyword_match": { "score": 65, "detail": "18/28 JD keywords found" },
    "section_headers": { "score": 100, "detail": "Standard headers used" },
    "date_format": { "score": 80, "detail": "Consistent Mon YYYY format" },
    "title_match": { "score": 70, "detail": "'Engineer' vs JD 'Senior Engineer'" },
    "hard_skills": { "score": 75, "detail": "12/16 required skills in Skills section" },
    "quantified_results": { "score": 60, "detail": "3/7 bullets have metrics" },
    "experience_depth": { "score": 50, "detail": "JD wants 5+ yrs, showing ~3 yrs" }
  },
  "brutal_verdict": "Your resume would pass initial screening but rank bottom half. Kubernetes gap and experience shortfall are deal-breakers for automated filters."
}
```

### ATS scorer prompt approach:

The prompt instructs the AI to be a ruthless ATS evaluator — not a career coach giving encouragement. It should:
- Count exact keyword matches (not synonyms)
- Flag every missing required skill
- Penalize heavily for experience level mismatch
- Check formatting issues that break real ATS parsers
- Give a score that reflects reality, not encouragement

## SSE Event Flow

The tailor endpoint adds new events:

1. `plan` event — now includes `scoring.before`, `scoring.predicted_after`, `scoring.gap_suggestions`
2. (existing agent events)
3. `complete` event — includes tailored markdown
4. **NEW** `ats_score` event — ATS scorer result (runs after assembly)

```python
# After assembly, before learning
yield _sse_event("status", {"phase": "ats_scoring", "message": "Running ATS analysis..."})
ats_agent = ATSScorerAgent(gemini)
ats_result = await ats_agent.score(tailored_md, job_description)
yield _sse_event("ats_score", ats_result)
```

## Frontend Store Changes

### JobState additions:

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

export interface JobState {
  // ... existing fields ...
  scoring: JobScoring | null
  atsResult: ATSResult | null
}
```

## Frontend Components

### ScorePanel.vue

A sticky bottom panel that shows:
- Left side: Before/After comparison cards with score numbers + colored indicators (red < 50, yellow 50-75, green > 75)
- ATS score with expandable breakdown (click to see per-category scores)
- Right side: Gap suggestions as a bullet list
- Collapsed by default, click to expand

### EditorView.vue Changes

Remove:
- Raw markdown textarea (MarkdownEditor component)
- PageModeToggle (already moved to Preferences)

Add:
- SectionEditor in the right panel (reuses the component from Profile, but bound to the active job's result or master resume)
- ScorePanel at the bottom
- Two-column layout within the right panel: section cards | preview

The left panel shrinks to just job cards + tailor button.

## File Changes Summary

### New Files
- `backend/agents/ats_scorer.py` — ATS scoring agent
- `frontend/src/components/ScorePanel.vue` — bottom floating score/metrics panel

### Modified Files
- `backend/agents/orchestrator.py` — add scoring section to prompt and output
- `backend/routers/tailor.py` — run ATS scorer after assembly, emit new SSE events
- `frontend/src/views/EditorView.vue` — new layout (jobs left, sections+preview right, score panel)
- `frontend/src/stores/editor.ts` — add scoring/atsResult to JobState, add interfaces
- `frontend/src/composables/useTailor.ts` — handle `ats_score` SSE event, store scoring from plan

### Unchanged Files
- `frontend/src/components/SectionEditor.vue` — reused as-is
- `frontend/src/components/SectionCard.vue` — reused as-is
- `frontend/src/components/EntryCard.vue` — reused as-is
- `frontend/src/components/ResumePreview.vue` — reused as-is
- `frontend/src/views/ProfileView.vue` — unchanged
- `backend/agents/summary.py`, `skills.py`, `experience.py`, `projects.py` — unchanged
- `backend/services/parser.py`, `assembler.py`, `formatter.py` — unchanged
