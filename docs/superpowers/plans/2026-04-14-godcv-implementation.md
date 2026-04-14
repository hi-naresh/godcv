# GodCV Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an event-driven multi-agent resume tailoring app (GodCV) with FastAPI backend, Vue 3 frontend, SQLite persistence, and Gemini AI.

**Architecture:** FastAPI backend with an internal agent bus dispatches Gemini API calls to section-specific sub-agents based on an orchestrator's analysis of job requirements. Vue 3 SPA consumes SSE streams for real-time progress. SQLite stores user profiles and learned role insights.

**Tech Stack:** Python 3.11+, FastAPI, aiosqlite, httpx, Vue 3, TypeScript, Vite, Pinia, marked.js

**Spec:** `docs/superpowers/specs/2026-04-14-godcv-design.md`

---

## Task Dependency Graph

```
Task 1 (scaffold) ──┬── Task 2 (database)
                     ├── Task 3 (parser + assembler)
                     ├── Task 4 (gemini client)
                     └── Task 8 (vue scaffold)
                          │
Task 2 ──────────── Task 5 (profile service)
Task 3 + 4 ──────── Task 6 (agent bus + orchestrator + section agents)
Task 5 + 6 ──────── Task 7 (API routers + main.py)
Task 8 ──────────── Task 9 (vue components + views)
Task 7 + 9 ──────── Task 10 (integration + build)
```

Tasks 2, 3, 4, 8 can run in parallel after Task 1.
Tasks 5 and 6 can run in parallel after their deps.

---

## Task 1: Project Scaffolding

**Files:**
- Create: `godcv/backend/requirements.txt`
- Create: `godcv/backend/__init__.py`
- Create: `godcv/backend/config.py`
- Create: all `__init__.py` files for packages

- [ ] **Step 1: Create directory structure**

```bash
cd /Users/naresh/Documents/resume_editor
mkdir -p godcv/backend/{agents,services,db,routers}
mkdir -p godcv/frontend
mkdir -p godcv/data
touch godcv/backend/__init__.py
touch godcv/backend/agents/__init__.py
touch godcv/backend/services/__init__.py
touch godcv/backend/db/__init__.py
touch godcv/backend/routers/__init__.py
```

- [ ] **Step 2: Create requirements.txt**

Write to `godcv/backend/requirements.txt`:
```
fastapi==0.115.12
uvicorn[standard]==0.34.2
aiosqlite==0.21.0
httpx==0.28.1
python-multipart==0.0.20
weasyprint==63.1
markdown==3.7.1
pydantic==2.11.3
```

- [ ] **Step 3: Create config.py**

Write to `godcv/backend/config.py`:
```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

GEMINI_API_KEY = os.environ.get("GODCV_GEMINI_API_KEY", "")
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
GEMINI_GENERATION_CONFIG = {
    "temperature": 0.7,
    "topK": 40,
    "topP": 0.95,
    "maxOutputTokens": 4096,
}
GEMINI_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

DB_PATH = str(BASE_DIR / "data" / "godcv.db")
FRONTEND_DIST = str(BASE_DIR / "frontend" / "dist")
```

