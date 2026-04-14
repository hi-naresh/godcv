# GodCV v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix agent output formatting issues, add page mode toggle (1-page/multi-page), add parallel batch tailoring with tabs, overhaul UI/UX for simplicity, and add comprehensive tests.

**Architecture:** Format enforcement via post-processing validator + hardened agent prompts. Parallel jobs managed entirely in frontend state (multiple SSE streams). UI restructured into left panel (resume + job cards) and right panel (tabbed preview). Backend gains a seniority_level field and formatter service. Tests use pytest (backend) and vitest (frontend).

**Tech Stack:** Python 3.11+, FastAPI, pytest, Vue 3, TypeScript, Pinia, Vite, vitest, @vue/test-utils, marked

---

## File Structure

### New Files
| File | Purpose |
|------|---------|
| `backend/services/formatter.py` | Post-processing format validator/fixer for agent outputs |
| `backend/services/seniority.py` | JD seniority level auto-detection utility |
| `frontend/src/composables/useJobs.ts` | Job list management, per-job state, batch tailoring |
| `frontend/src/composables/useSeniority.ts` | Frontend seniority detection from JD text |
| `frontend/src/components/JobCard.vue` | Single job card (title, seniority, JD textarea, remove) |
| `frontend/src/components/PageModeToggle.vue` | 1-Page / Multi-Page toggle control |
| `frontend/src/components/TabBar.vue` | Tab bar for Original + job result tabs |
| `frontend/src/components/ApiKeyModal.vue` | Modal/popover for API key entry |
| `frontend/vitest.config.ts` | Vitest configuration |
| `frontend/src/__tests__/useMarkdown.test.ts` | Markdown rendering tests |
| `frontend/src/__tests__/useJobs.test.ts` | Job store tests |
| `frontend/src/__tests__/useSeniority.test.ts` | Seniority detection tests |
| `frontend/src/__tests__/ResumePreview.test.ts` | Preview component tests |
| `tests/__init__.py` | Python test package init |
| `tests/test_parser.py` | Parser unit tests |
| `tests/test_assembler.py` | Assembler unit tests |
| `tests/test_formatter.py` | Formatter unit tests |
| `tests/test_agents.py` | Agent output format tests |
| `tests/test_seniority.py` | Seniority detection tests |
| `tests/conftest.py` | Shared fixtures (sample resume, parsed sections) |

### Modified Files
| File | Changes |
|------|---------|
| `backend/agents/experience.py` | Hardened prompt with explicit formatting rules |
| `backend/agents/skills.py` | Hardened prompt with explicit formatting rules |
| `backend/agents/summary.py` | Hardened prompt with explicit formatting rules |
| `backend/agents/projects.py` | Hardened prompt with explicit formatting rules |
| `backend/agents/orchestrator.py` | Accept seniority_level param, add to prompt |
| `backend/agents/bus.py` | Call formatter on each agent output before returning |
| `backend/db/models.py` | Add seniority_level to TailorRequest |
| `backend/routers/tailor.py` | Pass seniority_level to orchestrator |
| `frontend/package.json` | Add vitest, @vue/test-utils devDependencies |
| `frontend/src/stores/editor.ts` | Replace single-job state with multi-job map |
| `frontend/src/composables/useTailor.ts` | Accept jobId, scope state to that job |
| `frontend/src/composables/useMarkdown.ts` | Read font_size/line_spacing from frontmatter |
| `frontend/src/components/ResumePreview.vue` | Page mode support, multi-sheet rendering |
| `frontend/src/components/MarkdownEditor.vue` | Minor: better empty state |
| `frontend/src/views/EditorView.vue` | Full restructure: two-panel layout with tabs |
| `frontend/src/App.vue` | API key button in nav |
| `frontend/src/style.css` | Multi-page CSS, print improvements, responsive |
| `pyproject.toml` | Add pytest to dev dependencies |

---

## Task 1: Test Infrastructure Setup

**Files:**
- Modify: `pyproject.toml`
- Modify: `frontend/package.json`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `frontend/vitest.config.ts`

- [ ] **Step 1: Add pytest to pyproject.toml**

Add to `pyproject.toml` under `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
pdf = ["weasyprint>=63"]
dev = ["pytest>=8.0", "pytest-asyncio>=0.24"]
```

- [ ] **Step 2: Install pytest**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && pip install -e ".[dev]"`
Expected: pytest and pytest-asyncio installed successfully

- [ ] **Step 3: Create tests/__init__.py**

```python
```

(Empty file to make tests a package)

- [ ] **Step 4: Create tests/conftest.py with shared fixtures**

```python
import pytest
from collections import OrderedDict

SAMPLE_RESUME_MD = """---
name: Test User
title: Software Engineer | London, UK
email: test@example.com
phone: +441234567890
portfolio: example.com
github: github.com/testuser
linkedin: linkedin.com/in/testuser
font_size: 11
line_spacing: 1.4

---
# Summary
Software engineer with 3 years of experience in Python and cloud infrastructure.

---
# Education

**M.Sc. in Computer Science - University of London** *Jan 2023 – Jan 2024*
***Coursework**:* Distributed Systems; Machine Learning; Data Engineering.

---
# Skills

**Backend:** Python, FastAPI, Django, PostgreSQL, Redis.

**Cloud/Infra:** AWS, Docker, Kubernetes, Terraform, CI/CD.

**Programming:** Python, TypeScript, Go.

---
# Experience

**Senior Engineer — Acme Corp (London, ~50 people)** *Jan 2023 – Present*
- Built scalable data pipelines processing 1M+ records daily.
- Designed microservices architecture reducing latency by 30%.

**Junior Developer — StartupXYZ (Remote, ~10 people)** *Jun 2021 – Dec 2022*
- Developed REST APIs serving 500+ daily active users.
- Implemented CI/CD pipelines with GitHub Actions and Docker.

---
# Projects

**[DataFlow Engine](https://github.com/test/dataflow)** | Stack - Python, Apache Kafka, PostgreSQL, Docker
- Built real-time data streaming pipeline processing 10K events/second.

**[CloudDash](https://clouddash.dev)** | Stack - TypeScript, React, AWS Lambda, DynamoDB
- Dashboard for monitoring cloud infrastructure costs and usage.

---
# Volunteering and Interests
**Open Source Contributor** - Regular contributor to Python data tools.

**Interests**: Hiking, Chess, Coffee.
"""

SAMPLE_JD = """Senior Backend Engineer - TechCorp

We're looking for a Senior Backend Engineer to join our platform team.

Requirements:
- 5+ years of experience with Python and distributed systems
- Experience with Kubernetes, Docker, and cloud infrastructure (AWS preferred)
- Strong background in data pipelines and real-time processing
- Experience leading technical projects and mentoring junior engineers
- Familiarity with FastAPI or Django

Nice to have:
- Experience with Apache Kafka or similar streaming platforms
- Knowledge of infrastructure-as-code (Terraform)
"""


@pytest.fixture
def sample_resume():
    return SAMPLE_RESUME_MD


@pytest.fixture
def sample_jd():
    return SAMPLE_JD


@pytest.fixture
def parsed_resume():
    from backend.services.parser import parse_resume
    return parse_resume(SAMPLE_RESUME_MD)
```

- [ ] **Step 5: Install vitest and vue test utils for frontend**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npm install -D vitest @vue/test-utils jsdom`
Expected: packages added to devDependencies

- [ ] **Step 6: Create frontend/vitest.config.ts**

```typescript
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    include: ['src/__tests__/**/*.test.ts'],
  },
})
```

- [ ] **Step 7: Add test script to frontend/package.json**

Add to `"scripts"`:
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 8: Verify both test runners work**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && pytest --co -q`
Expected: "no tests ran" (collection works, no tests yet)

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vitest run`
Expected: "no test files found" (vitest configured correctly)

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml tests/ frontend/vitest.config.ts frontend/package.json frontend/package-lock.json
git commit -m "chore: set up pytest and vitest test infrastructure"
```

---

## Task 2: Format Validator (Backend)

**Files:**
- Create: `backend/services/formatter.py`
- Create: `tests/test_formatter.py`

- [ ] **Step 1: Write failing tests for formatter**

Create `tests/test_formatter.py`:

```python
import pytest
from backend.services.formatter import validate_and_fix


class TestExperienceFormatting:
    def test_adds_newline_before_bold_title(self):
        broken = "Some text**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n- Built pipelines."
        fixed = validate_and_fix("experience", broken)
        assert "\n\n**Senior Engineer — Acme Corp**" in fixed

    def test_ensures_bullets_on_own_lines(self):
        broken = "**Role — Company** *Jan 2023 – Present*\n- First point. - Second point."
        fixed = validate_and_fix("experience", broken)
        lines = fixed.strip().split("\n")
        bullet_lines = [l for l in lines if l.strip().startswith("- ")]
        assert len(bullet_lines) >= 2

    def test_preserves_correct_formatting(self):
        correct = "**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n- Built scalable pipelines.\n- Designed microservices."
        result = validate_and_fix("experience", correct)
        assert result.strip() == correct.strip()

    def test_normalizes_multiple_blank_lines(self):
        messy = "**Role — Company** *Dates*\n\n\n\n- Bullet one.\n\n\n- Bullet two."
        fixed = validate_and_fix("experience", messy)
        assert "\n\n\n" not in fixed

    def test_strips_trailing_whitespace(self):
        messy = "**Role — Company** *Dates*   \n- Bullet one.   \n- Bullet two.  "
        fixed = validate_and_fix("experience", messy)
        for line in fixed.split("\n"):
            assert line == line.rstrip()


