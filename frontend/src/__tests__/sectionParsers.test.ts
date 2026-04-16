import { describe, it, expect } from 'vitest'
import {
  getSectionType,
  isMultiEntryType,
  parseExperienceEntries,
  assembleExperienceEntries,
  parseEducationEntries,
  assembleEducationEntries,
  parseProjectEntries,
  assembleProjectEntries,
  parseSkillCategories,
  assembleSkillCategories,
  parseSectionEntries,
  assembleSectionContent,
  type EntryData,
} from '../utils/sectionParsers'

describe('getSectionType', () => {
  it('returns "experience" for Experience heading', () => {
    expect(getSectionType('Experience')).toBe('experience')
  })

  it('returns "education" for Education heading', () => {
    expect(getSectionType('Education')).toBe('education')
  })

  it('returns "skills" for Skills heading', () => {
    expect(getSectionType('Skills')).toBe('skills')
  })

  it('returns "projects" for Projects heading', () => {
    expect(getSectionType('Projects')).toBe('projects')
  })

  it('returns "generic" for unknown headings', () => {
    expect(getSectionType('Summary')).toBe('generic')
    expect(getSectionType('Volunteering and Interests')).toBe('generic')
  })

  it('is case-insensitive', () => {
    expect(getSectionType('experience')).toBe('experience')
    expect(getSectionType('SKILLS')).toBe('skills')
  })
})

describe('isMultiEntryType', () => {
  it('returns true for experience, education, projects', () => {
    expect(isMultiEntryType('experience')).toBe(true)
    expect(isMultiEntryType('education')).toBe(true)
    expect(isMultiEntryType('projects')).toBe(true)
  })

  it('returns true for skills', () => {
    expect(isMultiEntryType('skills')).toBe(true)
  })

  it('returns false for generic', () => {
    expect(isMultiEntryType('generic')).toBe(false)
  })
})

describe('parseExperienceEntries', () => {
  it('parses a standard experience entry with role, company, dates', () => {
    const content =
      '**Founding AI Engineer — NestDore (London based startup, ~10 people)**  *October 2025 – March 2026*\n' +
      '- Building the core intelligent-matching engine.\n' +
      '- Designing data pipelines.'

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].role).toBe('Founding AI Engineer')
    expect(entries[0].company).toBe('NestDore (London based startup, ~10 people)')
    expect(entries[0].startDate).toBe('October 2025')
    expect(entries[0].endDate).toBe('March 2026')
    expect(entries[0].content).toContain('- Building the core')
    expect(entries[0].content).toContain('- Designing data pipelines.')
  })

  it('parses multiple experience entries', () => {
    const content =
      '**Founding AI Engineer — NestDore (London based startup, ~10 people)**  *October 2025 – March 2026*\n' +
      '- Building the core engine.\n' +
      '\n' +
      '**AI/ML Engineer (Part-Time) — BotWot iCX (Remote, Indian SaaS startup, ~25 people)**  *Jan 2025 – Oct 2025*\n' +
      '- Building orchestrated multi-agent CRM automation.'

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(2)
    expect(entries[0].role).toBe('Founding AI Engineer')
    expect(entries[0].company).toBe('NestDore (London based startup, ~10 people)')
    expect(entries[1].role).toBe('AI/ML Engineer (Part-Time)')
    expect(entries[1].company).toBe('BotWot iCX (Remote, Indian SaaS startup, ~25 people)')
    expect(entries[1].startDate).toBe('Jan 2025')
    expect(entries[1].endDate).toBe('Oct 2025')
  })

  it('handles "Present" as end date', () => {
    const content =
      '**Software Engineer — Acme Corp**  *Jan 2024 – Present*\n' +
      '- Working on things.'

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].startDate).toBe('Jan 2024')
    expect(entries[0].endDate).toBe('Present')
  })

  it('falls back to generic entry for unparseable lines', () => {
    const content = 'Just some plain text that is not formatted as experience.'

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].role).toBeUndefined()
    expect(entries[0].company).toBeUndefined()
    expect(entries[0].header).toBe('Just some plain text that is not formatted as experience.')
  })

  it('handles entries with no dates', () => {
    const content =
      '**Software Engineer — Acme Corp**\n' +
      '- Did some work.'

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].role).toBe('Software Engineer')
    expect(entries[0].company).toBe('Acme Corp')
    expect(entries[0].startDate).toBeUndefined()
    expect(entries[0].endDate).toBeUndefined()
    expect(entries[0].content).toContain('- Did some work.')
  })

  it('handles hyphen separator between role and company', () => {
    const content =
      '**Student Software Engineer (Intern) - SAILC AURO, Surat, IN (University)** *Jan 2022 – Dec 2023*\n' +
      '- Developed blockchain-based payment system.'

    const entries = parseExperienceEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].role).toBe('Student Software Engineer (Intern)')
    expect(entries[0].company).toBe('SAILC AURO, Surat, IN (University)')
  })
})

