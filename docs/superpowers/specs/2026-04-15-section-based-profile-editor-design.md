# Section-Based Profile Editor + Smart Entry Selection

## Problem

The current master resume is edited as raw markdown in a single textarea on the Profile page. Users can't easily add extra experiences or projects beyond what fits in a 1-page resume. When tailoring, the AI rewrites existing content but can't select from a larger pool of entries. Users with many relevant experiences/projects lose the ability to showcase different strengths for different roles.

## Solution

Transform the Profile page into a structured section-based editor where each resume section is a collapsible card. Experience and Projects sections support multiple entries with an "+ Add" button. Users build an abundant pool of content. During tailoring, the orchestrator selects the most relevant subset to fit the target page count.

## Architecture

### Profile Page (Frontend)

The Profile page replaces its current single textarea with structured section cards.

#### Layout

```
Profile Page
├── Profile Info
│   ├── Name (text input)
│   └── Gemini API Key (password input)
│
├── Resume Header (card)
│   ├── Name (text input)
│   ├── Title (text input, e.g. "Software Engineer | San Francisco")
│   ├── Email (text input)
│   ├── Phone (text input)
│   ├── Portfolio URL (text input)
│   ├── GitHub URL (text input)
│   └── LinkedIn URL (text input)
│
├── Section Cards (collapsible)
│   ├── Summary
│   │   └── textarea (markdown)
│   │
│   ├── Education
│   │   └── textarea (markdown)
│   │
│   ├── Skills
│   │   └── textarea (markdown)
│   │
│   ├── Experience
│   │   ├── Entry Card 1
│   │   │   ├── Header: text input ("Role — Company (Location)" and dates)
│   │   │   ├── Content: textarea (bullet points as markdown)
│   │   │   └── Remove button
│   │   ├── Entry Card 2 ...
│   │   └── [+ Add Experience] button
│   │
│   ├── Projects
│   │   ├── Entry Card 1
│   │   │   ├── Header: text input ("**[Name](URL)** | Stack - Tech1, Tech2")
│   │   │   ├── Content: textarea (bullet points as markdown)
│   │   │   └── Remove button
│   │   ├── Entry Card 2 ...
│   │   └── [+ Add Project] button
│   │
│   └── Other sections (Volunteering, Interests, etc.)
│       └── textarea (markdown)
│
├── [+ Add Section] button
├── Save Profile button
└── Status message
```

#### Component: SectionEditor.vue

A new component that renders the full section-based editor.

**Props:**
- `markdown: string` — the full master resume markdown

**Emits:**
- `update:markdown` — emits the reassembled full markdown string whenever any field changes

**Internal state:**
- Parses the incoming markdown into frontmatter fields + section cards on mount
- Each edit to any field/textarea triggers reassembly into full markdown and emits the update

This keeps the backend unchanged — it still stores `master_resume` as a single markdown string. The frontend just provides a structured editing UI on top.

#### Component: SectionCard.vue

A collapsible card for a single section.

**Props:**
- `title: string` — section name (e.g. "Experience")
- `collapsed: boolean`
- `entries?: EntryData[]` — for multi-entry sections (Experience, Projects)
- `content?: string` — for single-textarea sections (Summary, Skills, Education, etc.)

**Emits:**
- `update:content` — content changed
- `update:entries` — entries changed (add/remove/edit)
- `toggle` — collapse/expand
- `remove` — remove this section

#### Component: EntryCard.vue

A card for a single experience or project entry within a multi-entry section.

**Props:**
- `header: string` — the title line
- `content: string` — the bullet points

**Emits:**
- `update:header`, `update:content`, `remove`

### Determining Multi-Entry Sections

Only **Experience** and **Projects** are multi-entry sections. These are hardcoded — the parser already splits Experience into entries, and Projects follows the same bold-header + bullets pattern. All other sections (Summary, Education, Skills, Volunteering, custom sections) use a single textarea.

### Markdown Reassembly

When the user edits any field, the frontend reassembles the full markdown:

