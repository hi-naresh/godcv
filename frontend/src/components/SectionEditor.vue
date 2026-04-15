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