describe('assembleExperienceEntries', () => {
  it('assembles a standard entry with role, company, and dates', () => {
    const entries: EntryData[] = [
      {
        key: '1',
        header: '',
        content: '- Building the core engine.',
        role: 'Founding AI Engineer',
        company: 'NestDore',
        startDate: 'October 2025',
        endDate: 'March 2026',
      },
    ]

    const result = assembleExperienceEntries(entries)
    expect(result).toBe(
      '**Founding AI Engineer — NestDore** *October 2025 – March 2026*\n- Building the core engine.'
    )
  })

  it('omits date portion when both dates are empty', () => {
    const entries: EntryData[] = [
      {
        key: '1',
        header: '',
        content: '- Did some work.',
        role: 'Software Engineer',
        company: 'Acme Corp',
      },
    ]

    const result = assembleExperienceEntries(entries)
    expect(result).toBe('**Software Engineer — Acme Corp**\n- Did some work.')
  })

  it('assembles multiple entries separated by blank lines', () => {
    const entries: EntryData[] = [
      {
        key: '1',
        header: '',
        content: '- Task A.',
        role: 'Role A',
        company: 'Company A',
        startDate: 'Jan 2024',
        endDate: 'Present',
      },
      {
        key: '2',
        header: '',
        content: '- Task B.',
        role: 'Role B',
        company: 'Company B',
        startDate: 'Jan 2023',
        endDate: 'Dec 2023',
      },
    ]

    const result = assembleExperienceEntries(entries)
    expect(result).toBe(
      '**Role A — Company A** *Jan 2024 – Present*\n- Task A.\n\n' +
      '**Role B — Company B** *Jan 2023 – Dec 2023*\n- Task B.'
    )
  })
})

describe('parseEducationEntries', () => {
  it('parses a standard education entry with degree, university, and dates', () => {
    const content =
      '**M.Sc. in Artificial Intelligence - Brunel University London, UK.** *Jan 2025 – Jan 2026*  \n' +
      '***Coursework**:* Predictive Analytics; Neural Networks.'

    const entries = parseEducationEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].degree).toBe('M.Sc. in Artificial Intelligence')
    expect(entries[0].university).toBe('Brunel University London, UK.')
    expect(entries[0].startDate).toBe('Jan 2025')
    expect(entries[0].endDate).toBe('Jan 2026')
    expect(entries[0].content).toContain('Coursework')
  })

  it('parses multiple education entries', () => {
    const content =
      '**M.Sc. in Artificial Intelligence - Brunel University London, UK.** *Jan 2025 – Jan 2026*\n' +
      '***Coursework**:* Predictive Analytics.\n' +
      '\n' +
      '**B.Tech in Computer Science – Some University** *Aug 2019 – May 2023*\n' +
      '- GPA: 3.8/4.0'

    const entries = parseEducationEntries(content)
    expect(entries).toHaveLength(2)
    expect(entries[0].degree).toBe('M.Sc. in Artificial Intelligence')
    expect(entries[0].university).toBe('Brunel University London, UK.')
    expect(entries[1].degree).toBe('B.Tech in Computer Science')
    expect(entries[1].university).toBe('Some University')
    expect(entries[1].startDate).toBe('Aug 2019')
    expect(entries[1].endDate).toBe('May 2023')
  })

  it('handles entry with no dates', () => {
    const content = '**B.A. in English - Oxford University**\n- First class honours.'

    const entries = parseEducationEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].degree).toBe('B.A. in English')
    expect(entries[0].university).toBe('Oxford University')
    expect(entries[0].startDate).toBeUndefined()
    expect(entries[0].endDate).toBeUndefined()
  })

  it('strips trailing double spaces from header lines', () => {
    const content = '**M.Sc. in AI - Brunel University** *Jan 2025 – Jan 2026*  '

    const entries = parseEducationEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].degree).toBe('M.Sc. in AI')
    expect(entries[0].university).toBe('Brunel University')
  })
})

