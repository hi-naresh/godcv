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
