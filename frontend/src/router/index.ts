import { createRouter, createWebHistory } from 'vue-router'
import { sseService } from '@/services/sseService'
import { useAuthStore } from '@/stores'
import MonitorView from '@/views/MonitorView.vue'
import LoginView from '@/views/LoginView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/monitor',
    },
    {
      path: '/monitor',
      name: 'monitor',
      component: MonitorView,
      meta: {
        title: 'NBA 实时监控',
        requiresAuth: true,
      },
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: {
        title: '登录',
      },
    },
  ],
})

// 离开监控页面时清理 SSE 连接，并处理登录态跳转
router.beforeEach((to, from) => {
  const authStore = useAuthStore()

  if (from.name === 'monitor' && to.name !== 'monitor') {
    sseService.disconnect()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }

  if (to.name === 'login' && authStore.isAuthenticated) {
    return { name: 'monitor' }
  }
})

// 更新页面标题
router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = title || 'NBA 实时监控'
})

export default router
