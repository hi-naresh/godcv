<script setup lang="ts">
defineProps<{
  header: string
  content: string
}>()

defineEmits<{
  'update:header': [value: string]
  'update:content': [value: string]
  remove: []
}>()
</script>

<template>
  <div class="entry-card">
    <div class="entry-header">
      <input
        class="entry-title-input"
        :value="header"
        @input="$emit('update:header', ($event.target as HTMLInputElement).value)"
        placeholder="Role — Company (Location) or Project Name | Stack"
      />
      <button class="entry-remove-btn" @click="$emit('remove')" title="Remove entry">&times;</button>
    </div>
    <textarea
      class="entry-content"
      :value="content"
      @input="$emit('update:content', ($event.target as HTMLTextAreaElement).value)"
      placeholder="- Bullet point 1&#10;- Bullet point 2"
      rows="3"
    />
  </div>
</template>

<style scoped>
.entry-card {
  border: 1px solid #e8e8e8; border-radius: 8px; padding: 10px;
  background: #fafafa;
}
.entry-header { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.entry-title-input {
  flex: 1; min-width: 0; border: 1px solid #d9d9d9; border-radius: 6px;
  padding: 6px 8px; font-size: 0.82rem; font-weight: 600;
  font-family: ui-monospace, monospace;
}
.entry-title-input:focus { outline: none; border-color: #667eea; }
.entry-remove-btn {
  width: 26px; height: 26px; min-width: 26px; border: none; background: #f0f0f0;
  border-radius: 6px; font-size: 1rem; cursor: pointer; color: #999;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.entry-remove-btn:hover { background: #ffe0e0; color: #d00; }
.entry-content {
  width: 100%; resize: vertical; padding: 6px 8px;
  border: 1px solid #d9d9d9; border-radius: 6px; font-size: 0.8rem;
  font-family: ui-monospace, monospace; line-height: 1.5;
}
.entry-content:focus { outline: none; border-color: #667eea; }
</style>
