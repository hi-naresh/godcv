# GodCV

AI-powered resume tailoring system that analyzes job descriptions and rewrites your resume to maximize ATS scores and recruiter fit.

## What It Does

1. **Paste a job description** -- GodCV analyzes requirements, skills, and seniority expectations
2. **AI agents tailor your resume** -- specialized agents rewrite each section (summary, skills, experience, projects) in parallel
3. **Score and improve** -- get ATS scores, keyword match metrics, and concrete suggestions to close gaps
4. **Export** -- download a pixel-perfect single-page A4 PDF

## Key Features

- **Multi-agent pipeline** -- orchestrator plans the work, specialist agents execute in parallel
- **Seniority-aware** -- tailoring adapts from graduate to principal level (section ordering, emphasis, language)
- **ATS scoring** -- simulates applicant tracking systems with a 9-category breakdown
- **Gap suggestions** -- recommends new bullets, skills, and projects based on what's missing
- **Live preview** -- A4 page preview with auto-fit font sizing and line spacing
- **Structured editor** -- edit experience entries, skills, projects as structured data (not raw markdown)
- **Multi-job support** -- tailor for multiple positions simultaneously, compare results
- **Role learning** -- remembers your strongest points and skill preferences per role type

## Screenshots

| Editor | Profile |
|--------|---------|
| Dual-pane: section editor + live A4 preview | Master resume management with collapsible sections |

## Quick Start

```bash
git clone https://github.com/hi-naresh/godcv.git
cd godcv
python -m venv venv && source venv/bin/activate
pip install -e .
echo "GEMINI_API_KEY=your_key" > .env
godcv build   # builds the frontend
godcv run     # starts everything on :9000
```

Open `http://localhost:9000`

See [Setup Guide](docs/setup.md) for detailed instructions.

## How It Works

```
Job Description ──> Orchestrator ──> Agent Bus ──> Assembler ──> Scorer
                    (analysis)      /  |  |  \    (rebuild)    (evaluate)
                                   S   K  P   E
                                   u   i  r   x
                                   m   l  o   p
                                   m   l  j   e
                                   a   s  e   r
                                   r      c   i
                                   y      t   e
                                          s   n
                                              c
                                              e
```

The orchestrator analyzes the JD and produces a plan. The agent bus dispatches specialist agents that work on individual sections. Results are assembled back into a complete resume, scored, and presented with improvement suggestions.

See [Architecture](docs/architecture.md) for the full technical design.

## Tech Stack

| | Technology |
|---|---|
| **Backend** | FastAPI, Python 3.11+, SQLite |
| **AI** | Google Gemini 2.5 Flash |
| **Frontend** | Vue 3, TypeScript, Vite, Pinia |
| **PDF** | jsPDF + html2canvas |
| **Testing** | pytest, vitest |

## Documentation

| Document | Description |
|----------|-------------|
| [Setup Guide](docs/setup.md) | Installation, configuration, running, troubleshooting |
| [Architecture](docs/architecture.md) | System design, data flow, component hierarchy |
| [API Reference](docs/api.md) | REST endpoints, SSE events, request/response formats |
| [Agent System](docs/agents.md) | How the multi-agent pipeline works |
| [Resume Format](docs/resume-format.md) | Markdown format spec for resumes |

## Project Structure

```
godcv/
  backend/
    main.py            # FastAPI app
    cli.py             # CLI (godcv run)
    agents/            # AI agents (orchestrator, summary, skills, experience, projects, scorers)
    services/          # Business logic (Gemini client, parser, assembler)
    routers/           # API routes (profile, tailor, jobs, export)
    db/                # SQLite schema + Pydantic models
  frontend/
    src/
      views/           # Pages (Editor, Profile, History, Roles, Preferences)
      components/      # Vue components (SectionEditor, ResumePreview, EntryCards)
      composables/     # Reusable logic (useTailor, useProfile, useMarkdown)
      stores/          # Pinia state (editor store)
      utils/           # Section parsers and assemblers
  data/                # SQLite database (auto-created)
  tests/               # Backend tests
  docs/                # Documentation
```

## License

MIT
