# Suggested Content from Gap Analysis — Design Spec

## Overview

After tailoring a resume, the system analyzes gap suggestions and generates concrete content (skills, bullet points) to fill those gaps. Suggestions appear inline in the resume preview with green highlighting. Users can accept or deny each suggestion via hover controls. Accepted content becomes permanent; denied content is removed. Print/export renders all text normally — no green highlights on paper.

## Backend

### SuggestionAgent (`backend/agents/suggestion_agent.py`)

- Input: `gap_suggestions: list[str]`, `tailored_resume: str`, `job_description: str`
- Uses Gemini to generate concrete content for each actionable gap
- Output: list of suggestion objects:
  ```json
  [
    {
      "id": "sug-1",
      "section": "Skills",
      "type": "skill",
      "content": "Kubernetes, Docker Compose",
      "context": "Missing container orchestration skills"
    },
    {
      "id": "sug-2",
      "section": "experience:BotWot",
      "type": "bullet",
      "content": "- Containerized ML pipelines using Docker and Kubernetes, reducing deployment time by 40%",
      "context": "No Kubernetes experience mentioned"
    }
  ]
  ```
- Rules:
  - Only generate for gaps that can plausibly be addressed (skip "needs 5 more years of experience")
  - Skills suggestions: comma-separated additions for the Skills section
  - Bullet suggestions: single bullet point targeting the most relevant experience/project entry
  - Keep content realistic and consistent with the candidate's existing experience level
  - Generate an `id` field: `sug-1`, `sug-2`, etc.

### Tailor endpoint changes (`backend/routers/tailor.py`)

- Add new phase after `scoring_after`, before ATS scoring
- Emit `suggestions` SSE event with the generated suggestions list
- Only runs if `gap_suggestions` is non-empty

## Frontend

### Store changes (`frontend/src/stores/editor.ts`)

- New interface:
  ```typescript
  interface Suggestion {
    id: string
    section: string       // "Skills", "experience:CompanyKey", "projects:ProjectKey"
    type: 'skill' | 'bullet'
    content: string
    context: string       // the original gap description
  }
  ```
- Add `suggestions: Suggestion[]` to `JobState` (default `[]`)
- Reset in `resetJobTailoring`

### useTailor changes (`frontend/src/composables/useTailor.ts`)

- Handle `suggestions` event: store suggestions in job state

### ResumePreview changes (`frontend/src/components/ResumePreview.vue`)

- New prop: `suggestions: Suggestion[]`
- New emits: `accept-suggestion`, `deny-suggestion`
- After rendering HTML via `useMarkdown`, post-process to inject suggestion content:
  - For each suggestion, find the target section in the rendered HTML
  - Append a `<span class="suggestion" data-id="sug-X">` containing the rendered suggestion content
  - Skills: append inline after existing skills text
  - Bullets: append as a new list item at the end of the entry's bullet list
- On hover over `.suggestion`: show a small tooltip with accept (checkmark) and deny (X) buttons
- Accept click: emit `accept-suggestion` with suggestion id
- Deny click: emit `deny-suggestion` with suggestion id

### EditorView changes (`frontend/src/views/EditorView.vue`)

- Pass `suggestions` prop to ResumePreview (filtered to current job)
- Handle `accept-suggestion`:
  - Merge suggestion content into the job's `result` markdown string (append skill/bullet to the right section)
  - Remove from `suggestions` array
- Handle `deny-suggestion`:
  - Remove from `suggestions` array (content disappears from preview)

### CSS Styling (`frontend/src/style.css`)

- `.suggestion` class:
  - `background: #e6ffe6` (light green background)
  - `border-left: 2px solid #28a745` (green left border for bullets)
  - `border-radius: 3px`
  - `position: relative` (for tooltip positioning)
- `.suggestion-tooltip`:
  - Hidden by default, shown on `.suggestion:hover`
  - Two small icon buttons: checkmark (accept) and X (deny)
  - Positioned above the suggestion text
- `@media print`:
  - `.suggestion { background: none; border-left: none; color: inherit; }` — no visual distinction on paper
  - `.suggestion-tooltip { display: none; }`

## Event Flow

```
1. Tailoring completes → "complete" event (tailored markdown)
2. Scoring runs → "scoring_after" event (real after scores)
3. SuggestionAgent runs → "suggestions" event (list of suggestions)
4. ATS scoring runs → "ats_score" event

Frontend:
5. Suggestions stored in job state
6. ResumePreview injects green-highlighted content at correct positions
7. User hovers → sees accept/deny tooltip
8. Accept → content merged into result markdown, suggestion removed
9. Deny → suggestion removed, content disappears
```

## Scope boundaries

- No undo for accept/deny (one-time action)
- No drag-and-drop reordering of suggestions
- No manual editing of suggestion text before accepting (accept as-is or deny)
- Suggestions generated once per tailoring run, not refreshable
