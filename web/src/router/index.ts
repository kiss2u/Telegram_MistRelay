import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/dashboard.vue')
  },
  {
    path: '/downloads',
    name: 'Downloads',
    component: () => import('@/views/downloads.vue')
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('@/views/tasks.vue')
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/settings.vue')
  },
  {
    path: '/drive',
    name: 'Drive',
    component: () => import('@/views/drive.vue')
  },
  {
    path: '/system',
    name: 'System',
    component: () => import('@/views/system.vue')
  },
  {
    path: '/logs',
    redirect: '/system?tab=app-logs'
  }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'Login' && auth.isLoggedIn) {
    return { path: '/' }
  }
})
