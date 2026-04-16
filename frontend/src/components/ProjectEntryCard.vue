<script setup lang="ts">
import type { EntryData } from '../utils/sectionParsers'
import ChipInput from './ChipInput.vue'

const props = defineProps<{ entry: EntryData }>()
const emit = defineEmits<{ 'update:entry': [value: EntryData]; remove: [] }>()

function update(fields: Partial<EntryData>) {
  emit('update:entry', { ...props.entry, ...fields })
}
</script>

<template>
  <div class="entry-card">
    <div class="entry-header">
      <div class="entry-fields">
        <div class="field-row">
          <div class="field">
            <label>Project Name</label>
            <input :value="entry.name" @input="update({ name: ($event.target as HTMLInputElement).value })" placeholder="e.g. MyProject" />
          </div>
          <div class="field">
            <label>URL</label>
            <input :value="entry.url" @input="update({ url: ($event.target as HTMLInputElement).value })" placeholder="e.g. https://github.com/you/project" />
          </div>
        </div>
        <div class="field">
          <label>Tech Stack</label>
          <ChipInput
            :modelValue="entry.techStack || []"
            @update:modelValue="update({ techStack: $event })"
            placeholder="Type a tech and press Enter"
          />
        </div>
      </div>
      <button class="entry-remove-btn" @click="$emit('remove')" title="Remove entry">&times;</button>
    </div>
    <textarea
      class="entry-content"
      :value="entry.content"
      @input="update({ content: ($event.target as HTMLTextAreaElement).value })"
      placeholder="- What you built and the impact&#10;- Quantified result"
      rows="3"
    />
  </div>
</template>

<style scoped>
.entry-card { border: 1px solid #e8e8e8; border-radius: 8px; padding: 10px; background: #fafafa; }
.entry-header { display: flex; gap: 6px; margin-bottom: 6px; }
.entry-fields { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.field { display: flex; flex-direction: column; gap: 2px; }
.field label { font-size: 0.7rem; font-weight: 600; color: #888; }
.field input { padding: 5px 8px; border: 1px solid #d9d9d9; border-radius: 6px; font-size: 0.82rem; font-family: ui-monospace, monospace; }
.field input:focus { outline: none; border-color: #667eea; }
.entry-remove-btn { width: 26px; height: 26px; border: none; background: #f0f0f0; border-radius: 6px; font-size: 1rem; cursor: pointer; color: #999; display: flex; align-items: center; justify-content: center; align-self: flex-start; }
.entry-remove-btn:hover { background: #ffe0e0; color: #d00; }
.entry-content { width: 100%; resize: vertical; padding: 6px 8px; border: 1px solid #d9d9d9; border-radius: 6px; font-size: 0.8rem; font-family: ui-monospace, monospace; line-height: 1.5; }
.entry-content:focus { outline: none; border-color: #667eea; }
</style>
