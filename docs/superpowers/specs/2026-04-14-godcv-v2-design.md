# GodCV v2 — Format Enforcement, Page Modes, Parallel Jobs, UI/UX, Tests

**Date:** 2026-04-14
**Status:** Approved

---

## 1. Format Enforcement Layer

### Problem
AI agents (Experience, Skills, Summary, Projects) return markdown with formatting defects: collapsed newlines, missing line breaks before headers, broken `**bold** *italic*` patterns, bullets merged into paragraphs. This causes the resume preview to render incorrectly.

### Solution — Two Layers

#### 1a. Agent Prompt Hardening
Each agent prompt includes explicit formatting rules with examples:

- **ExperienceAgent:** Each entry MUST start with `\n**Role — Company** *Dates*\n` on its own line, followed by bullet points each on their own line starting with `- `.
- **SkillsAgent:** Each category MUST be `\n**Category:** item1, item2.\n` with a blank line between categories.
- **SummaryAgent:** Return 2-3 sentences as a single paragraph, no headers.
- **ProjectsAgent:** Each project MUST start with `\n**[Project Name](url)** | Stack — ...\n` on its own line, followed by bullets.

#### 1b. Format Validator (`backend/services/formatter.py`)
Post-processing that runs on every agent output before assembly:

- Ensure blank line before any `**bold**` line that starts an experience entry.
- Ensure blank line before any `**Category:**` line in skills.
- Ensure each `- ` bullet is on its own line.
- Normalize multiple blank lines to single blank line.
- Strip trailing whitespace per line.
- Validate that experience entries match the `**Title — Company** *Dates*` pattern.
- Validate that skills entries match the `**Category:** items` pattern.

The assembler calls `validate_and_fix(section_name, content)` before stitching sections together.

---

## 2. Page Mode Toggle

### Current Behavior
Always auto-shrinks font to fit 1 page (minimum 8px). Frontmatter `font_size` and `line_spacing` fields are ignored.

### New Behavior

#### UI Control
A toggle above the A4 sheet in the preview area: **"1 Page"** | **"Multi-Page"**

#### 1-Page Mode (default)
- Same auto-shrink algorithm as today.
- Respects frontmatter `font_size` as the starting size (instead of hardcoded 11px).
- Respects frontmatter `line_spacing`.

#### Multi-Page Mode
- Uses frontmatter `font_size` (default 11px) and `line_spacing` (default 1.4) without shrinking.
- Renders as multiple A4 sheets stacked vertically, each with proper page boundaries.
- CSS `break-inside: avoid` on experience entries and project blocks prevents mid-entry page breaks.

#### Print Behavior
- **1-Page:** Prints single page (same as today).
- **Multi-Page:** Uses `@page { size: A4 }` with proper page breaks. Browser print dialog shows correct page count.

#### Component Changes
- `ResumePreview.vue` gets a `pageMode` ref (`'single' | 'multi'`) and renders either one `.sheet` or multiple.
- Store gets `pageMode` field so it persists during the session.

---

## 3. Parallel Jobs (Batch Tailoring)

### UI Flow
1. User loads their resume (once).
2. User adds multiple job descriptions — each in a card with a title field (optional, auto-extracted from JD), a seniority dropdown, and a JD textarea.
3. "Tailor All" button kicks off all jobs in parallel.
4. Each job gets its own tab showing: agent progress while running, then the tailored resume preview when done.

### Seniority Level
Each job card has a seniority level field:

- **Auto-detected** from JD keywords:
  - "entry level", "graduate", "new grad" → Graduate
  - "1-2 years", "junior" → Junior
  - "3-5 years", "mid-level" → Mid-Level
  - "5+ years", "senior" → Senior
  - "lead", "manage a team", "principal" → Lead / Principal
- **Manual fallback:** If detection fails, user picks from dropdown: Graduate | Junior | Mid-Level | Senior | Lead | Principal
- **Passed to orchestrator** so it adjusts tone/emphasis (Graduate → emphasize coursework/projects, Senior → emphasize leadership/impact).

Detection logic is a small utility using pattern matching on common JD phrases — no AI call needed.

### Tab System
- Tabs above the preview area: **"Original"** | **"Job 1: Title"** | **"Job 2: Title"** | ...
- "Original" tab always shows the master resume.
- Each job tab has: its own A4 preview, page mode toggle, Print/Export button, status indicator (spinner/checkmark/error).
- User can switch between tabs while jobs are still running.

### Backend
- `POST /api/tailor` request body gains an optional `seniority_level` field (string, one of: graduate, junior, mid-level, senior, lead, principal). Passed to the orchestrator prompt as context.
- No other backend changes needed for parallel jobs. Frontend opens multiple parallel SSE streams.
- Each stream is independent: same resume, different JD + seniority.

