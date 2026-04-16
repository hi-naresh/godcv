# Structured Section Editor Design

**Date:** 2026-04-16
**Status:** Approved

## Overview

Enhance the Profile tab's section editor with structured fields for known section types, reordering controls for sections and entries, and a chip/tag input for skills and tech stacks. All changes are frontend-only — the markdown-in, markdown-out data flow is preserved.

## Goals

1. Reorder sections and entries within sections via up/down arrow buttons
2. Structured fields for Experience entries (Role, Company+Location, Start Date, End Date)
3. Structured fields for Education entries (Degree, University, Start Date, End Date)
4. Structured fields for Project entries (Name, URL, Tech Stack as chips)
5. Structured editing for Skills (category name + skill chips per category, add/remove categories)
6. Graceful fallback for unknown sections or unparseable entries

## Non-Goals

- Drag-and-drop reordering (arrow buttons only)
- Backend changes (markdown storage model unchanged)
- External UI libraries

---

## Component Architecture

### New Components

```
frontend/src/components/
├── ChipInput.vue              — Reusable tag/chip input
├── ExperienceEntryCard.vue    — Structured experience entry
├── EducationEntryCard.vue     — Structured education entry
├── ProjectEntryCard.vue       — Structured project entry
└── SkillCategoryCard.vue      — Structured skill category
```

### Modified Components

```
SectionEditor.vue   — Section type map, reordering, expanded parsing
SectionCard.vue     — Entry dispatching, entry reordering, arrow buttons
```

### Component Hierarchy

```
SectionEditor.vue
├── Frontmatter Card (inline)
├── SectionCard.vue (per section, with up/down arrows)
│   ├── ExperienceEntryCard.vue   (section type: experience)
│   ├── ProjectEntryCard.vue      (section type: projects)
│   ├── EducationEntryCard.vue    (section type: education)
│   ├── SkillCategoryCard.vue     (section type: skills)
│   └── EntryCard.vue             (fallback for unknown types)
```

---

## Section Type Detection

Replace `MULTI_ENTRY_SECTIONS` array with a type map:

```typescript
type SectionType = 'experience' | 'projects' | 'education' | 'skills' | 'generic'

const SECTION_TYPE_MAP: Record<string, SectionType> = {
  experience: 'experience',
  projects: 'projects',
  education: 'education',
  skills: 'skills',
}

function getSectionType(name: string): SectionType {
  return SECTION_TYPE_MAP[name.toLowerCase()] || 'generic'
}
```

All four known types are treated as multi-entry (parsed into entries). Generic sections remain single textarea.

---

## Reordering

### Section Reordering (SectionEditor.vue)

- Up/down arrow buttons in each `SectionCard` header
- Top section hides up arrow; bottom section hides down arrow
- `SectionEditor` provides `moveSectionUp(index)` and `moveSectionDown(index)` as props/callbacks
- Each swaps adjacent elements in `sections` array, then calls `emitUpdate()`

### Entry Reordering (SectionCard.vue)

- Up/down arrow buttons on each entry card (all section types)
- Same hide-at-boundary logic
- `SectionCard` handles `moveEntryUp(index)` and `moveEntryDown(index)` on its entries array
- Emits `update:entries` after swap

### Arrow Button Style

- Small, subtle buttons (16×16px) placed in the card header row
- Up arrow: `▲` or chevron-up, Down arrow: `▼` or chevron-down
- Disabled/hidden state at boundaries (no wrap-around)

---

## Structured Entry Cards

### ExperienceEntryCard.vue

**Props:**
```typescript
interface ExperienceEntry {
  key: string
  role: string
  company: string       // includes location, e.g. "BotWot (Remote, India)"
  startDate: string
  endDate: string
  content: string       // bullet points
}
```

**Fields:** Role input, Company+Location input, Start Date input, End Date input, Content textarea

**Markdown format:** `**Role — Company** *Start – End*`

### EducationEntryCard.vue

**Props:**
```typescript
interface EducationEntry {
  key: string
  degree: string
  university: string
  startDate: string
  endDate: string
  content: string       // coursework, etc.
}
```

**Fields:** Degree input, University input, Start Date input, End Date input, Content textarea

**Markdown format:** `**Degree - University.** *Start – End*`

### ProjectEntryCard.vue

**Props:**
```typescript
interface ProjectEntry {
  key: string
  name: string
  url: string
  techStack: string[]
  content: string       // bullet points
}
```

**Fields:** Name input, URL input, Tech Stack (ChipInput), Content textarea

**Markdown format:** `**[Name](url)** | Stack - Tech1, Tech2`

### SkillCategoryCard.vue

**Props:**
```typescript
interface SkillCategory {
  key: string
  name: string          // category header, e.g. "Data Engineering"
  skills: string[]      // individual skills
}
```

**Fields:** Category name input, Skills (ChipInput)

**Markdown format:** `**Category:** Skill1, Skill2, Skill3.`

Note: SkillCategoryCard has no content textarea — just name + chips.

---

## ChipInput.vue

Reusable component for tag/chip input. Used by SkillCategoryCard and ProjectEntryCard.

**Props:** `modelValue: string[]`
**Emits:** `update:modelValue`