- [ ] **Step 4: Copy sample resume to godcv/data/**

```bash
cp /Users/naresh/Documents/resume_editor/data/resume_21oct.md /Users/naresh/Documents/resume_editor/godcv/data/sample_resume.md
```

- [ ] **Step 5: Install Python dependencies**

```bash
cd /Users/naresh/Documents/resume_editor/godcv
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

---

## Task 2: Database Layer

**Files:**
- Create: `godcv/backend/db/database.py`
- Create: `godcv/backend/db/models.py`

- [ ] **Step 1: Create database.py**

Write to `godcv/backend/db/database.py`:
```python
import aiosqlite
import json
from pathlib import Path
from backend.config import DB_PATH

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await _init_tables(_db)
    return _db


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None


async def _init_tables(db: aiosqlite.Connection):
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            master_resume TEXT NOT NULL,
            parsed_sections TEXT,
            gemini_api_key TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS role_insights (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
            role_type TEXT NOT NULL,
            strongest_points TEXT DEFAULT '[]',
            preferred_skill_order TEXT DEFAULT '[]',
            frequently_modified_sections TEXT DEFAULT '[]',
            tailoring_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tailoring_history (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
            job_title TEXT,
            company TEXT,
            job_description TEXT NOT NULL,
            original_resume TEXT NOT NULL,
            tailored_resume TEXT NOT NULL,
            orchestrator_plan TEXT,
            role_type TEXT,
            sections_modified TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    await db.commit()
```

- [ ] **Step 2: Create models.py**

Write to `godcv/backend/db/models.py`:
```python
from pydantic import BaseModel
from datetime import datetime


class ProfileCreate(BaseModel):
    name: str
    master_resume: str
    gemini_api_key: str = ""


class ProfileUpdate(BaseModel):
    name: str | None = None
    master_resume: str | None = None
    gemini_api_key: str | None = None


class ProfileResponse(BaseModel):
    id: int
    name: str
    master_resume: str
    gemini_api_key: str
    created_at: str
    updated_at: str


class RoleInsightResponse(BaseModel):
    id: int
    profile_id: int
    role_type: str
    strongest_points: list[str]
    preferred_skill_order: list[str]
    frequently_modified_sections: list[str]
    tailoring_count: int


class TailorRequest(BaseModel):
    job_description: str
    resume_override: str | None = None
    gemini_api_key: str | None = None


class TailoringHistoryResponse(BaseModel):
    id: int
    profile_id: int
    job_title: str | None
    company: str | None
    job_description: str
    original_resume: str
    tailored_resume: str
    orchestrator_plan: str | None
    role_type: str | None
    sections_modified: list[str]
    created_at: str


class ExportRequest(BaseModel):
    markdown: str
```

- [ ] **Step 3: Verify database creates successfully**

```bash
cd /Users/naresh/Documents/resume_editor/godcv
source venv/bin/activate
python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from backend.db.database import get_db, close_db
async def test():
    db = await get_db()
    cursor = await db.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
    tables = await cursor.fetchall()
    print('Tables:', [t[0] for t in tables])
    await close_db()
asyncio.run(test())
"
```
Expected: `Tables: ['profiles', 'role_insights', 'tailoring_history']`

---

## Task 3: Resume Parser + Assembler

**Files:**
- Create: `godcv/backend/services/parser.py`
- Create: `godcv/backend/services/assembler.py`

- [ ] **Step 1: Create parser.py**

Write to `godcv/backend/services/parser.py`:
```python
import re
from collections import OrderedDict


def parse_frontmatter(markdown: str) -> tuple[str, str]:
    """Extract frontmatter and body from markdown.
    Returns (frontmatter_block, body) where frontmatter_block includes --- markers."""
    match = re.match(r'^(---\s*\n[\s\S]*?\n---)\s*\n?([\s\S]*)', markdown)
    if not match:
        return "", markdown
    return match.group(1), match.group(2)


def parse_experience_entries(section_content: str) -> list[dict]:
    """Split experience section into individual job entries.
    Each entry starts with a bold line containing a job title pattern like:
    **Role — Company** *dates*
    """
    entries = []
    # Split on lines that start with ** and contain an em dash or hyphen (job title pattern)
    parts = re.split(r'(?=^\*\*[^*]+(?:—|–|-)[^*]+\*\*)', section_content, flags=re.MULTILINE)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Extract title from first bold segment
        title_match = re.match(r'^\*\*([^*]+)\*\*', part)
        title = title_match.group(1).strip() if title_match else "Unknown"
        # Create a short key from company name
        key = _extract_company_key(title)
        entries.append({"key": key, "title": title, "content": part})
    return entries


def _extract_company_key(title: str) -> str:
    """Extract a short company key from a title like 'AI Data Engineer — BotWot iCX ...'"""
    # Split on em dash, en dash, or regular dash surrounded by spaces
    parts = re.split(r'\s*(?:—|–|-)\s*', title)
    if len(parts) >= 2:
        company = parts[1].strip()
        # Take first word as key
        return re.split(r'[\s(,]', company)[0]
    return title[:20]


def parse_sections(body: str) -> tuple[OrderedDict, list[str]]:
    """Parse markdown body into ordered sections.
    Returns (sections_dict, separators_list).
    Sections are keyed by their # header name.
    Experience section gets special treatment with per-entry parsing.
    """
    sections = OrderedDict()
    separators = []

    # Split by # headers (h1 only)
    parts = re.split(r'^(# .+)$', body, flags=re.MULTILINE)

    current_key = None
    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue

        if stripped.startswith('# '):
            current_key = stripped[2:].strip()
            sections[current_key] = ""
        elif current_key is not None:
            # Check for separator before content
            content = part
            if content.strip() == '---':
                separators.append(current_key)
                continue
            # Remove leading/trailing --- separators from content
            content = re.sub(r'^\s*---\s*$', '', content, flags=re.MULTILINE).strip()
            if content:
                sections[current_key] = content

                # Special handling for Experience
                if current_key.lower() == "experience":
                    entries = parse_experience_entries(content)
                    if entries:
                        sections[current_key] = {
                            "_full": content,
                            "_entries": entries,
                        }
        else:
            # Content before any header (could be separator)
            if stripped == '---':
                separators.append("_pre")

    return sections, separators


def parse_resume(markdown: str) -> dict:
    """Full resume parser. Returns structured dict with frontmatter, sections, separators."""
    frontmatter, body = parse_frontmatter(markdown)
    sections, separators = parse_sections(body)
    return {
        "frontmatter": frontmatter,
        "sections": sections,
        "separators": separators,
    }
```

- [ ] **Step 2: Create assembler.py**

Write to `godcv/backend/services/assembler.py`:
```python
from collections import OrderedDict


def assemble_resume(
    original_parsed: dict,
    modified_sections: dict[str, str],
    modified_experience_entries: dict[str, str] | None = None,
) -> str:
    """Reconstruct full resume markdown from original + modifications.

    Args:
        original_parsed: Output of parse_resume()
        modified_sections: Dict of section_name -> new markdown content (only modified sections)
        modified_experience_entries: Dict of entry_key -> new markdown content (only modified entries)

    Rules:
        1. Frontmatter: always from original, verbatim
        2. Sections in original order; use modified version if present, else original verbatim
        3. Experience: per-entry replacement; unmodified entries preserved verbatim
        4. Separators restored between sections
    """
    parts = []

    # 1. Frontmatter
    if original_parsed["frontmatter"]:
        parts.append(original_parsed["frontmatter"])

    # 2. Sections in order
    sections = original_parsed["sections"]
    section_keys = list(sections.keys())

    for i, key in enumerate(section_keys):
        parts.append(f"\n# {key}")
        original = sections[key]

        if key in modified_sections:
            # Use modified version
            parts.append(modified_sections[key])
        elif isinstance(original, dict) and "_entries" in original and modified_experience_entries:
            # Experience: per-entry assembly
            entry_parts = []
            for entry in original["_entries"]:
                if entry["key"] in modified_experience_entries:
                    entry_parts.append(modified_experience_entries[entry["key"]])
                else:
                    entry_parts.append(entry["content"])
            parts.append("\n".join(entry_parts))
        elif isinstance(original, dict) and "_full" in original:
            parts.append(original["_full"])
        else:
            parts.append(str(original))

        # Add separator after section if not last
        if i < len(section_keys) - 1:
            parts.append("\n---")

    return "\n".join(parts) + "\n"
```

- [ ] **Step 3: Test parser with sample resume**

```bash
cd /Users/naresh/Documents/resume_editor/godcv
source venv/bin/activate
python3 -c "
import sys, json
sys.path.insert(0, '.')
from backend.services.parser import parse_resume
with open('data/sample_resume.md') as f:
    md = f.read()
result = parse_resume(md)
print('Frontmatter length:', len(result['frontmatter']))
print('Sections:', list(result['sections'].keys()))
exp = result['sections'].get('Experience', {})
if isinstance(exp, dict):
    print('Experience entries:', [e['key'] for e in exp['_entries']])
print('Separators:', result['separators'])
"
```
Expected: Shows sections [Summary, Education, Skills, Experience, Projects, Volunteering and Interests] with experience entries [BotWot, InsurStaq, SAILC].

---

## Task 4: Gemini API Client

**Files:**
- Create: `godcv/backend/services/gemini.py`

- [ ] **Step 1: Create gemini.py**

Write to `godcv/backend/services/gemini.py`:
```python
import httpx
import json
import re
from backend.config import (
    GEMINI_ENDPOINT,
    GEMINI_GENERATION_CONFIG,
    GEMINI_SAFETY_SETTINGS,
)


class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = GEMINI_ENDPOINT

    async def generate(self, prompt: str, json_mode: bool = False) -> str:
        """Call Gemini API and return the text response.
        If json_mode=True, adds instruction to return valid JSON and parses response."""
        gen_config = {**GEMINI_GENERATION_CONFIG}
        if json_mode:
            gen_config["responseMimeType"] = "application/json"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": gen_config,
            "safetySettings": GEMINI_SAFETY_SETTINGS,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.endpoint}?key={self.api_key}",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code != 200:
                error_data = response.json()
                msg = error_data.get("error", {}).get("message", f"API error {response.status_code}")
                raise RuntimeError(f"Gemini API error: {msg}")

            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return self._clean_response(text)

    async def generate_json(self, prompt: str) -> dict:
        """Call Gemini and parse the response as JSON."""
        text = await self.generate(prompt, json_mode=True)
        return json.loads(text)

    def _clean_response(self, text: str) -> str:
        """Remove markdown code fences if present."""
        cleaned = text.strip()
        cleaned = re.sub(r'^```(?:markdown|json|)?\s*\n', '', cleaned)
        cleaned = re.sub(r'\n```\s*$', '', cleaned)
        return cleaned.strip()
```

---

## Task 5: Profile Service

**Files:**
- Create: `godcv/backend/services/profile.py`

**Depends on:** Task 2 (database)

- [ ] **Step 1: Create profile.py**

Write to `godcv/backend/services/profile.py`:
```python
import json
from backend.db.database import get_db
from backend.services.parser import parse_resume


async def get_profile(profile_id: int = 1) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    return dict(row)


async def create_profile(name: str, master_resume: str, gemini_api_key: str = "") -> dict:
    db = await get_db()
    parsed = parse_resume(master_resume)
    parsed_json = json.dumps({
        "sections": {k: v if not isinstance(v, dict) else v.get("_full", str(v))
                     for k, v in parsed["sections"].items()},
        "separators": parsed["separators"],
    })
    cursor = await db.execute(
        "INSERT INTO profiles (name, master_resume, parsed_sections, gemini_api_key) VALUES (?, ?, ?, ?)",
        (name, master_resume, parsed_json, gemini_api_key),
    )
    await db.commit()
    return await get_profile(cursor.lastrowid)


async def update_profile(profile_id: int, **kwargs) -> dict | None:
    db = await get_db()
    fields = []
    values = []
    for key in ("name", "master_resume", "gemini_api_key"):
        if key in kwargs and kwargs[key] is not None:
            fields.append(f"{key} = ?")
            values.append(kwargs[key])

    if "master_resume" in kwargs and kwargs["master_resume"]:
        parsed = parse_resume(kwargs["master_resume"])
        parsed_json = json.dumps({
            "sections": {k: v if not isinstance(v, dict) else v.get("_full", str(v))
                         for k, v in parsed["sections"].items()},
            "separators": parsed["separators"],
        })
        fields.append("parsed_sections = ?")
        values.append(parsed_json)

    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(profile_id)

    await db.execute(f"UPDATE profiles SET {', '.join(fields)} WHERE id = ?", values)
    await db.commit()
    return await get_profile(profile_id)


async def get_role_insights(profile_id: int) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM role_insights WHERE profile_id = ? ORDER BY tailoring_count DESC",
        (profile_id,),
    )
    rows = await cursor.fetchall()
    results = []
    for row in rows:
        d = dict(row)
        for field in ("strongest_points", "preferred_skill_order", "frequently_modified_sections"):
            d[field] = json.loads(d[field]) if d[field] else []
        results.append(d)
    return results


async def upsert_role_insight(profile_id: int, role_type: str, strongest_points: list[str],
                               preferred_skill_order: list[str], modified_sections: list[str]):
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM role_insights WHERE profile_id = ? AND role_type = ?",
        (profile_id, role_type),
    )
    existing = await cursor.fetchone()

    if existing:
        existing = dict(existing)
        old_points = json.loads(existing["strongest_points"]) if existing["strongest_points"] else []
        merged_points = list(dict.fromkeys(strongest_points + old_points))[:10]
        old_skills = json.loads(existing["preferred_skill_order"]) if existing["preferred_skill_order"] else []
        merged_skills = list(dict.fromkeys(preferred_skill_order + old_skills))[:20]
        old_sections = json.loads(existing["frequently_modified_sections"]) if existing["frequently_modified_sections"] else []
        merged_sections = list(dict.fromkeys(modified_sections + old_sections))

        await db.execute(
            """UPDATE role_insights SET
               strongest_points = ?, preferred_skill_order = ?,
               frequently_modified_sections = ?, tailoring_count = tailoring_count + 1,
               updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (json.dumps(merged_points), json.dumps(merged_skills),
             json.dumps(merged_sections), existing["id"]),
        )
    else:
        await db.execute(
            """INSERT INTO role_insights
               (profile_id, role_type, strongest_points, preferred_skill_order,
                frequently_modified_sections, tailoring_count)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (profile_id, role_type, json.dumps(strongest_points),
             json.dumps(preferred_skill_order), json.dumps(modified_sections)),
        )
    await db.commit()


async def delete_role_insight(insight_id: int):
    db = await get_db()
    await db.execute("DELETE FROM role_insights WHERE id = ?", (insight_id,))
    await db.commit()


async def save_tailoring(profile_id: int, job_title: str | None, company: str | None,
                          job_description: str, original_resume: str, tailored_resume: str,
                          orchestrator_plan: dict, role_type: str | None,
                          sections_modified: list[str]) -> int:
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO tailoring_history
           (profile_id, job_title, company, job_description, original_resume,
            tailored_resume, orchestrator_plan, role_type, sections_modified)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (profile_id, job_title, company, job_description, original_resume,
         tailored_resume, json.dumps(orchestrator_plan), role_type,
         json.dumps(sections_modified)),
    )
    await db.commit()
    return cursor.lastrowid


async def get_tailoring_history(profile_id: int, limit: int = 20) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM tailoring_history WHERE profile_id = ? ORDER BY created_at DESC LIMIT ?",
        (profile_id, limit),
    )
    rows = await cursor.fetchall()
    results = []
    for row in rows:
        d = dict(row)
        d["sections_modified"] = json.loads(d["sections_modified"]) if d["sections_modified"] else []
        results.append(d)
    return results


async def get_tailoring_by_id(tailoring_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM tailoring_history WHERE id = ?", (tailoring_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    d = dict(row)
    d["sections_modified"] = json.loads(d["sections_modified"]) if d["sections_modified"] else []
    return d


async def delete_tailoring(tailoring_id: int):
    db = await get_db()
    await db.execute("DELETE FROM tailoring_history WHERE id = ?", (tailoring_id,))
    await db.commit()
```

---

## Task 6: Agent Bus + All Agents

**Files:**
- Create: `godcv/backend/agents/bus.py`
- Create: `godcv/backend/agents/orchestrator.py`
- Create: `godcv/backend/agents/summary.py`
- Create: `godcv/backend/agents/skills.py`
- Create: `godcv/backend/agents/experience.py`
- Create: `godcv/backend/agents/projects.py`
- Create: `godcv/backend/agents/profile_learner.py`

**Depends on:** Task 3 (parser), Task 4 (gemini)

- [ ] **Step 1: Create bus.py -- the agent dispatcher**

Write to `godcv/backend/agents/bus.py`:
```python
import asyncio
from typing import AsyncGenerator
from backend.agents.summary import SummaryAgent
from backend.agents.skills import SkillsAgent
from backend.agents.experience import ExperienceAgent
from backend.agents.projects import ProjectsAgent
from backend.services.gemini import GeminiClient


class AgentBus:
    """Event-driven agent dispatcher. Executes only the agents specified in the orchestrator's tool_calls."""

    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini
        self.agents = {
            "summary": SummaryAgent(gemini),
            "skills": SkillsAgent(gemini),
            "experience": ExperienceAgent(gemini),
            "projects": ProjectsAgent(gemini),
        }

    async def dispatch(
        self, tool_calls: list[dict], sections: dict, job_description: str
    ) -> AsyncGenerator[dict, None]:
        """Dispatch tool_calls to agents, yielding status events.
        Returns modified sections and experience entries via events."""

        modified_sections: dict[str, str] = {}
        modified_entries: dict[str, str] = {}

        # Group calls: parallel batch for non-experience, sequential for experience entries
        parallel_calls = []
        experience_calls = []

        for call in tool_calls:
            if call.get("action") == "keep":
                continue
            if call["agent"] == "experience":
                experience_calls.append(call)
            else:
                parallel_calls.append(call)

        # Dispatch parallel agents
        async def run_agent(call: dict):
            agent_name = call["agent"]
            agent = self.agents.get(agent_name)
            if not agent:
                return

            yield_key = agent_name
            section_content = sections.get(agent_name.capitalize(), sections.get(agent_name, ""))
            if isinstance(section_content, dict):
                section_content = section_content.get("_full", str(section_content))

            result = await agent.run(
                section_content=str(section_content),
                instructions=call.get("instructions", ""),
                job_description=job_description,
                extra=call,
            )
            return agent_name, result

        # Run parallel agents concurrently
        if parallel_calls:
            tasks = []
            for call in parallel_calls:
                agent_name = call["agent"]
                agent = self.agents.get(agent_name)
                if not agent:
                    continue

                section_key = _find_section_key(sections, agent_name)
                section_content = sections.get(section_key, "")
                if isinstance(section_content, dict):
                    section_content = section_content.get("_full", "")

                tasks.append(
                    _run_single_agent(agent, agent_name, str(section_content), call, job_description)
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    continue
                agent_name, content = r
                section_key = _find_section_key(sections, agent_name)
                modified_sections[section_key] = content

        # Run experience entries (can also be parallel)
        if experience_calls:
            exp_section = sections.get("Experience", {})
            entries = exp_section.get("_entries", []) if isinstance(exp_section, dict) else []
            entry_map = {e["key"]: e for e in entries}

            exp_tasks = []
            exp_agent = self.agents["experience"]
            for call in experience_calls:
                entry_key = call.get("entry", "")
                entry = entry_map.get(entry_key)
                if not entry:
                    # Try fuzzy match
                    for k, v in entry_map.items():
                        if entry_key.lower() in k.lower() or k.lower() in entry_key.lower():
                            entry = v
                            entry_key = k
                            break
                if not entry:
                    continue

                exp_tasks.append(
                    _run_single_agent(
                        exp_agent,
                        f"experience:{entry_key}",
                        entry["content"],
                        call,
                        job_description,
                    )
                )

            results = await asyncio.gather(*exp_tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    continue
                name, content = r
                entry_key = name.split(":", 1)[1] if ":" in name else name
                modified_entries[entry_key] = content

        yield {
            "modified_sections": modified_sections,
            "modified_entries": modified_entries,
        }


def _find_section_key(sections: dict, agent_name: str) -> str:
    """Find the actual section key matching an agent name (case-insensitive)."""
    for key in sections:
        if key.lower() == agent_name.lower():
            return key
    return agent_name.capitalize()


async def _run_single_agent(agent, name: str, content: str, call: dict, jd: str) -> tuple[str, str]:
    result = await agent.run(
        section_content=content,
        instructions=call.get("instructions", ""),
        job_description=jd,
        extra=call,
    )
    return name, result
```

- [ ] **Step 2: Create orchestrator.py**

Write to `godcv/backend/agents/orchestrator.py`:
```python
from backend.services.gemini import GeminiClient


class OrchestratorAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def analyze(
        self,
        resume_markdown: str,
        job_description: str,
        role_insights: list[dict] | None = None,
    ) -> dict:
        """Analyze job description against resume and produce a tool_calls plan."""
        insights_context = ""
        if role_insights:
            insights_context = "\nPROFILE INSIGHTS FROM PAST TAILORINGS:\n"
            for insight in role_insights:
                insights_context += (
                    f"- Role type '{insight['role_type']}' (tailored {insight['tailoring_count']}x): "
                    f"strongest points: {', '.join(insight.get('strongest_points', [])[:5])}\n"
                )

        prompt = f"""You are a resume tailoring orchestrator. Analyze the job description and the resume below.
Decide which resume sections need modification and which should stay unchanged.

For each section that needs changes, specify what agent should handle it and what instructions to give.

IMPORTANT RULES:
- Frontmatter (between --- markers at the top) is NEVER modified
- Education and Volunteering sections are almost always kept unchanged
- Only modify sections where the job description demands different emphasis
- For Experience, decide PER ENTRY whether to modify or keep
- Preserve the user's truthful experience -- only change wording and emphasis, never fabricate

AVAILABLE AGENTS AND ACTIONS:
- agent: "summary", action: "rewrite" -- rewrite the summary to match job requirements
- agent: "skills", action: "reorder" -- reorder and emphasize relevant skills (with promote/demote lists)
- agent: "experience", entry: "<CompanyKey>", action: "rewrite"|"keep" -- per job entry
- agent: "projects", action: "reorder" -- reorder projects by relevance to job
{insights_context}
RESUME:
{resume_markdown}

JOB DESCRIPTION:
{job_description}

Respond with a JSON object with this exact structure:
{{
  "analysis": {{
    "role_type": "<category like ai_ml, backend, data_eng, frontend, devops, leadership>",
    "key_requirements": ["<top 5-8 requirements from JD>"],
    "matched_strengths": ["<user's existing strengths that match>"]
  }},
  "tool_calls": [
    {{"agent": "<agent_name>", "action": "<rewrite|reorder|keep>", "entry": "<for experience only>", "instructions": "<specific instructions>", "promote": ["<for reorder>"], "demote": ["<for reorder>"]}}
  ],
  "sections_unchanged": ["<section names to keep verbatim>"]
}}"""

        return await self.gemini.generate_json(prompt)
```

- [ ] **Step 3: Create section agents -- summary.py**

Write to `godcv/backend/agents/summary.py`:
```python
from backend.services.gemini import GeminiClient


class SummaryAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        prompt = f"""You are a resume summary writer. Rewrite ONLY this summary section to better match the job description.

RULES:
- Keep it to 2-3 sentences maximum
- Maintain truthfulness -- only emphasize existing skills/experience
- Use keywords from the job description naturally
- Keep the same professional tone
- Return ONLY the rewritten summary text, no headers, no extra text

SPECIFIC INSTRUCTIONS: {instructions}

ORIGINAL SUMMARY:
{section_content}

JOB DESCRIPTION:
{job_description}

Rewritten summary:"""
        return await self.gemini.generate(prompt)
```

- [ ] **Step 4: Create skills.py**

Write to `godcv/backend/agents/skills.py`:
```python
from backend.services.gemini import GeminiClient


class SkillsAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        promote = extra.get("promote", []) if extra else []
        demote = extra.get("demote", []) if extra else []

        prompt = f"""You are a resume skills section optimizer. Reorder and adjust this skills section to better match the job description.

RULES:
- Keep ALL existing skills -- do not remove any
- Reorder categories and skills within categories to put most relevant first
- You may add 1-2 skills from the JD if the candidate likely has them based on their experience
- Do NOT fabricate skills the candidate doesn't have
- Maintain the exact markdown formatting (bold category headers, comma-separated skills)
- Return ONLY the skills section content, no section header

SKILLS TO PROMOTE (put first): {', '.join(promote) if promote else 'Use your judgment'}
SKILLS TO DEMOTE (put later): {', '.join(demote) if demote else 'None'}

ORIGINAL SKILLS:
{section_content}

JOB DESCRIPTION:
{job_description}

Reordered skills section:"""
        return await self.gemini.generate(prompt)
```

- [ ] **Step 5: Create experience.py**

Write to `godcv/backend/agents/experience.py`:
```python
from backend.services.gemini import GeminiClient


class ExperienceAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        prompt = f"""You are a resume experience bullet point writer. Rewrite ONLY this single job entry to better match the job description.

RULES:
- Keep the exact same job title, company name, and dates line (first bold line) UNCHANGED
- Only modify the bullet points below the title line
- Maintain truthfulness -- reword to emphasize relevant aspects, don't fabricate
- Use action verbs and keywords from the job description
- Keep quantified achievements (numbers, percentages) -- they are real
- Return the COMPLETE entry (title line + bullets), no section header
- Keep 2-4 bullet points per entry

SPECIFIC INSTRUCTIONS: {instructions}

ORIGINAL ENTRY:
{section_content}

JOB DESCRIPTION:
{job_description}

Rewritten entry:"""
        return await self.gemini.generate(prompt)
```

- [ ] **Step 6: Create projects.py**

Write to `godcv/backend/agents/projects.py`:
```python
from backend.services.gemini import GeminiClient


class ProjectsAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, section_content: str, instructions: str,
                  job_description: str, extra: dict = None) -> str:
        promote = extra.get("promote", []) if extra else []

        prompt = f"""You are a resume projects section optimizer. Reorder and adjust this projects section to better match the job description.

RULES:
- Keep ALL existing projects
- Reorder to put most relevant projects first
- You may slightly adjust bullet point wording to emphasize relevant aspects
- Keep project names, links, and tech stacks accurate
- Maintain the exact markdown formatting
- Return ONLY the projects content, no section header

PROJECTS TO PROMOTE (put first): {', '.join(promote) if promote else 'Use your judgment based on JD'}

ORIGINAL PROJECTS:
{section_content}

JOB DESCRIPTION:
{job_description}

Reordered projects section:"""
        return await self.gemini.generate(prompt)
```

- [ ] **Step 7: Create profile_learner.py**

Write to `godcv/backend/agents/profile_learner.py`:
```python
from backend.services.gemini import GeminiClient


class ProfileLearnerAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def learn(
        self,
        original_resume: str,
        tailored_resume: str,
        job_description: str,
        orchestrator_plan: dict,
    ) -> dict:
        """Extract learning insights from a tailoring session."""
        role_type = orchestrator_plan.get("analysis", {}).get("role_type", "general")

        prompt = f"""Analyze this resume tailoring session and extract key insights.

ORCHESTRATOR PLAN:
Role type: {role_type}
Key requirements: {orchestrator_plan.get('analysis', {}).get('key_requirements', [])}

ORIGINAL RESUME (abbreviated):
{original_resume[:2000]}

TAILORED RESUME (abbreviated):
{tailored_resume[:2000]}

JOB DESCRIPTION (abbreviated):
{job_description[:1000]}

Return a JSON object:
{{
  "role_type": "{role_type}",
  "strongest_points": ["<top 5 talking points that were most effective for this role type>"],
  "preferred_skill_order": ["<top 10 skills in order of importance for this role type>"],
  "sections_modified": ["<list of section names that were modified>"],
  "job_title": "<extracted job title from JD or null>",
  "company": "<extracted company name from JD or null>"
}}"""

        return await self.gemini.generate_json(prompt)
```

---

## Task 7: API Routers + FastAPI Main App

**Files:**
- Create: `godcv/backend/routers/profile.py`
- Create: `godcv/backend/routers/tailor.py`
- Create: `godcv/backend/routers/jobs.py`
- Create: `godcv/backend/routers/export.py`
- Create: `godcv/backend/main.py`

**Depends on:** Task 5 (profile service), Task 6 (agents)

- [ ] **Step 1: Create profile router**

Write to `godcv/backend/routers/profile.py`:
```python
from fastapi import APIRouter, HTTPException
from backend.db.models import ProfileCreate, ProfileUpdate, ProfileResponse
from backend.services import profile as profile_service

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
async def get_profile():
    p = await profile_service.get_profile()
    if not p:
        raise HTTPException(status_code=404, detail="No profile found. Create one first.")
    return p


@router.post("")
async def create_profile(data: ProfileCreate):
    p = await profile_service.create_profile(
        name=data.name,
        master_resume=data.master_resume,
        gemini_api_key=data.gemini_api_key,
    )
    return p


@router.put("")
async def update_profile(data: ProfileUpdate):
    p = await profile_service.get_profile()
    if not p:
        raise HTTPException(status_code=404, detail="No profile found.")
    updated = await profile_service.update_profile(p["id"], **data.model_dump(exclude_none=True))
    return updated


@router.get("/insights")
async def get_insights():
    p = await profile_service.get_profile()
    if not p:
        return []
    return await profile_service.get_role_insights(p["id"])


@router.delete("/insights/{insight_id}")
async def delete_insight(insight_id: int):
    await profile_service.delete_role_insight(insight_id)
    return {"ok": True}
```

- [ ] **Step 2: Create tailor router with SSE**

Write to `godcv/backend/routers/tailor.py`:
```python
import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.db.models import TailorRequest
from backend.services import profile as profile_service
from backend.services.parser import parse_resume
from backend.services.assembler import assemble_resume
from backend.services.gemini import GeminiClient
from backend.agents.orchestrator import OrchestratorAgent
from backend.agents.bus import AgentBus
from backend.agents.profile_learner import ProfileLearnerAgent
from backend.config import GEMINI_API_KEY

router = APIRouter(prefix="/api/tailor", tags=["tailor"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("")
async def tailor_resume(request: TailorRequest):
    # Resolve API key
    api_key = request.gemini_api_key or ""
    profile = await profile_service.get_profile()
    if not api_key and profile:
        api_key = profile.get("gemini_api_key", "")
    if not api_key:
        api_key = GEMINI_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="No Gemini API key configured.")

    # Resolve resume
    resume_md = request.resume_override
    if not resume_md and profile:
        resume_md = profile.get("master_resume", "")
    if not resume_md:
        raise HTTPException(status_code=400, detail="No resume available. Create a profile or provide resume_override.")

    job_description = request.job_description
    profile_id = profile["id"] if profile else None

    async def event_stream():
        try:
            gemini = GeminiClient(api_key)

            # Phase 1: Orchestrator
            yield _sse_event("status", {"phase": "orchestrator", "message": "Analyzing job requirements..."})

            orchestrator = OrchestratorAgent(gemini)
            insights = []
            if profile_id:
                insights = await profile_service.get_role_insights(profile_id)

            plan = await orchestrator.analyze(resume_md, job_description, insights)
            tool_calls = plan.get("tool_calls", [])
            sections_unchanged = plan.get("sections_unchanged", [])

            yield _sse_event("plan", {
                "analysis": plan.get("analysis", {}),
                "tool_calls": tool_calls,
                "sections_unchanged": sections_unchanged,
            })

            # Phase 2: Parse resume
            parsed = parse_resume(resume_md)

            # Phase 3: Dispatch agents
            active_calls = [c for c in tool_calls if c.get("action") != "keep"]
            for call in active_calls:
                agent_name = call["agent"]
                entry = call.get("entry", "")
                label = f"{agent_name}:{entry}" if entry else agent_name
                yield _sse_event("agent_start", {"agent": label})

            bus = AgentBus(gemini)
            result = None
            async for event in bus.dispatch(tool_calls, parsed["sections"], job_description):
                result = event

            # Emit agent_done events
            if result:
                for key in result.get("modified_sections", {}):
                    preview = result["modified_sections"][key][:100]
                    yield _sse_event("agent_done", {"agent": key.lower(), "preview": preview})
                for key in result.get("modified_entries", {}):
                    preview = result["modified_entries"][key][:100]
                    yield _sse_event("agent_done", {"agent": f"experience:{key}", "preview": preview})

            # Phase 4: Assembly
            yield _sse_event("assembly", {"message": "Assembling final resume..."})

            modified_sections = result["modified_sections"] if result else {}
            modified_entries = result["modified_entries"] if result else {}
            tailored_md = assemble_resume(parsed, modified_sections, modified_entries)

            sections_modified = list(modified_sections.keys()) + [f"experience:{k}" for k in modified_entries]

            yield _sse_event("complete", {
                "markdown": tailored_md,
                "sections_modified": len(sections_modified),
                "sections_kept": len(sections_unchanged),
            })

            # Phase 5: Learn (async, don't block response)
            if profile_id:
                try:
                    learner = ProfileLearnerAgent(gemini)
                    learning = await learner.learn(resume_md, tailored_md, job_description, plan)

                    await profile_service.upsert_role_insight(
                        profile_id=profile_id,
                        role_type=learning.get("role_type", "general"),
                        strongest_points=learning.get("strongest_points", []),
                        preferred_skill_order=learning.get("preferred_skill_order", []),
                        modified_sections=learning.get("sections_modified", []),
                    )

                    await profile_service.save_tailoring(
                        profile_id=profile_id,
                        job_title=learning.get("job_title"),
                        company=learning.get("company"),
                        job_description=job_description,
                        original_resume=resume_md,
                        tailored_resume=tailored_md,
                        orchestrator_plan=plan,
                        role_type=learning.get("role_type"),
                        sections_modified=sections_modified,
                    )
                except Exception as e:
                    yield _sse_event("error", {"message": f"Learning failed (resume still tailored): {str(e)}"})

        except Exception as e:
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 3: Create jobs router**

Write to `godcv/backend/routers/jobs.py`:
```python
from fastapi import APIRouter, HTTPException
from backend.services import profile as profile_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
async def list_jobs(limit: int = 20):
    profile = await profile_service.get_profile()
    if not profile:
        return []
    return await profile_service.get_tailoring_history(profile["id"], limit)


@router.get("/{job_id}")
async def get_job(job_id: int):
    job = await profile_service.get_tailoring_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Tailoring not found.")
    return job


@router.delete("/{job_id}")
async def delete_job(job_id: int):
    await profile_service.delete_tailoring(job_id)
    return {"ok": True}
```

- [ ] **Step 4: Create export router**

Write to `godcv/backend/routers/export.py`:
```python
import io
import markdown
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.db.models import ExportRequest

router = APIRouter(prefix="/api/export", tags=["export"])

CSS = """
@page { size: A4; margin: 8mm; }
body { font-family: Georgia, "Times New Roman", serif; font-size: 11px; line-height: 1.4; color: #111; }
h1 { font-size: 1.15rem; font-weight: 800; margin: 0.5rem 0 0.3rem; }
h2 { font-size: 1.05rem; font-weight: 800; margin: 0.5rem 0 0.3rem; }
h3 { font-size: 0.95rem; font-weight: 700; margin: 0.5rem 0 0.3rem; }
p { margin: 0.2rem 0; }
ul, ol { margin: 0.2rem 0 0.2rem 1.1rem; }
li { margin: 0.1rem 0; }
a { color: #0066cc; }
strong { font-weight: 700; }
hr { border: 0; border-top: 1px solid #bbb; margin: 0.3rem 0; }
"""


@router.post("/pdf")
async def export_pdf(request: ExportRequest):
    try:
        from weasyprint import HTML
        html_content = markdown.markdown(request.markdown, extensions=["tables", "fenced_code"])
        full_html = f"<html><head><style>{CSS}</style></head><body>{html_content}</body></html>"
        pdf_bytes = HTML(string=full_html).write_pdf()
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=resume.pdf"},
        )
    except ImportError:
        from fastapi import HTTPException
        raise HTTPException(status_code=501, detail="WeasyPrint not installed. Use browser print instead.")
```

- [ ] **Step 5: Create main.py**

Write to `godcv/backend/main.py`:
```python
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.db.database import get_db, close_db
from backend.routers import profile, tailor, jobs, export
from backend.config import FRONTEND_DIST


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_db()
    yield
    await close_db()


app = FastAPI(title="GodCV", version="1.0.0", lifespan=lifespan)

# CORS for dev mode
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(profile.router)
app.include_router(tailor.router)
app.include_router(jobs.router)
app.include_router(export.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "godcv"}


# Serve frontend (production)
dist_path = Path(FRONTEND_DIST)
if dist_path.exists():
    app.mount("/assets", StaticFiles(directory=str(dist_path / "assets")), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = dist_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_path / "index.html")
```

- [ ] **Step 6: Test backend starts**

```bash
cd /Users/naresh/Documents/resume_editor/godcv
source venv/bin/activate
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 9000 --reload &
sleep 2
curl http://localhost:9000/api/health
kill %1
```
Expected: `{"status":"ok","app":"godcv"}`

---

## Task 8: Vue 3 Frontend Scaffold

**Files:**
- Create: Vue project in `godcv/frontend/`

- [ ] **Step 1: Scaffold Vue project**

```bash
cd /Users/naresh/Documents/resume_editor/godcv
npm create vite@latest frontend -- --template vue-ts
cd frontend
npm install
npm install vue-router@4 pinia marked @types/marked
```

- [ ] **Step 2: Create vite.config.ts with proxy**

Write to `godcv/frontend/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:9000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: Create router.ts**

Write to `godcv/frontend/src/router.ts`:
```typescript
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', component: () => import('./views/EditorView.vue') },
  { path: '/profile', component: () => import('./views/ProfileView.vue') },
  { path: '/history', component: () => import('./views/HistoryView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
```

- [ ] **Step 4: Create main.ts**

Write to `godcv/frontend/src/main.ts`:
```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './style.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

- [ ] **Step 5: Create App.vue**

Write to `godcv/frontend/src/App.vue`:
```vue
<script setup lang="ts">
import { RouterView, RouterLink } from 'vue-router'
</script>

<template>
  <div class="app">
    <nav class="nav">
      <div class="nav-brand">GodCV</div>
      <div class="nav-links">
        <RouterLink to="/" class="nav-link">Editor</RouterLink>
        <RouterLink to="/profile" class="nav-link">Profile</RouterLink>
        <RouterLink to="/history" class="nav-link">History</RouterLink>
      </div>
    </nav>
    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app { min-height: 100vh; background: #f5f5f5; }
.nav {
  display: flex; align-items: center; gap: 24px;
  padding: 10px 24px; background: #111; color: #fff;
}
.nav-brand { font-weight: 800; font-size: 1.2rem; letter-spacing: 1px; }
.nav-links { display: flex; gap: 16px; }
.nav-link {
  color: #aaa; text-decoration: none; font-weight: 500;
  padding: 4px 8px; border-radius: 6px; transition: all 0.2s;
}
.nav-link:hover, .nav-link.router-link-active { color: #fff; background: #333; }
.main { padding: 18px; }
</style>
```

- [ ] **Step 6: Create global style.css**

Write to `godcv/frontend/src/style.css`:
```css
:root {
  --page-w: 210mm;
  --page-h: 297mm;
  --page-margin: 8mm;
  --base-font-size: 11px;
  --line-height: 1.4;
  --text-color: #111;
  --subtle: #666;
  --rule: #bbb;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

/* A4 Sheet Preview */
.sheet {
  width: var(--page-w); height: var(--page-h);
  background: white; box-shadow: 0 6px 20px rgba(0,0,0,.18);
  padding: var(--page-margin); overflow: hidden; position: relative;
}
.sheet-content {
  font-family: Georgia, "Times New Roman", serif;
  font-size: var(--base-font-size); height: 100%;
  overflow: auto; padding-right: 1px; color: var(--text-color);
  line-height: var(--line-height);
}

