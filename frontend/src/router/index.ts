import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { bare: true } },
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
    { path: '/compose', name: 'compose', component: () => import('@/views/ComposeView.vue') },
    { path: '/tide', name: 'tide', component: () => import('@/views/TideView.vue') },
    { path: '/mood', name: 'mood', component: () => import('@/views/MoodView.vue') },
    { path: '/ripples/:id', name: 'ripple-detail', component: () => import('@/views/RippleDetailView.vue') },
    { path: '/profile', name: 'profile', component: () => import('@/views/ProfileView.vue') },
    { path: '/admin', name: 'admin', component: () => import('@/views/AdminView.vue') },
  ],
})

// 全局路由守卫
// 1) 未登录一律先进登录页（带 redirect 以便登录后跳回）
// 2) 管理后台额外校验管理员角色
router.beforeEach(async (to) => {
  const userStore = useUserStore()
  const token = userStore.token

  if (!token && to.name !== 'login') {
    return {
      name: 'login',
      query: to.fullPath !== '/' ? { redirect: to.fullPath } : {},
    }
  }

  // 已登录再访问登录页 → 回首页
  if (token && to.name === 'login') {
    return { path: '/' }
  }

  // 管理后台 / 发布页：需恢复登录态后校验角色
  // 管理后台仅 admin 可进；发布页对 admin 关闭（管理员不提供发微澜）
  if (to.name === 'admin' || to.name === 'compose') {
    if (!userStore.user) {
      await userStore.refreshMe()
    }
    if (to.name === 'compose' && userStore.user?.role === 'admin') {
      return { path: '/' }
    }
    if (to.name === 'admin' && userStore.user?.role !== 'admin') {
      return { path: '/' }
    }
  }
})

export default router