1. Build frontmatter block from structured fields (name, title, email, etc.)
2. For each section in order:
   - Single-content sections: `# SectionName\n{content}`
   - Multi-entry sections: `# SectionName\n{entry1}\n\n{entry2}\n...`
3. Join sections with `\n\n---\n\n` separators
4. Emit the full markdown string

### Profile Page Changes

The existing Profile page (`ProfileView.vue`) is updated:
- Remove the raw `master_resume` textarea
- Add the `SectionEditor` component in its place
- The `SectionEditor` receives the current markdown and emits updates
- Save button still calls `updateProfile({ master_resume: assembledMarkdown })`

### On First Load (No Existing Resume)

If there's no master resume yet, show an empty state with a template button that populates a starter resume with common sections (Summary, Education, Skills, Experience, Projects). The user can then fill in their details.

## Orchestrator Changes (Backend)

### Updated Prompt

The orchestrator prompt is updated to understand entry selection. Key additions to the prompt:

```
The resume contains an ABUNDANCE of experience entries and projects — 
more than can fit on a single page. Your job is to SELECT the most 
relevant entries for this specific job description, not just rewrite 
existing ones.

For Experience entries:
- Use action "include" to select an entry for the tailored resume
- Use action "exclude" to drop an entry (it won't appear)
- Use action "rewrite" for included entries that need bullet adjustments
- Select enough entries to fill the page without overflow

For Projects:
- Same include/exclude/rewrite actions
- Prioritize projects whose tech stack matches the JD
```

### Updated Tool Call Schema

The `tool_calls` output adds `include` and `exclude` actions:

```json
{
  "agent": "experience",
  "action": "include",
  "entry": "CompanyKey",
  "instructions": "Keep as-is, highly relevant"
}
```

```json
{
  "agent": "experience",
  "action": "exclude",
  "entry": "CompanyKey"
}
```

```json
{
  "agent": "projects",
  "action": "include",
  "entry": "ProjectName",
  "instructions": "Relevant stack, keep"
}
```

### Assembler Changes

The assembler (`assembler.py`) is updated:
- Entries with action `exclude` are dropped from the final resume
- Entries with action `include` (no rewrite) are kept verbatim
- Entries with action `rewrite` go through the existing agent pipeline

### AgentBus Changes

The bus (`bus.py`) only dispatches to agents for entries with `rewrite` action. `include` entries pass through, `exclude` entries are filtered out.

## Frontend Store

### ToolCall Interface Update

```typescript
export interface ToolCall {
  agent: string
  action: string        // now includes 'include' | 'exclude' | 'rewrite' | 'reorder' | 'keep'
  entry?: string
  instructions?: string
  promote?: string[]
  demote?: string[]
}
```

No other store changes needed — the existing `JobState` and flow remain the same.

## What Stays the Same

- **Editor view** — raw textarea + job cards + preview, unchanged
- **Backend agents** (summary, skills, experience, projects) — same rewrite logic
- **SSE streaming** — same event flow
- **Resume preview** — same rendering
- **Database schema** — `master_resume` stays a single markdown TEXT column
- **Parser** — same parsing logic, already handles multiple entries
- **Formatter** — same post-processing
- **Profile learner** — same async learning

## File Changes Summary

### New Files
- `frontend/src/components/SectionEditor.vue` — main section-based editor
- `frontend/src/components/SectionCard.vue` — collapsible section card
- `frontend/src/components/EntryCard.vue` — experience/project entry card

### Modified Files
- `frontend/src/views/ProfileView.vue` — replace textarea with SectionEditor
- `backend/agents/orchestrator.py` — updated prompt for entry selection
- `backend/agents/bus.py` — handle include/exclude actions
- `backend/services/assembler.py` — filter excluded entries

### Unchanged Files
- `frontend/src/views/EditorView.vue`
- `frontend/src/stores/editor.ts`
- `frontend/src/components/ResumePreview.vue`
- `frontend/src/components/MarkdownEditor.vue`
- `backend/agents/summary.py`, `skills.py`, `experience.py`, `projects.py`
- `backend/services/parser.py`, `formatter.py`
- `backend/routers/tailor.py` (SSE flow unchanged)
- `backend/db/*`