class TestSkillsFormatting:
    def test_adds_blank_line_between_categories(self):
        broken = "**Backend:** Python, FastAPI.\n**Cloud:** AWS, Docker."
        fixed = validate_and_fix("skills", broken)
        assert "**Backend:** Python, FastAPI.\n\n**Cloud:** AWS, Docker." in fixed

    def test_preserves_correct_skills_format(self):
        correct = "**Backend:** Python, FastAPI.\n\n**Cloud:** AWS, Docker."
        result = validate_and_fix("skills", correct)
        assert result.strip() == correct.strip()

    def test_fixes_missing_bold_colon_pattern(self):
        broken = "Backend: Python, FastAPI.\n\nCloud: AWS, Docker."
        fixed = validate_and_fix("skills", broken)
        assert "**Backend:**" in fixed
        assert "**Cloud:**" in fixed


class TestSummaryFormatting:
    def test_removes_accidental_headers(self):
        broken = "# Summary\nExperienced engineer with 5 years of Python."
        fixed = validate_and_fix("summary", broken)
        assert not fixed.strip().startswith("#")

    def test_preserves_plain_paragraph(self):
        correct = "Experienced engineer with 5 years of Python and cloud infrastructure."
        result = validate_and_fix("summary", correct)
        assert result.strip() == correct.strip()


class TestProjectsFormatting:
    def test_adds_newline_before_project_entry(self):
        broken = "Some text**[Project](url)** | Stack - Python\n- Built thing."
        fixed = validate_and_fix("projects", broken)
        assert "\n\n**[Project](url)**" in fixed or fixed.strip().startswith("**[Project](url)**")

    def test_preserves_correct_project_format(self):
        correct = "**[Project](https://example.com)** | Stack - Python, Docker\n- Built real-time pipeline."
        result = validate_and_fix("projects", correct)
        assert result.strip() == correct.strip()


class TestGenericFormatting:
    def test_unknown_section_still_normalizes(self):
        messy = "Some text   \n\n\n\nMore text.  "
        fixed = validate_and_fix("unknown", messy)
        assert "\n\n\n" not in fixed
        for line in fixed.split("\n"):
            assert line == line.rstrip()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && pytest tests/test_formatter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.services.formatter'`

- [ ] **Step 3: Implement formatter**

Create `backend/services/formatter.py`:

```python
import re


def validate_and_fix(section_name: str, content: str) -> str:
    """Validate and fix markdown formatting for a given section type.

    Runs generic fixes (whitespace normalization) plus section-specific fixes.
    """
    content = _normalize_whitespace(content)

    section_lower = section_name.lower()
    if section_lower == "experience" or section_lower.startswith("experience:"):
        content = _fix_experience(content)
    elif section_lower == "skills":
        content = _fix_skills(content)
    elif section_lower == "summary":
        content = _fix_summary(content)
    elif section_lower == "projects":
        content = _fix_projects(content)

    content = _normalize_whitespace(content)
    return content


def _normalize_whitespace(content: str) -> str:
    """Strip trailing whitespace per line, collapse 3+ blank lines to 2."""
    lines = [line.rstrip() for line in content.split("\n")]
    result = "\n".join(lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def _fix_experience(content: str) -> str:
    """Ensure experience entries have proper line breaks and bullet formatting."""
    # Ensure bold title lines are on their own line
    content = re.sub(
        r"([^\n])(\*\*[^*]+(?:—|–|-)[^*]+\*\*)",
        r"\1\n\n\2",
        content,
    )

    # Ensure bullets that are joined on one line get split
    # Match "- text. - text" or "- text.- text" patterns
    content = re.sub(r"(\.\s*)- ", r".\n- ", content)

    # Ensure each bullet starts on its own line
    content = re.sub(r"([^\n])(\n?)- ", lambda m: m.group(1) + "\n- " if m.group(1) != "\n" else m.group(0), content)

    return content


def _fix_skills(content: str) -> str:
    """Ensure skills categories have proper formatting."""
    # Add blank line between category entries
    # Match end of one category line followed immediately by start of next
    content = re.sub(
        r"(\.\s*)\n(\*\*[A-Za-z/]+:?\*\*)",
        r"\1\n\n\2",
        content,
    )

    # Fix unbolded category headers: "Category: items" -> "**Category:** items"
    content = re.sub(
        r"^([A-Z][A-Za-z /]+):\s",
        r"**\1:** ",
        content,
        flags=re.MULTILINE,
    )

    # Ensure bold categories have colon inside: **Category** items -> **Category:** items
    content = re.sub(
        r"\*\*([A-Za-z /]+)\*\*\s+(?!\|)",
        lambda m: f"**{m.group(1).rstrip(':')}:** " if ":" not in m.group(1) else m.group(0),
        content,
    )

    return content


def _fix_summary(content: str) -> str:
    """Remove accidental headers from summary output."""
    # Remove any markdown headers
    content = re.sub(r"^#+\s*.*\n?", "", content, flags=re.MULTILINE)
    return content.strip()


def _fix_projects(content: str) -> str:
    """Ensure project entries have proper line breaks."""
    # Ensure bold project title lines are on their own line
    content = re.sub(
        r"([^\n])(\*\*\[[^\]]+\])",
        r"\1\n\n\2",
        content,
    )

    # Also handle non-linked project titles
    content = re.sub(
        r"([^\n])(\*\*[A-Z][^*]*\*\*\s*\|)",
        r"\1\n\n\2",
        content,
    )

    return content
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && pytest tests/test_formatter.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/formatter.py tests/test_formatter.py
git commit -m "feat: add format validator for agent output post-processing"
```

---

## Task 3: Parser and Assembler Tests

**Files:**
- Create: `tests/test_parser.py`
- Create: `tests/test_assembler.py`

- [ ] **Step 1: Write parser tests**

Create `tests/test_parser.py`:

```python
import pytest
from backend.services.parser import (
    parse_frontmatter,
    parse_experience_entries,
    parse_sections,
    parse_resume,
    _extract_company_key,
)


class TestParseFrontmatter:
    def test_extracts_frontmatter_and_body(self, sample_resume):
        fm, body = parse_frontmatter(sample_resume)
        assert "name: Test User" in fm
        assert fm.startswith("---")
        assert fm.endswith("---")
        assert "# Summary" in body

    def test_no_frontmatter_returns_full_body(self):
        md = "# Summary\nHello world"
        fm, body = parse_frontmatter(md)
        assert fm == ""
        assert body == md

    def test_malformed_frontmatter_returns_full_body(self):
        md = "---\nno closing marker\n# Summary\nHello"
        fm, body = parse_frontmatter(md)
        # Should either extract or fall through gracefully
        assert "Summary" in body or "Summary" in fm


class TestParseExperienceEntries:
    def test_splits_two_entries(self):
        content = (
            "**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n"
            "- Built pipelines.\n\n"
            "**Junior Dev — StartupXYZ** *Jun 2021 – Dec 2022*\n"
            "- Built APIs."
        )
        entries = parse_experience_entries(content)
        assert len(entries) == 2
        assert entries[0]["key"] == "Acme"
        assert entries[1]["key"] == "StartupXYZ"

    def test_single_entry(self):
        content = "**Engineer — BigCo** *2023 – Present*\n- Did things."
        entries = parse_experience_entries(content)
        assert len(entries) == 1

    def test_entry_has_content(self):
        content = "**Role — Company** *Dates*\n- Bullet one.\n- Bullet two."
        entries = parse_experience_entries(content)
        assert "Bullet one" in entries[0]["content"]
        assert "Bullet two" in entries[0]["content"]


class TestExtractCompanyKey:
    def test_em_dash_separator(self):
        assert _extract_company_key("AI Engineer — BotWot iCX") == "BotWot"

    def test_en_dash_separator(self):
        assert _extract_company_key("Engineer – Google LLC") == "Google"

    def test_hyphen_separator(self):
        assert _extract_company_key("Intern - SAILC AURO") == "AURO"

    def test_parenthetical_stripped(self):
        assert _extract_company_key("Engineer — NestDore (London)") == "NestDore"


class TestParseSections:
    def test_all_sections_found(self, sample_resume):
        _, body = parse_frontmatter(sample_resume)
        sections, separators = parse_sections(body)
        assert "Summary" in sections
        assert "Education" in sections
        assert "Skills" in sections
        assert "Experience" in sections
        assert "Projects" in sections

    def test_experience_has_entries(self, sample_resume):
        _, body = parse_frontmatter(sample_resume)
        sections, _ = parse_sections(body)
        exp = sections["Experience"]
        assert isinstance(exp, dict)
        assert "_entries" in exp
        assert len(exp["_entries"]) == 2

    def test_separators_tracked(self, sample_resume):
        _, body = parse_frontmatter(sample_resume)
        _, separators = parse_sections(body)
        assert len(separators) > 0


class TestParseResume:
    def test_full_parse(self, sample_resume):
        result = parse_resume(sample_resume)
        assert "frontmatter" in result
        assert "sections" in result
        assert "separators" in result
        assert "name: Test User" in result["frontmatter"]
```

- [ ] **Step 2: Write assembler tests**

Create `tests/test_assembler.py`:

```python
import pytest
from backend.services.parser import parse_resume
from backend.services.assembler import assemble_resume


class TestAssembleUnmodified:
    def test_roundtrip_preserves_content(self, sample_resume):
        parsed = parse_resume(sample_resume)
        reassembled = assemble_resume(parsed, {}, None)
        # All section headers present
        assert "# Summary" in reassembled
        assert "# Experience" in reassembled
        assert "# Skills" in reassembled
        assert "# Projects" in reassembled
        # Frontmatter preserved
        assert "name: Test User" in reassembled

    def test_roundtrip_preserves_experience_entries(self, sample_resume):
        parsed = parse_resume(sample_resume)
        reassembled = assemble_resume(parsed, {}, None)
        assert "Senior Engineer — Acme Corp" in reassembled
        assert "Junior Developer — StartupXYZ" in reassembled


class TestAssembleWithModifications:
    def test_replace_single_section(self, sample_resume):
        parsed = parse_resume(sample_resume)
        new_summary = "New AI-focused summary for testing."
        reassembled = assemble_resume(parsed, {"Summary": new_summary}, None)
        assert new_summary in reassembled
        # Other sections unchanged
        assert "Senior Engineer — Acme Corp" in reassembled

    def test_replace_experience_entry(self, sample_resume):
        parsed = parse_resume(sample_resume)
        new_entry = "**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n- Rewrote bullet point."
        reassembled = assemble_resume(parsed, {}, {"Acme": new_entry})
        assert "Rewrote bullet point" in reassembled
        # Other entry unchanged
        assert "Junior Developer — StartupXYZ" in reassembled

    def test_frontmatter_always_preserved(self, sample_resume):
        parsed = parse_resume(sample_resume)
        reassembled = assemble_resume(
            parsed,
            {"Summary": "Changed.", "Skills": "**New:** Skill."},
            None,
        )
        assert "name: Test User" in reassembled
        assert "email: test@example.com" in reassembled

    def test_separators_between_sections(self, sample_resume):
        parsed = parse_resume(sample_resume)
        reassembled = assemble_resume(parsed, {}, None)
        # There should be --- separators between sections
        assert "---" in reassembled
```

- [ ] **Step 3: Run all tests**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && pytest tests/test_parser.py tests/test_assembler.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_parser.py tests/test_assembler.py
git commit -m "test: add parser and assembler unit tests"
```

---

## Task 4: Harden Agent Prompts + Wire Formatter into Bus

**Files:**
- Modify: `backend/agents/experience.py`
- Modify: `backend/agents/skills.py`
- Modify: `backend/agents/summary.py`
- Modify: `backend/agents/projects.py`
- Modify: `backend/agents/bus.py`
- Create: `tests/test_agents.py`

- [ ] **Step 1: Write agent output format tests**

Create `tests/test_agents.py`:

```python
import pytest
from backend.services.formatter import validate_and_fix


class TestExperienceAgentOutput:
    """Test that typical agent outputs pass or get fixed by the formatter."""

    def test_well_formed_entry_passes(self):
        output = (
            "**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n"
            "- Built scalable data pipelines processing 1M+ records daily.\n"
            "- Designed microservices architecture reducing latency by 30%."
        )
        result = validate_and_fix("experience", output)
        assert "**Senior Engineer — Acme Corp**" in result
        assert result.count("- ") == 2

    def test_collapsed_bullets_get_fixed(self):
        output = (
            "**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n"
            "- Built scalable data pipelines processing 1M+ records daily. - Designed microservices."
        )
        result = validate_and_fix("experience", output)
        lines = [l for l in result.split("\n") if l.strip().startswith("- ")]
        assert len(lines) >= 2

    def test_missing_newline_before_title_fixed(self):
        output = "Some preamble text**Senior Engineer — Acme Corp** *Jan 2023 – Present*\n- Bullet."
        result = validate_and_fix("experience", output)
        assert "\n**Senior Engineer" in result


class TestSkillsAgentOutput:
    def test_well_formed_skills_pass(self):
        output = (
            "**Backend:** Python, FastAPI, Django.\n\n"
            "**Cloud/Infra:** AWS, Docker, Kubernetes."
        )
        result = validate_and_fix("skills", output)
        assert "**Backend:**" in result
        assert "**Cloud/Infra:**" in result

    def test_missing_blank_line_between_categories_fixed(self):
        output = (
            "**Backend:** Python, FastAPI.\n"
            "**Cloud:** AWS, Docker."
        )
        result = validate_and_fix("skills", output)
        assert "**Backend:** Python, FastAPI.\n\n**Cloud:**" in result


class TestSummaryAgentOutput:
    def test_clean_paragraph_passes(self):
        output = "Experienced engineer specializing in Python and cloud infrastructure."
        result = validate_and_fix("summary", output)
        assert result == output

    def test_accidental_header_removed(self):
        output = "# Summary\nExperienced engineer specializing in Python."
        result = validate_and_fix("summary", output)
        assert not result.startswith("#")
        assert "Experienced engineer" in result


class TestProjectsAgentOutput:
    def test_well_formed_project_passes(self):
        output = (
            "**[DataFlow](https://github.com/test)** | Stack - Python, Kafka\n"
            "- Built real-time streaming pipeline."
        )
        result = validate_and_fix("projects", output)
        assert "**[DataFlow]" in result
```

- [ ] **Step 2: Run tests to confirm they pass with existing formatter**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && pytest tests/test_agents.py -v`
Expected: All PASS (these use the formatter from Task 2)

- [ ] **Step 3: Harden experience agent prompt**

Replace the prompt in `backend/agents/experience.py` (lines 10-29):

```python
        prompt = f"""You are a resume experience bullet point writer. Rewrite ONLY this single job entry to better match the job description.

RULES:
- Keep the exact same job title, company name, and dates line (first bold line) UNCHANGED
- Only modify the bullet points below the title line
- Maintain truthfulness -- reword to emphasize relevant aspects, don't fabricate
- Use action verbs and keywords from the job description
- Keep quantified achievements (numbers, percentages) -- they are real
- Return the COMPLETE entry (title line + bullets), no section header
- Keep 2-4 bullet points per entry

FORMATTING (CRITICAL — follow exactly):
- The title line MUST be on its own line: **Role — Company** *Dates*
- Each bullet MUST start on its own new line with "- "
- Do NOT merge bullets onto the same line
- There must be a blank line before the title if any text precedes it
- Example of correct format:

**Senior Engineer — Acme Corp** *Jan 2023 – Present*
- Built scalable data pipelines processing 1M+ records daily.
- Designed microservices architecture reducing latency by 30%.

SPECIFIC INSTRUCTIONS: {instructions}

ORIGINAL ENTRY:
{section_content}

JOB DESCRIPTION:
{job_description}

Rewritten entry:"""
```

- [ ] **Step 4: Harden skills agent prompt**

Replace the prompt in `backend/agents/skills.py` (lines 13-32):

```python
        prompt = f"""You are a resume skills section optimizer. Reorder and adjust this skills section to better match the job description.

RULES:
- Keep ALL existing skills -- do not remove any
- Reorder categories and skills within categories to put most relevant first
- You may add 1-2 skills from the JD if the candidate likely has them based on their experience
- Do NOT fabricate skills the candidate doesn't have
- Return ONLY the skills section content, no section header (no "# Skills")

FORMATTING (CRITICAL — follow exactly):
- Each category MUST use bold header with colon: **Category Name:** skill1, skill2, skill3.
- Each category MUST be separated by exactly ONE blank line
- Do NOT merge categories onto the same line
- Example of correct format:

**Backend:** Python, FastAPI, Django, PostgreSQL, Redis.

**Cloud/Infra:** AWS, Docker, Kubernetes, Terraform, CI/CD.

**Programming:** Python, TypeScript, Go.

SKILLS TO PROMOTE (put first): {', '.join(promote) if promote else 'Use your judgment'}
SKILLS TO DEMOTE (put later): {', '.join(demote) if demote else 'None'}

ORIGINAL SKILLS:
{section_content}

JOB DESCRIPTION:
{job_description}

Reordered skills section:"""
```

- [ ] **Step 5: Harden summary agent prompt**

Replace the prompt in `backend/agents/summary.py` (lines 10-27):

```python
        prompt = f"""You are a resume summary writer. Rewrite ONLY this summary section to better match the job description.

RULES:
- Keep it to 2-3 sentences maximum
- Maintain truthfulness -- only emphasize existing skills/experience
- Use keywords from the job description naturally
- Keep the same professional tone
- Return ONLY the rewritten summary text

FORMATTING (CRITICAL — follow exactly):
- Return ONLY a plain text paragraph — no markdown headers, no bullet points
- Do NOT start with "# Summary" or any header
- Do NOT add "---" separators
- Just the paragraph text, nothing else

SPECIFIC INSTRUCTIONS: {instructions}

ORIGINAL SUMMARY:
{section_content}

JOB DESCRIPTION:
{job_description}

Rewritten summary:"""
```

- [ ] **Step 6: Harden projects agent prompt**

Replace the prompt in `backend/agents/projects.py` (lines 12-30):

```python
        prompt = f"""You are a resume projects section optimizer. Reorder and adjust this projects section to better match the job description.

RULES:
- Keep ALL existing projects
- Reorder to put most relevant projects first
- You may slightly adjust bullet point wording to emphasize relevant aspects
- Keep project names, links, and tech stacks accurate
- Return ONLY the projects content, no section header (no "# Projects")

FORMATTING (CRITICAL — follow exactly):
- Each project MUST start on its own line with bold title: **[Project Name](url)** | Stack - tech1, tech2
- If project has no URL, use: **Project Name** | Stack - tech1, tech2
- Each bullet MUST start on its own new line with "- "
- Separate projects with exactly ONE blank line
- Example of correct format:

**[DataFlow Engine](https://github.com/test/dataflow)** | Stack - Python, Apache Kafka, Docker
- Built real-time data streaming pipeline processing 10K events/second.

**[CloudDash](https://clouddash.dev)** | Stack - TypeScript, React, AWS Lambda
- Dashboard for monitoring cloud infrastructure costs and usage.

PROJECTS TO PROMOTE (put first): {', '.join(promote) if promote else 'Use your judgment based on JD'}

ORIGINAL PROJECTS:
{section_content}

JOB DESCRIPTION:
{job_description}

Reordered projects section:"""
```

- [ ] **Step 7: Wire formatter into AgentBus**

Modify `backend/agents/bus.py`. Add import at top (after line 8):

```python
from backend.services.formatter import validate_and_fix
```

Modify `_run_single_agent` function (line 122-129) to apply formatter:

