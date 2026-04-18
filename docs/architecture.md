# Architecture

## Overview

GodCV follows a **Parse-Modify-Assemble** pattern for resume tailoring, with an event-driven agent system orchestrated by a central planner.

```
User                Frontend (Vue 3)           Backend (FastAPI)         Gemini API
 |                      |                           |                       |
 |-- paste JD --------->|                           |                       |
 |                      |-- POST /api/tailor ------>|                       |
 |                      |                           |-- analyze JD -------->|
 |                      |<--- SSE: analysis --------|<--- plan ------------|
 |                      |<--- SSE: agent_start -----|                       |
 |                      |                           |-- run agents -------->|
 |                      |<--- SSE: agent_done ------|<--- rewritten -------|
 |                      |<--- SSE: complete --------|                       |
 |<-- live preview -----|                           |                       |
```

## Backend Architecture

### Layered Structure

```
backend/
  main.py              # FastAPI app, lifespan, CORS, static files
  cli.py               # CLI entry point (godcv run)
  config.py            # Environment config, Gemini settings
  routers/             # HTTP route handlers
    profile.py         # Profile CRUD
    tailor.py          # Tailoring SSE stream
    jobs.py            # Tailoring history
    export.py          # PDF export
  agents/              # AI agent modules
    orchestrator.py    # Job analysis + planning
    bus.py             # Agent dispatcher
    summary.py         # Summary rewriter
    skills.py          # Skills reorderer
    experience.py      # Experience rewriter
    projects.py        # Projects rewriter
    resume_scorer.py   # Post-tailor scoring
    ats_scorer.py      # ATS simulation
    suggestion_agent.py # Gap-based suggestions
    profile_learner.py # Role insight extraction
  services/            # Business logic
    gemini.py          # Gemini API client
    parser.py          # Resume markdown parser
    assembler.py       # Resume reassembly
    formatter.py       # Markdown validation
    profile.py         # Profile data access
    seniority.py       # Seniority level config
  db/                  # Data layer
    database.py        # SQLite setup + schema
    models.py          # Pydantic models
```

### Tailoring Pipeline

1. **Parse** -- `parser.py` breaks the resume into frontmatter, sections, and entries
2. **Analyze** -- `orchestrator.py` sends JD + resume to Gemini, gets a plan with `tool_calls`
3. **Dispatch** -- `bus.py` runs agents in parallel (summary, skills, projects) and sequentially (experience entries)
4. **Assemble** -- `assembler.py` merges agent outputs back into a complete resume
5. **Score** -- `resume_scorer.py` and `ats_scorer.py` evaluate the result
6. **Suggest** -- `suggestion_agent.py` generates improvement suggestions from gap analysis
7. **Learn** -- `profile_learner.py` saves role insights for future tailorings

### Agent Bus

The agent bus implements an event-driven dispatch pattern:

- Reads `tool_calls` from the orchestrator plan
- Groups agents by type (parallel vs sequential)
- Non-experience agents run concurrently
- Experience agents run per-entry to preserve ordering context
- Each agent receives: resume section, JD, orchestrator instructions, seniority context

### Streaming (SSE)

The `/api/tailor` endpoint uses Server-Sent Events for real-time progress:

| Event | Payload | When |
|-------|---------|------|
| `status` | phase name | Pipeline stage changes |
| `analysis` | job analysis JSON | After orchestrator analysis |
| `agent_start` | agent name | Agent begins work |
| `agent_done` | agent name + result | Agent completes |
| `scoring_after` | score metrics | Post-tailor scoring done |
| `ats_score` | ATS breakdown | ATS evaluation done |
| `suggestions` | suggestion list | Gap suggestions generated |
| `complete` | final markdown | All done |
| `error` | error message | Something failed |

## Frontend Architecture

### State Flow

```
Pinia Store (editor.ts)
  |
  |-- markdown: string          # Current resume source of truth
  |-- jobs: Map<id, JobState>   # All job tailoring states
  |-- activeJobId: string       # Selected job tab
  |-- profile: Profile          # Loaded user profile
  |
  |-- Views read/write store
  |-- Components receive props from views
  |-- Composables handle API calls + SSE streams
```

### Key Patterns

- **Single source of truth** -- both Editor and Profile tabs read/write `store.markdown`
- **Structured editing** -- `SectionEditor` parses markdown into entries, edits structured data, re-assembles
- **Auto-fit** -- `ResumePreview` dynamically adjusts font size and line spacing to fill exactly one A4 page
- **Round-trip fidelity** -- parsers and assemblers are tested for lossless markdown round-trips

### Component Hierarchy

```
App
  TabBar (navigation)
  EditorView
    JobCard (job description input)
    SectionEditor
      SectionCard (per-section: experience, education, etc.)
        ExperienceEntryCard / ProjectEntryCard / etc.
    ResumePreview (live A4 preview)
    ScorePanel (ATS + fit scores)
  ProfileView
    SectionEditor (same component, shared store)
    ResumePreview
```

## Database

SQLite with WAL mode for concurrent read access.

### Tables

- **profiles** -- user profile, master resume, API key, page mode
- **role_insights** -- learned patterns per role type (strongest points, skill order)
- **tailoring_history** -- past tailoring jobs with full plan and result

See [API Reference](./api.md) for endpoint details.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Uvicorn, Python 3.11+ |
| Database | SQLite (aiosqlite, WAL mode) |
| AI | Google Gemini 2.5 Flash |
| Frontend | Vue 3, TypeScript, Vite |
| State | Pinia |
| Routing | Vue Router 4 |
| PDF | jsPDF + html2canvas (client), WeasyPrint (server) |
| Testing | pytest (backend), vitest (frontend) |