**Behavior:**
- Renders chips as inline pill badges with × remove button
- Text input at the end of the chip row (flex-wrap layout)
- Press **Enter** or **comma** to add current input as a new chip
- **Backspace** on empty input removes the last chip
- Chips are trimmed and deduplicated on add
- Compact visual style to fit many chips per line

---

## Parsing Logic

Parsing lives in `SectionEditor.vue`, expanding the existing `parseEntries` function.

### Entry Point

```typescript
function parseSectionEntries(content: string, type: SectionType): EntryData[] {
  switch (type) {
    case 'experience': return parseExperienceEntries(content)
    case 'education': return parseEducationEntries(content)
    case 'projects': return parseProjectEntries(content)
    case 'skills': return parseSkillCategories(content)
    default: return parseGenericEntries(content)
  }
}
```

### Experience Parser

Split on lines starting with `**`. For each block:
- Regex: `^\*\*(.+?)\s*[—–-]\s*(.+?)\*\*\s*\*(.+?)\*\s*$` on first line
- Extract: role, company (with location), dates (split on `–` or `-` for start/end)
- Rest of block → content (bullet points)
- Fallback: if regex fails, treat as generic entry

### Education Parser

Split on lines starting with `**`. For each block:
- Regex: `^\*\*(.+?)\s*[-–]\s*(.+?)\*\*\s*\*(.+?)\*\s*$` on first line
- Extract: degree, university, dates
- Rest → content (coursework)
- Fallback: generic entry

### Projects Parser

Split on lines starting with `**`. For each block:
- Regex: `^\*\*\[(.+?)\]\((.+?)\)\*\*\s*\|\s*Stack\s*[-–]\s*(.+)$` on first line (with link)
- Also handle: `^\*\*(.+?)\*\*\s*\|\s*Stack\s*[-–]\s*(.+)$` (without link)
- Extract: name, url, tech stack (split on `,` and trim)
- Rest → content
- Fallback: generic entry

### Skills Parser

Split on lines starting with `**`. For each block:
- Regex: `^\*\*(.+?):\*\*\s*(.+)$`
- Extract: category name, skills (split on `,`, trim, remove trailing `.`)
- Fallback: if line doesn't match, treat as a generic entry with content only

---

## Assembly Logic

Each section type has a corresponding assembler in `SectionEditor.vue`.

### Experience Assembly

```
**{role} — {company}** *{startDate} – {endDate}*
{content}
```

### Education Assembly

```
**{degree} - {university}.** *{startDate} – {endDate}*
{content}
```

### Projects Assembly

```
**[{name}]({url})** | Stack - {techStack.join(', ')}
{content}
```

If url is empty: `**{name}** | Stack - {techStack.join(', ')}`

### Skills Assembly

```
**{name}:** {skills.join(', ')}.
```

Trailing period added automatically. Categories separated by blank lines.

---

## EntryData Type Extension

The existing `EntryData` interface (`{ key, header, content }`) is extended with optional structured fields:

```typescript
interface EntryData {
  key: string
  header: string          // kept for generic fallback
  content: string         // bullet points / coursework / empty for skills

  // Structured fields (populated based on section type)
  role?: string
  company?: string
  degree?: string
  university?: string
  startDate?: string
  endDate?: string
  name?: string
  url?: string
  techStack?: string[]
  skills?: string[]       // for skill categories
  categoryName?: string   // for skill categories
}
```

This keeps a single array type for `SectionCard`'s entries prop while allowing each specialized card to read its relevant fields.

---

## SectionCard Changes

- Accept a `sectionType` prop from `SectionEditor`
- Render the appropriate entry card component based on type:
  ```
  experience  → ExperienceEntryCard
  education   → EducationEntryCard
  projects    → ProjectEntryCard
  skills      → SkillCategoryCard
  generic     → EntryCard (existing)
  ```
- Add up/down arrow buttons on each entry card
- "Add Entry" button label adapts: "Add Experience", "Add Project", "Add Education", "Add Skill Category"

---

## Edge Cases

- **Empty sections:** Allowed. Section card shows empty state, user can add entries.
- **Unparseable entries:** Fall back to generic EntryCard with the raw text in header/content. User can edit manually.
- **Experience with no dates:** startDate and endDate default to empty strings. Assembly omits the date portion if both are empty.
- **Projects with no URL:** Assembly uses `**{name}**` instead of `**[{name}]({url})**`.
- **Skills with trailing periods/spaces:** Trimmed during parsing. Period added consistently during assembly.
- **Section name editing:** Not in scope — section names remain fixed (derived from markdown headers). Users can add custom sections via "Add Section".

---

## Files Changed

| File | Change |
|------|--------|
| `SectionEditor.vue` | Section type map, section reordering, expanded parse/assemble per type |
| `SectionCard.vue` | `sectionType` prop, component dispatch, entry reordering, arrow buttons |
| `EntryCard.vue` | No changes (remains generic fallback) |
| `ChipInput.vue` | **New** — reusable chip/tag input |
| `ExperienceEntryCard.vue` | **New** — structured experience fields |
| `EducationEntryCard.vue` | **New** — structured education fields |
| `ProjectEntryCard.vue` | **New** — structured project fields |
| `SkillCategoryCard.vue` | **New** — structured skill category |

No backend changes. No new dependencies.
