import { createRouter, createWebHistory } from 'vue-router'
import { sseService } from '@/services/sseService'
import MonitorView from '@/views/MonitorView.vue'

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
      },
    },
  ],
})

// 离开监控页面时清理 SSE 连接
router.beforeEach((to, from) => {
  if (from.name === 'monitor' && to.name !== 'monitor') {
    sseService.disconnect()
  }
})

// 更新页面标题
router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = title || 'NBA 实时监控'
})

export default router
