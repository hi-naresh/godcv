# GodCV -- Design Specification

**Date:** 2026-04-14
**Status:** Approved
**App name:** godcv

## 1. Problem

The current resume editor is a static HTML app that sends the entire resume + job description in one monolithic Gemini API call. This rewrites everything indiscriminately -- changing content that doesn't need changing, losing formatting, and wasting API tokens on irrelevant sections.

## 2. Solution

An event-driven, multi-agent resume tailoring system with:
- **Orchestrator** that analyzes job requirements and activates only the sub-agents needed
- **Section sub-agents** that modify only their assigned section, preserving everything else verbatim
- **User profile** that learns from each tailoring, building knowledge of the user's strengths per role type
- **Vue 3 + FastAPI** full-stack architecture replacing the static HTML app

## 3. Architecture

### 3.1 Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3 + TypeScript + Vite |
| Backend | Python + FastAPI |
| Database | SQLite (via aiosqlite) |
| AI | Gemini API (gemini-2.5-flash) |
| PDF | WeasyPrint (server-side) or browser print |
| Ports | 3000 (Vite dev), 9000 (FastAPI serves built frontend + API) |

### 3.2 High-Level Flow

```
User loads master resume into profile (one-time)
         │
         ▼
User pastes job description
         │
         ▼
POST /api/tailor (SSE stream)
         │
         ▼
┌────────────────────────┐
│ 1. ORCHESTRATOR AGENT  │  (1 Gemini call)
│    - Parse resume into │
│      sections           │
│    - Analyze JD          │
│    - Check profile       │
│      insights            │
│    - Emit tool_calls     │
│      for sections that   │
│      need modification   │
└──────────┬─────────────┘
           │
     ┌─────┴──── only "modify" sections ──────┐
     ▼              ▼              ▼           ▼
┌─────────┐  ┌──────────┐  ┌───────────┐ ┌─────────┐
│ Summary │  │  Skills   │  │ Exp Entry │ │Projects │
│ Agent   │  │  Agent    │  │ Agent x N │ │ Agent   │
└────┬────┘  └─────┬─────┘  └─────┬─────┘ └────┬────┘
     │             │              │             │
     └─────────────┴──────┬───────┴─────────────┘
                          ▼
              ┌───────────────────┐
              │ ASSEMBLER (Python)│  (no API call)
              │ Stitch unchanged  │
              │ + modified sections│
              └─────────┬─────────┘
                        ▼
              ┌───────────────────┐
              │ PROFILE LEARNER   │  (1 Gemini call, async)
              │ Extract insights  │
              │ from this tailoring│
              └───────────────────┘
```

### 3.3 Event-Driven Agent Bus

The agent bus is an internal Python dispatcher. Agents register themselves with the bus. The orchestrator produces a plan (list of tool calls). The bus executes only the called agents.

```python
# Orchestrator output format
{
  "analysis": {
    "role_type": "backend_ai",
    "key_requirements": ["RAG systems", "Python", "Kubernetes"],
    "matched_strengths": ["InsurStaq RAG work", "BotWot multi-agent"]
  },
  "tool_calls": [
    {"agent": "summary", "action": "rewrite", "instructions": "Focus on RAG and production AI systems"},
    {"agent": "skills", "action": "reorder", "promote": ["RAG Systems", "LangChain"], "demote": ["Blockchain"]},
    {"agent": "experience", "entry": "BotWot", "action": "rewrite", "instructions": "Emphasize multi-agent orchestration"},
    {"agent": "experience", "entry": "InsurStaq", "action": "rewrite", "instructions": "Emphasize RAG and production deployment"},
    {"agent": "experience", "entry": "SAILC", "action": "keep"},
    {"agent": "projects", "action": "reorder", "promote": ["Career Craft Agent"]}
  ],
  "sections_unchanged": ["Education", "Volunteering and Interests"]
}
```

