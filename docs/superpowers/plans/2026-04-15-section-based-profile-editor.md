# Section-Based Profile Editor + Smart Entry Selection — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Profile page's raw textarea with a structured section-based editor (collapsible cards, multi-entry for Experience/Projects with add/remove), and update the orchestrator to select the most relevant entries for a 1-page tailored CV.

**Architecture:** Frontend-only editor change — parse markdown into structured UI on load, reassemble into markdown on save. Backend adds `include`/`exclude` actions to orchestrator + assembler so entries can be dropped during tailoring. Parser gets project entry splitting. Database schema unchanged (`master_resume` stays a TEXT column).

**Tech Stack:** Vue 3 (Composition API, `<script setup>`), Pinia, Python/FastAPI, existing `marked` + parser pipeline.

---

## File Structure

### New Files
| File | Responsibility |
|---|---|
| `frontend/src/components/EntryCard.vue` | Single experience/project entry: header text input + content textarea + remove button |
| `frontend/src/components/SectionCard.vue` | Collapsible card for one section. Single-textarea for most sections, multi-entry for Experience/Projects |
| `frontend/src/components/SectionEditor.vue` | Top-level editor: parses markdown into frontmatter fields + section cards, reassembles on change |

### Modified Files
| File | What Changes |
|---|---|
| `frontend/src/views/ProfileView.vue` | Replace raw textarea with `SectionEditor`, wire up save |
| `backend/services/parser.py` | Add `parse_project_entries()`, apply to Projects section like Experience |
| `backend/agents/orchestrator.py` | Add `include`/`exclude` actions for experience and project entries |
| `backend/agents/bus.py` | Skip `exclude` entries, pass through `include` entries unchanged |
| `backend/services/assembler.py` | Accept `excluded_entries` set, drop them from final output; handle Projects entries like Experience |
| `backend/routers/tailor.py` | Pass excluded entries from plan to assembler |
| `tests/test_parser.py` | Add tests for project entry parsing |
| `tests/test_assembler.py` | Add tests for entry exclusion |

---

### Task 1: Add Project Entry Parsing to Backend Parser

**Files:**
- Modify: `backend/services/parser.py:47-83`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write failing tests for project entry parsing**

Add to `tests/test_parser.py`:

```python
class TestParseProjectEntries:
    def test_splits_projects_into_entries(self, parsed_resume):
        projects = parsed_resume["sections"]["Projects"]
        assert isinstance(projects, dict)
        assert "_entries" in projects
        assert "_full" in projects
        assert len(projects["_entries"]) == 2

    def test_project_entry_keys(self, parsed_resume):
        projects = parsed_resume["sections"]["Projects"]
        keys = [e["key"] for e in projects["_entries"]]
        assert "DataFlow" in keys[0] or "DataFlow" in keys[1]

    def test_project_entry_content(self, parsed_resume):
        projects = parsed_resume["sections"]["Projects"]
        entry = projects["_entries"][0]
        assert "content" in entry
        assert "title" in entry
        assert entry["content"].strip() != ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -m pytest tests/test_parser.py::TestParseProjectEntries -v`
Expected: FAIL — Projects section is currently a plain string, not a dict with `_entries`.

- [ ] **Step 3: Add `parse_project_entries()` and wire it into `parse_sections()`**

In `backend/services/parser.py`, add after `_extract_company_key` (after line 44):

```python
def parse_project_entries(section_content: str) -> list[dict]:
    """Split projects section into individual project entries.
    Each entry starts with a bold title line like:
    **[ProjectName](url)** | Stack - Tech1, Tech2
    or **ProjectName** | Stack - Tech1, Tech2
    """
    entries = []
    parts = re.split(r'(?=^\*\*[\[{]?.+?\*\*)', section_content, flags=re.MULTILINE)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        title_match = re.match(r'^\*\*\[?([^\]*]+)', part)
        title = title_match.group(1).strip() if title_match else "Unknown"
        key = re.split(r'[\s(\]|]', title)[0]
        entries.append({"key": key, "title": title, "content": part})
    return entries
```

Then in `parse_sections()`, add a Projects block after the Experience block (after line 78):

```python
                if current_key.lower() == "projects":
                    entries = parse_project_entries(content)
                    if entries:
                        sections[current_key] = {
                            "_full": content,
                            "_entries": entries,
                        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -m pytest tests/test_parser.py -v`
Expected: All tests pass including new `TestParseProjectEntries`.