```python
async def _run_single_agent(agent, name: str, content: str, call: dict, jd: str) -> tuple[str, str]:
    result = await agent.run(
        section_content=content,
        instructions=call.get("instructions", ""),
        job_description=jd,
        extra=call,
    )
    # Determine section type for formatting
    section_type = name.split(":")[0] if ":" in name else name
    result = validate_and_fix(section_type, result)
    return name, result
```

- [ ] **Step 8: Run all tests**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 9: Commit**

```bash
git add backend/agents/ backend/services/formatter.py tests/test_agents.py
git commit -m "feat: harden agent prompts and wire format validator into agent bus"
```

---

## Task 5: Seniority Detection

**Files:**
- Create: `backend/services/seniority.py`
- Create: `tests/test_seniority.py`
- Create: `frontend/src/composables/useSeniority.ts`

- [ ] **Step 1: Write seniority detection tests**

Create `tests/test_seniority.py`:

```python
import pytest
from backend.services.seniority import detect_seniority


class TestSeniorityDetection:
    def test_graduate_keywords(self):
        jd = "Looking for a graduate software engineer to join our team. No experience required."
        assert detect_seniority(jd) == "graduate"

    def test_entry_level(self):
        jd = "Entry level position for a data analyst. 0-1 years experience."
        assert detect_seniority(jd) == "graduate"

    def test_junior(self):
        jd = "Junior developer with 1-2 years of experience in Python."
        assert detect_seniority(jd) == "junior"

    def test_mid_level_years(self):
        jd = "We need someone with 3-5 years of experience building distributed systems."
        assert detect_seniority(jd) == "mid-level"

    def test_senior_explicit(self):
        jd = "Senior Backend Engineer with 5+ years experience leading projects."
        assert detect_seniority(jd) == "senior"

    def test_senior_years(self):
        jd = "Requires 7 years of experience in software development."
        assert detect_seniority(jd) == "senior"

    def test_lead(self):
        jd = "Lead Engineer to manage a team of 8 developers and architect solutions."
        assert detect_seniority(jd) == "lead"

    def test_principal(self):
        jd = "Principal Engineer to drive technical strategy across the organization."
        assert detect_seniority(jd) == "principal"

    def test_no_signals_returns_none(self):
        jd = "Software engineer to work on our platform. Python and AWS required."
        assert detect_seniority(jd) is None

    def test_case_insensitive(self):
        jd = "SENIOR SOFTWARE ENGINEER needed for our team."
        assert detect_seniority(jd) == "senior"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && pytest tests/test_seniority.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement seniority detection**

Create `backend/services/seniority.py`:

```python
import re


def detect_seniority(job_description: str) -> str | None:
    """Detect seniority level from job description text.

    Returns one of: 'graduate', 'junior', 'mid-level', 'senior', 'lead', 'principal', or None.
    """
    text = job_description.lower()

    # Check explicit title keywords (highest priority)
    if re.search(r"\b(principal|staff)\b", text):
        return "principal"

    if re.search(r"\b(lead|head|manager)\b.*\b(engineer|developer|team)\b", text) or \
       re.search(r"\b(engineer|developer)\b.*\b(lead|head)\b", text) or \
       re.search(r"\btech(?:nical)?\s+lead\b", text) or \
       re.search(r"\blead\s+(?:software|backend|frontend|full\s*stack)\b", text):
        return "lead"

    if re.search(r"\bsenior\b", text):
        return "senior"

    if re.search(r"\bjunior\b", text):
        return "junior"

    if re.search(r"\b(?:graduate|grad|entry[\s-]level|new\s+grad|intern(?:ship)?|trainee)\b", text):
        return "graduate"

    # Check years of experience
    years_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)", text)
    if years_match:
        years = int(years_match.group(1))
        if years <= 1:
            return "graduate"
        elif years <= 2:
            return "junior"
        elif years <= 5:
            return "mid-level"
        else:
            return "senior"

    # Check range patterns like "3-5 years"
    range_match = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)", text)
    if range_match:
        upper = int(range_match.group(2))
        if upper <= 2:
            return "junior"
        elif upper <= 5:
            return "mid-level"
        else:
            return "senior"

    return None
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && pytest tests/test_seniority.py -v`
Expected: All PASS

- [ ] **Step 5: Create frontend seniority composable**

Create `frontend/src/composables/useSeniority.ts`:

```typescript
export type SeniorityLevel = 'graduate' | 'junior' | 'mid-level' | 'senior' | 'lead' | 'principal'

export function detectSeniority(jobDescription: string): SeniorityLevel | null {
  const text = jobDescription.toLowerCase()

  if (/\b(principal|staff)\b/.test(text)) return 'principal'

  if (
    /\b(lead|head|manager)\b.*\b(engineer|developer|team)\b/.test(text) ||
    /\b(engineer|developer)\b.*\b(lead|head)\b/.test(text) ||
    /\btech(?:nical)?\s+lead\b/.test(text) ||
    /\blead\s+(?:software|backend|frontend|full\s*stack)\b/.test(text)
  ) return 'lead'

  if (/\bsenior\b/.test(text)) return 'senior'
  if (/\bjunior\b/.test(text)) return 'junior'
  if (/\b(?:graduate|grad|entry[\s-]level|new\s+grad|intern(?:ship)?|trainee)\b/.test(text)) return 'graduate'

  const yearsMatch = text.match(/(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)/)
  if (yearsMatch) {
    const years = parseInt(yearsMatch[1])
    if (years <= 1) return 'graduate'
    if (years <= 2) return 'junior'
    if (years <= 5) return 'mid-level'
    return 'senior'
  }

  const rangeMatch = text.match(/(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)/)
  if (rangeMatch) {
    const upper = parseInt(rangeMatch[2])
    if (upper <= 2) return 'junior'
    if (upper <= 5) return 'mid-level'
    return 'senior'
  }

  return null
}

export const SENIORITY_OPTIONS: SeniorityLevel[] = [
  'graduate', 'junior', 'mid-level', 'senior', 'lead', 'principal'
]
```

- [ ] **Step 6: Write frontend seniority test**

Create `frontend/src/__tests__/useSeniority.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { detectSeniority } from '../composables/useSeniority'

describe('detectSeniority', () => {
  it('detects graduate from keywords', () => {
    expect(detectSeniority('Graduate software engineer position')).toBe('graduate')
  })

  it('detects senior from keyword', () => {
    expect(detectSeniority('Senior Backend Engineer with 5+ years')).toBe('senior')
  })

  it('detects mid-level from years range', () => {
    expect(detectSeniority('3-5 years of experience required')).toBe('mid-level')
  })

  it('detects lead from title', () => {
    expect(detectSeniority('Lead Software Engineer to manage a team')).toBe('lead')
  })

  it('detects principal', () => {
    expect(detectSeniority('Principal Engineer driving technical strategy')).toBe('principal')
  })

  it('returns null for ambiguous JD', () => {
    expect(detectSeniority('Software engineer to work on Python projects')).toBeNull()
  })
})
```

- [ ] **Step 7: Run frontend tests**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vitest run`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add backend/services/seniority.py tests/test_seniority.py frontend/src/composables/useSeniority.ts frontend/src/__tests__/useSeniority.test.ts
git commit -m "feat: add seniority level auto-detection from job descriptions"
```

---

## Task 6: Backend — Add Seniority to Tailor Request + Orchestrator

**Files:**
- Modify: `backend/db/models.py:36-39`
- Modify: `backend/agents/orchestrator.py`
- Modify: `backend/routers/tailor.py:58`

- [ ] **Step 1: Add seniority_level to TailorRequest**

In `backend/db/models.py`, modify the `TailorRequest` class (line 36-39):

```python
class TailorRequest(BaseModel):
    job_description: str
    resume_override: str | None = None
    gemini_api_key: str | None = None
    seniority_level: str | None = None
```

- [ ] **Step 2: Update orchestrator to accept seniority_level**

In `backend/agents/orchestrator.py`, modify the `analyze` method signature (line 8-12) to accept seniority:

```python
    async def analyze(
        self,
        resume_markdown: str,
        job_description: str,
        role_insights: list[dict] | None = None,
        seniority_level: str | None = None,
    ) -> dict:
```

Add seniority context into the prompt. After the `insights_context` block (after line 22), add:

```python
        seniority_context = ""
        if seniority_level:
            seniority_guidance = {
                "graduate": "Target is a GRADUATE/ENTRY-LEVEL role. Emphasize coursework, projects, internships, and eagerness to learn. Tone down leadership language.",
                "junior": "Target is a JUNIOR role. Emphasize hands-on technical work, learning ability, and projects. Keep language confident but not senior.",
                "mid-level": "Target is a MID-LEVEL role. Balance technical depth with some ownership. Show progression and impact.",
                "senior": "Target is a SENIOR role. Emphasize leadership, architecture decisions, mentoring, and measurable business impact.",
                "lead": "Target is a LEAD/MANAGEMENT role. Emphasize team leadership, cross-functional work, technical strategy, and people management.",
                "principal": "Target is a PRINCIPAL/STAFF role. Emphasize org-wide impact, technical vision, and strategic thinking.",
            }
            seniority_context = f"\nSENIORITY CONTEXT:\n{seniority_guidance.get(seniority_level, '')}\n"
```

Insert `{seniority_context}` into the prompt string, right after `{insights_context}` (line 41).

- [ ] **Step 3: Pass seniority from router to orchestrator**

In `backend/routers/tailor.py`, modify the orchestrator call (line 58):

```python
            plan = await orchestrator.analyze(resume_md, job_description, insights, request.seniority_level)
```

- [ ] **Step 4: Run all backend tests**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && pytest tests/ -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/db/models.py backend/agents/orchestrator.py backend/routers/tailor.py
git commit -m "feat: pass seniority level through tailor pipeline to orchestrator"
```

---

## Task 7: Frontend — useMarkdown Improvements (Font Size + Line Spacing from Frontmatter)