/* Resume rendered styles */
.sheet-content .cv-head { margin-bottom: 0.3rem; }
.sheet-content .name { font-size: 2.3rem; font-weight: 800; line-height: 1.05; }
.sheet-content .role { font-weight: 600; margin: .15rem 0; }
.sheet-content .meta { color: var(--subtle); font-size: .95em; }
.sheet-content .meta a { color: #0066cc; text-decoration: none; border-bottom: 1px solid rgba(0,0,0,.12); }
.sheet-content hr.thin { border: 0; border-top: 1px solid var(--rule); margin: 0.3rem 0; }

.sheet-content h1 { font-size: 1.15rem; font-weight: 800; margin: .5rem 0 .3rem; }
.sheet-content h2 { font-size: 1.05rem; font-weight: 800; margin: .5rem 0 .3rem; }
.sheet-content h3 { font-size: .95rem; font-weight: 700; margin: .5rem 0 .3rem; }
.sheet-content p { margin: .2rem 0; line-height: var(--line-height); }
.sheet-content ul, .sheet-content ol { margin: .2rem 0 .2rem 1.1rem; line-height: var(--line-height); }
.sheet-content li { margin: .1rem 0; line-height: var(--line-height); }
.sheet-content strong { font-weight: 700; }
.sheet-content a { color: #0066cc; text-decoration: underline; }

.sheet-content p strong + em { float: right; font-style: italic; margin-left: 1rem; white-space: nowrap; }
.sheet-content p:after { content: ""; display: table; clear: both; }

/* Warning */
.warn {
  position: absolute; right: 8px; bottom: 6px;
  background: #ffe8c2; border: 1px solid #f0c36c; color: #7a4e00;
  font-size: .9em; padding: 4px 8px; border-radius: 8px; display: none;
}

/* Print */
@page { size: A4; margin: 3mm; }
@media print {
  body { background: white; margin: 0; }
  .nav, .panel, .sidebar { display: none !important; }
  .sheet { box-shadow: none !important; margin: 0; padding: 3mm !important; width: 100% !important; }
  .sheet-content { overflow: visible !important; height: auto !important; font-size: 11px !important; }
  .warn { display: none !important; }
}
```

---

## Task 9: Vue Components + Views

**Files:**
- Create: `godcv/frontend/src/stores/editor.ts`
- Create: `godcv/frontend/src/composables/useProfile.ts`
- Create: `godcv/frontend/src/composables/useTailor.ts`
- Create: `godcv/frontend/src/composables/useMarkdown.ts`
- Create: `godcv/frontend/src/components/MarkdownEditor.vue`
- Create: `godcv/frontend/src/components/ResumePreview.vue`
- Create: `godcv/frontend/src/components/AgentProgress.vue`
- Create: `godcv/frontend/src/components/JobInput.vue`
- Create: `godcv/frontend/src/views/EditorView.vue`
- Create: `godcv/frontend/src/views/ProfileView.vue`
- Create: `godcv/frontend/src/views/HistoryView.vue`

**Depends on:** Task 8

- [ ] **Step 1: Create Pinia store**

Write to `godcv/frontend/src/stores/editor.ts`:
```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ToolCall {
  agent: string
  action: string
  entry?: string
  instructions?: string
  promote?: string[]
  demote?: string[]
}

export interface Profile {
  id: number
  name: string
  master_resume: string
  gemini_api_key: string
}

export const useEditorStore = defineStore('editor', () => {
  const markdown = ref('')
  const profile = ref<Profile | null>(null)
  const tailoringStatus = ref<'idle' | 'running' | 'done' | 'error'>('idle')
  const tailoringPlan = ref<ToolCall[] | null>(null)
  const agentStatuses = ref<Record<string, 'pending' | 'running' | 'done'>>({})
  const tailoringResult = ref<string | null>(null)
  const error = ref<string | null>(null)

  function resetTailoring() {
    tailoringStatus.value = 'idle'
    tailoringPlan.value = null
    agentStatuses.value = {}
    tailoringResult.value = null
    error.value = null
  }

  return {
    markdown, profile,
    tailoringStatus, tailoringPlan, agentStatuses, tailoringResult, error,
    resetTailoring,
  }
})
```

- [ ] **Step 2: Create composables**

Write to `godcv/frontend/src/composables/useProfile.ts`:
```typescript
import { ref } from 'vue'
import type { Profile } from '../stores/editor'

export function useProfile() {
  const loading = ref(false)

  async function fetchProfile(): Promise<Profile | null> {
    try {
      const res = await fetch('/api/profile')
      if (res.status === 404) return null
      return await res.json()
    } catch { return null }
  }

  async function createProfile(name: string, masterResume: string, apiKey: string = ''): Promise<Profile> {
    const res = await fetch('/api/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, master_resume: masterResume, gemini_api_key: apiKey }),
    })
    return res.json()
  }

  async function updateProfile(data: Partial<{ name: string; master_resume: string; gemini_api_key: string }>): Promise<Profile> {
    const res = await fetch('/api/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return res.json()
  }

  async function fetchInsights() {
    const res = await fetch('/api/profile/insights')
    return res.json()
  }

  async function deleteInsight(id: number) {
    await fetch(`/api/profile/insights/${id}`, { method: 'DELETE' })
  }

  return { loading, fetchProfile, createProfile, updateProfile, fetchInsights, deleteInsight }
}
```

Write to `godcv/frontend/src/composables/useTailor.ts`:
```typescript
import { useEditorStore } from '../stores/editor'

export function useTailor() {
  const store = useEditorStore()

  function startTailoring(jobDescription: string, apiKey?: string, resumeOverride?: string) {
    store.resetTailoring()
    store.tailoringStatus = 'running'

    const body: Record<string, string> = { job_description: jobDescription }
    if (apiKey) body.gemini_api_key = apiKey
    if (resumeOverride) body.resume_override = resumeOverride

    fetch('/api/tailor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(async (response) => {
      const reader = response.body?.getReader()
      if (!reader) return
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let eventType = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ') && eventType) {
            try {
              const data = JSON.parse(line.slice(6))
              handleEvent(eventType, data)
            } catch {}
            eventType = ''
          }
        }
      }
    }).catch((err) => {
      store.tailoringStatus = 'error'
      store.error = err.message
    })
  }

  function handleEvent(event: string, data: Record<string, unknown>) {
    switch (event) {
      case 'plan':
        store.tailoringPlan = data.tool_calls as any[]
        for (const call of store.tailoringPlan || []) {
          const key = call.entry ? `${call.agent}:${call.entry}` : call.agent
          store.agentStatuses[key] = call.action === 'keep' ? 'done' : 'pending'
        }
        break
      case 'agent_start':
        store.agentStatuses[data.agent as string] = 'running'
        break
      case 'agent_done':
        store.agentStatuses[data.agent as string] = 'done'
        break
      case 'complete':
        store.tailoringStatus = 'done'
        store.tailoringResult = data.markdown as string
        store.markdown = data.markdown as string
        break
      case 'error':
        store.tailoringStatus = 'error'
        store.error = data.message as string
        break
    }
  }

  return { startTailoring }
}
```

Write to `godcv/frontend/src/composables/useMarkdown.ts`:
```typescript
import { marked } from 'marked'

