import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { shouldUseHashHistory } from '@/utils/runtime'

function getFirstQueryValue(value: unknown): string | undefined {
  if (typeof value === 'string') {
    return value
  }
  if (Array.isArray(value) && typeof value[0] === 'string') {
    return value[0]
  }
  return undefined
}

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
    redirect: '/downloads?tab=queue'
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
    path: '/local-downloads',
    redirect: '/downloads?tab=local'
  },
  {
    path: '/system',
    redirect: (to) => {
      const tab = getFirstQueryValue(to.query.tab) === 'app-logs' ? 'app-logs' : 'docker'
      return {
        path: '/settings',
        query: {
          ...to.query,
          scope: 'management',
          tab,
        },
      }
    }
  },
  {
    path: '/logs',
    redirect: (to) => ({
      path: '/settings',
      query: {
        ...to.query,
        scope: 'management',
        tab: 'app-logs',
      },
    })
  }
]

export const router = createRouter({
  history: shouldUseHashHistory() ? createWebHashHistory() : createWebHistory(),
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
