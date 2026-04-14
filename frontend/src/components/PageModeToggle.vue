<script setup lang="ts">
defineProps<{ modelValue: 'single' | 'multi' }>()
defineEmits<{ 'update:modelValue': [value: 'single' | 'multi'] }>()
</script>

<template>
  <div class="page-mode-toggle">
    <button
      :class="{ active: modelValue === 'single' }"
      @click="$emit('update:modelValue', 'single')"
    >1 Page</button>
    <button
      :class="{ active: modelValue === 'multi' }"
      @click="$emit('update:modelValue', 'multi')"
    >Multi-Page</button>
  </div>
</template>

<style scoped>
.page-mode-toggle {
  display: flex; border: 1px solid #d0d0d0; border-radius: 8px; overflow: hidden;
}
.page-mode-toggle button {
  flex: 1; padding: 6px 12px; border: none; background: #fafafa;
  font-size: 0.8rem; font-weight: 600; cursor: pointer; transition: all 0.15s;
}
.page-mode-toggle button.active {
  background: #111; color: #fff;
}
.page-mode-toggle button:not(.active):hover {
  background: #eee;
}
</style>