describe('assembleEducationEntries', () => {
  it('assembles a standard education entry', () => {
    const entries: EntryData[] = [
      {
        key: '1',
        header: '',
        content: '***Coursework**:* Predictive Analytics.',
        degree: 'M.Sc. in AI',
        university: 'Brunel University',
        startDate: 'Jan 2025',
        endDate: 'Jan 2026',
      },
    ]

    const result = assembleEducationEntries(entries)
    expect(result).toBe(
      '**M.Sc. in AI - Brunel University** *Jan 2025 – Jan 2026*\n***Coursework**:* Predictive Analytics.'
    )
  })

  it('omits dates when both are empty', () => {
    const entries: EntryData[] = [
      {
        key: '1',
        header: '',
        content: '',
        degree: 'B.A. in English',
        university: 'Oxford',
      },
    ]

    const result = assembleEducationEntries(entries)
    expect(result).toBe('**B.A. in English - Oxford**')
  })
})

describe('parseProjectEntries', () => {
  it('parses a project with link and tech stack', () => {
    const content =
      '**[Luxury Concierge LLM Agent](https://kaiconcierge.ai)** at BotWot **| Stack -** Python, LangChain, FastAPI\n' +
      '- Multi-agent orchestration system.'

    const entries = parseProjectEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].name).toBe('Luxury Concierge LLM Agent')
    expect(entries[0].url).toBe('https://kaiconcierge.ai')
    expect(entries[0].techStack).toEqual(['Python', 'LangChain', 'FastAPI'])
    expect(entries[0].content).toContain('- Multi-agent orchestration system.')
  })

  it('parses a project without link', () => {
    const content =
      '**Framework Benchmark Performance Analysis & Tech-Stack Prediction** at University **| Stack -** Python, R, scikit-learn\n' +
      '- Built automated data pipeline.'

    const entries = parseProjectEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].name).toBe('Framework Benchmark Performance Analysis & Tech-Stack Prediction')
    expect(entries[0].url).toBeUndefined()
    expect(entries[0].techStack).toEqual(['Python', 'R', 'scikit-learn'])
  })

  it('parses simple format with link and no "at Company"', () => {
    const content = '**[MyProject](https://github.com/me/proj)** | Stack - React, Node.js'

    const entries = parseProjectEntries(content)
    expect(entries).toHaveLength(1)
    expect(entries[0].name).toBe('MyProject')
    expect(entries[0].url).toBe('https://github.com/me/proj')
    expect(entries[0].techStack).toEqual(['React', 'Node.js'])
  })

  it('parses multiple project entries', () => {
    const content =
      '**[Project A](https://a.com)** **| Stack -** Python, FastAPI\n' +
      '- Did A.\n' +
      '\n' +
      '**Project B** **| Stack -** TypeScript, React\n' +
      '- Did B.'

    const entries = parseProjectEntries(content)
    expect(entries).toHaveLength(2)
    expect(entries[0].name).toBe('Project A')
    expect(entries[1].name).toBe('Project B')
    expect(entries[1].url).toBeUndefined()
  })
})

describe('assembleProjectEntries', () => {
  it('assembles a project with URL', () => {
    const entries: EntryData[] = [
      {
        key: '1',
        header: '',
        content: '- Multi-agent system.',
        name: 'Luxury Concierge',
        url: 'https://kaiconcierge.ai',
        techStack: ['Python', 'LangChain', 'FastAPI'],
      },
    ]

    const result = assembleProjectEntries(entries)
    expect(result).toBe(
      '**[Luxury Concierge](https://kaiconcierge.ai)** | Stack - Python, LangChain, FastAPI\n- Multi-agent system.'
    )
  })

  it('assembles a project without URL', () => {
    const entries: EntryData[] = [
      {
        key: '1',
        header: '',
        content: '- Built pipeline.',
        name: 'Benchmark Analysis',
        techStack: ['Python', 'R'],
      },
    ]

    const result = assembleProjectEntries(entries)
    expect(result).toBe(
      '**Benchmark Analysis** | Stack - Python, R\n- Built pipeline.'
    )
  })
})