- [ ] **Step 5: Run existing assembler tests to check for regressions**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -m pytest tests/test_assembler.py -v`
Expected: All pass. The assembler already handles dict sections with `_entries` and `_full` keys (lines 55-64 of `assembler.py`).

- [ ] **Step 6: Commit**

```bash
git add backend/services/parser.py tests/test_parser.py
git commit -m "feat: parse Projects section into individual entries"
```

---

### Task 2: Update Assembler to Support Entry Exclusion

**Files:**
- Modify: `backend/services/assembler.py:4-71`
- Test: `tests/test_assembler.py`

- [ ] **Step 1: Write failing tests for entry exclusion**

Add to `tests/test_assembler.py`:

```python
class TestAssembleWithExcludedEntries:
    def test_exclude_experience_entry(self, sample_resume):
        parsed = parse_resume(sample_resume)
        output = assemble_resume(parsed, {}, excluded_entries={"StartupXYZ"})
        assert "Senior Engineer — Acme Corp" in output
        assert "StartupXYZ" not in output

    def test_exclude_project_entry(self, sample_resume):
        parsed = parse_resume(sample_resume)
        output = assemble_resume(parsed, {}, excluded_entries={"CloudDash"})
        assert "DataFlow" in output
        assert "CloudDash" not in output

    def test_exclude_multiple_entries(self, sample_resume):
        parsed = parse_resume(sample_resume)
        output = assemble_resume(parsed, {}, excluded_entries={"StartupXYZ", "CloudDash"})
        assert "Acme Corp" in output
        assert "StartupXYZ" not in output
        assert "CloudDash" not in output

    def test_no_exclusion_preserves_all(self, sample_resume):
        parsed = parse_resume(sample_resume)
        output = assemble_resume(parsed, {}, excluded_entries=set())
        assert "Acme Corp" in output
        assert "StartupXYZ" in output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -m pytest tests/test_assembler.py::TestAssembleWithExcludedEntries -v`
Expected: FAIL — `assemble_resume` doesn't accept `excluded_entries` parameter yet.

- [ ] **Step 3: Add `excluded_entries` parameter to `assemble_resume()`**

Modify `backend/services/assembler.py`. Update the function signature and the entry loop:

```python
def assemble_resume(
    original_parsed: dict,
    modified_sections: dict[str, str],
    modified_experience_entries: dict[str, str] | None = None,
    section_order: list[str] | None = None,
    excluded_entries: set[str] | None = None,
) -> str:
```

Replace the block at lines 55-62 (the `elif isinstance(original, dict) and "_entries" in original` branch) with:

```python
        elif isinstance(original, dict) and "_entries" in original:
            entry_parts = []
            for entry in original["_entries"]:
                # Skip excluded entries
                if excluded_entries and _entry_matches_exclusion(entry["key"], excluded_entries):
                    continue
                if modified_experience_entries and entry["key"] in modified_experience_entries:
                    entry_parts.append(modified_experience_entries[entry["key"]])
                else:
                    entry_parts.append(entry["content"])
            if entry_parts:
                parts.append("\n\n".join(entry_parts))
```

Add a helper at the bottom of the file:

```python
def _entry_matches_exclusion(key: str, excluded: set[str]) -> bool:
    """Check if an entry key matches any exclusion (case-insensitive, substring)."""
    for ex in excluded:
        if ex.lower() in key.lower() or key.lower() in ex.lower():
            return True
    return False
```

- [ ] **Step 4: Run all assembler tests**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -m pytest tests/test_assembler.py -v`
Expected: All pass (old + new).

- [ ] **Step 5: Commit**

```bash
git add backend/services/assembler.py tests/test_assembler.py
git commit -m "feat: assembler supports excluding entries by key"
```

---

### Task 3: Update Orchestrator Prompt for Entry Selection

**Files:**
- Modify: `backend/agents/orchestrator.py:45-88`

- [ ] **Step 1: Update the orchestrator prompt**

In `backend/agents/orchestrator.py`, replace the `AVAILABLE AGENTS AND ACTIONS` block and surrounding context in the prompt string (lines 58-63) with:

