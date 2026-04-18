<script setup lang="ts">
import { ref } from 'vue'
import type { EntryData, SectionType } from '../utils/sectionParsers'
import EntryCard from './EntryCard.vue'
import ExperienceEntryCard from './ExperienceEntryCard.vue'
import EducationEntryCard from './EducationEntryCard.vue'
import ProjectEntryCard from './ProjectEntryCard.vue'
import SkillCategoryCard from './SkillCategoryCard.vue'

const props = defineProps<{
  title: string
  sectionType: SectionType
  content?: string
  entries?: EntryData[]
  isFirst?: boolean
  isLast?: boolean
}>()

const emit = defineEmits<{
  'update:content': [value: string]
  'update:entries': [value: EntryData[]]
  remove: []
  moveUp: []
  moveDown: []
}>()

const collapsed = ref(true)

const isMultiEntry = ['experience', 'education', 'projects', 'skills'].includes(props.sectionType)

function updateEntry(index: number, updated: EntryData) {
  if (!props.entries) return
  const list = [...props.entries]
  list[index] = updated
  emit('update:entries', list)
}

function removeEntry(index: number) {
  if (!props.entries) return
  emit('update:entries', props.entries.filter((_, i) => i !== index))
}

function moveEntryUp(index: number) {
  if (!props.entries || index === 0) return
  const list = [...props.entries]
  ;[list[index - 1], list[index]] = [list[index], list[index - 1]]
  emit('update:entries', list)
}

function moveEntryDown(index: number) {
  if (!props.entries || index >= props.entries.length - 1) return
  const list = [...props.entries]
  ;[list[index], list[index + 1]] = [list[index + 1], list[index]]
  emit('update:entries', list)
}

function addEntry() {
  const key = `new-${Date.now()}`
  const base: EntryData = { key, header: '', content: '' }

  let newEntry: EntryData
  switch (props.sectionType) {
    case 'experience':
      newEntry = { ...base, role: '', company: '', startDate: '', endDate: '' }
      break
    case 'education':
      newEntry = { ...base, degree: '', university: '', startDate: '', endDate: '' }
      break
    case 'projects':
      newEntry = { ...base, name: '', url: '', techStack: [] }
      break
    case 'skills':
      newEntry = { ...base, categoryName: '', skills: [] }
      break
    default:
      newEntry = base
  }

  emit('update:entries', [...(props.entries || []), newEntry])
}

const ADD_LABELS: Record<string, string> = {
  experience: '+ Add Experience',
  education: '+ Add Education',
  projects: '+ Add Project',
  skills: '+ Add Skill Category',
}

const addLabel = ADD_LABELS[props.sectionType] || '+ Add Entry'
</script>

<template>
  <div class="section-card">
    <div class="section-header" @click="collapsed = !collapsed">
      <div class="section-arrows" @click.stop>
        <button v-if="!isFirst" class="arrow-btn" @click="$emit('moveUp')" title="Move section up">&#9650;</button>
        <button v-if="!isLast" class="arrow-btn" @click="$emit('moveDown')" title="Move section down">&#9660;</button>
      </div>
      <span class="collapse-icon">{{ collapsed ? '+' : '-' }}</span>
      <h3>{{ title }}</h3>
      <span class="entry-count" v-if="isMultiEntry && entries">{{ entries.length }} {{ sectionType === 'skills' ? 'categories' : 'entries' }}</span>
      <button class="section-remove-btn" @click.stop="$emit('remove')" title="Remove section">&times;</button>
    </div>

    <div v-show="!collapsed" class="section-body">
      <!-- Single-content section (generic) -->
      <template v-if="!isMultiEntry">
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
          <div v-for="(entry, index) in entries" :key="entry.key" class="entry-wrapper">
            <div class="entry-arrows">
              <button v-if="index > 0" class="arrow-btn" @click="moveEntryUp(index)" title="Move up">&#9650;</button>
              <button v-if="entries && index < entries.length - 1" class="arrow-btn" @click="moveEntryDown(index)" title="Move down">&#9660;</button>
            </div>
            <div class="entry-content-area">
              <ExperienceEntryCard
                v-if="sectionType === 'experience'"
                :entry="entry"
                @update:entry="updateEntry(index, $event)"
                @remove="removeEntry(index)"
              />
              <EducationEntryCard
                v-else-if="sectionType === 'education'"
                :entry="entry"
                @update:entry="updateEntry(index, $event)"
                @remove="removeEntry(index)"
              />
              <ProjectEntryCard
                v-else-if="sectionType === 'projects'"
                :entry="entry"
                @update:entry="updateEntry(index, $event)"
                @remove="removeEntry(index)"
              />
              <SkillCategoryCard
                v-else-if="sectionType === 'skills'"
                :entry="entry"
                @update:entry="updateEntry(index, $event)"
                @remove="removeEntry(index)"
              />
              <EntryCard
                v-else
                :header="entry.header"
                :content="entry.content"
                @update:header="updateEntry(index, { ...entry, header: $event })"
                @update:content="updateEntry(index, { ...entry, content: $event })"
                @remove="removeEntry(index)"
              />
            </div>
          </div>
        </div>
        <button class="add-entry-btn" @click="addEntry">{{ addLabel }}</button>
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
.section-arrows {
  display: flex; flex-direction: column; gap: 2px;
}
.arrow-btn {
  width: 18px; height: 16px; border: none; background: transparent;
  cursor: pointer; font-size: 0.6rem; color: #999; border-radius: 3px;
  display: flex; align-items: center; justify-content: center; padding: 0;
}
.arrow-btn:hover { background: #e0e0e0; color: #333; }
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
.entry-wrapper { display: flex; gap: 4px; align-items: flex-start; }
.entry-arrows {
  display: flex; flex-direction: column; gap: 2px; padding-top: 8px;
  min-width: 20px;
}
.entry-content-area { flex: 1; min-width: 0; }
.add-entry-btn {
  margin-top: 8px; width: 100%; padding: 8px; border: 1px dashed #ccc;
  border-radius: 8px; background: #fafafa; font-size: 0.82rem;
  font-weight: 600; cursor: pointer; color: #666;
}
.add-entry-btn:hover { background: #f0f0f0; border-color: #999; }
</style>
