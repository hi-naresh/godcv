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
  <div class="skill-cat-card">
    <div class="skill-cat-header">
      <input
        class="cat-name-input"
        :value="entry.categoryName"
        @input="update({ categoryName: ($event.target as HTMLInputElement).value })"
        placeholder="Category name (e.g. Programming)"
      />
      <button class="entry-remove-btn" @click="$emit('remove')" title="Remove category">&times;</button>
    </div>
    <ChipInput
      :modelValue="entry.skills || []"
      @update:modelValue="update({ skills: $event })"
      placeholder="Type a skill and press Enter"
    />
  </div>
</template>

<style scoped>
.skill-cat-card { border: 1px solid #e8e8e8; border-radius: 8px; padding: 10px; background: #fafafa; display: flex; flex-direction: column; gap: 6px; }
.skill-cat-header { display: flex; align-items: center; gap: 6px; }
.cat-name-input { flex: 1; padding: 5px 8px; border: 1px solid #d9d9d9; border-radius: 6px; font-size: 0.82rem; font-weight: 600; }
.cat-name-input:focus { outline: none; border-color: #667eea; }
.entry-remove-btn { width: 26px; height: 26px; border: none; background: #f0f0f0; border-radius: 6px; font-size: 1rem; cursor: pointer; color: #999; display: flex; align-items: center; justify-content: center; }
.entry-remove-btn:hover { background: #ffe0e0; color: #d00; }
</style>
