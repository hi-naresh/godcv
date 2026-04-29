# Stealth Mode, Suggestion Removal, and Graduate/Non-Graduate — Design

**Date:** 2026-04-29
**Status:** Approved, ready for implementation plan

## Summary

Three coupled changes that together turn godcv into a "generate a real ideal CV after analysis verdict" app:

1. **Remove the suggestion feature** — accept/deny overlay agents and UI go away. The tailored CV produced by the Tailor pipeline is the final output.
2. **Rename `fabrication_mode` → `stealth_mode`** with a stricter default and a clearer ON-mode hierarchy: match-existing-first → reshape → invent only for uncovered JD requirements. `generate_projects` is folded into stealth (no longer an independent flag).
3. **Collapse the 6-level seniority enum to two values** (`graduate` | `non-graduate`), JD-driven, with deterministic section order chosen by the backend (no longer an LLM output field).

The two-stage flow (Check → verdict → Tailor) is preserved so users can bail out when a JD is a poor fit.

## Decisions (from brainstorming)

| # | Question | Decision |
|---|----------|----------|
| 1 | Content rules in stealth mode | Hierarchy: existing-first → reshape → invent for gaps with believability guardrails |
| 2 | Behavior when stealth is OFF | Strict rewrite-only. Forbid invented bullets, metrics, projects, skills. Folds `generate_projects` into stealth. |
| 3 | Flow shape | Keep two-stage (Check then Tailor) so users can bail when JD doesn't fit |
| 4 | Graduate/non-graduate semantics | Binary by JD intent (not by candidate years). Drives prompt tone and section order. |
| 5 | Section order | Graduate: Summary → Education → Skills → Experience → Projects → Volunteering. Non-graduate: Summary → Skills → Experience → Projects → Education → Volunteering. Backend-deterministic, not LLM-chosen. |
| 6 | Suggestion feature | Remove entirely (agent, route phases, UI). Keep `highlightChanges()` (green pills for tailored content) — adjacent UX, still useful. |
| 7 | Low-fit warning | Show a gentle warning on the verdict card when `before.overall_fit < 40`. Never block. |
| 8 | Stealth toggle UI | Profile-level setting (renamed) + per-job override on the verdict card. |

## Out of scope

- Re-architecting the agent bus or per-section agents beyond prompt updates
- Changing the analysis/scoring/ATS pipelines beyond removing the suggestion phases
- New stealth-mode features (e.g. per-category toggles, "stealth strength" slider)
- Auditing or marking which content was invented in stealth mode
- Backfilling old `tailoring_history` rows with suggestion content (rows persist read-only with whatever data they have; the runtime UI no longer surfaces suggestions)

---

## Architecture

This is primarily a deletion + rename + prompt change. No new endpoints, no new agents, no new pipeline stages. One SQLite migration coerces existing data.

The boolean `stealth_mode` flows the same path `fabrication_mode` does today: SQLite `profiles` row → `TailorRequest` / `ExecuteRequest` → orchestrator + per-call `extra` dict → each agent's prompt block. Strict mode swaps the agent's strict block; stealth mode swaps in the new `STEALTH_ALLOWED_BLOCK` whose hierarchy is encoded in the prompt itself.

Section order is no longer an LLM output. The orchestrator stops including `section_order` in its JSON response. The backend computes it deterministically from `role_level` and passes it directly to `assemble_resume`.

---

## Section 1 — Suggestion feature removal

**Backend deletions:**

- `backend/agents/suggestion_agent.py` — delete the file.
- `backend/routers/tailor.py`:
  - In `tailor_resume`: delete Phase 4.6 (the `gap_suggestions` → `SuggestionAgent` block).
  - In `execute_tailoring`: delete Phase 5 (the equivalent block).
  - Remove `from backend.agents.suggestion_agent import SuggestionAgent` import.
- `backend/db/models.py` — drop any `suggestions` field from response/schema models if present (grep + remove).