marked.setOptions({ gfm: true, breaks: false })

export function useMarkdown() {
  function parseFrontmatter(md: string): { data: Record<string, string>; body: string } {
    const match = md.match(/^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)/)
    if (!match) return { data: {}, body: md }
    const raw = match[1]
    const data: Record<string, string> = {}
    for (const line of raw.split('\n')) {
      const kv = line.match(/^\s*([A-Za-z0-9_]+)\s*:\s*(.*)\s*$/)
      if (kv) {
        const val = kv[2].trim().replace(/^["'](.*)["']$/, '$1')
        if (!kv[1].startsWith('#')) data[kv[1]] = val
      }
    }
    return { data, body: match[2] }
  }

  function escapeHtml(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
  }

  function buildHeader(data: Record<string, string>): string {
    const safe = (x?: string) => x ? escapeHtml(x) : ''
    const linkify = (v: string) => /^https?:\/\//i.test(v) ? v : 'https://' + v.replace(/^\/+/, '')
    const parts: string[] = []
    if (data.name) parts.push(`<div class="name">${safe(data.name)}</div>`)
    if (data.title) parts.push(`<div class="role">${safe(data.title)}</div>`)
    const meta: string[] = []
    if (data.email) meta.push(`<a href="mailto:${safe(data.email)}">${safe(data.email)}</a>`)
    if (data.phone) meta.push(`<a href="tel:${safe(data.phone)}">${safe(data.phone)}</a>`)
    for (const key of ['portfolio', 'github', 'linkedin']) {
      if (data[key]) meta.push(`<a href="${linkify(data[key])}" target="_blank" rel="noopener">${safe(data[key])}</a>`)
    }
    if (meta.length) parts.push(`<div class="meta">${meta.join(' &middot; ')}</div>`)
    return parts.length ? `<header class="cv-head">${parts.join('')}<hr class="thin"/></header>` : ''
  }

  function renderResume(md: string): string {
    const { data, body } = parseFrontmatter(md)
    const header = Object.keys(data).length ? buildHeader(data) : ''
    const bodyHtml = marked.parse(body) as string
    return `${header}<div class="md">${bodyHtml}</div>`
  }

  return { renderResume, parseFrontmatter }
}
```

- [ ] **Step 3: Create components**

Write to `godcv/frontend/src/components/MarkdownEditor.vue`:
```vue
<script setup lang="ts">
const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLTextAreaElement).value)
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  const file = e.dataTransfer?.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => emit('update:modelValue', reader.result as string)
  reader.readAsText(file)
}
</script>

