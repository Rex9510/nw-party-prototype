<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Layout from '@/components/Layout.vue'

const auth = useAuthStore()
const route = useRoute()

// login 路由不走主布局（自己就是全屏）
const useLayout = computed(() => {
  // 公开 H5 页面（党员名片）不走 Layout，全屏显示
  if (route.name === 'public-member') return false
  if (!auth.token) return false
  return route.name !== 'login'
})

onMounted(async () => {
  console.log('党员学时统计系统 启动')
  if (auth.token && !auth.user) {
    try {
      await auth.fetchMe()
    } catch (e) {
      console.warn('fetchMe failed', e)
    }
  }
})
</script>

<template>
  <Layout v-if="useLayout">
    <!-- :key 强制路由变化时重新挂载，避免 router-view 在 slot 里不更新 -->
    <router-view :key="route.fullPath" />
  </Layout>
  <router-view v-else :key="route.fullPath" />
</template>

<style>
:root {
  --primary: #B22222;
  --primary-dark: #8B0000;
  --primary-light: #FFF0F0;
  --bg: #F7F8FA;
  --surface: #fff;
  --border: #f0f0f0;
  --text-primary: #222;
  --text-secondary: #666;
  --text-muted: #999;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --shadow-sm: 0 1px 4px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.06);
}
html, body, #app { height: 100%; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: var(--bg);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
}
* { box-sizing: border-box; }
button { font-family: inherit; }

/* ============== 全局响应式 ============== */
/* 在 PC 端，让被 Layout 包住的页面不再使用 min-height: 100vh（那是为了独立页面准备的，
   在 Layout 里会导致内容区空一大块），并让页面在容器中可滚动 */
@media (min-width: 768px) {
  /* 覆盖 scoped 样式里的 min-height: 100vh */
  .app-shell.pc .content > .page,
  .app-shell.pc .content > .dashboard,
  .app-shell.pc .content > * {
    min-height: 0 !important;
    background: transparent;
  }
}
</style>
