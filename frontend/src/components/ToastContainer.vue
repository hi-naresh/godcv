<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useToast } from '../composables/useToast'

const router = useRouter()
const { toasts, dismiss } = useToast()

function handleAction(toast: typeof toasts.value[0]) {
  if (toast.action?.route) {
    router.push(toast.action.route)
  }
  dismiss(toast.id)
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="['toast', toast.type]"
        >
          <span class="toast-msg">{{ toast.message }}</span>
          <button v-if="toast.action" class="toast-action" @click="handleAction(toast)">
            {{ toast.action.label }}
          </button>
          <button class="toast-close" @click="dismiss(toast.id)">&times;</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed; bottom: 20px; right: 20px; z-index: 9999;
  display: flex; flex-direction: column-reverse; gap: 8px;
  max-width: 400px;
}
.toast {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-radius: 10px;
  font-size: 0.85rem; font-weight: 500;
  box-shadow: 0 4px 16px rgba(0,0,0,.15);
  animation: toast-in 0.2s ease;
}
.toast.info { background: #111; color: #fff; }
.toast.error { background: #dc3545; color: #fff; }
.toast.success { background: #28a745; color: #fff; }
.toast.warning { background: #f0ad4e; color: #111; }

.toast-msg { flex: 1; }
.toast-action {
  border: 1px solid rgba(255,255,255,.4); background: none; color: inherit;
  padding: 3px 10px; border-radius: 6px; font-size: 0.78rem;
  font-weight: 700; cursor: pointer; white-space: nowrap;
}
.toast-action:hover { background: rgba(255,255,255,.15); }
.toast-close {
  border: none; background: none; color: inherit; font-size: 1.1rem;
  cursor: pointer; opacity: 0.6; padding: 0 2px;
}
.toast-close:hover { opacity: 1; }

@keyframes toast-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.toast-enter-active { animation: toast-in 0.2s ease; }
.toast-leave-active { transition: all 0.2s ease; }
.toast-leave-to { opacity: 0; transform: translateX(30px); }
</style>