<template>
  <textarea
    class="md-editor"
    :value="modelValue"
    @input="onInput"
    @drop.prevent="onDrop"
    @dragover.prevent
    placeholder="Paste or type Markdown here... (drag & drop .md files supported)"
  />
</template>

<style scoped>
.md-editor {
  width: 100%; min-height: 300px; resize: vertical;
  font: 13px/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  border: 1px dashed #b9b9b9; border-radius: 10px; padding: 10px; outline: none;
}
.md-editor:focus { border-color: #6a6a6a; }
</style>
```

Write to `godcv/frontend/src/components/ResumePreview.vue`:
```vue
<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useMarkdown } from '../composables/useMarkdown'

const props = defineProps<{ markdown: string }>()
const { renderResume } = useMarkdown()
const contentRef = ref<HTMLElement>()
const showWarn = ref(false)

watch(() => props.markdown, async () => {
  await nextTick()
  fitToOnePage()
}, { immediate: true })

function fitToOnePage() {
  const el = contentRef.value
  if (!el) return
  showWarn.value = false
  let size = 11
  const min = 8, max = 16

  document.documentElement.style.setProperty('--base-font-size', size + 'px')
  requestAnimationFrame(() => {
    let safety = 100
    while (el.scrollHeight > el.clientHeight + 1 && size > min && safety--) {
      size = Math.max(min, size - 0.15)
      document.documentElement.style.setProperty('--base-font-size', size + 'px')
    }
    if (el.scrollHeight > el.clientHeight + 1) {
      showWarn.value = true
    }
  })
}
</script>

