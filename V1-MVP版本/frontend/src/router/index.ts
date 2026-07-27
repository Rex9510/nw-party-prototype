/**
 * Vue Router 配置（代替 uni-app 的 pages.json 路由）
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/pages/login/index' },
    {
      path: '/pages/login/index',
      name: 'login',
      component: () => import('@/pages/login/index.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/pages/index/index',
      name: 'home',
      component: () => import('@/pages/index/index.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/pages/members/list',
      name: 'members-list',
      component: () => import('@/pages/members/list.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/pages/members/new',
      name: 'members-new',
      component: () => import('@/pages/members/new.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/pages/members/edit/:id',
      name: 'members-edit',
      component: () => import('@/pages/members/new.vue'),
      meta: { requiresAuth: true },
      props: true,
    },
    {
      path: '/pages/members/import',
      name: 'members-import',
      component: () => import('@/pages/members/import.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/pages/activities/list',
      name: 'activities-list',
      component: () => import('@/pages/activities/list.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/pages/activities/new',
      name: 'activities-new',
      component: () => import('@/pages/activities/new.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/pages/activities/edit/:id',
      name: 'activities-edit',
      component: () => import('@/pages/activities/new.vue'),
      meta: { requiresAuth: true },
      props: true,
    },
    {
      path: '/pages/audit/pending',
      name: 'audit-pending',
      component: () => import('@/pages/audit/pending.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/pages/study-hours/index',
      name: 'study-hours',
      component: () => import('@/pages/study-hours/index.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/pages/stats/yearly',
      name: 'stats-yearly',
      component: () => import('@/pages/stats/yearly.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/pages/admin/dicts',
      name: 'admin-dicts',
      component: () => import('@/pages/admin/dicts.vue'),
      // admin 全权；street_lead 可进（但不能编辑街道/字典）
      meta: { requiresAuth: true, requiresOrgAdmin: true },
    },
    {
      // 公开 H5 党员名片（扫码访问，不需登录）
      path: '/public/member/:id',
      name: 'public-member',
      component: () => import('@/pages/public/MemberCard.vue'),
      meta: { requiresAuth: false, publicPage: true },
    },
    {
      // 党员 "我的" 页面（个人中心）
      path: '/pages/me/index',
      name: 'me',
      component: () => import('@/pages/me/index.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

// 全局守卫：未登录跳登录；权限不足 → 跳首页
router.beforeEach((to, _from, next) => {
  // 公开页面（党员名片扫码）直接放行
  if (to.meta.publicPage) return next()
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.token) {
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else if (to.name === 'login' && auth.token) {
    next({ name: 'home' })
  } else if (to.meta.requiresOrgAdmin) {
    if (!['system_admin', 'street_lead'].includes(auth.user?.role || '')) {
      next({ name: 'home' })
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