describe('parseSkillCategories', () => {
  it('parses skill categories with trailing periods stripped', () => {
    const content =
      '**Data Engineering:** ETL Pipelines, API Integrations, MongoDB, Supabase, VectorDB.\n' +
      '\n' +
      '**AI Orchestration:** LangChain, LangGraph, RAG Systems, PyTorch.'

    const entries = parseSkillCategories(content)
    expect(entries).toHaveLength(2)
    expect(entries[0].categoryName).toBe('Data Engineering')
    expect(entries[0].skills).toEqual(['ETL Pipelines', 'API Integrations', 'MongoDB', 'Supabase', 'VectorDB'])
    expect(entries[1].categoryName).toBe('AI Orchestration')
    expect(entries[1].skills).toEqual(['LangChain', 'LangGraph', 'RAG Systems', 'PyTorch'])
  })

  it('handles lines with trailing whitespace (double space for markdown line break)', () => {
    const content =
      '**Cloud/Infra:** AWS, Azure, Docker.  \n' +
      '**Programming:** Python, TypeScript, Go.'

    const entries = parseSkillCategories(content)
    expect(entries).toHaveLength(2)
    expect(entries[0].categoryName).toBe('Cloud/Infra')
    expect(entries[0].skills).toEqual(['AWS', 'Azure', 'Docker'])
    expect(entries[1].categoryName).toBe('Programming')
    expect(entries[1].skills).toEqual(['Python', 'TypeScript', 'Go'])
  })

  it('handles multiline skills block from real resume', () => {
    const content =
      '**Data Engineering:** ETL Pipelines, API Integrations, Data Cleaning & Structuring, Airflow, DataHub, MongoDB, Supabase, VectorDB.\n' +
      '\n' +
      '**AI Orchestration:** LangChain, LangGraph, RAG Systems, Multi-Agent Workflows, ChatGPT/Claude/Gemini APIs, n8n workflows, Prompt Engineering, PyTorch, Streamlit, TensorFlow, Hugging Face, MLflow, XGBoost, SHAP, Fine-tuning (LoRA/QLoRA/PEFT), Model Compression.  \n' +
      '**Cloud/Infra:** AWS, Azure, Docker, Kubernetes, Helm, CI/CD, Monitoring (OpenTelemetry, Prometheus/Grafana).  \n' +
      '**Programming:** Python, TypeScript, Go.'

    const entries = parseSkillCategories(content)
    expect(entries).toHaveLength(4)
    expect(entries[0].categoryName).toBe('Data Engineering')
    expect(entries[1].categoryName).toBe('AI Orchestration')
    expect(entries[2].categoryName).toBe('Cloud/Infra')
    expect(entries[3].categoryName).toBe('Programming')
    expect(entries[3].skills).toEqual(['Python', 'TypeScript', 'Go'])
  })
})

describe('assembleSkillCategories', () => {
  it('assembles with trailing period and double newline between categories', () => {
    const entries: EntryData[] = [
      {
        key: '1',
        header: '',
        content: '',
        categoryName: 'Programming',
        skills: ['Python', 'TypeScript', 'Go'],
      },
      {
        key: '2',
        header: '',
        content: '',
        categoryName: 'Cloud',
        skills: ['AWS', 'Azure'],
      },
    ]

    const result = assembleSkillCategories(entries)
    expect(result).toBe(
      '**Programming:** Python, TypeScript, Go.\n\n**Cloud:** AWS, Azure.'
    )
  })
})

describe('parseSectionEntries', () => {
  it('dispatches to experience parser', () => {
    const content = '**Engineer — Acme**  *Jan 2024 – Present*\n- Work.'
    const entries = parseSectionEntries(content, 'experience')
    expect(entries).toHaveLength(1)
    expect(entries[0].role).toBe('Engineer')
  })

  it('dispatches to education parser', () => {
    const content = '**M.Sc. in AI - Brunel University** *Jan 2025 – Jan 2026*'
    const entries = parseSectionEntries(content, 'education')
    expect(entries).toHaveLength(1)
    expect(entries[0].degree).toBe('M.Sc. in AI')
  })

  it('dispatches to projects parser', () => {
    const content = '**[Proj](https://x.com)** | Stack - Python\n- Did stuff.'
    const entries = parseSectionEntries(content, 'projects')
    expect(entries).toHaveLength(1)
    expect(entries[0].name).toBe('Proj')
  })

  it('dispatches to skills parser', () => {
    const content = '**Programming:** Python, TypeScript.'
    const entries = parseSectionEntries(content, 'skills')
    expect(entries).toHaveLength(1)
    expect(entries[0].categoryName).toBe('Programming')
  })

  it('dispatches to generic parser for unknown types', () => {
    const content = '**Some Header**\nSome content.'
    const entries = parseSectionEntries(content, 'generic')
    expect(entries).toHaveLength(1)
    expect(entries[0].header).toContain('Some Header')
  })
})

