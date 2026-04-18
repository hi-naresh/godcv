# API Reference

Base URL: `http://localhost:9000/api`

## Health

### `GET /health`

Returns server status.

```json
{ "status": "ok", "app": "godcv" }
```

## Profile

### `GET /profile`

Returns the current user profile.

**Response:**
```json
{
  "id": 1,
  "name": "Naresh Jhawar",
  "master_resume": "---\nname: ...\n---\n# Summary\n...",
  "gemini_api_key": "AIza...",
  "page_mode": "single",
  "created_at": "2026-04-14T10:00:00",
  "updated_at": "2026-04-17T15:30:00"
}
```

### `POST /profile`

Creates a new profile.

**Body:**
```json
{
  "name": "Your Name",
  "master_resume": "---\nname: ...\n---\n...",
  "gemini_api_key": "your_key",
  "page_mode": "single"
}
```

### `PUT /profile`

Updates the existing profile. All fields are optional.

**Body:**
```json
{
  "name": "Updated Name",
  "master_resume": "...",
  "gemini_api_key": "new_key"
}
```

### `GET /profile/insights`

Returns learned role insights from past tailorings.

**Response:**
```json
[
  {
    "id": 1,
    "role_type": "ai_engineer",
    "strongest_points": ["LLM orchestration", "data pipelines"],
    "preferred_skill_order": ["Python", "LangChain", "FastAPI"],
    "frequently_modified_sections": ["summary", "experience"],
    "tailoring_count": 5
  }
]
```

### `DELETE /profile/insights/{insight_id}`

Deletes a role insight.

## Tailoring

### `POST /tailor`

Starts resume tailoring. Returns a **Server-Sent Events** stream.

**Body:**
```json
{
  "job_description": "We are looking for an AI Engineer...",
  "resume_override": null,
  "gemini_api_key": null,
  "seniority_level": "mid-level",
  "analyze_only": false
}
```

- `resume_override` -- optional; uses profile's master resume if null
- `gemini_api_key` -- optional; uses profile's key if null
- `seniority_level` -- one of: `graduate`, `junior`, `mid-level`, `senior`, `lead`, `principal`
- `analyze_only` -- if true, only runs analysis phase (no tailoring)

**SSE Events:**

```
event: status
data: {"phase": "orchestrator"}

event: analysis
data: {"job_title": "AI Engineer", "company": "Acme", ...}

event: agent_start
data: {"agent": "summary"}

event: agent_done
data: {"agent": "summary", "section": "Summary", "content": "..."}

event: scoring_after
data: {"keyword_match": 85, "skills_coverage": 78, "overall_fit": 82}

event: ats_score
data: {"ats_score": 88, "breakdown": {...}, "brutal_verdict": "..."}

event: suggestions
data: [{"id": "s1", "type": "bullet", "section": "Experience:Acme", "content": "..."}]

event: complete
data: {"markdown": "---\nname: ...\n---\n# Summary\n..."}
```

### `POST /tailor/execute`

Re-executes an existing orchestrator plan (e.g., from history).

**Body:**
```json
{
  "orchestrator_plan": { ... },
  "resume_override": null,
  "gemini_api_key": null
}
```

## Jobs (History)

### `GET /jobs?limit=20`

Returns recent tailoring history.

**Response:**
```json
[
  {
    "id": 1,
    "job_title": "AI Engineer",
    "company": "Acme Corp",
    "job_description": "...",
    "tailored_resume": "...",
    "role_type": "ai_engineer",
    "sections_modified": ["summary", "skills", "experience"],
    "created_at": "2026-04-17T14:00:00"
  }
]
```

### `GET /jobs/{job_id}`

Returns a single tailoring record with full details including `original_resume` and `orchestrator_plan`.

### `DELETE /jobs/{job_id}`

Deletes a tailoring record.

## Export

### `POST /export/pdf`

Server-side PDF export (requires WeasyPrint).

**Body:**
```json
{
  "markdown": "---\nname: ...\n---\n# Summary\n..."
}
```

**Response:** PDF file (`application/pdf`)

Falls back to error if WeasyPrint is not installed. The frontend uses client-side PDF export (jsPDF + html2canvas) as the primary method.