**Files:**
- Modify: `frontend/src/composables/useMarkdown.ts`
- Create: `frontend/src/__tests__/useMarkdown.test.ts`

- [ ] **Step 1: Write useMarkdown tests**

Create `frontend/src/__tests__/useMarkdown.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { useMarkdown } from '../composables/useMarkdown'

const { renderResume, parseFrontmatter } = useMarkdown()

describe('parseFrontmatter', () => {
  it('extracts name and title', () => {
    const md = '---\nname: John Doe\ntitle: Engineer\n---\n# Summary\nHello'
    const { data, body } = parseFrontmatter(md)
    expect(data.name).toBe('John Doe')
    expect(data.title).toBe('Engineer')
    expect(body).toContain('# Summary')
  })

  it('extracts font_size and line_spacing', () => {
    const md = '---\nname: Jane\nfont_size: 10.5\nline_spacing: 1.3\n---\nBody'
    const { data } = parseFrontmatter(md)
    expect(data.font_size).toBe('10.5')
    expect(data.line_spacing).toBe('1.3')
  })

  it('returns empty data for no frontmatter', () => {
    const md = '# Summary\nHello'
    const { data, body } = parseFrontmatter(md)
    expect(Object.keys(data).length).toBe(0)
    expect(body).toBe(md)
  })
})

describe('renderResume', () => {
  it('renders header with name and meta', () => {
    const md = '---\nname: John Doe\ntitle: Engineer\nemail: john@example.com\n---\n# Summary\nHello'
    const html = renderResume(md)
    expect(html).toContain('class="name"')
    expect(html).toContain('John Doe')
    expect(html).toContain('john@example.com')
  })

  it('renders experience with bold and italic', () => {
    const md = '---\nname: Test\n---\n# Experience\n\n**Engineer — Acme** *2023 – Present*\n- Built things.'
    const html = renderResume(md)
    expect(html).toContain('<strong>')
    expect(html).toContain('<em>')
  })

  it('renders skills with bold categories', () => {
    const md = '---\nname: Test\n---\n# Skills\n\n**Backend:** Python, FastAPI.'
    const html = renderResume(md)
    expect(html).toContain('<strong>Backend:</strong>')
  })

  it('renders section separators as hr', () => {
    const md = '---\nname: Test\n---\n# Summary\nHello\n\n---\n# Skills\n**A:** B.'
    const html = renderResume(md)
    expect(html).toContain('<hr')
  })

  it('does not crash on empty input', () => {
    const html = renderResume('')
    expect(html).toBeDefined()
  })

  it('does not crash on malformed markdown', () => {
    const html = renderResume('---\nbroken\n# Huh')
    expect(html).toBeDefined()
  })
})
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vitest run`
Expected: All PASS (existing useMarkdown already handles these)

- [ ] **Step 3: Export frontmatter data from renderResume for font/spacing access**

Modify `frontend/src/composables/useMarkdown.ts` to also export a `getResumeSettings` function:

```typescript
import { marked } from 'marked'

marked.setOptions({ gfm: true, breaks: false })

export interface ResumeSettings {
  fontSize: number
  lineSpacing: number
}

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

  function getResumeSettings(md: string): ResumeSettings {
    const { data } = parseFrontmatter(md)
    return {
      fontSize: parseFloat(data.font_size) || 11,
      lineSpacing: parseFloat(data.line_spacing) || 1.4,
    }
  }

  function renderResume(md: string): string {
    const { data, body } = parseFrontmatter(md)
    const header = Object.keys(data).length ? buildHeader(data) : ''
    const bodyHtml = marked.parse(body) as string
    return `${header}<div class="md">${bodyHtml}</div>`
  }

  return { renderResume, parseFrontmatter, getResumeSettings }
}
```

- [ ] **Step 4: Run tests again**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vitest run`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/composables/useMarkdown.ts frontend/src/__tests__/useMarkdown.test.ts
git commit -m "feat: export resume settings from frontmatter, add rendering tests"
```

---

## Task 8: Frontend — Jobs Store + useJobs Composable

**Files:**
- Modify: `frontend/src/stores/editor.ts`
- Create: `frontend/src/composables/useJobs.ts`
- Create: `frontend/src/__tests__/useJobs.test.ts`

- [ ] **Step 1: Write useJobs tests**

Create `frontend/src/__tests__/useJobs.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEditorStore } from '../stores/editor'

describe('editor store — jobs', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('adds a job', () => {
    const store = useEditorStore()
    store.addJob()
    expect(store.jobs.size).toBe(1)
    const job = [...store.jobs.values()][0]
    expect(job.tailoringStatus).toBe('idle')
  })

  it('removes a job', () => {
    const store = useEditorStore()
    store.addJob()
    const id = [...store.jobs.keys()][0]
    store.removeJob(id)
    expect(store.jobs.size).toBe(0)
  })

  it('isolates state between jobs', () => {
    const store = useEditorStore()
    store.addJob()
    store.addJob()
    const [id1, id2] = [...store.jobs.keys()]
    store.updateJob(id1, { tailoringStatus: 'running' })
    expect(store.jobs.get(id1)!.tailoringStatus).toBe('running')
    expect(store.jobs.get(id2)!.tailoringStatus).toBe('idle')
  })

  it('updates job fields', () => {
    const store = useEditorStore()
    store.addJob()
    const id = [...store.jobs.keys()][0]
    store.updateJob(id, { title: 'ML Engineer @ Google', seniorityLevel: 'senior' })
    expect(store.jobs.get(id)!.title).toBe('ML Engineer @ Google')
    expect(store.jobs.get(id)!.seniorityLevel).toBe('senior')
  })

  it('sets active job', () => {
    const store = useEditorStore()
    store.addJob()
    const id = [...store.jobs.keys()][0]
    store.activeJobId = id
    expect(store.activeJobId).toBe(id)
  })

  it('resets single job tailoring state', () => {
    const store = useEditorStore()
    store.addJob()
    const id = [...store.jobs.keys()][0]
    store.updateJob(id, { tailoringStatus: 'done', result: 'some result' })
    store.resetJobTailoring(id)
    expect(store.jobs.get(id)!.tailoringStatus).toBe('idle')
    expect(store.jobs.get(id)!.result).toBeNull()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vitest run`
Expected: FAIL — `addJob`, `removeJob`, etc. don't exist yet

- [ ] **Step 3: Rewrite editor store with multi-job support**

Replace `frontend/src/stores/editor.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { SeniorityLevel } from '../composables/useSeniority'

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

export interface JobState {
  id: string
  title: string
  jobDescription: string
  seniorityLevel: SeniorityLevel | null
  tailoringStatus: 'idle' | 'running' | 'done' | 'error'
  tailoringPlan: ToolCall[] | null
  agentStatuses: Record<string, 'pending' | 'running' | 'done'>
  result: string | null
  error: string | null
  pageMode: 'single' | 'multi'
}

let _jobCounter = 0

export const useEditorStore = defineStore('editor', () => {
  const markdown = ref('')
  const profile = ref<Profile | null>(null)
  const jobs = ref<Map<string, JobState>>(new Map())
  const activeJobId = ref<string | null>(null)
  const pageMode = ref<'single' | 'multi'>('single')

  function addJob(): string {
    const id = `job-${++_jobCounter}`
    jobs.value.set(id, {
      id,
      title: '',
      jobDescription: '',
      seniorityLevel: null,
      tailoringStatus: 'idle',
      tailoringPlan: null,
      agentStatuses: {},
      result: null,
      error: null,
      pageMode: 'single',
    })
    // Trigger reactivity
    jobs.value = new Map(jobs.value)
    return id
  }

  function removeJob(id: string) {
    jobs.value.delete(id)
    jobs.value = new Map(jobs.value)
    if (activeJobId.value === id) {
      activeJobId.value = null
    }
  }

  function updateJob(id: string, updates: Partial<JobState>) {
    const job = jobs.value.get(id)
    if (!job) return
    Object.assign(job, updates)
    jobs.value = new Map(jobs.value)
  }

  function resetJobTailoring(id: string) {
    updateJob(id, {
      tailoringStatus: 'idle',
      tailoringPlan: null,
      agentStatuses: {},
      result: null,
      error: null,
    })
  }

  return {
    markdown, profile, jobs, activeJobId, pageMode,
    addJob, removeJob, updateJob, resetJobTailoring,
  }
})
```

- [ ] **Step 4: Create useJobs composable**

Create `frontend/src/composables/useJobs.ts`:

```typescript
import { useEditorStore, type JobState } from '../stores/editor'
import { detectSeniority } from './useSeniority'

export function useJobs() {
  const store = useEditorStore()

  function addJob(): string {
    return store.addJob()
  }

  function removeJob(id: string) {
    store.removeJob(id)
  }

  function updateJobDescription(id: string, jd: string) {
    const detected = detectSeniority(jd)
    const job = store.jobs.get(id)
    const updates: Partial<JobState> = { jobDescription: jd }
    // Only auto-set seniority if user hasn't manually selected one
    if (detected && (!job?.seniorityLevel || job.seniorityLevel === null)) {
      updates.seniorityLevel = detected
    }
    store.updateJob(id, updates)
  }

  function setJobTitle(id: string, title: string) {
    store.updateJob(id, { title })
  }

  function setJobSeniority(id: string, level: string | null) {
    store.updateJob(id, { seniorityLevel: level as any })
  }

  function getJobList(): JobState[] {
    return [...store.jobs.values()]
  }

  return { addJob, removeJob, updateJobDescription, setJobTitle, setJobSeniority, getJobList }
}
```

- [ ] **Step 5: Run tests**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vitest run`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/stores/editor.ts frontend/src/composables/useJobs.ts frontend/src/composables/useSeniority.ts frontend/src/__tests__/useJobs.test.ts
git commit -m "feat: add multi-job store with per-job state isolation"
```

---