**Activation rules:**
- `"action": "keep"` -- section passes through verbatim, no API call
- `"action": "rewrite"` -- sub-agent receives original text + instructions, returns modified markdown
- `"action": "reorder"` -- sub-agent reorders items within the section + minor wording tweaks
- Sections not mentioned in tool_calls are preserved unchanged
- Experience entries are dispatched individually (hybrid approach)
- Independent agents run in parallel via `asyncio.gather()`

### 3.4 Agent Definitions

| Agent | Trigger | Input | Output |
|-------|---------|-------|--------|
| **Orchestrator** | Always | Full resume + JD + profile insights | JSON plan with tool_calls |
| **SummaryAgent** | `tool_calls` contains `agent: "summary"` | Original summary + instructions + JD keywords | Modified summary markdown |
| **SkillsAgent** | `tool_calls` contains `agent: "skills"` | Original skills section + promote/demote lists | Reordered/tweaked skills markdown |
| **ExperienceAgent** | Per entry in `tool_calls` with `agent: "experience"` | Single job entry + instructions + JD keywords | Modified entry markdown |
| **ProjectsAgent** | `tool_calls` contains `agent: "projects"` | Original projects section + promote list + JD keywords | Reordered/tweaked projects markdown |
| **ProfileLearner** | Always, post-assembly | Original resume + tailored resume + JD + orchestrator plan | Structured insights to store |

**Agents NOT needed (preserved verbatim):**
- Frontmatter -- never modified, always preserved by the assembler
- Education -- rarely needs tailoring; orchestrator can flag it if needed
- Volunteering -- same as education

## 4. Profile & Learning System

### 4.1 Profile Schema

```sql
CREATE TABLE profiles (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    master_resume TEXT NOT NULL,      -- full markdown
    parsed_sections TEXT,              -- JSON of parsed section map
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE role_insights (
    id INTEGER PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id),
    role_type TEXT NOT NULL,           -- "ai_ml", "backend", "data_eng", etc.
    strongest_points TEXT,             -- JSON array of top talking points
    preferred_skill_order TEXT,        -- JSON array of skill ordering
    frequently_modified_sections TEXT, -- JSON array
    tailoring_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tailoring_history (
    id INTEGER PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id),
    job_title TEXT,
    company TEXT,
    job_description TEXT NOT NULL,
    original_resume TEXT NOT NULL,
    tailored_resume TEXT NOT NULL,
    orchestrator_plan TEXT,            -- JSON of the tool_calls plan
    role_type TEXT,
    sections_modified TEXT,            -- JSON array of section names
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 Learning Flow

After each tailoring:

1. **ProfileLearner** agent analyzes:
   - What role type was this? (classify into categories)
   - Which sections were modified and how?
   - What were the strongest talking points selected?
   - Which skills were promoted?

2. **Upsert into `role_insights`:**
   - If role_type exists: merge new insights with existing, increment count
   - If new role_type: create entry

3. **Orchestrator uses insights on next tailoring:**
   - "For ai_ml roles, you've previously led with InsurStaq RAG work 4 times"
   - "Your strongest backend talking points are: multi-agent orchestration, data pipelines"
   - These become additional context for sub-agent instructions

## 5. API Endpoints

### 5.1 Profile

```
GET    /api/profile              -- Get current profile
POST   /api/profile              -- Create profile (upload master resume)
PUT    /api/profile              -- Update profile/master resume
GET    /api/profile/insights     -- Get learned role insights
DELETE /api/profile/insights/:id -- Remove a specific insight
```

### 5.2 Tailoring

```
POST   /api/tailor               -- Start tailoring (SSE stream)
  Body: { job_description: string, resume_override?: string }
  Response: SSE stream of events (see 5.4)
```

### 5.3 History

```
GET    /api/jobs                  -- List past tailorings
GET    /api/jobs/:id              -- Get specific tailoring result
DELETE /api/jobs/:id              -- Delete a tailoring
```

### 5.4 SSE Event Stream

```
event: status
data: {"phase": "orchestrator", "message": "Analyzing job requirements..."}