```python
AVAILABLE AGENTS AND ACTIONS:
- agent: "summary", action: "rewrite" -- rewrite the summary to match job requirements
- agent: "skills", action: "reorder" -- reorder and emphasize relevant skills (with promote/demote lists)
- agent: "experience", entry: "<CompanyKey>", action: "rewrite"|"include"|"exclude" -- per job entry
  - "include": keep this entry as-is (relevant, no changes needed)
  - "exclude": drop this entry entirely (not relevant for this role)
  - "rewrite": include but rewrite bullets to better match the JD
- agent: "projects", entry: "<ProjectKey>", action: "rewrite"|"include"|"exclude" -- per project entry
  - Same include/exclude/rewrite logic as experience
  - Prioritize projects whose tech stack matches the JD

ENTRY SELECTION RULES:
- The resume may contain MORE entries than can fit on a single page
- You MUST provide an action for EVERY experience and project entry (include, exclude, or rewrite)
- Select enough entries to fill a 1-page resume without overflow
- For a 1-page resume: typically 2-3 experience entries and 2-3 projects
- Prefer entries most relevant to the job description
- When excluding, drop the least relevant entries first
```

- [ ] **Step 2: Update the JSON output schema in the prompt**

Replace the tool_calls example in the JSON schema (line 84) with:

```python
    {{"agent": "<name>", "action": "<rewrite|reorder|include|exclude|keep>", "entry": "<for experience/projects>", "instructions": "<1-2 sentences>", "promote": ["<items>"], "demote": ["<items>"]}}
```

- [ ] **Step 3: Verify the orchestrator module loads**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -c "from backend.agents.orchestrator import OrchestratorAgent; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/agents/orchestrator.py
git commit -m "feat: orchestrator supports include/exclude for entry selection"
```

---

### Task 4: Update AgentBus to Handle include/exclude Actions

**Files:**
- Modify: `backend/agents/bus.py:25-114`

- [ ] **Step 1: Update dispatch to skip exclude and include actions, and collect excluded keys**

In `backend/agents/bus.py`, modify the `dispatch` method. The return value adds `excluded_entries`. Update the method:

At the top of `dispatch()` (after line 31), add:

```python
        excluded_entries: set[str] = set()
```

In the for-loop that categorizes calls (lines 36-42), update to:

```python
        for call in tool_calls:
            action = call.get("action", "")
            if action == "keep" or action == "include":
                continue
            if action == "exclude":
                entry_key = call.get("entry", "")
                if entry_key:
                    excluded_entries.add(entry_key)
                continue
            if call["agent"] == "experience":
                experience_calls.append(call)
            elif call["agent"] == "projects":
                # Project rewrite calls — dispatch like experience but for projects section
                experience_calls.append(call)
            else:
                parallel_calls.append(call)
