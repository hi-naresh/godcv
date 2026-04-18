# Agent System

GodCV uses an event-driven multi-agent architecture for resume tailoring. Each agent is a specialist that handles one section of the resume.

## Pipeline

```
Job Description + Resume
        |
        v
  Orchestrator Agent
  (analysis + planning)
        |
        v
    Agent Bus
   /    |    \
  v     v     v
Summary Skills Projects   (parallel)
              |
              v
        Experience         (sequential, per-entry)
              |
              v
        Resume Assembler
              |
        +-----+------+
        |     |      |
        v     v      v
     Scorer  ATS  Suggestions  (parallel)
              |
              v
       Profile Learner
```

## Orchestrator

The orchestrator is the brain of the system. It analyzes the job description against the resume and produces a structured plan.

**Input:** Job description, resume markdown, seniority level, role insights

**Output:**
- `analysis` -- job title, company, position level, key requirements, matched strengths
- `tool_calls` -- list of agent actions to execute
- `sections_unchanged` -- sections that don't need modification
- `section_order` -- optimal section ordering (seniority-aware)
- `scoring` -- before/after score estimates with gap suggestions

### Tool Call Format

Each tool call specifies what an agent should do:

```json
{
  "agent": "experience",
  "action": "rewrite",
  "entry": "AI Engineer at Acme Corp",
  "instructions": "Emphasize LLM orchestration and quantify pipeline throughput"
}
```

Actions vary by agent:
- `rewrite` -- modify content
- `reorder` -- change item ordering
- `include` / `exclude` -- for experience/project entries
- `keep` -- leave unchanged

## Agents

### Summary Agent

Rewrites the professional summary (2-3 sentences) to align with the target role. Uses keywords from the JD naturally without keyword stuffing.

### Skills Agent

Reorders skill categories and individual skills within categories. Promotes JD-relevant skills to the top, demotes less relevant ones. Never removes skills -- only reorders and may add 1-2 clearly inferred ones.

### Experience Agent

Rewrites bullet points for individual job entries. Preserves job title, company, dates, and quantified achievements. Uses action verbs and weaves in relevant terminology. Runs per-entry (sequentially) to maintain context.

### Projects Agent

Reorders projects by relevance to the JD. Adjusts project descriptions to highlight relevant technologies and outcomes. Keeps project names and links accurate.

### Resume Scorer

Post-tailoring evaluation. Scores the tailored resume against the JD on four dimensions:
- `keyword_match` (0-100) -- JD keyword coverage
- `skills_coverage` (0-100) -- required skills present
- `experience_fit` -- one-sentence assessment
- `overall_fit` (0-100) -- holistic match score

### ATS Scorer

Simulates an Applicant Tracking System. Evaluates nine categories:
- Contact info, parsability, keyword match, section headers, date format, title match, hard skills, quantified results, experience depth

Returns a weighted `ats_score` (0-100) and a `brutal_verdict`.

### Suggestion Agent

Generates concrete improvement suggestions from gap analysis:
- **skill** -- add missing skills mentioned in JD
- **bullet** -- new achievement bullets for existing entries
- **project** -- suggest academic/personal projects to add
- **remove** -- flag irrelevant or space-wasting content
- **replace** -- rephrase weak bullets with stronger alternatives

### Profile Learner

Extracts patterns from each tailoring run and stores them as role insights:
- Strongest points for this role type
- Preferred skill ordering
- Which sections get modified most

These insights are fed back into future orchestrator runs for the same role type.

## Agent Bus

The bus reads `tool_calls` from the orchestrator plan and dispatches agents:

1. Groups tool calls by agent type
2. Runs summary, skills, and projects agents in parallel
3. Runs experience agents sequentially (one per job entry)
4. Collects results into `modified_sections` and `modified_entries`
5. Emits SSE events for each agent start/done

## Seniority Awareness

The orchestrator adjusts its plan based on seniority level:

| Level | Behavior |
|-------|----------|
| Graduate | Education first, emphasize coursework and projects |
| Junior | Balance projects and early experience |
| Mid-level | Experience-led, skills aligned to JD |
| Senior | Leadership and impact emphasis |
| Lead | Architecture decisions, team management |
| Principal | Strategy, org-level impact, thought leadership |