event: plan
data: {"tool_calls": [...], "sections_unchanged": [...]}

event: agent_start
data: {"agent": "summary"}

event: agent_done
data: {"agent": "summary", "preview": "AI Engineer specialising in..."}

event: agent_start
data: {"agent": "experience:BotWot"}

event: agent_done
data: {"agent": "experience:BotWot", "preview": "Building orchestrated..."}

event: assembly
data: {"message": "Assembling final resume..."}

event: complete
data: {"markdown": "---\nname: ...", "sections_modified": 3, "sections_kept": 3}

event: error
data: {"message": "Gemini API error: ..."}
```

### 5.5 Export

```
POST   /api/export/pdf           -- Generate PDF from markdown
  Body: { markdown: string }
  Response: PDF file download
```

## 6. Resume Section Parser

```python
def parse_resume(markdown: str) -> dict:
    """
    Splits resume markdown into frontmatter + ordered sections.
    
    Returns:
    {
        "frontmatter": "---\nname: ...\n---",
        "sections": OrderedDict({
            "Summary": "AI Engineer specialising in...",
            "Education": "**M.Sc. in AI...",
            "Skills": "**Data Engineering:** ETL...",
            "Experience": {
                "_full": "full section text",
                "_entries": [
                    {"title": "AI Data Engineer — BotWot", "content": "- Building..."},
                    {"title": "LLM Data Engineer — InsurStaq", "content": "- Built..."},
                    {"title": "Student Software Engineer — SAILC", "content": "- Developed..."}
                ]
            },
            "Projects": "**[Luxury Concierge...]...",
            "Volunteering and Interests": "**National Service..."
        }),
        "separators": ["---", "---", "---", "---"]  # preserve original separators
    }
    """
```

**Parsing rules:**
- Frontmatter: everything between first `---` pair (inclusive)
- Sections: split by `# ` headers (h1)
- Experience entries: split by `**...**` bold lines that contain job title patterns (company name + date)
- Separators (`---` between sections): tracked and restored during assembly
- Section order: preserved exactly as original

## 7. Assembler

```python
def assemble_resume(
    original_parsed: dict,
    modified_sections: dict,  # only sections that were modified
) -> str:
    """
    Reconstructs the full resume markdown.
    
    Rules:
    1. Frontmatter: always from original, verbatim
    2. For each section in original order:
       - If section key exists in modified_sections: use modified version
       - Otherwise: use original verbatim (character-for-character)
    3. Experience: per-entry assembly
       - Modified entries replaced, unmodified entries preserved verbatim
    4. Separators restored in original positions
    """
```

## 8. Frontend (Vue 3)

### 8.1 Views

| View | Route | Purpose |
|------|-------|---------|
| EditorView | `/` | Main workspace: markdown editor + A4 preview + job input + agent progress |
| ProfileView | `/profile` | Upload/edit master resume, view learned insights |
| HistoryView | `/history` | Browse past tailorings, re-use or compare |

### 8.2 Key Components

| Component | Purpose |
|-----------|---------|
| `MarkdownEditor.vue` | Textarea with syntax highlighting, drag-drop support |
| `ResumePreview.vue` | A4 sheet preview with auto-fit (ported from current app) |
| `AgentProgress.vue` | Live panel showing orchestrator plan + agent status (SSE-driven) |
| `JobInput.vue` | Job description textarea + tailor button |
| `PdfExporter.vue` | Export/download/print controls |
| `ProfileCard.vue` | Shows learned role insights with edit/delete |

### 8.3 State Management

Pinia store `editor.ts`:
```typescript
{
  markdown: string,           // current editor content
  profile: Profile | null,    // loaded profile
  tailoring: {
    status: 'idle' | 'running' | 'done' | 'error',
    plan: ToolCall[] | null,  // orchestrator plan
    agentStatuses: Record<string, 'pending' | 'running' | 'done'>,
    result: string | null     // final tailored markdown
  }
}
```