**Frontend deletions:**

- `frontend/src/stores/editor.ts`:
  - Drop the `Suggestion` interface.
  - Drop `suggestions: Suggestion[]` from `JobState`.
  - Drop the field from `addJob` initial state and `resetJobTailoring`.
- `frontend/src/composables/useTailor.ts` — drop the `suggestions` SSE event handler.
- `frontend/src/components/ResumePreview.vue`:
  - Drop `injectSuggestion`, `handleSuggestionClick`, the suggestion-related props (`suggestions`) and emits (`accept-suggestion`, `deny-suggestion`).
  - Drop the click listener wiring in `onMounted`/`onUnmounted`.
  - **Keep** `highlightChanges`, `extractTextLines`, and the `originalMarkdown` prop — green-pill highlighting of tailored content stays.
- `frontend/src/components/JobCard.vue`, `ScorePanel.vue`, `EditorView.vue` — remove suggestion props/badges/lists. `EditorView.vue` no longer wires accept/deny handlers.
- `frontend/src/style.css` — strip selectors `.suggestion`, `.suggestion-remove`, `.suggestion-replace`, `.suggestion-project`, `.sug-tooltip`, `.sug-accept`, `.sug-deny`, `.sug-old`, `.sug-new`. Keep `.changed-content`.

**Verification step (during implementation):** grep the repo for `suggestion`/`Suggestion`/`sug-` after the deletions; only acceptable hits are inside `gap_suggestions` (the orchestrator's gap analysis) and `highlightChanges`.

---

## Section 2 — Stealth mode (renamed fabrication, with hierarchy)

**Renames (top to bottom):**

- DB column: `profiles.fabrication_mode` → `profiles.stealth_mode`.
- Pydantic models in `backend/db/models.py`: `Profile`, `ProfileCreate`, `ProfileUpdate`, `ProfileResponse`, `TailorRequest`, `ExecuteRequest` — every `fabrication_mode` → `stealth_mode`.
- Backend Python references: `prefs["fabrication_mode"]`, `request.fabrication_mode`, `fabrication_mode=...` in `tailor.py`, `orchestrator.py`, every agent file → `stealth_mode`.
- Frontend store/composables/components: `fabricationMode` → `stealthMode`. UI label "Fabrication Mode" → "Stealth Mode" (Preferences page + per-job toggle on verdict card).
- File: `backend/agents/fabrication.py` → `backend/agents/stealth.py`. Constant `FABRICATION_ALLOWED_BLOCK` → `STEALTH_ALLOWED_BLOCK`. Update all imports.

**Stealth ON — new prompt block** (replaces the current `FABRICATION_ALLOWED_BLOCK`):

```
STEALTH MODE — IDEAL CV CONSTRUCTION:
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
```

**Stealth OFF — new strict block** (replaces today's per-agent strict wording, centralized for consistency):

```
STRICT MODE:
Use ONLY content present in the master CV. You may reorder, rephrase,
promote, demote, and tighten language. You may NOT invent bullets,
metrics, projects, skills, or any content not derivable from the
master CV.
```

Both blocks live in `agents/stealth.py` as named constants (`STEALTH_ALLOWED_BLOCK`, `STRICT_BLOCK`).

**`generate_projects` folded in:**

- Today the orchestrator may set `generate_projects: true` on a tool_call regardless of `fabrication_mode`. After this change, the orchestrator prompt only mentions `generate_projects` when `stealth_mode` is True. The strict-mode prompt explicitly forbids it.
- Server-side enforcement: when `stealth_mode` is False and a tool_call arrives with `generate_projects: true`, strip the flag before dispatching. Defensive — protects against prompt drift.

**Per-agent prompt audit:**

Each agent file (`summary.py`, `skills.py`, `experience.py`, `projects.py`, `education.py`) currently has either an inline strict-mode wording or imports `FABRICATION_ALLOWED_BLOCK`. Replace the inline strict wording with `STRICT_BLOCK` from `agents/stealth.py` so all agents share one strict prompt. Update the swap site to use `STEALTH_ALLOWED_BLOCK` when `stealth_mode` is True. This eliminates per-agent drift in strict-mode wording.

---

## Section 3 — Graduate vs non-graduate

**File rename:**
- `backend/services/seniority.py` → `backend/services/role_level.py`. Function `detect_seniority` → `detect_role_level`. Returns `'graduate' | 'non-graduate' | None`.
- `frontend/src/composables/useSeniority.ts` → `useRoleLevel.ts`. Same return shape (`'graduate' | 'non-graduate' | null`).
- `frontend/src/__tests__/useSeniority.test.ts` → `useRoleLevel.test.ts`. Update assertions for the binary output.

**Detection rules (collapsed):**

| Signal | Result |
|---|---|
| JD mentions: graduate, grad, entry-level, new grad, intern, internship, trainee, junior | `graduate` |
| JD mentions: senior, lead, principal, staff, head, manager+engineer, tech lead | `non-graduate` |
| Years requirement ≤ 2 | `graduate` |
| Years requirement ≥ 3 | `non-graduate` |
| No signal | `None` (orchestrator defaults to `non-graduate`) |

Detection logic mirrors the existing rules in `services/seniority.py`, just bucketed two ways.

**Orchestrator prompt** (`backend/agents/orchestrator.py`):

- Replace the 6-key `seniority_guidance` dict with a 2-key one:
  - `graduate`: "Target is a GRADUATE-level role. Lead with education, coursework, internships, and projects. Tone: capable and eager. Avoid leadership/architectural claims."
  - `non-graduate`: "Target is a non-graduate professional role. Lead with experience and impact. Show ownership, scale, and measurable outcomes appropriate to the seniority signaled in the JD."
- Drop `section_order` from the JSON response schema. The orchestrator no longer chooses it.
- `analysis.position_level` → `analysis.role_level` with values `"graduate" | "non-graduate"`.
- The orchestrator prompt still references the JD's seniority cue ("Senior", "Staff", etc.) so generated bullets match the JD's pitch level — but the structural choice (section order) is no longer in its hands.

**Section order — backend-deterministic:**

In `tailor.py`, after analysis returns:

```python
if role_level == "graduate":
    section_order = ["Summary", "Education", "Skills", "Experience",
                     "Projects", "Volunteering and Interests"]
else:
    section_order = ["Summary", "Skills", "Experience", "Projects",
                     "Education", "Volunteering and Interests"]
```

Pass `section_order` directly into `assemble_resume(...)`. Drop the `plan.get("section_order")` lookup.

**`agents/stealth.py`:** "No leadership-scale claims for graduate/junior candidates" → "No leadership-scale claims for graduate-level roles".

**DB schema:**
- `tailoring_history.seniority_level` → `tailoring_history.role_level`.
- Other tables that store seniority (verify with grep) → same rename.

---

## Section 4 — Flow, verdict UX, and assembly

**Two-stage flow stays.** No structural change.

**`tailor_resume` (analyze_only / Check):**
- Returns: `analysis` (job_title, company, role_level, role_type, key_requirements, matched_strengths), `tool_calls`, `sections_unchanged`, `scoring.before` (keyword_match, skills_coverage, experience_fit, overall_fit), `scoring.gap_suggestions`.
- `gap_suggestions` is repurposed: it becomes the "JD requirements not covered by your CV" hints displayed on the verdict card. Not fed into a separate suggestion agent.
  - Strict mode: gaps are surfaced as "won't be filled — consider whether you fit".
  - Stealth mode: gaps inform per-agent prompts so invention targets the right places.

**`execute_tailoring` (Tailor):**
- Phases: parse → dispatch agents → assemble → after-score → ATS-score → learn.
- Phases 4.6/5 (suggestion generation) deleted in both `tailor_resume` and `execute_tailoring`.
- `assemble_resume` is called with the deterministic `section_order` from `role_level`, not from `plan.get("section_order")`.

**Verdict card UI:**
- Shows: job title + company, role-level chip ("Graduate" / "Non-Graduate"), `scoring.before` numbers, key requirements, matched strengths, gap list (informational).
- Two buttons: **Tailor** (proceeds to execute pipeline), **Re-check** (re-runs analysis — already exists).
- **Low-fit warning:** when `before.overall_fit < 40`, show a banner "Low fit ({score}/100) — review the gap list before tailoring." Non-blocking.
- **Stealth toggle:** small switch on the verdict card ("Stealth: ON/OFF"), defaulting to the profile-level setting. Per-job override carries into the Tailor request body.

---

## Section 5 — Data migration and rollout

**SQLite migration** (added to the migration block in `backend/db/database.py`'s `_init_tables`):

Idempotent steps, run inside a single transaction:

1. **`profiles.fabrication_mode` → `profiles.stealth_mode`.** Check `PRAGMA table_info(profiles)`; rename only if `fabrication_mode` exists and `stealth_mode` does not. SQLite ≥ 3.25 supports `ALTER TABLE ... RENAME COLUMN`.
2. **`tailoring_history.seniority_level` → `tailoring_history.role_level`.** Same `PRAGMA` guard. After rename, run an UPDATE to coerce values: `'junior' → 'graduate'`, `'mid-level'/'senior'/'lead'/'principal' → 'non-graduate'`. `'graduate'` and `NULL` unchanged.
3. **Drop suggestion fields** if any tables persist them (verify via grep before writing the migration; current code suggests `suggestions` is transient SSE-only, but check `saved_cvs` / `tailoring_history` columns).

Migration function: `migrate_007_stealth_and_role_level` (or whatever the next sequence number is — check existing migrations). Wrapped in a try/except so partial failure on a fresh DB doesn't break startup.

**API request compatibility:**
- Stale frontend tabs sending `fabrication_mode` or `seniority_level` in request bodies → backend rejects with HTTP 400 and a clear error message ("Field renamed; refresh the app"). No silent coercion.
- Saved CVs and tailoring history are read-only in the UI flow; coerced values display as the new labels.

**Default behavior post-migration:**
- `fabrication_mode = false` → `stealth_mode = false` (strict). Same behavior, stricter prompt wording.
- `fabrication_mode = true` → `stealth_mode = true`. Behavior is *stricter* than before (existing-content-first hierarchy biases away from invention). This is the explicit goal — reduce hallucination.

**Rollout order:**

1. DB migration + Pydantic model renames (no behavior change yet — column in DB matches, but prompts unchanged).
2. Suggestion feature removal (backend + frontend).
3. Seniority → role_level collapse + deterministic section order.
4. Stealth prompts (`STRICT_BLOCK` + `STEALTH_ALLOWED_BLOCK`); per-agent prompt audit.
5. Frontend renames + verdict card cleanup + low-fit warning.

Each step is independently testable. Steps 1 and 2 don't change tailoring output; steps 3–5 do. Anyone reviewing diffs can isolate "what changed the CV output" from "what was just renamed".

---

## Verification

- **Unit tests:** Update `useSeniority.test.ts` → `useRoleLevel.test.ts` to assert binary output. `useMarkdown.test.ts` already passes; no changes expected.
- **Manual smoke test:** Existing fixture JD + master CV →
  - Strict mode: tailored CV contains only content derivable from master CV.
  - Stealth mode: tailored CV may contain plausibility-bounded inventions targeting the JD's gaps.
  - Verdict card shows "Graduate" or "Non-Graduate" chip; section order in tailored CV matches the binary rule.
  - No "Suggestions" panel anywhere in the UI.
- **Migration safety:** Start app on a copy of the production DB; confirm the migration runs once, is idempotent on restart, and that an existing profile with `fabrication_mode=true` becomes `stealth_mode=true`.