describe('assembleSectionContent', () => {
  it('dispatches to experience assembler', () => {
    const entries: EntryData[] = [
      { key: '1', header: '', content: '- Work.', role: 'Eng', company: 'Co', startDate: 'Jan 2024', endDate: 'Present' },
    ]
    const result = assembleSectionContent(entries, 'experience')
    expect(result).toContain('**Eng — Co**')
  })

  it('dispatches to education assembler', () => {
    const entries: EntryData[] = [
      { key: '1', header: '', content: '', degree: 'M.Sc.', university: 'Uni', startDate: 'Jan 2025', endDate: 'Jan 2026' },
    ]
    const result = assembleSectionContent(entries, 'education')
    expect(result).toContain('**M.Sc. - Uni**')
  })

  it('dispatches to projects assembler', () => {
    const entries: EntryData[] = [
      { key: '1', header: '', content: '', name: 'Proj', url: 'https://x.com', techStack: ['Python'] },
    ]
    const result = assembleSectionContent(entries, 'projects')
    expect(result).toContain('**[Proj](https://x.com)**')
  })

  it('dispatches to skills assembler', () => {
    const entries: EntryData[] = [
      { key: '1', header: '', content: '', categoryName: 'Lang', skills: ['Python'] },
    ]
    const result = assembleSectionContent(entries, 'skills')
    expect(result).toBe('**Lang:** Python.')
  })

  it('dispatches to generic assembler', () => {
    const entries: EntryData[] = [
      { key: '1', header: '**Heading**', content: 'Body text.' },
    ]
    const result = assembleSectionContent(entries, 'generic')
    expect(result).toContain('**Heading**')
    expect(result).toContain('Body text.')
  })
})

describe('round-trip: parse then assemble then re-parse', () => {
  it('experience entries survive round-trip', () => {
    const original =
      '**Founding AI Engineer — NestDore (London based startup, ~10 people)**  *October 2025 – March 2026*\n' +
      '- Building the core **intelligent-matching engine**.\n' +
      '- Designing **data pipelines**.\n' +
      '\n' +
      '**AI/ML Engineer (Part-Time) — BotWot iCX (Remote, Indian SaaS startup, ~25 people)**  *Jan 2025 – Oct 2025*\n' +
      '- Building orchestrated **multi-agent CRM automation**.'

    const entries = parseExperienceEntries(original)
    const assembled = assembleExperienceEntries(entries)
    const reparsed = parseExperienceEntries(assembled)
    expect(reparsed).toHaveLength(2)
    expect(reparsed[0].role).toBe('Founding AI Engineer')
    expect(reparsed[0].company).toBe('NestDore (London based startup, ~10 people)')
    expect(reparsed[1].role).toBe('AI/ML Engineer (Part-Time)')
  })

  it('skill categories survive round-trip', () => {
    const original =
      '**Data Engineering:** ETL Pipelines, API Integrations, MongoDB, Supabase, VectorDB.\n' +
      '\n' +
      '**Programming:** Python, TypeScript, Go.'

    const entries = parseSkillCategories(original)
    const assembled = assembleSkillCategories(entries)
    const reparsed = parseSkillCategories(assembled)
    expect(reparsed).toHaveLength(2)
    expect(reparsed[0].categoryName).toBe('Data Engineering')
    expect(reparsed[0].skills).toContain('VectorDB')
    expect(reparsed[1].skills).toEqual(['Python', 'TypeScript', 'Go'])
  })

  it('project entries survive round-trip', () => {
    const original = '**[MyProject](https://github.com/me/proj)** | Stack - React, Node.js\n- Built a thing.'

    const entries = parseProjectEntries(original)
    const assembled = assembleProjectEntries(entries)
    const reparsed = parseProjectEntries(assembled)
    expect(reparsed).toHaveLength(1)
    expect(reparsed[0].name).toBe('MyProject')
    expect(reparsed[0].url).toBe('https://github.com/me/proj')
    expect(reparsed[0].techStack).toEqual(['React', 'Node.js'])
  })

  it('education entries survive round-trip', () => {
    const original = '**M.Sc. in AI - Brunel University.** *Jan 2025 – Jan 2026*\n***Coursework**:* ML, DL.'

    const entries = parseEducationEntries(original)
    const assembled = assembleEducationEntries(entries)
    const reparsed = parseEducationEntries(assembled)
    expect(reparsed).toHaveLength(1)
    expect(reparsed[0].degree).toBe('M.Sc. in AI')
    expect(reparsed[0].university).toBe('Brunel University.')
  })
})
