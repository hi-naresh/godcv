# Stealth Mode, Suggestion Removal, Graduate/Non-Graduate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drop the accept/deny suggestion overlay; rename `fabrication_mode` → `stealth_mode` with a strict default and a match-first → reshape → invent hierarchy; collapse the 6-level seniority enum to a JD-driven `graduate` / `non-graduate` binary with backend-deterministic section order.

**Architecture:** Mostly deletion + rename + prompt change. One SQLite migration coerces `profiles.fabrication_mode` → `profiles.stealth_mode`. The boolean flows the same path it does today (DB row → request body → orchestrator → per-agent extra). Section order moves from LLM JSON output to a deterministic backend dict keyed on `role_level`. Two-stage Check → Tailor flow stays.

**Tech Stack:** FastAPI + aiosqlite (backend), Vue 3 + Pinia + Vitest (frontend), Gemini SDK (agent prompts). No new libraries.

**Spec:** `docs/superpowers/specs/2026-04-29-stealth-mode-and-suggestion-removal-design.md`

**Spec correction discovered during planning:** Spec mentions migrating `tailoring_history.seniority_level` — that column does not exist. Seniority is request-only / in-flight. The migration only renames `profiles.fabrication_mode` → `profiles.stealth_mode`.

---

## Task 1: DB migration — `fabrication_mode` → `stealth_mode`

**Files:**
- Modify: `backend/db/database.py`
- Modify: `backend/services/profile.py`

The `profiles` table has a `fabrication_mode INTEGER DEFAULT 0` column. We rename it in the `CREATE TABLE` block (for fresh installs) and add an idempotent rename step to the migration block (for existing DBs).

- [ ] **Step 1: Update `_init_tables` in `backend/db/database.py`**

Change the `CREATE TABLE profiles` block — replace `fabrication_mode INTEGER DEFAULT 0,` with `stealth_mode INTEGER DEFAULT 0,`:

```python
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            master_resume TEXT NOT NULL,
            parsed_sections TEXT,
            gemini_api_key TEXT DEFAULT '',
            page_mode TEXT DEFAULT 'single',
            stealth_mode INTEGER DEFAULT 0,
            max_projects INTEGER DEFAULT 4,
            max_bullets_per_entry INTEGER DEFAULT 3,
            require_quantified_bullets INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
```

- [ ] **Step 2: Replace the `fabrication_mode` migration step with a rename step**

In the migration block at the bottom of `_init_tables`, replace:

```python
    if "fabrication_mode" not in columns:
        await db.execute("ALTER TABLE profiles ADD COLUMN fabrication_mode INTEGER DEFAULT 0")
        await db.commit()
```

with:

```python
    # Rename fabrication_mode → stealth_mode (idempotent)
    if "fabrication_mode" in columns and "stealth_mode" not in columns:
        await db.execute("ALTER TABLE profiles RENAME COLUMN fabrication_mode TO stealth_mode")
        await db.commit()
    elif "stealth_mode" not in columns:
        # Fresh DB path didn't run for some reason — add the column
        await db.execute("ALTER TABLE profiles ADD COLUMN stealth_mode INTEGER DEFAULT 0")
        await db.commit()
```

- [ ] **Step 3: Update `backend/services/profile.py`**

Three changes in this file:

1. Replace the `BOOL_KEYS` tuple and the column list in `update_profile`:

```python
    BOOL_KEYS = ("stealth_mode", "require_quantified_bullets")
    for key in ("name", "master_resume", "gemini_api_key", "page_mode", "stealth_mode",
                "max_projects", "max_bullets_per_entry", "require_quantified_bullets"):
```

2. Update `create_profile` signature and body — `fabrication_mode` → `stealth_mode`:

```python
async def create_profile(
    name: str, master_resume: str, gemini_api_key: str = "", page_mode: str = "single",
    stealth_mode: bool = False, max_projects: int = 4,
    max_bullets_per_entry: int = 3, require_quantified_bullets: bool = True,
) -> dict:
    db = await get_db()
    parsed = parse_resume(master_resume)
    parsed_json = json.dumps({
        "sections": {k: v if not isinstance(v, dict) else v.get("_full", str(v))
                     for k, v in parsed["sections"].items()},
        "separators": parsed["separators"],
    })
    cursor = await db.execute(
        "INSERT INTO profiles (name, master_resume, parsed_sections, gemini_api_key, page_mode, stealth_mode, max_projects, max_bullets_per_entry, require_quantified_bullets) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (name, master_resume, parsed_json, gemini_api_key, page_mode, int(bool(stealth_mode)), max_projects, max_bullets_per_entry, int(bool(require_quantified_bullets))),
    )
    await db.commit()
    return await get_profile(cursor.lastrowid)
```

- [ ] **Step 4: Verify migration runs cleanly on the existing dev DB**

Start the backend once (assumes you have a Python venv with backend deps):

```bash
cd /Users/naresh/Documents/resume_editor/godcv
python -c "import asyncio; from backend.db.database import get_db; asyncio.run(get_db())"
```

Expected: no exception. Then verify the column was renamed:

```bash
sqlite3 backend/godcv.db "PRAGMA table_info(profiles)" | grep -E "fabrication_mode|stealth_mode"
```