```

Wait — projects currently goes through `parallel_calls` as a whole-section agent. With per-entry projects, we need to handle project entries like experience entries. Update the project rewrite handling:

After the experience entry dispatch block (after line 109), add a similar block for project entries:

```python
        # Run project entries in parallel (rewrite only)
        project_calls = [c for c in tool_calls if c["agent"] == "projects" and c.get("action") == "rewrite"]
        if project_calls:
            proj_section = sections.get("Projects", {})
            proj_entries = proj_section.get("_entries", []) if isinstance(proj_section, dict) else []
            proj_entry_map = {e["key"]: e for e in proj_entries}

            proj_tasks = []
            proj_agent = self.agents["projects"]
            for call in project_calls:
                entry_key = call.get("entry", "")
                entry = proj_entry_map.get(entry_key)
                if not entry:
                    for k, v in proj_entry_map.items():
                        if entry_key.lower() in k.lower() or k.lower() in entry_key.lower():
                            entry = v
                            entry_key = k
                            break
                if not entry:
                    continue

                proj_tasks.append(
                    _run_single_agent(
                        proj_agent,
                        f"projects:{entry_key}",
                        entry["content"],
                        call,
                        job_description,
                    )
                )

            results = await asyncio.gather(*proj_tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    self.log.error("Projects agent failed: %s", r)
                    continue
                name, content = r
                entry_key = name.split(":", 1)[1] if ":" in name else name
                modified_entries[entry_key] = content
```

Also update the filter in `parallel_calls` categorization to exclude per-entry project calls:

```python
            if call["agent"] == "experience":
                experience_calls.append(call)
            else:
                # Only add to parallel if it's a whole-section agent (not per-entry projects)
                if call["agent"] == "projects" and call.get("entry"):
                    pass  # handled separately below
                else:
                    parallel_calls.append(call)
```

Update the return value (line 111-114):

```python
        return {
            "modified_sections": modified_sections,
            "modified_entries": modified_entries,
            "excluded_entries": excluded_entries,
        }
```

- [ ] **Step 2: Verify module loads**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -c "from backend.agents.bus import AgentBus; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/agents/bus.py
git commit -m "feat: agent bus handles include/exclude actions and per-entry projects"
```

---

### Task 5: Update Tailor Router to Pass Excluded Entries to Assembler

**Files:**
- Modify: `backend/routers/tailor.py:86-104`

- [ ] **Step 1: Extract excluded_entries from bus result and pass to assembler**

In `backend/routers/tailor.py`, update the Phase 4 assembly block (lines 101-104):

```python
            modified_sections = result["modified_sections"] if result else {}
            modified_entries = result["modified_entries"] if result else {}
            excluded_entries = result.get("excluded_entries", set()) if result else set()
            section_order = plan.get("section_order")
            tailored_md = assemble_resume(parsed, modified_sections, modified_entries, section_order, excluded_entries)
```

- [ ] **Step 2: Verify module loads**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -c "from backend.routers.tailor import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/routers/tailor.py
git commit -m "feat: pass excluded entries from bus to assembler during tailoring"
```

---

### Task 6: Create EntryCard Component

**Files:**
- Create: `frontend/src/components/EntryCard.vue`

- [ ] **Step 1: Create the EntryCard component**

Create `frontend/src/components/EntryCard.vue`:

```vue
<script setup lang="ts">
defineProps<{
  header: string
  content: string
}>()

defineEmits<{
  'update:header': [value: string]
  'update:content': [value: string]
  remove: []
}>()
</script>

<template>
  <div class="entry-card">
    <div class="entry-header">
      <input
        class="entry-title-input"
        :value="header"
        @input="$emit('update:header', ($event.target as HTMLInputElement).value)"
        placeholder="Role — Company (Location) or Project Name | Stack"
      />
      <button class="entry-remove-btn" @click="$emit('remove')" title="Remove entry">&times;</button>
    </div>
    <textarea
      class="entry-content"
      :value="content"
      @input="$emit('update:content', ($event.target as HTMLTextAreaElement).value)"
      placeholder="- Bullet point 1&#10;- Bullet point 2"
      rows="3"
    />
  </div>
</template>

<style scoped>
.entry-card {
  border: 1px solid #e8e8e8; border-radius: 8px; padding: 10px;
  background: #fafafa;
}
.entry-header { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.entry-title-input {
  flex: 1; border: 1px solid #d9d9d9; border-radius: 6px;
  padding: 6px 8px; font-size: 0.82rem; font-weight: 600;
  font-family: ui-monospace, monospace;
}
.entry-title-input:focus { outline: none; border-color: #667eea; }
.entry-remove-btn {
  width: 26px; height: 26px; border: none; background: #f0f0f0;
  border-radius: 6px; font-size: 1rem; cursor: pointer; color: #999;
  display: flex; align-items: center; justify-content: center;
}
.entry-remove-btn:hover { background: #ffe0e0; color: #d00; }
.entry-content {
  width: 100%; resize: vertical; padding: 6px 8px;
  border: 1px solid #d9d9d9; border-radius: 6px; font-size: 0.8rem;
  font-family: ui-monospace, monospace; line-height: 1.5;
}
.entry-content:focus { outline: none; border-color: #667eea; }
</style>
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/EntryCard.vue
git commit -m "feat: add EntryCard component for experience/project entries"
```

---

### Task 7: Create SectionCard Component

**Files:**
- Create: `frontend/src/components/SectionCard.vue`

- [ ] **Step 1: Create the SectionCard component**

Create `frontend/src/components/SectionCard.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import EntryCard from './EntryCard.vue'

export interface EntryData {
  key: string
  header: string
  content: string
}

const props = defineProps<{
  title: string
  multiEntry: boolean
  content?: string
  entries?: EntryData[]
}>()

const emit = defineEmits<{
  'update:content': [value: string]
  'update:entries': [value: EntryData[]]
  remove: []
}>()

const collapsed = ref(false)

function updateEntryHeader(index: number, value: string) {
  if (!props.entries) return
  const updated = [...props.entries]
  updated[index] = { ...updated[index], header: value }
  emit('update:entries', updated)
}

function updateEntryContent(index: number, value: string) {
  if (!props.entries) return
  const updated = [...props.entries]
  updated[index] = { ...updated[index], content: value }
  emit('update:entries', updated)
}

function removeEntry(index: number) {
  if (!props.entries) return
  const updated = props.entries.filter((_, i) => i !== index)
  emit('update:entries', updated)
}

function addEntry() {
  const updated = [...(props.entries || [])]
  const key = `new-${Date.now()}`
  updated.push({ key, header: '', content: '' })
  emit('update:entries', updated)
}
</script>

<template>
  <div class="section-card">
    <div class="section-header" @click="collapsed = !collapsed">
      <span class="collapse-icon">{{ collapsed ? '+' : '-' }}</span>
      <h3>{{ title }}</h3>
      <span class="entry-count" v-if="multiEntry && entries">{{ entries.length }} entries</span>
      <button class="section-remove-btn" @click.stop="$emit('remove')" title="Remove section">&times;</button>
    </div>

    <div v-show="!collapsed" class="section-body">
      <!-- Single-content section -->
      <template v-if="!multiEntry">
        <textarea
          class="section-textarea"
          :value="content"
          @input="$emit('update:content', ($event.target as HTMLTextAreaElement).value)"
          :placeholder="`${title} content (markdown)...`"
          rows="4"
        />
      </template>

      <!-- Multi-entry section -->
      <template v-else>
        <div class="entries-list">
          <EntryCard
            v-for="(entry, index) in entries"
            :key="entry.key"
            :header="entry.header"
            :content="entry.content"
            @update:header="updateEntryHeader(index, $event)"
            @update:content="updateEntryContent(index, $event)"
            @remove="removeEntry(index)"
          />
        </div>
        <button class="add-entry-btn" @click="addEntry">
          + Add {{ title === 'Experience' ? 'Experience' : 'Project' }}
        </button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.section-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px;
  overflow: hidden;
}
.section-header {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 14px; cursor: pointer; user-select: none;
  background: #f8f8f8; border-bottom: 1px solid #e0e0e0;
}
.section-header:hover { background: #f0f0f0; }
.collapse-icon {
  width: 20px; height: 20px; display: flex; align-items: center;
  justify-content: center; font-weight: 700; font-size: 1rem; color: #666;
}
.section-header h3 { margin: 0; font-size: 0.9rem; flex: 1; }
.entry-count { font-size: 0.75rem; color: #999; }
.section-remove-btn {
  width: 24px; height: 24px; border: none; background: transparent;
  font-size: 1.1rem; cursor: pointer; color: #bbb; border-radius: 4px;
}
.section-remove-btn:hover { background: #ffe0e0; color: #d00; }
.section-body { padding: 12px 14px; }
.section-textarea {
  width: 100%; resize: vertical; padding: 8px; border: 1px solid #d9d9d9;
  border-radius: 8px; font-size: 0.82rem; font-family: ui-monospace, monospace;
  line-height: 1.5;
}
.section-textarea:focus { outline: none; border-color: #667eea; }
.entries-list { display: flex; flex-direction: column; gap: 8px; }
.add-entry-btn {
  margin-top: 8px; width: 100%; padding: 8px; border: 1px dashed #ccc;
  border-radius: 8px; background: #fafafa; font-size: 0.82rem;
  font-weight: 600; cursor: pointer; color: #666;
}
.add-entry-btn:hover { background: #f0f0f0; border-color: #999; }
</style>
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SectionCard.vue
git commit -m "feat: add SectionCard component with collapsible sections and multi-entry support"
```

---

### Task 8: Create SectionEditor Component

**Files:**
- Create: `frontend/src/components/SectionEditor.vue`

This is the core component. It parses incoming markdown into structured state, renders frontmatter fields + section cards, and reassembles everything back into markdown on any change.

- [ ] **Step 1: Create the SectionEditor component**

Create `frontend/src/components/SectionEditor.vue`:

```vue
<script setup lang="ts">
import { ref, watch } from 'vue'
import SectionCard from './SectionCard.vue'
import type { EntryData } from './SectionCard.vue'

const MULTI_ENTRY_SECTIONS = ['experience', 'projects']

const props = defineProps<{ markdown: string }>()
const emit = defineEmits<{ 'update:markdown': [value: string] }>()

// --- Frontmatter fields ---
const fmName = ref('')
const fmTitle = ref('')
const fmEmail = ref('')
const fmPhone = ref('')
const fmPortfolio = ref('')
const fmGithub = ref('')
const fmLinkedin = ref('')
const fmFontSize = ref('11')
const fmLineSpacing = ref('1.4')

// --- Sections ---
interface SectionState {
  name: string
  multiEntry: boolean
  content: string
  entries: EntryData[]
}

const sections = ref<SectionState[]>([])
let skipEmit = false

// --- Parse markdown into state ---
function parseMarkdown(md: string) {
  skipEmit = true

  // Parse frontmatter
  const fmMatch = md.match(/^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)/)
  const fmBlock = fmMatch ? fmMatch[1] : ''
  const body = fmMatch ? fmMatch[2] : md

  const fmData: Record<string, string> = {}
  for (const line of fmBlock.split('\n')) {
    const kv = line.match(/^\s*([A-Za-z0-9_]+)\s*:\s*(.*)\s*$/)
    if (kv) fmData[kv[1]] = kv[2].trim().replace(/^["'](.*)["']$/, '$1')
  }

  fmName.value = fmData.name || ''
  fmTitle.value = fmData.title || ''
  fmEmail.value = fmData.email || ''
  fmPhone.value = fmData.phone || ''
  fmPortfolio.value = fmData.portfolio || ''
  fmGithub.value = fmData.github || ''
  fmLinkedin.value = fmData.linkedin || ''
  fmFontSize.value = fmData.font_size || '11'
  fmLineSpacing.value = fmData.line_spacing || '1.4'

  // Parse sections
  const sectionList: SectionState[] = []
  const parts = body.split(/^# /m)

  for (const part of parts) {
    const trimmed = part.trim()
    if (!trimmed) continue

    const newlineIdx = trimmed.indexOf('\n')
    const name = newlineIdx > -1 ? trimmed.substring(0, newlineIdx).trim() : trimmed.trim()
    let content = newlineIdx > -1 ? trimmed.substring(newlineIdx + 1) : ''
    // Strip separator lines
    content = content.replace(/^\s*---\s*$/gm, '').trim()

    const isMulti = MULTI_ENTRY_SECTIONS.includes(name.toLowerCase())

    if (isMulti) {
      const entries = parseEntries(content)
      sectionList.push({ name, multiEntry: true, content: '', entries })
    } else {
      sectionList.push({ name, multiEntry: false, content, entries: [] })
    }
  }

  sections.value = sectionList
  skipEmit = false
}

function parseEntries(content: string): EntryData[] {
  const entries: EntryData[] = []
  // Split on lines starting with bold markers
  const parts = content.split(/(?=^\*\*)/m)
  for (const part of parts) {
    const trimmed = part.trim()
    if (!trimmed) continue
    // First line is the header, rest is content
    const nlIdx = trimmed.indexOf('\n')
    const header = nlIdx > -1 ? trimmed.substring(0, nlIdx).trim() : trimmed
    const body = nlIdx > -1 ? trimmed.substring(nlIdx + 1).trim() : ''
    const key = `entry-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
    entries.push({ key, header, content: body })
  }
  return entries
}

// --- Reassemble markdown from state ---
function assembleMarkdown(): string {
  const fmLines = [
    '---',
    `name: ${fmName.value}`,
    `title: ${fmTitle.value}`,
    `email: ${fmEmail.value}`,
    `phone: ${fmPhone.value}`,
  ]
  if (fmPortfolio.value) fmLines.push(`portfolio: ${fmPortfolio.value}`)
  if (fmGithub.value) fmLines.push(`github: ${fmGithub.value}`)
  if (fmLinkedin.value) fmLines.push(`linkedin: ${fmLinkedin.value}`)
  fmLines.push(`font_size: ${fmFontSize.value}`)
  fmLines.push(`line_spacing: ${fmLineSpacing.value}`)
  fmLines.push('')
  fmLines.push('---')

  const sectionParts: string[] = []
  for (const section of sections.value) {
    let sectionContent = ''
    if (section.multiEntry) {
      const entryTexts = section.entries
        .filter(e => e.header.trim() || e.content.trim())
        .map(e => {
          if (e.content.trim()) return `${e.header}\n${e.content}`
          return e.header
        })
      sectionContent = entryTexts.join('\n\n')
    } else {
      sectionContent = section.content
    }
    sectionParts.push(`# ${section.name}\n\n${sectionContent}`)
  }

  return fmLines.join('\n') + '\n' + sectionParts.join('\n\n---\n\n') + '\n'
}

function emitUpdate() {
  if (skipEmit) return
  emit('update:markdown', assembleMarkdown())
}

// Parse on initial load
parseMarkdown(props.markdown)

// Re-parse if markdown prop changes externally
watch(() => props.markdown, (newVal) => {
  // Only re-parse if the new value differs from what we'd assemble
  // (avoids infinite loop)
  const current = assembleMarkdown()
  if (newVal.trim() !== current.trim()) {
    parseMarkdown(newVal)
  }
})

// --- Section management ---
function addSection() {
  sections.value.push({
    name: 'New Section',
    multiEntry: false,
    content: '',
    entries: [],
  })
  emitUpdate()
}

function removeSection(index: number) {
  sections.value.splice(index, 1)
  emitUpdate()
}

function updateSectionContent(index: number, value: string) {
  sections.value[index].content = value
  emitUpdate()
}

function updateSectionEntries(index: number, entries: EntryData[]) {
  sections.value[index].entries = entries
  emitUpdate()
}

function updateSectionName(index: number, name: string) {
  sections.value[index].name = name
  emitUpdate()
}

// Template for new resumes
const STARTER_TEMPLATE = `---
name: Your Name
title: Software Engineer | City
email: your@email.com
phone: +1234567890
github: github.com/you
linkedin: linkedin.com/in/you
font_size: 11
line_spacing: 1.4

---
# Summary

A brief professional summary.

---
# Education

**Degree — University** *Start – End*
***Coursework***: Subject1; Subject2.

---
# Skills

**Category:** Skill1, Skill2, Skill3.

---
# Experience

**Role — Company (Location)** *Start – Present*
- Achievement or responsibility.

---
# Projects

**[Project Name](https://github.com/you/project)** | Stack - Tech1, Tech2
- What you built and the impact.
`

function loadTemplate() {
  parseMarkdown(STARTER_TEMPLATE)
  emit('update:markdown', STARTER_TEMPLATE)
}
</script>

<template>
  <div class="section-editor">
    <!-- Empty state -->
    <div v-if="!props.markdown && sections.length === 0" class="empty-state">
      <p>No resume yet. Start with a template or paste your markdown.</p>
      <button class="template-btn" @click="loadTemplate">Start with Template</button>
    </div>

    <template v-else>
      <!-- Resume Header -->
      <div class="fm-card">
        <h3>Resume Header</h3>
        <div class="fm-grid">
          <div class="fm-field">
            <label>Name</label>
            <input v-model="fmName" @input="emitUpdate()" placeholder="Your Name" />
          </div>
          <div class="fm-field">
            <label>Title / Location</label>
            <input v-model="fmTitle" @input="emitUpdate()" placeholder="Software Engineer | City" />
          </div>
          <div class="fm-field">
            <label>Email</label>
            <input v-model="fmEmail" @input="emitUpdate()" placeholder="you@email.com" />
          </div>
          <div class="fm-field">
            <label>Phone</label>
            <input v-model="fmPhone" @input="emitUpdate()" placeholder="+1234567890" />
          </div>
          <div class="fm-field">
            <label>Portfolio</label>
            <input v-model="fmPortfolio" @input="emitUpdate()" placeholder="yoursite.com" />
          </div>
          <div class="fm-field">
            <label>GitHub</label>
            <input v-model="fmGithub" @input="emitUpdate()" placeholder="github.com/you" />
          </div>
          <div class="fm-field">
            <label>LinkedIn</label>
            <input v-model="fmLinkedin" @input="emitUpdate()" placeholder="linkedin.com/in/you" />
          </div>
        </div>
      </div>

      <!-- Section Cards -->
      <SectionCard
        v-for="(section, index) in sections"
        :key="section.name + '-' + index"
        :title="section.name"
        :multiEntry="section.multiEntry"
        :content="section.content"
        :entries="section.entries"
        @update:content="updateSectionContent(index, $event)"
        @update:entries="updateSectionEntries(index, $event)"
        @remove="removeSection(index)"
      />

      <!-- Add Section -->
      <button class="add-section-btn" @click="addSection">+ Add Section</button>
    </template>
  </div>
</template>

<style scoped>
.section-editor { display: flex; flex-direction: column; gap: 10px; }

.empty-state {
  text-align: center; padding: 40px; color: #999;
  border: 2px dashed #e0e0e0; border-radius: 12px; background: #fafafa;
}
.empty-state p { margin-bottom: 12px; }
.template-btn {
  padding: 10px 24px; border: none; background: #111; color: #fff;
  border-radius: 8px; font-weight: 600; cursor: pointer;
}

.fm-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 14px;
}
.fm-card h3 { margin: 0 0 10px; font-size: 0.9rem; }
.fm-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
}
.fm-field { display: flex; flex-direction: column; gap: 2px; }
.fm-field label { font-size: 0.75rem; font-weight: 600; color: #666; }
.fm-field input {
  padding: 6px 8px; border: 1px solid #d9d9d9; border-radius: 6px;
  font-size: 0.82rem;
}
.fm-field input:focus { outline: none; border-color: #667eea; }

.add-section-btn {
  width: 100%; padding: 10px; border: 1px dashed #ccc; border-radius: 10px;
  background: #fafafa; font-size: 0.85rem; font-weight: 600;
  cursor: pointer; color: #666;
}
.add-section-btn:hover { background: #f0f0f0; border-color: #999; }
</style>
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SectionEditor.vue
git commit -m "feat: add SectionEditor component — parses markdown into structured UI"
```

---

### Task 9: Update ProfileView to Use SectionEditor

**Files:**
- Modify: `frontend/src/views/ProfileView.vue`

- [ ] **Step 1: Replace the textarea with SectionEditor**

Replace the full content of `frontend/src/views/ProfileView.vue` with:

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useProfile } from '../composables/useProfile'
import { useEditorStore } from '../stores/editor'
import SectionEditor from '../components/SectionEditor.vue'

const store = useEditorStore()
const { fetchProfile, createProfile, updateProfile } = useProfile()

const name = ref('')
const apiKey = ref('')
const resume = ref('')
const hasProfile = ref(false)
const saving = ref(false)
const msg = ref('')

onMounted(async () => {
  const p = await fetchProfile()
  if (p) {
    hasProfile.value = true
    name.value = p.name
    apiKey.value = p.gemini_api_key || ''
    resume.value = p.master_resume || ''
    store.profile = p
  }
})

function onResumeUpdate(md: string) {
  resume.value = md
}

async function save() {
  saving.value = true
  try {
    if (hasProfile.value) {
      const p = await updateProfile({
        name: name.value,
        master_resume: resume.value,
        gemini_api_key: apiKey.value,
      })
      store.profile = p
      if (store.markdown !== resume.value) store.markdown = resume.value
    } else {
      const p = await createProfile(name.value, resume.value, apiKey.value)
      store.profile = p
      store.markdown = resume.value
      hasProfile.value = true
    }
    msg.value = 'Profile saved!'
    setTimeout(() => msg.value = '', 2000)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="profile-page">
    <div class="profile-header-card">
      <h2>{{ hasProfile ? 'Edit Profile' : 'Create Profile' }}</h2>
      <div class="profile-fields">
        <div class="field">
          <label>Name</label>
          <input v-model="name" placeholder="Your name" />
        </div>
        <div class="field">
          <label>Gemini API Key</label>
          <input v-model="apiKey" type="password" placeholder="Gemini API Key" />
        </div>
      </div>
    </div>

    <SectionEditor :markdown="resume" @update:markdown="onResumeUpdate" />

    <div class="save-bar">
      <button class="save-btn" @click="save" :disabled="saving">
        {{ saving ? 'Saving...' : 'Save Profile' }}
      </button>
      <span v-if="msg" class="msg">{{ msg }}</span>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 800px; margin: 0 auto;
  display: flex; flex-direction: column; gap: 12px;
}
.profile-header-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px;
}
.profile-header-card h2 { margin: 0 0 10px; }
.profile-fields { display: flex; gap: 12px; }
.field { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.field label { font-weight: 600; font-size: 0.82rem; color: #555; }
.field input {
  padding: 8px; border: 1px solid #d0d0d0; border-radius: 8px; font-size: 0.85rem;
}

.save-bar {
  display: flex; align-items: center; gap: 10px;
  position: sticky; bottom: 12px;
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px;
  padding: 12px 16px; box-shadow: 0 -2px 8px rgba(0,0,0,.05);
}
.save-btn {
  padding: 10px 24px; font-weight: 700; border-radius: 8px;
  border: none; background: #111; color: #fff; cursor: pointer; font-size: 0.9rem;
}
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.msg { color: #28a745; font-size: 0.85rem; }
</style>
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/ProfileView.vue
git commit -m "feat: Profile page uses SectionEditor instead of raw textarea"
```

---

### Task 10: End-to-End Verification

**Files:** None (testing only)

- [ ] **Step 1: Run all backend tests**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && python -m pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 2: Run frontend type check**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Start dev server and test the Profile page**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && make dev` (or however the dev server starts)

Verify in browser:
1. Navigate to `/profile`
2. If a profile exists, sections should render as collapsible cards
3. Experience and Projects show individual entry cards with add/remove
4. Editing any field and clicking Save should persist correctly
5. Navigate to Editor — master resume should reflect Profile changes
6. If no profile exists, the "Start with Template" button should populate sections

- [ ] **Step 4: Test tailoring with entry selection**

1. Add 4-5 experience entries and 4-5 project entries on the Profile page
2. Save the profile
3. Go to Editor, add a job, paste a JD, click "Tailor All"
4. Verify the tailored result excludes some entries (not all 4-5 appear)
5. Verify included entries are relevant to the JD

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: section-based profile editor with smart entry selection for tailoring"
```