<template>
  <section class="sheet">
    <div ref="contentRef" class="sheet-content" v-html="renderResume(markdown)" />
    <div class="warn" v-show="showWarn">Content exceeds one page at minimum size.</div>
  </section>
</template>
```

Write to `godcv/frontend/src/components/AgentProgress.vue`:
```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useEditorStore } from '../stores/editor'

const store = useEditorStore()

const agents = computed(() => {
  const entries = Object.entries(store.agentStatuses)
  return entries.map(([key, status]) => ({
    key,
    label: key.includes(':') ? key.split(':')[1] : key,
    type: key.includes(':') ? 'experience' : key,
    status,
  }))
})

const statusLabel = computed(() => {
  switch (store.tailoringStatus) {
    case 'running': return 'Tailoring in progress...'
    case 'done': return 'Tailoring complete!'
    case 'error': return 'Error: ' + (store.error || 'Unknown')
    default: return ''
  }
})
</script>

<template>
  <div v-if="store.tailoringStatus !== 'idle'" class="progress-panel">
    <div class="progress-header">
      <span class="progress-status" :class="store.tailoringStatus">{{ statusLabel }}</span>
    </div>
    <div class="agent-list">
      <div v-for="agent in agents" :key="agent.key" class="agent-item" :class="agent.status">
        <span class="agent-dot" />
        <span class="agent-name">{{ agent.label }}</span>
        <span class="agent-badge">{{ agent.status }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.progress-panel {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
  padding: 12px; margin-top: 10px;
}
.progress-header { margin-bottom: 8px; font-weight: 600; }
.progress-status.running { color: #667eea; }
.progress-status.done { color: #28a745; }
.progress-status.error { color: #dc3545; }
.agent-list { display: flex; flex-direction: column; gap: 4px; }
.agent-item {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 8px; border-radius: 6px; font-size: 0.85rem;
}
.agent-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.agent-item.pending .agent-dot { background: #ccc; }
.agent-item.running .agent-dot { background: #667eea; animation: pulse 1s infinite; }
.agent-item.done .agent-dot { background: #28a745; }
.agent-badge { margin-left: auto; font-size: 0.75rem; color: #999; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
```

Write to `godcv/frontend/src/components/JobInput.vue`:
```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useEditorStore } from '../stores/editor'
import { useTailor } from '../composables/useTailor'

const store = useEditorStore()
const { startTailoring } = useTailor()
const jobDescription = ref('')
const apiKey = ref('')

function tailor() {
  if (!jobDescription.value.trim()) return alert('Paste a job description first.')
  if (!store.markdown.trim()) return alert('Load a resume first.')
  const key = apiKey.value.trim() || store.profile?.gemini_api_key || ''
  if (!key) return alert('Enter a Gemini API key.')
  startTailoring(jobDescription.value, key, store.markdown)
}
</script>

<template>
  <div class="job-input">
    <h3>AI Resume Tailoring</h3>
    <input v-model="apiKey" type="password" placeholder="Gemini API Key (or set in Profile)" class="api-key-input" />
    <textarea v-model="jobDescription" placeholder="Paste job description here..." class="jd-input" />
    <button @click="tailor" :disabled="store.tailoringStatus === 'running'" class="tailor-btn">
      {{ store.tailoringStatus === 'running' ? 'Tailoring...' : 'Tailor Resume to Job' }}
    </button>
  </div>
</template>

<style scoped>
.job-input { display: flex; flex-direction: column; gap: 8px; }
h3 { margin: 0; font-size: 0.95rem; }
.api-key-input {
  width: 100%; padding: 8px; border: 1px solid #d0d0d0;
  border-radius: 8px; font-size: 0.85rem;
}
.jd-input {
  width: 100%; min-height: 80px; resize: vertical; padding: 8px;
  border: 1px dashed #b9b9b9; border-radius: 8px; font-size: 0.85rem;
}
.tailor-btn {
  width: 100%; padding: 10px; font-weight: 600; border-radius: 8px;
  border: none; color: white; cursor: pointer;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.tailor-btn:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
```

- [ ] **Step 4: Create views**

Write to `godcv/frontend/src/views/EditorView.vue`:
```vue
<script setup lang="ts">
import { onMounted } from 'vue'
import { useEditorStore } from '../stores/editor'
import { useProfile } from '../composables/useProfile'
import MarkdownEditor from '../components/MarkdownEditor.vue'
import ResumePreview from '../components/ResumePreview.vue'
import JobInput from '../components/JobInput.vue'
import AgentProgress from '../components/AgentProgress.vue'

const store = useEditorStore()
const { fetchProfile } = useProfile()

onMounted(async () => {
  const p = await fetchProfile()
  if (p) {
    store.profile = p
    if (!store.markdown) store.markdown = p.master_resume
  }
})

function exportPdf() { window.print() }
</script>

<template>
  <div class="editor-layout">
    <aside class="sidebar">
      <h2>GodCV Editor</h2>
      <small>Paste or drag your .md resume. AI tailors it section-by-section.</small>
      <MarkdownEditor v-model="store.markdown" />
      <div class="controls">
        <button @click="exportPdf">Print / PDF</button>
      </div>
      <JobInput />
      <AgentProgress />
    </aside>
    <ResumePreview :markdown="store.markdown" />
  </div>
</template>

<style scoped>
.editor-layout {
  display: flex; align-items: flex-start; justify-content: center;
  gap: 18px; padding: 0 18px;
}
.sidebar {
  width: min(440px, 32vw); min-width: 300px;
  position: sticky; top: 60px; align-self: flex-start;
  background: #fff; border: 1px solid #d9d9d9; border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0,0,0,.08); padding: 14px;
  display: flex; flex-direction: column; gap: 10px;
}
h2 { margin: 0; font-size: 1.05rem; }
.controls { display: flex; flex-wrap: wrap; gap: 8px; }
.controls button {
  appearance: none; border: 1px solid #c9c9c9; background: #fafafa;
  border-radius: 10px; padding: 8px 12px; cursor: pointer; font-weight: 600;
}
</style>
```

Write to `godcv/frontend/src/views/ProfileView.vue`:
```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useProfile } from '../composables/useProfile'
import { useEditorStore } from '../stores/editor'

const store = useEditorStore()
const { fetchProfile, createProfile, updateProfile, fetchInsights, deleteInsight } = useProfile()

const name = ref('')
const resume = ref('')
const apiKey = ref('')
const insights = ref<any[]>([])
const hasProfile = ref(false)
const saving = ref(false)
const msg = ref('')

onMounted(async () => {
  const p = await fetchProfile()
  if (p) {
    hasProfile.value = true
    name.value = p.name
    resume.value = p.master_resume
    apiKey.value = p.gemini_api_key || ''
    store.profile = p
    insights.value = await fetchInsights()
  }
})

async function save() {
  saving.value = true
  try {
    if (hasProfile.value) {
      const p = await updateProfile({ name: name.value, master_resume: resume.value, gemini_api_key: apiKey.value })
      store.profile = p
    } else {
      const p = await createProfile(name.value, resume.value, apiKey.value)
      store.profile = p
      hasProfile.value = true
    }
    msg.value = 'Profile saved!'
    setTimeout(() => msg.value = '', 2000)
  } finally { saving.value = false }
}

async function removeInsight(id: number) {
  await deleteInsight(id)
  insights.value = insights.value.filter(i => i.id !== id)
}
</script>

<template>
  <div class="profile-page">
    <div class="profile-form">
      <h2>{{ hasProfile ? 'Edit Profile' : 'Create Profile' }}</h2>
      <label>Name</label>
      <input v-model="name" placeholder="Your name" />
      <label>Gemini API Key</label>
      <input v-model="apiKey" type="password" placeholder="Gemini API Key" />
      <label>Master Resume (Markdown)</label>
      <textarea v-model="resume" placeholder="Paste your full resume markdown here..." rows="20" />
      <button @click="save" :disabled="saving">{{ saving ? 'Saving...' : 'Save Profile' }}</button>
      <span v-if="msg" class="msg">{{ msg }}</span>
    </div>

    <div v-if="insights.length" class="insights">
      <h3>Learned Role Insights</h3>
      <div v-for="insight in insights" :key="insight.id" class="insight-card">
        <div class="insight-header">
          <strong>{{ insight.role_type }}</strong>
          <span class="count">{{ insight.tailoring_count }}x tailored</span>
          <button class="delete-btn" @click="removeInsight(insight.id)">Remove</button>
        </div>
        <div class="insight-body">
          <div v-if="insight.strongest_points?.length">
            <small>Strongest points:</small>
            <ul><li v-for="p in insight.strongest_points" :key="p">{{ p }}</li></ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-page { max-width: 800px; margin: 0 auto; }
.profile-form {
  background: #fff; padding: 20px; border-radius: 12px;
  border: 1px solid #d9d9d9; display: flex; flex-direction: column; gap: 8px;
}
.profile-form label { font-weight: 600; font-size: 0.85rem; margin-top: 4px; }
.profile-form input, .profile-form textarea {
  width: 100%; padding: 8px; border: 1px solid #d0d0d0; border-radius: 8px;
  font-size: 0.9rem;
}
.profile-form textarea { font-family: ui-monospace, monospace; font-size: 0.8rem; }
.profile-form button {
  padding: 10px; font-weight: 600; border-radius: 8px;
  border: none; background: #111; color: #fff; cursor: pointer;
}
.msg { color: #28a745; font-size: 0.85rem; }
.insights { margin-top: 20px; }
.insights h3 { margin-bottom: 10px; }
.insight-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
  padding: 12px; margin-bottom: 8px;
}
.insight-header { display: flex; align-items: center; gap: 10px; }
.count { color: #666; font-size: 0.8rem; }
.delete-btn {
  margin-left: auto; font-size: 0.75rem; background: none;
  border: 1px solid #ddd; border-radius: 6px; padding: 2px 8px; cursor: pointer;
  color: #dc3545;
}
.insight-body { margin-top: 6px; font-size: 0.85rem; }
.insight-body ul { margin: 4px 0 0 16px; }
</style>
```

Write to `godcv/frontend/src/views/HistoryView.vue`:
```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'

const history = ref<any[]>([])
const selected = ref<any>(null)

onMounted(async () => {
  const res = await fetch('/api/jobs')
  history.value = await res.json()
})

async function deleteJob(id: number) {
  await fetch(`/api/jobs/${id}`, { method: 'DELETE' })
  history.value = history.value.filter(j => j.id !== id)
  if (selected.value?.id === id) selected.value = null
}
</script>

<template>
  <div class="history-page">
    <h2>Tailoring History</h2>
    <div v-if="!history.length" class="empty">No tailoring history yet.</div>
    <div v-for="job in history" :key="job.id" class="history-card" @click="selected = job">
      <div class="history-header">
        <strong>{{ job.job_title || 'Untitled' }}</strong>
        <span v-if="job.company"> at {{ job.company }}</span>
        <span class="date">{{ new Date(job.created_at).toLocaleDateString() }}</span>
        <button class="delete-btn" @click.stop="deleteJob(job.id)">Delete</button>
      </div>
      <div class="history-meta">
        <span class="badge">{{ job.role_type || 'general' }}</span>
        <span>{{ job.sections_modified?.length || 0 }} sections modified</span>
      </div>
    </div>

    <div v-if="selected" class="detail-panel">
      <h3>Tailored Resume</h3>
      <pre class="resume-preview">{{ selected.tailored_resume }}</pre>
      <button @click="selected = null" class="close-btn">Close</button>
    </div>
  </div>
</template>

<style scoped>
.history-page { max-width: 800px; margin: 0 auto; }
h2 { margin-bottom: 12px; }
.empty { color: #666; }
.history-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
  padding: 12px; margin-bottom: 8px; cursor: pointer;
}
.history-card:hover { border-color: #667eea; }
.history-header { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.date { margin-left: auto; color: #999; font-size: 0.8rem; }
.delete-btn {
  font-size: 0.75rem; background: none; border: 1px solid #ddd;
  border-radius: 6px; padding: 2px 8px; cursor: pointer; color: #dc3545;
}
.history-meta { margin-top: 4px; font-size: 0.8rem; color: #666; display: flex; gap: 10px; }
.badge {
  background: #f0f0f0; padding: 1px 8px; border-radius: 4px;
  font-size: 0.75rem; font-weight: 600;
}
.detail-panel {
  margin-top: 16px; background: #fff; border: 1px solid #d9d9d9;
  border-radius: 12px; padding: 16px;
}
.resume-preview {
  white-space: pre-wrap; font-size: 0.8rem; max-height: 400px;
  overflow-y: auto; background: #f9f9f9; padding: 10px; border-radius: 8px;
}
.close-btn {
  margin-top: 10px; padding: 6px 16px; border: 1px solid #ccc;
  border-radius: 8px; background: #fafafa; cursor: pointer;
}
</style>
```

---

## Task 10: Integration + Build + Verification

**Depends on:** Task 7 (backend), Task 9 (frontend)

- [ ] **Step 1: Build frontend**

```bash
cd /Users/naresh/Documents/resume_editor/godcv/frontend
npm run build
```

- [ ] **Step 2: Start full app on port 9000**

```bash
cd /Users/naresh/Documents/resume_editor/godcv
source venv/bin/activate
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 9000
```

- [ ] **Step 3: Verify health endpoint**

```bash
curl http://localhost:9000/api/health
```
Expected: `{"status":"ok","app":"godcv"}`

- [ ] **Step 4: Verify frontend loads at localhost:9000**

Open browser to http://localhost:9000 -- should show GodCV with nav bar and editor view.

- [ ] **Step 5: Create profile via API**

```bash
curl -X POST http://localhost:9000/api/profile \
  -H "Content-Type: application/json" \
  -d '{"name": "Naresh Jhawar", "master_resume": "'"$(cat data/sample_resume.md | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))'  | tr -d '"')"'"}'
```

- [ ] **Step 6: Verify end-to-end tailoring works**

Test with a sample job description via the UI:
1. Go to Profile, paste master resume, save
2. Go to Editor, paste a job description
3. Enter Gemini API key
4. Click "Tailor Resume to Job"
5. Watch agent progress panel light up
6. Verify tailored resume appears in editor

---
