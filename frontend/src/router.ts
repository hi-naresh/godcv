import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', component: () => import('./views/EditorView.vue') },
  { path: '/profile', component: () => import('./views/ProfileView.vue') },
  { path: '/history', component: () => import('./views/HistoryView.vue') },
  { path: '/preferences', component: () => import('./views/PreferencesView.vue') },
  { path: '/roles', component: () => import('./views/RolesView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
