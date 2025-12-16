import './assets/main.css'   // ⬅️ OBLIGATOIRE

import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import LoginView from './views/LoginView.vue'
import DashboardView from './views/DashboardView.vue'
import PartView from './views/PartView.vue'
import AllPartView from './views/AllPartView.vue'
import { auth } from './services/auth'
import { initSocket } from "./services/socket"
import ChatView from './views/ChatView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView },
    { path: '/', component: DashboardView, meta: { requiresAuth: true } },
    { path: '/parts/:partId', component: PartView, meta: { requiresAuth: true } },
    { path: '/parts', component: AllPartView, meta: { requiresAuth: true } },
    { path: '/chatIA', component: ChatView, meta: { requiresAuth: true } }
  ]
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !auth.isAuthenticated()) return '/login'
  if (to.path === '/login' && auth.isAuthenticated()) return '/'
})

initSocket()

createApp(App).use(router).mount('#app')