Expected: only `stealth_mode` appears, not `fabrication_mode`. (DB filename may differ — check `backend/config.py:DB_PATH` if the path doesn't match.)

- [ ] **Step 5: Commit**

```bash
git add backend/db/database.py backend/services/profile.py
git commit -m "refactor: rename fabrication_mode column to stealth_mode

Idempotent SQLite ALTER TABLE RENAME COLUMN; CREATE TABLE block
updated for fresh installs."
```

---

## Task 2: Pydantic models + backend route renames — `fabrication_mode` → `stealth_mode`

**Files:**
- Modify: `backend/db/models.py`
- Modify: `backend/routers/tailor.py`
- Modify: `backend/routers/profile.py` (if it touches `fabrication_mode`)

This task only renames the field at the API boundary. Per-agent prompt code keeps reading from `extra.get("fabrication_mode", ...)` until Task 9, which renames the agents file as a single coherent change.

- [ ] **Step 1: Update `backend/db/models.py`**

Add a `model_config = ConfigDict(extra="forbid")` to `TailorRequest`, `ExecuteRequest`, and `ProfileUpdate` so a stale frontend sending `fabrication_mode` or `seniority_level` gets a 422 instead of a silent default — surfaces drift instead of masking it. Add the import:

```python
from pydantic import BaseModel, ConfigDict
```

Then in each model below, add the line as shown.

Find every `fabrication_mode` and rename to `stealth_mode` in `ProfileCreate`, `ProfileUpdate`, `ProfileResponse`, `TailorRequest`, `ExecuteRequest`. Specifically:

```python
class ProfileCreate(BaseModel):
    name: str
    master_resume: str
    gemini_api_key: str = ""
    page_mode: str = "single"
    stealth_mode: bool = False
    max_projects: int = 4
    max_bullets_per_entry: int = 3
    require_quantified_bullets: bool = True


class ProfileUpdate(BaseModel):
    name: str | None = None
    master_resume: str | None = None
    gemini_api_key: str | None = None
    page_mode: str | None = None
    stealth_mode: bool | None = None
    max_projects: int | None = None
    max_bullets_per_entry: int | None = None
    require_quantified_bullets: bool | None = None


class ProfileResponse(BaseModel):
    id: int
    name: str
    master_resume: str
    gemini_api_key: str
    page_mode: str
    stealth_mode: bool
    max_projects: int
    max_bullets_per_entry: int
    require_quantified_bullets: bool
    created_at: str
    updated_at: str
```

For `TailorRequest` and `ExecuteRequest` — replace `fabrication_mode: bool | None = None` with `stealth_mode: bool | None = None`. Also add `model_config = ConfigDict(extra="forbid")` as the first attribute:

```python
class TailorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_description: str
    resume_override: str | None = None
    gemini_api_key: str | None = None
    role_level: str | None = None  # renamed in Task 7; for now: seniority_level
    page_mode: str = "single"
    analyze_only: bool = False
    stealth_mode: bool | None = None
    max_projects: int | None = None
    max_bullets_per_entry: int | None = None
    require_quantified_bullets: bool | None = None
```

(In this task, keep the field as `seniority_level: str | None = None`; Task 7 renames it to `role_level`. The `extra="forbid"` is what we want now so a stale tab sending `fabrication_mode` errors out rather than being silently ignored.)

Apply the same to `ExecuteRequest` and `ProfileUpdate`.

- [ ] **Step 2: Update `backend/routers/tailor.py`**

The `_resolve_tailoring_prefs` function reads `getattr(request, field, None)` for each pref name. Rename `"fabrication_mode"` to `"stealth_mode"` everywhere in this file:

```python
def _resolve_tailoring_prefs(request, profile: dict | None) -> dict:
    """Resolve stealth_mode and tailoring style prefs: request override → profile → default."""
    def _get(field: str, default):
        req_val = getattr(request, field, None)
        if req_val is not None:
            return req_val
        if profile and profile.get(field) is not None:
            val = profile.get(field)
            return bool(val) if isinstance(default, bool) else val
        return default
    return {
        "stealth_mode": _get("stealth_mode", False),
        "max_projects": _get("max_projects", 4),
        "max_bullets_per_entry": _get("max_bullets_per_entry", 3),
        "require_quantified_bullets": _get("require_quantified_bullets", True),
    }
```

Then in both `tailor_resume` and `execute_tailoring`, replace `prefs["fabrication_mode"]` and `fabrication_mode=prefs["fabrication_mode"]` with `stealth_mode` equivalents. Also rename the `fabrication_mode = prefs["fabrication_mode"]` local var in `tailor_resume` to `stealth_mode = prefs["stealth_mode"]`. The orchestrator call signature still takes `fabrication_mode=...` for now (renamed in Task 6) — adapt the kwarg name when you change the orchestrator signature.

For this task, change the call site to:

```python
            plan = await orchestrator.analyze(resume_md, job_description, insights, request.seniority_level, page_mode, entry_keys,
                                              fabrication_mode=prefs["stealth_mode"],
                                              max_projects=prefs["max_projects"])
```

(Same kwarg name, value sourced from the new pref key. Task 6 renames the kwarg.)

In the `for call in tool_calls:` block, change:

```python
                call["fabrication_mode"] = prefs["fabrication_mode"]
```

to:

```python
                call["fabrication_mode"] = prefs["stealth_mode"]
```

(Same dict key — agents still read `extra["fabrication_mode"]` until Task 9.)

The same pattern applies in `execute_tailoring`.

- [ ] **Step 3: Update `backend/routers/profile.py`** (if it forwards `fabrication_mode`)

Check the file:

```bash
grep -n "fabrication_mode" backend/routers/profile.py
```

If any line uses `fabrication_mode`, rename it to `stealth_mode`. If no hits, skip this step.

- [ ] **Step 4: Smoke test — backend imports cleanly**

```bash
cd /Users/naresh/Documents/resume_editor/godcv
python -c "from backend.routers import tailor, profile; from backend.db import models; print('ok')"
```

Expected: prints `ok`. No `AttributeError` or `ImportError`.

- [ ] **Step 5: Commit**

```bash
git add backend/db/models.py backend/routers/tailor.py backend/routers/profile.py
git commit -m "refactor: rename fabrication_mode to stealth_mode in API models

Renames at the request/response boundary. Per-agent prompt internals
still read extra['fabrication_mode'] (renamed in a later commit when
the agents file is also renamed)."
```

---

## Task 3: Delete suggestion agent + remove tailor.py phases

**Files:**
- Delete: `backend/agents/suggestion_agent.py`
- Modify: `backend/routers/tailor.py`

- [ ] **Step 1: Delete the suggestion agent file**

```bash
rm backend/agents/suggestion_agent.py
```

- [ ] **Step 2: Remove the import from `backend/routers/tailor.py`**

Delete the line:

```python
from backend.agents.suggestion_agent import SuggestionAgent
```

- [ ] **Step 3: Delete Phase 4.6 in `tailor_resume`**

Remove this entire block:

```python
            # Phase 4.6: Generate content suggestions from gaps
            gap_suggestions = plan.get("scoring", {}).get("gap_suggestions", [])
            if gap_suggestions:
                try:
                    yield _sse_event("status", {"phase": "suggestions", "message": "Generating content suggestions..."})
                    sug_agent = SuggestionAgent(gemini)
                    suggestions = await sug_agent.generate(gap_suggestions, tailored_md, job_description, resume_md, fabrication_mode=fabrication_mode)
                    if suggestions:
                        yield _sse_event("suggestions", {"items": suggestions})
                except Exception as e:
                    logger.error("Suggestion generation failed: %s", e)
```

- [ ] **Step 4: Delete Phase 5 in `execute_tailoring`**

Remove this entire block:

```python
            # Phase 5: Generate suggestions
            gap_suggestions = plan.get("scoring", {}).get("gap_suggestions", [])
            if gap_suggestions:
                try:
                    yield _sse_event("status", {"phase": "suggestions", "message": "Generating suggestions..."})
                    sug_agent = SuggestionAgent(gemini)
                    suggestions = await sug_agent.generate(gap_suggestions, tailored_md, job_description, resume_md, fabrication_mode=fabrication_mode)
                    if suggestions:
                        yield _sse_event("suggestions", {"items": suggestions})
                except Exception as e:
                    logger.error("Suggestion generation failed: %s", e)
```

- [ ] **Step 5: Verify no other Python file references SuggestionAgent or imports the deleted module**

```bash
grep -rn "suggestion_agent\|SuggestionAgent" backend/
```

Expected: no output.

- [ ] **Step 6: Smoke test**

```bash
python -c "from backend.routers.tailor import router; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 7: Commit**

```bash
git add -A backend/
git commit -m "feat: remove suggestion agent and tailor pipeline phases

The accept/deny overlay is being replaced by a deterministic ideal-CV
output. The orchestrator's gap_suggestions list is repurposed as
informational text on the verdict card; no second agent generates
content from it."
```

---

## Task 4: Frontend — remove Suggestion type, SSE handler, UI handlers

**Files:**
- Modify: `frontend/src/stores/editor.ts`
- Modify: `frontend/src/composables/useTailor.ts`
- Modify: `frontend/src/components/ResumePreview.vue`
- Modify: `frontend/src/views/EditorView.vue`
- Modify: `frontend/src/components/JobCard.vue`
- Modify: `frontend/src/components/ScorePanel.vue`
- Modify: `frontend/src/style.css`

`highlightChanges` and `extractTextLines` stay (per spec — green-pill highlighting of tailored content is kept).

- [ ] **Step 1: `frontend/src/stores/editor.ts` — drop Suggestion type and field**

Delete the `Suggestion` interface (lines ~38–46). In `JobState`, delete `suggestions: Suggestion[]`. In `addJob`'s initial state object, delete `suggestions: [],`. In `resetJobTailoring`'s update object, delete `suggestions: [],`.

After the change, `JobState` looks like:

```typescript
export interface JobState {
  id: string
  title: string
  jobDescription: string
  seniorityLevel: SeniorityLevel | null
  tailoringStatus: 'idle' | 'analyzing' | 'analyzed' | 'running' | 'done' | 'error'
  statusMessage: string | null
  tailoringPlan: ToolCall[] | null
  agentStatuses: Record<string, 'pending' | 'running' | 'done'>
  result: string | null
  error: string | null
  pageMode: 'single' | 'multi'
  analysis: JobAnalysis | null
  scoring: JobScoring | null
  atsResult: ATSResult | null
}
```

- [ ] **Step 2: `frontend/src/composables/useTailor.ts` — drop SSE handler and reset entries**

Delete the `case 'suggestions':` block:

```typescript
      case 'suggestions':
        store.updateJob(jobId, {
          suggestions: (data.items as any[]) || [],
        })
        break
```

In any object that resets job state, delete `suggestions: [],`.

- [ ] **Step 3: `frontend/src/components/ResumePreview.vue` — strip suggestion code, keep highlight**

Remove the `Suggestion` import:

```typescript
import type { Suggestion } from '../stores/editor'
```

In `defineProps`, remove `suggestions?: Suggestion[]`.

In `defineEmits`, remove `'accept-suggestion': [id: string]` and `'deny-suggestion': [id: string]`.

Delete the entire `injectSuggestion`, `escapeHtml` (only if unused after — keep if `highlightChanges` uses it), `escapeRegex`, `makeTooltip`, `handleSuggestionClick` functions. Verify `escapeHtml`/`escapeRegex` are no longer referenced before deleting them.

In `renderedHtml` computed, delete the suggestion injection block:

```typescript
  // Inject suggestion content
  if (props.suggestions?.length) {
    for (const sug of props.suggestions) {
      html = injectSuggestion(html, sug)
    }
  }
```

In `onMounted` and `onUnmounted`, delete the `addEventListener('click', handleSuggestionClick)` and matching remove call.

- [ ] **Step 4: `frontend/src/views/EditorView.vue` — drop suggestion handlers**

Delete:

```typescript
const activeSuggestions = computed(() => activeJob.value?.suggestions ?? [])
```

Delete the `acceptSuggestion` and `denySuggestion` functions (they include logic that updates `job.suggestions.filter(...)`).

In the `<ResumePreview>` template tag, remove these props/listeners:

```vue
:suggestions="activeSuggestions"
@accept-suggestion="acceptSuggestion"
@deny-suggestion="denySuggestion"
```

- [ ] **Step 5: `frontend/src/components/JobCard.vue` and `ScorePanel.vue`**

```bash
grep -n "suggestion\|Suggestion\|sug-" frontend/src/components/JobCard.vue frontend/src/components/ScorePanel.vue
```

For each hit that is *not* `gap_suggestions` (which stays — that's the orchestrator's gap analysis), delete it. The gap_suggestions display lines at JobCard.vue:84-87 and ScorePanel.vue:122-126 stay.

- [ ] **Step 6: `frontend/src/style.css` — strip suggestion selectors**

```bash
grep -n "\.suggestion\|\.sug-\|\.changed-content" frontend/src/style.css
```

Delete CSS rules whose selectors start with `.suggestion`, `.suggestion-remove`, `.suggestion-replace`, `.suggestion-project`, `.sug-tooltip`, `.sug-accept`, `.sug-deny`, `.sug-old`, `.sug-new`. Keep `.changed-content` (used by `highlightChanges`).

- [ ] **Step 7: Verify nothing remains**

```bash
grep -rn "Suggestion\|suggestions:\|suggestion-\|sug-" frontend/src --include="*.ts" --include="*.vue" --include="*.css"
```

Expected hits: only `gap_suggestions` (the gap-analysis array, which stays) and possibly `gap-suggestions` in CSS class names.

- [ ] **Step 8: Type-check and run frontend tests**

```bash
cd frontend && npx vue-tsc --noEmit
npx vitest run
```

Expected: type check passes, all tests pass.

- [ ] **Step 9: Commit**

```bash
git add -A frontend/src/
git commit -m "feat: remove suggestion overlay UI, types, and SSE handler

Keeps highlightChanges (green-pill rewrite indicator) and the
gap_suggestions list shown on the verdict card. Suggestion accept/
deny is gone from ResumePreview and EditorView."
```

---

## Task 5: Backend — `services/seniority.py` → `services/role_level.py`, binary detection

**Files:**
- Create: `backend/services/role_level.py`
- Delete: `backend/services/seniority.py`
- Create: `backend/tests/test_role_level.py`

The new function returns `'graduate' | 'non-graduate' | None`. Tests come first.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_role_level.py`:

```python
from backend.services.role_level import detect_role_level


class TestDetectRoleLevel:
    def test_graduate_keyword(self):
        assert detect_role_level("Graduate Data Engineer at Capgemini") == "graduate"

    def test_intern_keyword(self):
        assert detect_role_level("Software Engineering Intern, summer 2026") == "graduate"

    def test_junior_keyword_maps_to_graduate(self):
        assert detect_role_level("Junior Backend Developer") == "graduate"

    def test_senior_keyword(self):
        assert detect_role_level("Senior Software Engineer, 5+ years experience") == "non-graduate"

    def test_lead_keyword(self):
        assert detect_role_level("Tech Lead — Platform team") == "non-graduate"

    def test_principal_keyword(self):
        assert detect_role_level("Principal ML Engineer") == "non-graduate"

    def test_years_one(self):
        assert detect_role_level("looking for engineer with 1 year of experience") == "graduate"

    def test_years_two(self):
        assert detect_role_level("2 years of experience required") == "graduate"

    def test_years_three(self):
        assert detect_role_level("3+ years of experience in Python") == "non-graduate"

    def test_years_five(self):
        assert detect_role_level("5+ years experience required") == "non-graduate"

    def test_no_signal(self):
        assert detect_role_level("We're hiring great people who love product.") is None
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd /Users/naresh/Documents/resume_editor/godcv
python -m pytest backend/tests/test_role_level.py -v
```

Expected: `ImportError: cannot import name 'detect_role_level'` or similar — module doesn't exist yet.

- [ ] **Step 3: Create the new module**

Create `backend/services/role_level.py`:

```python
import re


def detect_role_level(job_description: str) -> str | None:
    """Detect role level from job description text.
    Returns one of: 'graduate', 'non-graduate', or None.

    'graduate' covers entry-level and junior roles (1-2 yrs typical).
    'non-graduate' covers everything mid-level and above.
    """
    text = job_description.lower()

    # Senior signals win over graduate signals when both appear
    if re.search(r"\b(principal|staff)\b", text):
        return "non-graduate"
    if re.search(r"\b(lead|head|manager)\b.*\b(engineer|developer|team)\b", text) or \
       re.search(r"\b(engineer|developer)\b.*\b(lead|head)\b", text) or \
       re.search(r"\btech(?:nical)?\s+lead\b", text) or \
       re.search(r"\blead\s+(?:software|backend|frontend|full\s*stack)\b", text):
        return "non-graduate"
    if re.search(r"\bsenior\b", text):
        return "non-graduate"
    if re.search(r"\bjunior\b", text):
        return "graduate"
    if re.search(r"\b(?:graduate|grad|entry[\s-]level|new\s+grad|intern(?:ship)?|trainee)\b", text):
        return "graduate"

    # Years of experience
    years_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)", text)
    if years_match:
        years = int(years_match.group(1))
        return "graduate" if years <= 2 else "non-graduate"

    range_match = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)", text)
    if range_match:
        upper = int(range_match.group(2))
        return "graduate" if upper <= 2 else "non-graduate"

    return None
```

- [ ] **Step 4: Run the test — should pass**

```bash
python -m pytest backend/tests/test_role_level.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Delete the old seniority module**

```bash
rm backend/services/seniority.py
```

Verify nothing imports it:

```bash
grep -rn "from backend.services.seniority\|services.seniority" backend/
```

Expected: no output. (If anything references it, that import will be fixed in Task 6 & 7.)

- [ ] **Step 6: Commit**

```bash
git add backend/services/role_level.py backend/tests/test_role_level.py
git rm backend/services/seniority.py
git commit -m "refactor: collapse seniority detection to graduate/non-graduate

Replaces 6-level enum with a JD-driven binary. The 'graduate' bucket
covers entry-level + junior + intern + ≤2 years; 'non-graduate' covers
everything mid+ and 3+ years."
```

---

## Task 6: Backend orchestrator — collapse seniority guidance, drop section_order, role_level

**Files:**
- Modify: `backend/agents/orchestrator.py`

- [ ] **Step 1: Rename signature parameter**

In `OrchestratorAgent.analyze`, rename `seniority_level: str | None = None` → `role_level: str | None = None`. Rename references in the body accordingly.

- [ ] **Step 2: Replace the `seniority_guidance` dict with the binary version**

Replace the existing block:

```python
        seniority_context = ""
        if seniority_level:
            seniority_guidance = {
                "graduate": "Target is a GRADUATE/ENTRY-LEVEL role. ...",
                ... (six entries)
            }
            seniority_context = f"\nSENIORITY CONTEXT:\n{seniority_guidance.get(seniority_level, '')}\n"
```

with:

```python
        role_level_context = ""
        if role_level:
            role_level_guidance = {
                "graduate": (
                    "Target is a GRADUATE-level role. Lead with education, coursework, "
                    "internships, and projects. Tone: capable and eager. Avoid leadership "
                    "or architectural claims."
                ),
                "non-graduate": (
                    "Target is a non-graduate professional role. Lead with experience and "
                    "impact. Show ownership, scale, and measurable outcomes appropriate to "
                    "the seniority signaled in the JD (mid-level vs senior vs lead vs principal)."
                ),
            }
            role_level_context = f"\nROLE LEVEL CONTEXT:\n{role_level_guidance.get(role_level, '')}\n"
```

- [ ] **Step 3: Drop the `order_example`/`order_rule` section-order branch**

Delete the section-order computation block:

```python
        # Determine section order example based on seniority
        if seniority_level in ("graduate", "junior"):
            order_example = '["Summary", "Education", "Skills", "Experience", "Projects", "Publications (optional)", "Volunteering and Interests"]'
            order_rule = "For graduate/junior roles: Education MUST come BEFORE Experience and Skills."
        else:
            order_example = '["Summary", "Experience", "Skills", "Education", "Projects", "Publications (optional)", "Volunteering and Interests"]'
            order_rule = "For mid-level+ roles: Experience comes first, then Skills, then Education."
```

In the prompt body, delete the `- SECTION ORDER: {order_rule}` line and the `"section_order": {order_example},` line in the JSON template.

- [ ] **Step 4: Use `role_level_context` in the prompt body**

Find the line:

```python
{insights_context}{seniority_context}
```

and replace with:

```python
{insights_context}{role_level_context}
```

- [ ] **Step 5: Update analysis JSON schema field**

In the prompt's JSON template, change:

```json
"position_level": "<graduate|junior|mid-level|senior|lead|principal>",
```

to:

```json
"role_level": "<graduate|non-graduate>",
```

Update any narrative mention of `position_level` in the prompt accordingly.

- [ ] **Step 6: Smoke test — orchestrator imports**

```bash
python -c "from backend.agents.orchestrator import OrchestratorAgent; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 7: Commit**

```bash
git add backend/agents/orchestrator.py
git commit -m "refactor: collapse orchestrator seniority guidance to graduate/non-graduate

- Parameter renamed to role_level
- 6-key seniority_guidance dict → 2-key role_level_guidance
- Drops section_order from JSON output (now backend-deterministic)
- Drops position_level field; replaced with role_level"
```

---

## Task 7: Backend `tailor.py` — request rename + deterministic section_order

**Files:**
- Modify: `backend/db/models.py`
- Modify: `backend/routers/tailor.py`
- Modify: `backend/services/assembler.py` (verify only)

- [ ] **Step 1: Rename request fields**

In `backend/db/models.py`, in `TailorRequest` and `ExecuteRequest`, rename:

```python
seniority_level: str | None = None
```

to:

```python
role_level: str | None = None
```

- [ ] **Step 2: Compute deterministic section_order in `tailor.py`**

Add this helper near the top of `backend/routers/tailor.py` (just after the `_resolve_tailoring_prefs` function):

```python
SECTION_ORDER_GRADUATE = [
    "Summary", "Education", "Skills", "Experience",
    "Projects", "Volunteering and Interests",
]
SECTION_ORDER_NON_GRADUATE = [
    "Summary", "Skills", "Experience", "Projects",
    "Education", "Volunteering and Interests",
]


def _section_order_for(role_level: str | None) -> list[str]:
    """Backend-deterministic section order. Defaults to non-graduate when
    role_level is unknown (safer for the 'ideal CV' framing)."""
    if role_level == "graduate":
        return SECTION_ORDER_GRADUATE
    return SECTION_ORDER_NON_GRADUATE
```

- [ ] **Step 3: Use it in `tailor_resume`**

Replace the orchestrator call kwarg `request.seniority_level` with `request.role_level`, and swap the `section_order = plan.get("section_order")` lookup with `section_order = _section_order_for(role_level)`. Also rename the orchestrator kwarg `fabrication_mode=` to `role_level=` where appropriate — wait, those are different.

Concretely, in `tailor_resume`:

```python
            page_mode = request.page_mode or (profile.get("page_mode", "single") if profile else "single")
            prefs = _resolve_tailoring_prefs(request, profile)
            stealth_mode = prefs["stealth_mode"]

            # Determine role_level from request, JD detection, or default
            from backend.services.role_level import detect_role_level
            role_level = request.role_level or detect_role_level(job_description)

            plan = await orchestrator.analyze(
                resume_md, job_description, insights,
                role_level=role_level, page_mode=page_mode,
                entry_keys=entry_keys,
                fabrication_mode=stealth_mode,
                max_projects=prefs["max_projects"],
            )
```

Note: `OrchestratorAgent.analyze` was renamed in Task 6 to take `role_level`; this task uses the new name. The kwarg `fabrication_mode=stealth_mode` is the temporary bridge — Task 9 renames it to `stealth_mode=` once the agents file is renamed.

Replace the section-order pull:

```python
            modified_sections = result["modified_sections"] if result else {}
            modified_entries = result["modified_entries"] if result else {}
            excluded_entries = result.get("excluded_entries", set()) if result else set()
            section_order = _section_order_for(role_level)
            tailored_md = assemble_resume(parsed, modified_sections, modified_entries, section_order, excluded_entries)
```

- [ ] **Step 4: Same change in `execute_tailoring`**

Apply the same `role_level` derivation and `_section_order_for(role_level)` call. The plan dict from the request no longer carries `section_order`; the backend regenerates it from `request.role_level`:

```python
    role_level = request.role_level
    ...
    section_order = _section_order_for(role_level)
    tailored_md = assemble_resume(parsed, modified_sections, modified_entries, section_order, excluded_entries)
```

- [ ] **Step 5: Verify `assemble_resume` accepts `section_order` as before**

```bash
grep -n "def assemble_resume" backend/services/assembler.py
```

Expected: signature includes a `section_order` parameter. No code change here, just a sanity check that the existing API matches the call sites.

- [ ] **Step 6: Smoke test**

```bash
python -c "from backend.routers.tailor import router; from backend.db.models import TailorRequest; r = TailorRequest(job_description='test', role_level='graduate'); print(r.role_level)"
```

Expected: prints `graduate`.

- [ ] **Step 7: Commit**

```bash
git add backend/db/models.py backend/routers/tailor.py
git commit -m "feat: deterministic section_order from role_level

TailorRequest/ExecuteRequest field renamed seniority_level → role_level.
Backend computes section_order from role_level via a hardcoded dict —
the orchestrator no longer chooses it.

Graduate:     Summary → Education → Skills → Experience → Projects → Volunteering
Non-graduate: Summary → Skills → Experience → Projects → Education → Volunteering"
```

---

## Task 8: Frontend — `useSeniority` → `useRoleLevel`, binary types

**Files:**
- Create: `frontend/src/composables/useRoleLevel.ts`
- Delete: `frontend/src/composables/useSeniority.ts`
- Create: `frontend/src/__tests__/useRoleLevel.test.ts`
- Delete: `frontend/src/__tests__/useSeniority.test.ts`
- Modify: `frontend/src/composables/useJobs.ts`
- Modify: `frontend/src/composables/useTailor.ts`
- Modify: `frontend/src/stores/editor.ts`
- Modify: `frontend/src/components/JobCard.vue`
- Modify: `frontend/src/views/EditorView.vue`
- Modify: `frontend/src/__tests__/useJobs.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/__tests__/useRoleLevel.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { detectRoleLevel } from '../composables/useRoleLevel'

describe('detectRoleLevel', () => {
  it('detects graduate from "Graduate Data Engineer"', () => {
    expect(detectRoleLevel('Graduate Data Engineer at Capgemini')).toBe('graduate')
  })
  it('detects graduate from intern keyword', () => {
    expect(detectRoleLevel('Summer 2026 Software Engineering Intern')).toBe('graduate')
  })
  it('maps junior to graduate', () => {
    expect(detectRoleLevel('Junior Backend Developer')).toBe('graduate')
  })
  it('detects non-graduate from senior keyword', () => {
    expect(detectRoleLevel('Senior ML Engineer')).toBe('non-graduate')
  })
  it('detects non-graduate from principal keyword', () => {
    expect(detectRoleLevel('Principal Software Engineer')).toBe('non-graduate')
  })
  it('detects non-graduate from tech lead', () => {
    expect(detectRoleLevel('Tech Lead — Platform team')).toBe('non-graduate')
  })
  it('graduate when years ≤ 2', () => {
    expect(detectRoleLevel('Looking for 2 years of experience')).toBe('graduate')
  })
  it('non-graduate when years ≥ 3', () => {
    expect(detectRoleLevel('5+ years experience required')).toBe('non-graduate')
  })
  it('returns null when no signal', () => {
    expect(detectRoleLevel('We hire great people')).toBeNull()
  })
})
```

- [ ] **Step 2: Run the test — should fail**

```bash
cd frontend && npx vitest run src/__tests__/useRoleLevel.test.ts
```

Expected: import error — module doesn't exist.

- [ ] **Step 3: Create `frontend/src/composables/useRoleLevel.ts`**

```typescript
export type RoleLevel = 'graduate' | 'non-graduate'

export function detectRoleLevel(jobDescription: string): RoleLevel | null {
  const text = jobDescription.toLowerCase()

  if (/\b(principal|staff)\b/.test(text)) return 'non-graduate'
  if (/\b(lead|head|manager)\b.*\b(engineer|developer|team)\b/.test(text)
    || /\b(engineer|developer)\b.*\b(lead|head)\b/.test(text)
    || /\btech(nical)?\s+lead\b/.test(text)
    || /\blead\s+(software|backend|frontend|full\s*stack)\b/.test(text)) {
    return 'non-graduate'
  }
  if (/\bsenior\b/.test(text)) return 'non-graduate'
  if (/\bjunior\b/.test(text)) return 'graduate'
  if (/\b(graduate|grad|entry[\s-]level|new\s+grad|intern(ship)?|trainee)\b/.test(text)) {
    return 'graduate'
  }

  const yearsMatch = text.match(/(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)/)
  if (yearsMatch) {
    const years = parseInt(yearsMatch[1], 10)
    return years <= 2 ? 'graduate' : 'non-graduate'
  }
  const rangeMatch = text.match(/(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)/)
  if (rangeMatch) {
    const upper = parseInt(rangeMatch[2], 10)
    return upper <= 2 ? 'graduate' : 'non-graduate'
  }

  return null
}
```

- [ ] **Step 4: Run the test — should pass**

```bash
npx vitest run src/__tests__/useRoleLevel.test.ts
```

Expected: 9 passed.

- [ ] **Step 5: Update consumers — `useJobs.ts`**

Replace:

```typescript
import { detectSeniority } from './useSeniority'
```

with:

```typescript
import { detectRoleLevel } from './useRoleLevel'
```

Rename every `detectSeniority(...)` call → `detectRoleLevel(...)`. Rename every `seniorityLevel` → `roleLevel` (property on the job object).

- [ ] **Step 6: Update `frontend/src/stores/editor.ts`**

Replace:

```typescript
import type { SeniorityLevel } from '../composables/useSeniority'
```

with:

```typescript
import type { RoleLevel } from '../composables/useRoleLevel'
```

In `JobState`, replace `seniorityLevel: SeniorityLevel | null` with `roleLevel: RoleLevel | null`. In `addJob`'s initial state, replace `seniorityLevel: null,` with `roleLevel: null,`.

- [ ] **Step 7: Update `useTailor.ts`**

Find every `job.seniorityLevel` → `job.roleLevel`. Find every `body.seniority_level = job.seniorityLevel` → `body.role_level = job.roleLevel`. Find every `updates.seniorityLevel = ...` → `updates.roleLevel = ...`.

After the change, the analysis-card update (lines around 178-179) is gone — `aiPosition` was `position_level` from the old JSON; in Task 6 we renamed it to `role_level`. Rename it:

```typescript
          const aiRoleLevel = (data.analysis as any)?.role_level
          if (aiRoleLevel && !job.roleLevel) {
            updates.roleLevel = aiRoleLevel as RoleLevel
          }
```

- [ ] **Step 8: Update `JobCard.vue`**

Replace the `useSeniority` import and the `SENIORITY_OPTIONS` dropdown with a binary chip display. The 6-option `<select>` (lines 95-96) becomes a read-only chip showing "Graduate" or "Non-Graduate". If you want manual override, use a 2-option toggle:

```vue
<script setup lang="ts">
import type { RoleLevel } from '../composables/useRoleLevel'
// ... other imports
const emit = defineEmits<{
  'update:roleLevel': [value: RoleLevel | null]
  // ... existing emits
}>()
</script>

<template>
  <!-- in place of the existing <select> -->
  <div class="role-level-chip" v-if="job.roleLevel">
    <button
      :class="{ active: job.roleLevel === 'graduate' }"
      @click="$emit('update:roleLevel', 'graduate')"
    >Graduate</button>
    <button
      :class="{ active: job.roleLevel === 'non-graduate' }"
      @click="$emit('update:roleLevel', 'non-graduate')"
    >Non-Graduate</button>
  </div>
</template>
```

(Adapt to existing styles. Keep CSS compact.)

- [ ] **Step 9: Update `EditorView.vue`**

Replace:

```vue
@update:seniority-level="store.updateJob(activeJob!.id, { seniorityLevel: $event })"
```

with:

```vue
@update:role-level="store.updateJob(activeJob!.id, { roleLevel: $event })"
```

- [ ] **Step 10: Update `useJobs.test.ts`**

In `frontend/src/__tests__/useJobs.test.ts`, replace `seniorityLevel: 'senior'` with `roleLevel: 'non-graduate'` and update assertion.

- [ ] **Step 11: Delete the old composable and test**

```bash
rm frontend/src/composables/useSeniority.ts
rm frontend/src/__tests__/useSeniority.test.ts
```

- [ ] **Step 12: Type-check + run all frontend tests**

```bash
cd frontend && npx vue-tsc --noEmit
npx vitest run
```

Expected: type check passes; all tests pass (including the new `useRoleLevel.test.ts`).

- [ ] **Step 13: Commit**

```bash
git add -A frontend/src/
git commit -m "refactor: collapse frontend seniority to role_level binary

- useSeniority.ts → useRoleLevel.ts (binary detection)
- JobState.seniorityLevel → roleLevel
- JobCard 6-option select replaced with Graduate / Non-Graduate toggle
- TailorRequest body field renamed seniority_level → role_level"
```

---

## Task 9: Backend — `fabrication.py` → `stealth.py`, STRICT_BLOCK + STEALTH_ALLOWED_BLOCK, per-agent audit

**Files:**
- Create: `backend/agents/stealth.py`
- Delete: `backend/agents/fabrication.py`
- Modify: `backend/agents/orchestrator.py`
- Modify: `backend/agents/summary.py`
- Modify: `backend/agents/skills.py`
- Modify: `backend/agents/experience.py`
- Modify: `backend/agents/projects.py`
- Modify: `backend/agents/education.py`
- Modify: `backend/routers/tailor.py`

- [ ] **Step 1: Create `backend/agents/stealth.py`**

```python
"""Shared prompt blocks for stealth mode (the rebrand of fabrication mode).

When stealth_mode is False (default), agents use STRICT_BLOCK — rewrite-only.
When True, agents use STEALTH_ALLOWED_BLOCK — match-first → reshape → invent
for gaps with believability guardrails.
"""

STRICT_BLOCK = """STRICT MODE:
Use ONLY content present in the master CV. You may reorder, rephrase,
promote, demote, and tighten language. You may NOT invent bullets,
metrics, projects, skills, or any content not derivable from the
master CV.
"""


STEALTH_ALLOWED_BLOCK = """STEALTH MODE — IDEAL CV CONSTRUCTION:
Your job is to produce the strongest possible CV for this JD.

Hierarchy (in order):
1. MATCH-FIRST. Scan the master CV for content that already maps to JD
   requirements. Use those bullets, projects, and skills verbatim (or
   lightly reshape) — they are the strongest evidence.
2. RESHAPE. For partial matches, rephrase emphasis and terminology to
   mirror the JD's language without changing facts.
3. INVENT ONLY FOR GAPS. Where a JD requirement has no coverage in the
   master CV, you may add believable, candidate-consistent content to
   fill it.

Each invented item must be:
- Plausible for this candidate's seniority, role, company, and degree
- Consistent with their actual stack (no technologies they have zero
  exposure to)
- Bounded — minor upgrades, not bold claims
- Within believable metric ranges for the role

Never invent: employers, job titles, degrees, leadership-scale claims
for graduate-level roles.
"""
```

- [ ] **Step 2: Delete `backend/agents/fabrication.py`**

```bash
rm backend/agents/fabrication.py
```

- [ ] **Step 3: Update orchestrator.py**

Replace the import:

```python
from backend.agents.fabrication import FABRICATION_ALLOWED_BLOCK
```

with:

```python
from backend.agents.stealth import STEALTH_ALLOWED_BLOCK, STRICT_BLOCK
```

Rename the kwarg `fabrication_mode: bool = False` → `stealth_mode: bool = False` in `OrchestratorAgent.analyze`. Rename references in the body.

Replace the `fabrication_notice` block:

```python
        if fabrication_mode:
            fabrication_notice = FABRICATION_ALLOWED_BLOCK
        else:
            fabrication_notice = (
                "TRUTHFULNESS:\n"
                "DO NOT fabricate professional work experience or company names.\n"
            )
```

with:

```python
        stealth_notice = STEALTH_ALLOWED_BLOCK if stealth_mode else STRICT_BLOCK
```

Use `stealth_notice` everywhere `fabrication_notice` was used in the prompt body.

In the `generate_projects_rule` selection, also gate on `stealth_mode`:

```python
        if stealth_mode:
            generate_projects_rule = (
                "    1-2 new project entries demonstrating JD-relevant skills. "
                "Adjacent technologies the candidate hasn't directly used but could plausibly learn are acceptable.\n"
            )
        else:
            # Strict mode: forbid generated projects entirely.
            generate_projects_rule = (
                "    NEVER set generate_projects in strict mode — fabricated projects are forbidden.\n"
            )
```

- [ ] **Step 4a: Update `backend/agents/summary.py`**

Replace import:

```python
from backend.agents.fabrication import FABRICATION_ALLOWED_BLOCK
```

with:

```python
from backend.agents.stealth import STEALTH_ALLOWED_BLOCK, STRICT_BLOCK
```

Replace the entire `truthfulness_rule` block:

```python
        fabrication_mode = extra.get("fabrication_mode", False) if extra else False
        truthfulness_rule = (
            FABRICATION_ALLOWED_BLOCK
            if fabrication_mode
            else "- Maintain truthfulness — only mention skills and experience the candidate actually has"
        )
```

with:

```python
        stealth_mode = extra.get("stealth_mode", False) if extra else False
        truthfulness_rule = STEALTH_ALLOWED_BLOCK if stealth_mode else STRICT_BLOCK
```

- [ ] **Step 4b: Update `backend/agents/skills.py`**

Replace import (same as 4a). Replace the strict/stealth selector block:

```python
        fabrication_mode = extra.get("fabrication_mode", False) if extra else False
        if fabrication_mode:
            truthfulness_rules = (
                "4. " + FABRICATION_ALLOWED_BLOCK +
                "5. You may add up to 3 plausible JD-relevant skills consistent with the candidate's stack."
            )
        else:
            truthfulness_rules = (
                "4. Do NOT remove any existing skills\n"
                "5. Do NOT fabricate skills the candidate doesn't have"
            )
```

with:

```python
        stealth_mode = extra.get("stealth_mode", False) if extra else False
        if stealth_mode:
            truthfulness_rules = (
                "4. " + STEALTH_ALLOWED_BLOCK +
                "5. You may add up to 3 plausible JD-relevant skills consistent with the candidate's stack."
            )
        else:
            # STRICT_BLOCK covers the no-fabrication line; "do NOT remove" is
            # a skills-specific constraint and stays.
            truthfulness_rules = (
                "4. Do NOT remove any existing skills\n"
                "5. " + STRICT_BLOCK
            )
```

- [ ] **Step 4c: Update `backend/agents/experience.py`**

Replace import (same as 4a). Rename `fabrication_mode = extra.get(...)` → `stealth_mode = extra.get("stealth_mode", False) if extra else False`. Replace the `cannot_do_block` selector:

```python
        if fabrication_mode:
            cannot_do_block = (
                FABRICATION_ALLOWED_BLOCK +
                "Per-entry constraints (still apply):\n"
                "- Do NOT change the job title, company name, or dates (first bold line stays UNCHANGED)\n"
                "- You may invent at most 1 plausible bullet per entry\n"
                "- You may upgrade existing metrics to plausible higher values\n"
                "- Stack Used line may include adjacent technologies the candidate plausibly used"
            )
        else:
            cannot_do_block = (
                "WHAT YOU CANNOT DO:\n"
                "- Change the job title, company name, or dates (first bold line stays UNCHANGED)\n"
                "- Fabricate achievements, metrics, or technologies you didn't use\n"
                "- Add technologies to Stack Used that weren't part of this specific role\n"
                "- Remove quantified achievements (numbers, percentages) — they are real"
            )
```

with:

```python
        if stealth_mode:
            cannot_do_block = (
                STEALTH_ALLOWED_BLOCK +
                "Per-entry constraints (still apply):\n"
                "- Do NOT change the job title, company name, or dates (first bold line stays UNCHANGED)\n"
                "- You may invent at most 1 plausible bullet per entry\n"
                "- You may upgrade existing metrics to plausible higher values\n"
                "- Stack Used line may include adjacent technologies the candidate plausibly used"
            )
        else:
            # STRICT_BLOCK is the shared "no invention" line; per-entry
            # specifics (title/company/dates, Stack Used scope) stay below.
            cannot_do_block = (
                STRICT_BLOCK +
                "WHAT YOU CANNOT DO (in addition):\n"
                "- Change the job title, company name, or dates (first bold line stays UNCHANGED)\n"
                "- Add technologies to Stack Used that weren't part of this specific role\n"
                "- Remove quantified achievements (numbers, percentages) — they are real"
            )
```

- [ ] **Step 4d: Update `backend/agents/projects.py`**

Replace import (same as 4a). Rename `fabrication_mode = extra.get(...)` → `stealth_mode = ...`.

Replace the `dont_fabricate_block` selector:

```python
        if fabrication_mode:
            dont_fabricate_block = (
                FABRICATION_ALLOWED_BLOCK +
                "Per-project rules:\n"
                "- You may upgrade existing project metrics to plausible higher values\n"
                "- You may add capabilities that are plausibly adjacent to what the project actually did\n"
                "- Do NOT change project NAMES or URLs — those remain real"
            )
        else:
            dont_fabricate_block = (
                "4. DON'T FABRICATE: Never add capabilities, metrics, or technologies that weren't part of the project.\n"
                "   Reframing is fine (\"built data pipeline\" → \"engineered scalable research pipeline processing X records\").\n"
                "   Inventing is not (\"built chatbot\" → \"conducted cutting-edge ML research\" — this is a lie)."
            )
```

with:

```python
        if stealth_mode:
            dont_fabricate_block = (
                STEALTH_ALLOWED_BLOCK +
                "Per-project rules:\n"
                "- You may upgrade existing project metrics to plausible higher values\n"
                "- You may add capabilities that are plausibly adjacent to what the project actually did\n"
                "- Do NOT change project NAMES or URLs — those remain real"
            )
        else:
            dont_fabricate_block = (
                "4. " + STRICT_BLOCK +
                "   Reframing is fine (\"built data pipeline\" → \"engineered scalable research pipeline processing X records\").\n"
                "   Inventing is not (\"built chatbot\" → \"conducted cutting-edge ML research\" — this is a lie)."
            )
```

Replace the `generation_rule` selector:

```python
        generation_rule = ""
        if generate_new:
            if fabrication_mode:
                generation_rule = f"""
GENERATE NEW PROJECTS:
...
"""
            else:
                generation_rule = f"""
GENERATE NEW PROJECTS:
...
"""
```

with:

```python
        generation_rule = ""
        if generate_new and stealth_mode:
            # generate_projects is stealth-only. The strict path is impossible
            # because the orchestrator never sets the flag in strict mode AND
            # the router strips it server-side (see Task 10).
            generation_rule = f"""
GENERATE NEW PROJECTS:
Generate 1-2 NEW project entries demonstrating JD requirements existing projects don't cover.
Rules:
- Adjacent technologies the candidate hasn't directly used but could plausibly learn are acceptable
- Must be realistic — something they would actually build
- No fake URLs — use "at University" or "Personal" after the name
- Place after real projects

CANDIDATE'S KNOWN SKILLS:
{candidate_skills}
"""
```

- [ ] **Step 4e: Update `backend/agents/education.py`**

Replace import (same as 4a). Replace the `coursework_rules` selector:

```python
        fabrication_mode = extra.get("fabrication_mode", False) if extra else False
        if fabrication_mode:
            coursework_rules = (
                FABRICATION_ALLOWED_BLOCK +
                "- You may add up to 5 plausible JD-relevant coursework items consistent with the degree program\n"
                "- Degree names, university names, and dates remain UNCHANGED"
            )
        else:
            coursework_rules = (
                "- You may add 1-2 relevant coursework items if they are clearly implied by the degree (e.g., an MSc in AI clearly includes \"Machine Learning\")\n"
                "- Do NOT fabricate courses that wouldn't exist in the program\n"
                "- Do NOT remove any courses — only reorder and optionally rephrase"
            )
```

with:

```python
        stealth_mode = extra.get("stealth_mode", False) if extra else False
        if stealth_mode:
            coursework_rules = (
                STEALTH_ALLOWED_BLOCK +
                "- You may add up to 5 plausible JD-relevant coursework items consistent with the degree program\n"
                "- Degree names, university names, and dates remain UNCHANGED"
            )
        else:
            # Strict mode: only reorder/rephrase what's already listed.
            # Per-agent specifics (don't remove courses, degree names unchanged)
            # stay; STRICT_BLOCK covers the no-fabrication line.
            coursework_rules = (
                STRICT_BLOCK +
                "- Do NOT remove any courses — only reorder and optionally rephrase\n"
                "- Degree names, university names, and dates remain UNCHANGED"
            )
```

- [ ] **Step 5: Update `tailor.py` to pass `stealth_mode`**

In `tailor.py`, every `call["fabrication_mode"] = prefs["stealth_mode"]` becomes:

```python
                call["stealth_mode"] = prefs["stealth_mode"]
```

Every `fabrication_mode=stealth_mode` in the orchestrator call becomes:

```python
            plan = await orchestrator.analyze(
                resume_md, job_description, insights,
                role_level=role_level, page_mode=page_mode,
                entry_keys=entry_keys,
                stealth_mode=stealth_mode,
                max_projects=prefs["max_projects"],
            )
```

- [ ] **Step 6: Smoke test — backend imports**

```bash
python -c "from backend.routers.tailor import router; from backend.agents.orchestrator import OrchestratorAgent; from backend.agents.stealth import STRICT_BLOCK, STEALTH_ALLOWED_BLOCK; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 7: Run any existing backend tests**

```bash
python -m pytest backend/tests/ -v
```

Expected: all tests pass (including the new `test_role_level.py`).

- [ ] **Step 8: Commit**

```bash
git add -A backend/agents/ backend/routers/tailor.py
git commit -m "refactor: rename fabrication.py to stealth.py with STRICT_BLOCK

Adds STRICT_BLOCK for the off-mode prompt — was previously inline and
varied per agent. Now centralized so all agents share one strict
prompt. STEALTH_ALLOWED_BLOCK replaces FABRICATION_ALLOWED_BLOCK with
the match-first → reshape → invent hierarchy. Per-agent strict-mode
wording audited and replaced with the shared constant."
```

---

## Task 10: Server-side `generate_projects` enforcement

**Files:**
- Modify: `backend/routers/tailor.py`
- Create: `backend/tests/test_generate_projects_gating.py`

When `stealth_mode` is False, defensively strip any `generate_projects: true` flag from tool_calls before dispatching — protects against orchestrator drift.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_generate_projects_gating.py`:

```python
from backend.routers.tailor import _strip_generate_projects_when_strict


class TestStripGenerateProjectsWhenStrict:
    def test_strict_strips_flag(self):
        tool_calls = [
            {"agent": "projects", "action": "rewrite", "generate_projects": True},
            {"agent": "summary", "action": "rewrite"},
        ]
        out = _strip_generate_projects_when_strict(tool_calls, stealth_mode=False)
        assert "generate_projects" not in out[0]
        assert out[1] == {"agent": "summary", "action": "rewrite"}

    def test_stealth_keeps_flag(self):
        tool_calls = [
            {"agent": "projects", "action": "rewrite", "generate_projects": True},
        ]
        out = _strip_generate_projects_when_strict(tool_calls, stealth_mode=True)
        assert out[0]["generate_projects"] is True

    def test_no_flag_strict_passthrough(self):
        tool_calls = [{"agent": "summary", "action": "rewrite"}]
        out = _strip_generate_projects_when_strict(tool_calls, stealth_mode=False)
        assert out == tool_calls
```

- [ ] **Step 2: Run the test — should fail**

```bash
python -m pytest backend/tests/test_generate_projects_gating.py -v
```

Expected: `ImportError: cannot import name '_strip_generate_projects_when_strict'`.

- [ ] **Step 3: Add the helper to `backend/routers/tailor.py`**

Near the other helpers at the top of the file:

```python
def _strip_generate_projects_when_strict(tool_calls: list[dict], stealth_mode: bool) -> list[dict]:
    """When stealth is off, defensively strip generate_projects flags from
    orchestrator output so a drifted prompt can't cause the projects agent
    to fabricate. No-op when stealth is on."""
    if stealth_mode:
        return tool_calls
    cleaned = []
    for call in tool_calls:
        c = dict(call)
        c.pop("generate_projects", None)
        cleaned.append(c)
    return cleaned
```

- [ ] **Step 4: Run the test — should pass**

```bash
python -m pytest backend/tests/test_generate_projects_gating.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Wire it into `tailor_resume` and `execute_tailoring`**

After the orchestrator returns the plan in `tailor_resume`:

```python
            tool_calls = plan.get("tool_calls", [])
            tool_calls = _strip_generate_projects_when_strict(tool_calls, stealth_mode)
            sections_unchanged = plan.get("sections_unchanged", [])
```

In `execute_tailoring`:

```python
            tool_calls = plan.get("tool_calls", [])
            tool_calls = _strip_generate_projects_when_strict(tool_calls, prefs["stealth_mode"])
            sections_unchanged = plan.get("sections_unchanged", [])
```

- [ ] **Step 6: Commit**

```bash
git add backend/routers/tailor.py backend/tests/test_generate_projects_gating.py
git commit -m "feat: server-side strip generate_projects when stealth is off

Defensive belt-and-suspenders against orchestrator prompt drift. The
orchestrator prompt forbids the flag in strict mode, but we also strip
it server-side before dispatching agents."
```

---

## Task 11: Frontend — stealth label rename, per-job toggle, low-fit warning

**Files:**
- Modify: `frontend/src/composables/useProfile.ts`
- Modify: `frontend/src/views/PreferencesView.vue`
- Modify: `frontend/src/stores/editor.ts`
- Modify: `frontend/src/composables/useTailor.ts`
- Modify: `frontend/src/components/JobCard.vue` or `ScorePanel.vue` (whichever hosts the verdict card)

- [ ] **Step 1: `useProfile.ts` — rename type field**

In `frontend/src/composables/useProfile.ts`, find the `Profile` interface and rename:

```typescript
fabrication_mode: boolean
```

to:

```typescript
stealth_mode: boolean
```

- [ ] **Step 2: `editor.ts` — same rename in the `Profile` interface**

```typescript
export interface Profile {
  id: number
  name: string
  master_resume: string
  gemini_api_key: string
  page_mode: 'single' | 'multi'
  stealth_mode: boolean
  max_projects: number
  max_bullets_per_entry: number
  require_quantified_bullets: boolean
}
```

- [ ] **Step 3: `PreferencesView.vue` — rename the toggle and label**

Replace every `fabricationMode` → `stealthMode`. Replace every `fabrication_mode` (in the API payload) → `stealth_mode`. Update the visible label:

```vue
<label class="setting">
  <span class="setting-label">Stealth Mode</span>
  <input type="checkbox" v-model="stealthMode" />
  <span class="fab-label">{{ stealthMode ? 'ON' : 'OFF' }}</span>
</label>
```

Update the helper text near the toggle to describe the new behavior:

> When ON, agents may invent believable, JD-aligned content where the master CV has gaps. When OFF (default), agents only reorder and rephrase existing content.

- [ ] **Step 4: Verdict card — low-fit warning**

In whichever component renders `scoring.before` (likely `JobCard.vue`), add:

```vue
<div
  v-if="job.scoring?.before && Number(job.scoring.before.overall_fit) < 40"
  class="low-fit-warning"
>
  Low fit ({{ job.scoring.before.overall_fit }}/100) — review the gap list
  before tailoring.
</div>
```

CSS (add to `style.css` or component scoped style):

```css
.low-fit-warning {
  margin: 0.5rem 0;
  padding: 0.5rem 0.75rem;
  background: #fff5e6;
  border: 1px solid #f0b67a;
  color: #8b4500;
  border-radius: 4px;
  font-size: 0.9rem;
}
```

- [ ] **Step 5: Verdict card — per-job stealth toggle**

In the same component, add a small toggle for the per-job stealth override. When the user flips it, store an override on the job state and use it when calling `tailor`:

In `JobState` (`stores/editor.ts`):

```typescript
export interface JobState {
  // ... existing fields
  stealthOverride: boolean | null  // null = use profile default
}
```

Initialize `stealthOverride: null` in `addJob`.

In `JobCard.vue`:

```vue
<label class="stealth-toggle">
  <input
    type="checkbox"
    :checked="job.stealthOverride ?? store.profile?.stealth_mode ?? false"
    @change="store.updateJob(job.id, { stealthOverride: ($event.target as HTMLInputElement).checked })"
  />
  Stealth: {{ (job.stealthOverride ?? store.profile?.stealth_mode) ? 'ON' : 'OFF' }}
</label>
```

In `useTailor.ts`, when building the request body for both Check and Tailor, include the override when set:

```typescript
if (job.stealthOverride !== null) body.stealth_mode = job.stealthOverride
```

- [ ] **Step 6: Type-check + run frontend tests**

```bash
cd frontend && npx vue-tsc --noEmit
npx vitest run
```

Expected: type check passes, all tests pass.

- [ ] **Step 7: Manual smoke test — open the app**

```bash
cd frontend && npm run dev
```

Open the editor in a browser. Confirm:
- Preferences page shows "Stealth Mode" label, toggle persists.
- Pasting a JD still detects role level (graduate / non-graduate) — visible chip on the job card.
- After Check, the verdict card shows the gap list.
- If the JD scores below 40 overall_fit, the orange low-fit warning appears.
- The per-job stealth toggle switches state when clicked and persists across page refresh? (Not required — `stealthOverride` is per-session.)
- No "Suggestions" panel anywhere.

- [ ] **Step 8: Commit**

```bash
git add -A frontend/src/
git commit -m "feat: rename fabrication to stealth in UI; add low-fit warning + per-job toggle

- Profile.fabrication_mode → stealth_mode (frontend types + payloads)
- PreferencesView label updated
- JobCard verdict card: low-fit warning when overall_fit < 40
- Per-job stealth override toggle on the verdict card; null = use profile default"
```

---

## Verification

After all tasks land, run a final pass:

- [ ] **Backend tests:**

```bash
cd /Users/naresh/Documents/resume_editor/godcv
python -m pytest backend/tests/ -v
```

Expected: all green, including `test_role_level.py` (11 tests) and `test_generate_projects_gating.py` (3 tests).

- [ ] **Frontend tests + type check:**

```bash
cd frontend && npx vue-tsc --noEmit && npx vitest run
```

Expected: type check passes; all suites pass (including `useRoleLevel.test.ts`).

- [ ] **Final repo grep for stale names:**

```bash
cd /Users/naresh/Documents/resume_editor/godcv
grep -rn "fabrication_mode\|fabricationMode\|FABRICATION_ALLOWED_BLOCK\|seniority_level\|seniorityLevel\|SeniorityLevel\|detectSeniority\|SuggestionAgent\|suggestion_agent" \
  backend/ frontend/src/ --include="*.py" --include="*.ts" --include="*.vue"
```

Expected: no hits. (Acceptable: `gap_suggestions` — that's the orchestrator gap-analysis array, which stays.)

- [ ] **Manual end-to-end test:**

Start backend + frontend; from the editor:
1. Paste a graduate JD → confirm chip shows "Graduate", verdict card appears after Check.
2. Click Tailor → confirm tailored CV uses graduate section order (Education before Experience).
3. Toggle Stealth ON → re-tailor → confirm the tailored CV may include believable filler bullets/skills targeting the JD gaps.
4. Toggle Stealth OFF → re-tailor → confirm tailored CV uses only content derivable from the master CV.
5. Repeat 1-4 with a senior JD → confirm chip shows "Non-Graduate", non-graduate section order applied.
6. Confirm no "Suggestions" panel appears at any point.
