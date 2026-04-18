# Resume Markdown Format

GodCV uses a specific markdown format for resumes. This document describes the expected structure.

## Structure

```markdown
---
name: Your Name
title: Role | Location
email: you@email.com
phone: +1234567890
portfolio: yoursite.com
github: github.com/you
linkedin: linkedin.com/in/you
font_size: 11.5
line_spacing: 1.5
---
# Summary

Your professional summary here.

---
# Education

**Degree - University** *Start – End*
***Coursework**:* Subject1; Subject2; Subject3.

---
# Skills

**Category:** Skill1, Skill2, Skill3.

---
# Experience

**Role — Company (Location)** *Start – End*
**Stack Used:** Tech1, Tech2, Tech3
- Achievement or responsibility.
- Another bullet point.

---
# Projects

**[Project Name](https://url)** **| Stack -** Tech1, Tech2
- What you built and the impact.
```

## Frontmatter

The YAML block between `---` markers contains metadata:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Full name (displayed large at top) |
| `title` | string | Role and location |
| `email` | string | Contact email (linked) |
| `phone` | string | Phone number (linked) |
| `portfolio` | string | Portfolio URL |
| `github` | string | GitHub profile URL |
| `linkedin` | string | LinkedIn profile URL |
| `font_size` | number | Base font size in pt (default: 11) |
| `line_spacing` | number | Line height multiplier (default: 1.4) |

## Section Formats

### Experience

```markdown
**Role — Company (Location)** *Start Date – End Date*
**Stack Used:** Tech1, Tech2, Tech3
- Achievement with **quantified result**.
- Another bullet point.
```

- Role and company separated by em-dash (—), en-dash (--), or hyphen (-)
- Dates in italics, displayed bold on the right side
- **Stack Used** line is optional, appears below the header
- Bullet points start with `-`

### Education

```markdown
**Degree - University** *Start – End*
***Coursework**:* Subject1; Subject2.
```

- Degree and university separated by hyphen or en-dash
- Coursework line appears on a new line (uses markdown line break)

### Skills

```markdown
**Category:** Skill1, Skill2, Skill3.
```

- Each line is a category with comma-separated skills
- Trailing period is conventional

### Projects

```markdown
**[Project Name](https://url)** **| Stack -** Tech1, Tech2
- Description of what you built.
```

- Name can be a markdown link or plain text
- **Stack** label is bold in the preview
- Tech stack is comma-separated after the dash

### Generic Sections

Any section not matching the above types (e.g., Summary, Volunteering) is treated as generic markdown.

## Preview Rendering

- Dates float to the right side via CSS (`strong + em` selector)
- Dates render bold in the preview (CSS override: `font-style: normal; font-weight: 700`)
- `<br>` tags clear floats so Stack Used appears on its own line
- Font size and line spacing auto-adjust to fill exactly one A4 page