### 8.4 Tailoring UX Flow

1. User has resume loaded in editor (from profile or pasted)
2. User pastes job description in JobInput
3. Clicks "Tailor Resume"
4. AgentProgress panel appears, SSE stream begins:
   - Orchestrator phase: "Analyzing job requirements..."
   - Plan revealed: shows which agents will activate (others greyed out)
   - Each agent lights up as it runs, turns green when done
   - Preview snippets shown per completed agent
5. On complete: editor updates with tailored resume, preview re-renders
6. User can edit further, then export PDF

## 9. Project Structure

```
godcv/
├── backend/
│   ├── main.py                     # FastAPI app entry point
│   ├── requirements.txt
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── bus.py                  # AgentBus dispatcher
│   │   ├── orchestrator.py         # Orchestrator agent
│   │   ├── summary.py              # SummaryAgent
│   │   ├── skills.py               # SkillsAgent
│   │   ├── experience.py           # ExperienceAgent
│   │   ├── projects.py             # ProjectsAgent
│   │   └── profile_learner.py      # Post-tailoring learner
│   ├── services/
│   │   ├── gemini.py               # Gemini API client
│   │   ├── profile.py              # Profile service
│   │   ├── parser.py               # Resume section parser
│   │   └── assembler.py            # Section assembler
│   ├── db/
│   │   ├── database.py             # SQLite setup + migrations
│   │   └── models.py               # Data models
│   └── routers/
│       ├── profile.py              # Profile endpoints
│       ├── tailor.py               # Tailor SSE endpoint
│       ├── jobs.py                 # History endpoints
│       └── export.py               # PDF export
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   ├── router.ts
│   │   ├── views/
│   │   │   ├── EditorView.vue
│   │   │   ├── ProfileView.vue
│   │   │   └── HistoryView.vue
│   │   ├── components/
│   │   │   ├── MarkdownEditor.vue
│   │   │   ├── ResumePreview.vue
│   │   │   ├── AgentProgress.vue
│   │   │   ├── JobInput.vue
│   │   │   ├── PdfExporter.vue
│   │   │   └── ProfileCard.vue
│   │   ├── composables/
│   │   │   ├── useProfile.ts
│   │   │   ├── useTailor.ts
│   │   │   └── useMarkdown.ts
│   │   └── stores/
│   │       └── editor.ts
│   └── dist/                       # Built output served by FastAPI
├── data/
│   ├── godcv.db                    # SQLite (created at runtime)
│   └── resume_21oct.md             # Sample resume (migrated)
└── README.md
```

## 10. Migration from Current App

The current static HTML app's logic is preserved:
- **Frontmatter parser** -- ported to `backend/services/parser.py`
- **Header builder** -- ported to Vue `ResumePreview.vue` component
- **Auto-fit algorithm** -- ported to `ResumePreview.vue` (runs client-side)
- **CSS styles** -- migrated to Vue component styles + global stylesheet
- **Sample resumes** -- moved to `data/` directory
- **Prompt templates** -- replaced by agent-specific prompts in each agent file

## 11. Configuration

```python
# backend/config.py
GEMINI_API_KEY = ""  # set via env var GODCV_GEMINI_API_KEY or UI
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
GEMINI_GENERATION_CONFIG = {
    "temperature": 0.7,
    "topK": 40,
    "topP": 0.95,
    "maxOutputTokens": 4096,
}
DB_PATH = "data/godcv.db"
FRONTEND_DIST = "frontend/dist"
```

API key management: set via `GODCV_GEMINI_API_KEY` environment variable, or entered in the UI (stored in SQLite, plain text -- this is a local single-user tool). UI input takes precedence over env var.

### 11.1 CORS (Dev Mode)

FastAPI enables CORS for `http://localhost:3000` in development so the Vite dev server can call the API on port 9000. In production (built frontend served by FastAPI), CORS is not needed.
