import { ref } from 'vue'

export interface Toast {
  id: number
  message: string
  type: 'info' | 'error' | 'success' | 'warning'
  action?: { label: string; route: string }
}

const toasts = ref<Toast[]>([])
let nextId = 0

export function useToast() {
  function show(message: string, type: Toast['type'] = 'info', action?: Toast['action'], duration = 5000) {
    const id = nextId++
    toasts.value.push({ id, message, type, action })
    if (duration > 0) {
      setTimeout(() => dismiss(id), duration)
    }
  }

  function dismiss(id: number) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  return { toasts, show, dismiss }
}