## Task 9: Frontend — Update useTailor for Multi-Job Support

**Files:**
- Modify: `frontend/src/composables/useTailor.ts`

- [ ] **Step 1: Rewrite useTailor to scope state per job**

Replace `frontend/src/composables/useTailor.ts`:

```typescript
import { useEditorStore } from '../stores/editor'

export function useTailor() {
  const store = useEditorStore()

  function startTailoring(jobId: string, apiKey?: string, resumeOverride?: string) {
    const job = store.jobs.get(jobId)
    if (!job) return

    store.resetJobTailoring(jobId)
    store.updateJob(jobId, { tailoringStatus: 'running' })

    const body: Record<string, string> = { job_description: job.jobDescription }
    if (apiKey) body.gemini_api_key = apiKey
    if (resumeOverride) body.resume_override = resumeOverride
    if (job.seniorityLevel) body.seniority_level = job.seniorityLevel

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
              handleEvent(jobId, eventType, data)
            } catch {}
            eventType = ''
          }
        }
      }
    }).catch((err) => {
      store.updateJob(jobId, { tailoringStatus: 'error', error: err.message })
    })
  }

  function startBatchTailoring(apiKey?: string, resumeOverride?: string) {
    for (const [jobId, job] of store.jobs) {
      if (job.jobDescription.trim()) {
        startTailoring(jobId, apiKey, resumeOverride)
      }
    }
  }

  function handleEvent(jobId: string, event: string, data: Record<string, unknown>) {
    const job = store.jobs.get(jobId)
    if (!job) return

    switch (event) {
      case 'plan': {
        const plan = data.tool_calls as any[]
        const statuses: Record<string, 'pending' | 'running' | 'done'> = {}
        for (const call of plan || []) {
          const key = call.entry ? `${call.agent}:${call.entry}` : call.agent
          statuses[key] = call.action === 'keep' ? 'done' : 'pending'
        }
        store.updateJob(jobId, { tailoringPlan: plan, agentStatuses: statuses })
        break
      }
      case 'agent_start': {
        const statuses = { ...job.agentStatuses, [data.agent as string]: 'running' as const }
        store.updateJob(jobId, { agentStatuses: statuses })
        break
      }
      case 'agent_done': {
        const statuses = { ...job.agentStatuses, [data.agent as string]: 'done' as const }
        store.updateJob(jobId, { agentStatuses: statuses })
        break
      }
      case 'complete':
        store.updateJob(jobId, {
          tailoringStatus: 'done',
          result: data.markdown as string,
        })
        break
      case 'error':
        store.updateJob(jobId, {
          tailoringStatus: 'error',
          error: data.message as string,
        })
        break
    }
  }

  return { startTailoring, startBatchTailoring }
}
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vitest run`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useTailor.ts
git commit -m "feat: scope tailor SSE handling per job, add batch tailoring"
```

---

## Task 10: Frontend — PageModeToggle Component

**Files:**
- Create: `frontend/src/components/PageModeToggle.vue`

- [ ] **Step 1: Create PageModeToggle component**

```vue
<script setup lang="ts">
defineProps<{ modelValue: 'single' | 'multi' }>()
defineEmits<{ 'update:modelValue': [value: 'single' | 'multi'] }>()
</script>

<template>
  <div class="page-mode-toggle">
    <button
      :class="{ active: modelValue === 'single' }"
      @click="$emit('update:modelValue', 'single')"
    >1 Page</button>
    <button
      :class="{ active: modelValue === 'multi' }"
      @click="$emit('update:modelValue', 'multi')"
    >Multi-Page</button>
  </div>
</template>

