import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', component: () => import('./views/EditorView.vue') },
  { path: '/profile', component: () => import('./views/ProfileView.vue') },
  { path: '/history', component: () => import('./views/HistoryView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