### Frontend Architecture
- New composable `useJobs.ts` — manages the job list, creates/removes jobs, tracks state per job.
- `useTailor.ts` updated to accept a job ID and scope its state to that job.
- Store: `jobs: Map<string, JobState>` where each JobState has `title`, `seniority`, `jobDescription`, `tailoringStatus`, `agentStatuses`, `result`, `pageMode`.
- `EditorView.vue` restructured: left panel = resume editor + job cards, right panel = tabbed preview.

---

## 4. UI/UX Overhaul

### Design Principles
- Simplicity — clean, uncluttered, no explanation needed.
- Guided flow — empty states and step indicators tell users what to do.
- Organization — controls grouped logically, nothing hidden.

### Layout — Three Zones

#### Top Bar (Nav)
- Dark nav bar: **GodCV** | Editor | Profile | History
- **API Key** icon/button in the top-right corner (opens a small modal/popover) — removes it from cluttering the workspace.

#### Left Panel — Resume & Jobs
Split into two collapsible sections:

**Resume Section (top half)**
- Markdown editor with drag-drop support.
- Clear label: "Your Master Resume".
- Empty state: "Paste your markdown resume or drag a .md file here".

**Jobs Section (bottom half)**
- "Add Job" button creates a new job card.
- Each job card contains:
  - Title field (auto-fills from JD or user types).
  - Seniority dropdown (auto-detected or manual select).
  - JD textarea (compact).
  - Remove button (x icon).
- Cards are collapsible when there are multiple jobs.
- "Tailor All" button at the bottom — prominent, gradient styled.

#### Right Panel — Tabbed Preview
- Tab bar: **Original** | **Job 1** | **Job 2** | ...
- Page mode toggle below tabs: **1 Page** | **Multi-Page**
- A4 sheet preview.
- Per-tab: Print/Export button, status badge.
- Agent progress shows inline below the tab bar for the active job while running.

### Guided Empty States
- No resume loaded: centered message in preview area — "Load a resume to see preview".
- No jobs added: prompt in jobs section — "Add a job description to start tailoring".
- First visit: subtle step indicators — 1. Load resume → 2. Add jobs → 3. Tailor.

### Responsive
- On narrow screens (< 900px), panels stack vertically.

---

## 5. Test Coverage

### Backend Tests (`tests/backend/`)

#### Parser (`test_parser.py`)
- Frontmatter extraction: with frontmatter, without, malformed YAML.
- Section splitting: all section types, missing headers, extra separators.
- Experience entry parsing: bold title + dates, hyphens vs em-dashes, entries without dates.
- Skills section parsing: category groupings preserved.
- Round-trip fidelity: `parse → assemble → parse` produces identical structure.

#### Assembler (`test_assembler.py`)
- Unmodified resume reconstructs identically.
- Single section replacement preserves all other sections verbatim.
- Experience per-entry replacement: modify one entry, keep others unchanged.
- Separator (`---`) preservation between sections.
- Frontmatter always preserved verbatim.

#### Formatter (`test_formatter.py`)
- Collapsed newlines before headers get fixed.
- Bullets merged into paragraphs get split onto separate lines.
- Experience entry format validation and repair.
- Skills category format validation and repair.
- Multiple blank lines normalized to single.
- Already-correct content passes through unchanged (no unnecessary modification).

#### Agent Output (`test_agents.py`)
- Mock Gemini responses, verify each agent's output passes format validation.
- ExperienceAgent: output matches `**Title — Company** *Dates*` + bullets pattern.
- SkillsAgent: output matches `**Category:** items` pattern.
- SummaryAgent: output is plain paragraph, no headers.
- ProjectsAgent: output matches project format.

#### Seniority Detection (`test_seniority.py`)
- JD with "5+ years experience" → Senior.
- JD with "graduate" / "entry level" → Graduate.
- JD with "lead a team" → Lead.
- JD with no signals → None (user must select manually).

### Frontend Tests (`tests/frontend/`)

#### Markdown Rendering (`useMarkdown.test.ts`)
- Frontmatter parsed correctly into header HTML (name, title, contacts).
- Experience entries render with right-floated dates.
- Skills categories render with bold category headers.
- Section separators render as `<hr>`.
- Malformed markdown doesn't crash.

#### Store (`editor.test.ts`, `jobs.test.ts`)
- Job CRUD: creation, removal, state isolation between jobs.
- Tailoring status transitions per job.
- Reset clears correct job state only, doesn't affect other jobs.

#### ResumePreview (`ResumePreview.test.ts`)
- Single-page mode triggers auto-fit algorithm.
- Multi-page mode renders multiple `.sheet` elements.
- Frontmatter `font_size` and `line_spacing` values are applied.

### Test Tooling
- **Backend:** pytest (already a dependency).
- **Frontend:** vitest + @vue/test-utils (natural fit with Vite).
- Both runnable via `pytest` and `npm test`.