<style scoped>
.page-mode-toggle {
  display: flex; border: 1px solid #d0d0d0; border-radius: 8px; overflow: hidden;
}
.page-mode-toggle button {
  flex: 1; padding: 6px 12px; border: none; background: #fafafa;
  font-size: 0.8rem; font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.page-mode-toggle button.active {
  background: #111; color: #fff;
}
.page-mode-toggle button:not(.active):hover {
  background: #eee;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/PageModeToggle.vue
git commit -m "feat: add page mode toggle component (1-page / multi-page)"
```

---

## Task 11: Frontend — ResumePreview with Page Mode Support

**Files:**
- Modify: `frontend/src/components/ResumePreview.vue`
- Modify: `frontend/src/style.css`

- [ ] **Step 1: Rewrite ResumePreview to support both page modes**

Replace `frontend/src/components/ResumePreview.vue`:

```vue
<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useMarkdown } from '../composables/useMarkdown'

const props = defineProps<{
  markdown: string
  pageMode: 'single' | 'multi'
}>()

const { renderResume, getResumeSettings } = useMarkdown()
const contentRef = ref<HTMLElement>()
const showWarn = ref(false)

const settings = computed(() => getResumeSettings(props.markdown))

watch([() => props.markdown, () => props.pageMode], async () => {
  await nextTick()
  if (props.pageMode === 'single') {
    fitToOnePage()
  } else {
    applyMultiPageStyles()
  }
}, { immediate: true })

function fitToOnePage() {
  const el = contentRef.value
  if (!el) return
  showWarn.value = false
  let size = settings.value.fontSize
  const min = 8
  const lineHeight = settings.value.lineSpacing

  document.documentElement.style.setProperty('--base-font-size', size + 'px')
  document.documentElement.style.setProperty('--line-height', String(lineHeight))

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

function applyMultiPageStyles() {
  showWarn.value = false
  document.documentElement.style.setProperty('--base-font-size', settings.value.fontSize + 'px')
  document.documentElement.style.setProperty('--line-height', String(settings.value.lineSpacing))
}
</script>

<template>
  <div :class="['preview-container', { 'multi-page': pageMode === 'multi' }]">
    <section :class="['sheet', { 'sheet-multi': pageMode === 'multi' }]">
      <div ref="contentRef" class="sheet-content" v-html="renderResume(markdown)" />
      <div class="warn" v-show="showWarn && pageMode === 'single'">Content exceeds one page at minimum size.</div>
    </section>
  </div>
</template>

<style scoped>
.preview-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.sheet-multi {
  height: auto !important;
  min-height: var(--page-h);
}
</style>
```

- [ ] **Step 2: Update style.css for multi-page support**

Add to `frontend/src/style.css` before the `@page` rule (before line 52):

```css
/* Multi-page mode */
.sheet-multi .sheet-content {
  overflow: visible !important;
  height: auto !important;
}

.sheet-multi {
  height: auto !important;
  min-height: var(--page-h);
}

/* Prevent page breaks inside entries */
.sheet-content li,
.sheet-content p {
  break-inside: avoid;
}
```

Update the print CSS (lines 53-59) to handle multi-page:

```css
@page { size: A4; margin: 3mm; }
@media print {
  body { background: white; margin: 0; }
  .nav, .panel, .sidebar, .page-mode-toggle, .tab-bar, .preview-controls { display: none !important; }
  .sheet { box-shadow: none !important; margin: 0; padding: 3mm !important; width: 100% !important; }
  .sheet:not(.sheet-multi) .sheet-content { overflow: visible !important; height: auto !important; font-size: 11px !important; }
  .sheet-multi { page-break-after: auto; }
  .sheet-multi .sheet-content { overflow: visible !important; height: auto !important; }
  .warn { display: none !important; }
}
```

- [ ] **Step 3: Run frontend tests**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vitest run`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ResumePreview.vue frontend/src/style.css
git commit -m "feat: add multi-page resume preview with auto-fit from frontmatter settings"
```

---

## Task 12: Frontend — TabBar Component

**Files:**
- Create: `frontend/src/components/TabBar.vue`

- [ ] **Step 1: Create TabBar component**

```vue
<script setup lang="ts">
import type { JobState } from '../stores/editor'

defineProps<{
  jobs: JobState[]
  activeTab: string | null
}>()

defineEmits<{
  select: [id: string | null]
}>()

function statusIcon(status: JobState['tailoringStatus']): string {
  switch (status) {
    case 'running': return '...'
    case 'done': return 'done'
    case 'error': return '!'
    default: return ''
  }
}
</script>

<template>
  <div class="tab-bar">
    <button
      class="tab"
      :class="{ active: activeTab === null }"
      @click="$emit('select', null)"
    >Original</button>
    <button
      v-for="job in jobs"
      :key="job.id"
      class="tab"
      :class="{ active: activeTab === job.id, [job.tailoringStatus]: true }"
      @click="$emit('select', job.id)"
    >
      <span class="tab-label">{{ job.title || job.id }}</span>
      <span v-if="job.tailoringStatus !== 'idle'" class="tab-status" :class="job.tailoringStatus">
        {{ statusIcon(job.tailoringStatus) }}
      </span>
    </button>
  </div>
</template>

<style scoped>
.tab-bar {
  display: flex; gap: 2px; background: #e8e8e8; border-radius: 10px;
  padding: 3px; overflow-x: auto; flex-shrink: 0;
}
.tab {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 14px; border: none; background: transparent;
  border-radius: 8px; font-size: 0.82rem; font-weight: 600;
  cursor: pointer; white-space: nowrap; transition: all 0.15s;
  color: #666;
}
.tab:hover { background: #f0f0f0; color: #333; }
.tab.active { background: #fff; color: #111; box-shadow: 0 1px 4px rgba(0,0,0,.1); }
.tab-label { max-width: 160px; overflow: hidden; text-overflow: ellipsis; }
.tab-status {
  font-size: 0.7rem; padding: 1px 5px; border-radius: 4px;
}
.tab-status.running { color: #667eea; animation: pulse 1s infinite; }
.tab-status.done { color: #28a745; }
.tab-status.error { color: #dc3545; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TabBar.vue
git commit -m "feat: add tab bar component for switching between original and job results"
```

---

## Task 13: Frontend — JobCard Component

**Files:**
- Create: `frontend/src/components/JobCard.vue`

- [ ] **Step 1: Create JobCard component**

```vue
<script setup lang="ts">
import { watch } from 'vue'
import { SENIORITY_OPTIONS, detectSeniority, type SeniorityLevel } from '../composables/useSeniority'
import type { JobState } from '../stores/editor'

const props = defineProps<{ job: JobState }>()

const emit = defineEmits<{
  'update:title': [value: string]
  'update:jobDescription': [value: string]
  'update:seniorityLevel': [value: SeniorityLevel | null]
  remove: []
}>()

function onJdInput(value: string) {
  emit('update:jobDescription', value)
  const detected = detectSeniority(value)
  if (detected) {
    emit('update:seniorityLevel', detected)
  }
}
</script>

<template>
  <div class="job-card" :class="job.tailoringStatus">
    <div class="job-card-header">
      <input
        class="job-title-input"
        :value="job.title"
        @input="$emit('update:title', ($event.target as HTMLInputElement).value)"
        placeholder="Job title (e.g., ML Engineer @ Google)"
      />
      <button class="remove-btn" @click="$emit('remove')" title="Remove job">&times;</button>
    </div>
    <div class="job-card-row">
      <select
        class="seniority-select"
        :value="job.seniorityLevel || ''"
        @change="$emit('update:seniorityLevel', ($event.target as HTMLSelectElement).value as SeniorityLevel || null)"
      >
        <option value="">Auto-detect level</option>
        <option v-for="level in SENIORITY_OPTIONS" :key="level" :value="level">
          {{ level.charAt(0).toUpperCase() + level.slice(1) }}
        </option>
      </select>
      <span v-if="job.tailoringStatus === 'done'" class="status-badge done">Done</span>
      <span v-else-if="job.tailoringStatus === 'running'" class="status-badge running">Running...</span>
      <span v-else-if="job.tailoringStatus === 'error'" class="status-badge error">Error</span>
    </div>
    <textarea
      class="jd-textarea"
      :value="job.jobDescription"
      @input="onJdInput(($event.target as HTMLTextAreaElement).value)"
      placeholder="Paste job description here..."
    />
  </div>
</template>

<style scoped>
.job-card {
  border: 1px solid #e0e0e0; border-radius: 10px; padding: 10px;
  display: flex; flex-direction: column; gap: 6px;
  transition: border-color 0.2s;
}
.job-card.running { border-color: #667eea; }
.job-card.done { border-color: #28a745; }
.job-card.error { border-color: #dc3545; }
.job-card-header { display: flex; align-items: center; gap: 6px; }
.job-title-input {
  flex: 1; border: 1px solid #d9d9d9; border-radius: 6px;
  padding: 6px 8px; font-size: 0.85rem; font-weight: 600;
}
.job-title-input:focus { outline: none; border-color: #667eea; }
.remove-btn {
  width: 28px; height: 28px; border: none; background: #f5f5f5;
  border-radius: 6px; font-size: 1.1rem; cursor: pointer; color: #999;
  display: flex; align-items: center; justify-content: center;
}
.remove-btn:hover { background: #ffe0e0; color: #d00; }
.job-card-row { display: flex; align-items: center; gap: 8px; }
.seniority-select {
  flex: 1; border: 1px solid #d9d9d9; border-radius: 6px;
  padding: 5px 8px; font-size: 0.8rem; background: #fff;
}
.status-badge {
  font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 4px;
}
.status-badge.done { background: #e6f9e6; color: #28a745; }
.status-badge.running { background: #eef0ff; color: #667eea; }
.status-badge.error { background: #ffe6e6; color: #dc3545; }
.jd-textarea {
  width: 100%; min-height: 60px; resize: vertical; padding: 8px;
  border: 1px dashed #c9c9c9; border-radius: 8px; font-size: 0.8rem;
}
.jd-textarea:focus { outline: none; border-color: #667eea; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/JobCard.vue
git commit -m "feat: add job card component with title, seniority, and JD input"
```

---

## Task 14: Frontend — ApiKeyModal Component

**Files:**
- Create: `frontend/src/components/ApiKeyModal.vue`

- [ ] **Step 1: Create ApiKeyModal component**

```vue
<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const open = ref(false)

function save() {
  open.value = false
}
</script>

<template>
  <div class="api-key-wrapper">
    <button class="api-key-btn" @click="open = !open" title="API Key">
      <span class="key-icon">&#128273;</span>
      <span v-if="modelValue" class="key-dot"></span>
    </button>
    <div v-if="open" class="api-key-popover">
      <label class="popover-label">Gemini API Key</label>
      <input
        type="password"
        class="api-key-input"
        :value="modelValue"
        @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        placeholder="Paste your Gemini API key"
      />
      <button class="save-btn" @click="save">Done</button>
    </div>
    <div v-if="open" class="popover-backdrop" @click="open = false" />
  </div>
</template>

<style scoped>
.api-key-wrapper { position: relative; }
.api-key-btn {
  position: relative; border: none; background: #333; color: #fff;
  border-radius: 8px; padding: 6px 10px; cursor: pointer; font-size: 0.85rem;
}
.api-key-btn:hover { background: #555; }
.key-icon { font-style: normal; }
.key-dot {
  position: absolute; top: 4px; right: 4px;
  width: 6px; height: 6px; border-radius: 50%; background: #28a745;
}
.api-key-popover {
  position: absolute; right: 0; top: 100%; margin-top: 8px;
  background: #fff; border: 1px solid #d0d0d0; border-radius: 10px;
  padding: 12px; width: 280px; box-shadow: 0 8px 24px rgba(0,0,0,.15);
  z-index: 100; display: flex; flex-direction: column; gap: 8px;
}
.popover-label { font-size: 0.8rem; font-weight: 600; color: #555; }
.api-key-input {
  width: 100%; padding: 8px; border: 1px solid #d0d0d0;
  border-radius: 6px; font-size: 0.85rem;
}
.save-btn {
  align-self: flex-end; padding: 6px 16px; border: none;
  background: #111; color: #fff; border-radius: 6px; font-weight: 600;
  cursor: pointer; font-size: 0.8rem;
}
.popover-backdrop {
  position: fixed; inset: 0; z-index: 99;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ApiKeyModal.vue
git commit -m "feat: add API key popover component for nav bar"
```

---

## Task 15: Frontend — Full EditorView Restructure

**Files:**
- Modify: `frontend/src/views/EditorView.vue`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/components/MarkdownEditor.vue`

- [ ] **Step 1: Update App.vue with API key in nav**

Replace `frontend/src/App.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { RouterView, RouterLink } from 'vue-router'
import ApiKeyModal from './components/ApiKeyModal.vue'

const apiKey = ref('')
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
      <div class="nav-right">
        <ApiKeyModal v-model="apiKey" />
      </div>
    </nav>
    <main class="main">
      <RouterView :apiKey="apiKey" />
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
.nav-links { display: flex; gap: 16px; flex: 1; }
.nav-link {
  color: #aaa; text-decoration: none; font-weight: 500;
  padding: 4px 8px; border-radius: 6px; transition: all 0.2s;
}
.nav-link:hover, .nav-link.router-link-active { color: #fff; background: #333; }
.nav-right { margin-left: auto; }
.main { padding: 18px; }
</style>
```

- [ ] **Step 2: Update MarkdownEditor with better empty state**

Replace `frontend/src/components/MarkdownEditor.vue`:

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
  <div class="editor-wrapper">
    <label class="editor-label">Your Master Resume</label>
    <textarea
      class="md-editor"
      :value="modelValue"
      @input="onInput"
      @drop.prevent="onDrop"
      @dragover.prevent
      placeholder="Paste your markdown resume here or drag & drop a .md file..."
    />
  </div>
</template>

<style scoped>
.editor-wrapper { display: flex; flex-direction: column; gap: 4px; }
.editor-label { font-size: 0.8rem; font-weight: 700; color: #555; }
.md-editor {
  width: 100%; min-height: 220px; resize: vertical;
  font: 12px/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  border: 1px dashed #b9b9b9; border-radius: 10px; padding: 10px; outline: none;
}
.md-editor:focus { border-color: #667eea; }
</style>
```

- [ ] **Step 3: Rewrite EditorView with two-panel layout**

Replace `frontend/src/views/EditorView.vue`:

```vue
<script setup lang="ts">
import { ref, computed, onMounted, provide } from 'vue'
import { useEditorStore } from '../stores/editor'
import { useProfile } from '../composables/useProfile'
import { useTailor } from '../composables/useTailor'
import MarkdownEditor from '../components/MarkdownEditor.vue'
import ResumePreview from '../components/ResumePreview.vue'
import JobCard from '../components/JobCard.vue'
import AgentProgress from '../components/AgentProgress.vue'
import TabBar from '../components/TabBar.vue'
import PageModeToggle from '../components/PageModeToggle.vue'

const props = defineProps<{ apiKey?: string }>()

const store = useEditorStore()
const { fetchProfile } = useProfile()
const { startTailoring, startBatchTailoring } = useTailor()

onMounted(async () => {
  const p = await fetchProfile()
  if (p) {
    store.profile = p
    if (!store.markdown) store.markdown = p.master_resume
  }
})

const jobList = computed(() => [...store.jobs.values()])
const activeJob = computed(() => store.activeJobId ? store.jobs.get(store.activeJobId) ?? null : null)
const previewMarkdown = computed(() => {
  if (!store.activeJobId) return store.markdown
  return activeJob.value?.result ?? store.markdown
})

const currentPageMode = computed({
  get: () => {
    if (!store.activeJobId) return store.pageMode
    return activeJob.value?.pageMode ?? 'single'
  },
  set: (val: 'single' | 'multi') => {
    if (!store.activeJobId) {
      store.pageMode = val
    } else {
      store.updateJob(store.activeJobId, { pageMode: val })
    }
  },
})

const hasJobs = computed(() => store.jobs.size > 0)
const anyRunning = computed(() => [...store.jobs.values()].some(j => j.tailoringStatus === 'running'))
const canTailor = computed(() =>
  hasJobs.value &&
  [...store.jobs.values()].some(j => j.jobDescription.trim()) &&
  store.markdown.trim()
)

function addJob() {
  store.addJob()
}

function removeJob(id: string) {
  store.removeJob(id)
}

function tailorAll() {
  const key = props.apiKey || store.profile?.gemini_api_key || ''
  if (!key) return alert('Set your Gemini API key first (key icon in the nav bar).')
  if (!store.markdown.trim()) return alert('Load a resume first.')
  startBatchTailoring(key, store.markdown)
}

function exportPdf() { window.print() }
</script>

<template>
  <div class="editor-layout">
    <!-- LEFT PANEL -->
    <aside class="left-panel">
      <!-- Resume Section -->
      <section class="panel-section">
        <MarkdownEditor v-model="store.markdown" />
      </section>

      <!-- Jobs Section -->
      <section class="panel-section jobs-section">
        <div class="section-header">
          <h3>Jobs</h3>
          <button class="add-job-btn" @click="addJob">+ Add Job</button>
        </div>

        <div v-if="!hasJobs" class="empty-state">
          Add a job description to start tailoring your resume.
        </div>

        <div class="job-list">
          <JobCard
            v-for="job in jobList"
            :key="job.id"
            :job="job"
            @update:title="store.updateJob(job.id, { title: $event })"
            @update:job-description="store.updateJob(job.id, { jobDescription: $event })"
            @update:seniority-level="store.updateJob(job.id, { seniorityLevel: $event })"
            @remove="removeJob(job.id)"
          />
        </div>

        <button
          v-if="hasJobs"
          class="tailor-all-btn"
          :disabled="!canTailor || anyRunning"
          @click="tailorAll"
        >
          {{ anyRunning ? 'Tailoring...' : 'Tailor All' }}
        </button>
      </section>
    </aside>

    <!-- RIGHT PANEL -->
    <div class="right-panel">
      <!-- Tab Bar -->
      <TabBar
        v-if="hasJobs"
        :jobs="jobList"
        :activeTab="store.activeJobId"
        @select="store.activeJobId = $event"
      />

      <!-- Preview Controls -->
      <div class="preview-controls">
        <PageModeToggle v-model="currentPageMode" />
        <button class="export-btn" @click="exportPdf">Print / PDF</button>
      </div>

      <!-- Agent Progress (for active running job) -->
      <AgentProgress v-if="activeJob && activeJob.tailoringStatus === 'running'" :job="activeJob" />

      <!-- Resume Preview -->
      <div v-if="!store.markdown" class="empty-preview">
        <div class="empty-preview-content">
          <div class="empty-preview-icon">&#128196;</div>
          <p>Load a resume to see preview</p>
          <small>Paste markdown in the editor or drag a .md file</small>
        </div>
      </div>
      <ResumePreview
        v-else
        :markdown="previewMarkdown"
        :pageMode="currentPageMode"
      />

      <!-- Step Guide (first-time hint) -->
      <div v-if="!store.markdown && !hasJobs" class="step-guide">
        <div class="step"><span class="step-num">1</span> Load your resume</div>
        <div class="step-arrow">&rarr;</div>
        <div class="step"><span class="step-num">2</span> Add job descriptions</div>
        <div class="step-arrow">&rarr;</div>
        <div class="step"><span class="step-num">3</span> Tailor &amp; export</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.editor-layout {
  display: flex; align-items: flex-start; justify-content: center;
  gap: 18px; padding: 0 18px; max-width: 1400px; margin: 0 auto;
}

/* LEFT PANEL */
.left-panel {
  width: min(440px, 34vw); min-width: 320px;
  position: sticky; top: 60px; align-self: flex-start;
  display: flex; flex-direction: column; gap: 12px;
  max-height: calc(100vh - 80px); overflow-y: auto;
}

.panel-section {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.05); padding: 14px;
}

.section-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px;
}
.section-header h3 { margin: 0; font-size: 0.95rem; }
.add-job-btn {
  border: 1px solid #d0d0d0; background: #fafafa; border-radius: 8px;
  padding: 5px 12px; font-size: 0.8rem; font-weight: 600; cursor: pointer;
}
.add-job-btn:hover { background: #eee; }

.job-list { display: flex; flex-direction: column; gap: 8px; }

.empty-state {
  text-align: center; padding: 20px; color: #999; font-size: 0.85rem;
}

.tailor-all-btn {
  width: 100%; padding: 11px; font-weight: 700; border-radius: 10px;
  border: none; color: white; cursor: pointer; font-size: 0.9rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  margin-top: 8px;
}
.tailor-all-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.tailor-all-btn:not(:disabled):hover { opacity: 0.9; }

/* RIGHT PANEL */
.right-panel {
  flex: 1; max-width: 240mm;
  display: flex; flex-direction: column; gap: 10px;
}

.preview-controls {
  display: flex; align-items: center; gap: 10px;
}
.export-btn {
  margin-left: auto; border: 1px solid #d0d0d0; background: #fafafa;
  border-radius: 8px; padding: 6px 14px; font-weight: 600;
  font-size: 0.8rem; cursor: pointer;
}
.export-btn:hover { background: #eee; }

.empty-preview {
  width: var(--page-w); min-height: 300px;
  background: #fff; border: 2px dashed #d9d9d9; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
}
.empty-preview-content { text-align: center; color: #999; }
.empty-preview-icon { font-size: 3rem; margin-bottom: 8px; }
.empty-preview-content p { margin: 0; font-weight: 600; }
.empty-preview-content small { font-size: 0.8rem; }

.step-guide {
  display: flex; align-items: center; justify-content: center;
  gap: 12px; padding: 14px; color: #999; font-size: 0.82rem;
}
.step {
  display: flex; align-items: center; gap: 6px;
  background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
  padding: 8px 14px;
}
.step-num {
  width: 22px; height: 22px; border-radius: 50%; background: #667eea;
  color: #fff; font-weight: 700; font-size: 0.75rem;
  display: flex; align-items: center; justify-content: center;
}
.step-arrow { color: #ccc; font-size: 1.2rem; }

/* Responsive */
@media (max-width: 900px) {
  .editor-layout { flex-direction: column; align-items: stretch; }
  .left-panel {
    width: 100%; min-width: unset; position: static;
    max-height: unset;
  }
  .right-panel { max-width: 100%; }
}
</style>
```

- [ ] **Step 4: Update AgentProgress to accept job prop**

Replace `frontend/src/components/AgentProgress.vue`:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import type { JobState } from '../stores/editor'

const props = defineProps<{ job: JobState }>()

const agents = computed(() => {
  const entries = Object.entries(props.job.agentStatuses)
  return entries.map(([key, status]) => ({
    key,
    label: key.includes(':') ? key.split(':')[1] : key,
    type: key.includes(':') ? 'experience' : key,
    status,
  }))
})
</script>

<template>
  <div class="progress-panel">
    <div class="progress-header">
      <span class="progress-status running">Tailoring in progress...</span>
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
  padding: 12px;
}
.progress-header { margin-bottom: 8px; font-weight: 600; }
.progress-status.running { color: #667eea; }
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

- [ ] **Step 5: Run frontend tests**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vitest run`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/EditorView.vue frontend/src/App.vue frontend/src/components/MarkdownEditor.vue frontend/src/components/AgentProgress.vue
git commit -m "feat: restructure editor with two-panel layout, tabs, and batch tailoring UI"
```

---

## Task 16: Frontend — Visual Testing in Browser

**Files:** None (manual testing)

- [ ] **Step 1: Start backend dev server**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && source venv/bin/activate && godcv run --dev --port 9000`
Expected: FastAPI running on port 9000

- [ ] **Step 2: Start frontend dev server**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npm run dev`
Expected: Vite dev server running on port 3000

- [ ] **Step 3: Open browser and test the following**

Open `http://localhost:3000` and verify:

1. **Empty state:** Step guide (1→2→3) shows when no resume and no jobs
2. **Load resume:** Paste sample resume markdown → preview renders correctly with name, contacts, sections, right-floated dates
3. **Page mode:** Toggle between 1-Page and Multi-Page — font shrinks in 1-Page, flows naturally in Multi-Page
4. **Add jobs:** Click "Add Job" → job card appears with title, seniority dropdown, JD textarea
5. **Auto-detect seniority:** Paste a JD with "senior" → dropdown auto-selects Senior
6. **Multiple jobs:** Add 2-3 jobs → tabs appear (Original + job tabs)
7. **API key:** Key icon in nav → popover opens, enter key, green dot appears
8. **Tailor All:** Click → all jobs run in parallel, progress shows per tab
9. **Tab switching:** Switch between tabs while running/after done → each shows correct result
10. **Print:** Click Print/PDF → print dialog shows clean A4 resume
11. **Responsive:** Narrow the browser → layout stacks vertically

- [ ] **Step 4: Fix any issues found during testing**

Address any rendering, layout, or interaction bugs discovered.

- [ ] **Step 5: Commit any fixes**

```bash
git add -u
git commit -m "fix: address visual testing issues in editor UI"
```

---

## Task 17: Run All Tests — Final Verification

**Files:** None (test execution)

- [ ] **Step 1: Run all backend tests**

Run: `cd /Users/naresh/Documents/resume_editor/godcv && pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run all frontend tests**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vitest run`
Expected: All tests PASS

- [ ] **Step 3: Run type checking**

Run: `cd /Users/naresh/Documents/resume_editor/godcv/frontend && npx vue-tsc --noEmit`
Expected: No type errors

- [ ] **Step 4: Final commit if any adjustments needed**

```bash
git add -u
git commit -m "chore: final test and type-check cleanup"
```
