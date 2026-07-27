<!--
  统一布局：
  - PC（>=768px）：左侧固定侧栏（240px）+ 右侧主区（max-width 1200px，居中）
  - H5（<768px）：顶部条 + 内容区 + 底部 Tab Bar

  使用：
    <Layout>
      <router-view />
    </Layout>
-->
<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showConfirmDialog, showToast, showSuccessToast } from 'vant'
import { useAuthStore } from '@/stores/auth'
import { ROLES, type Role } from '@/utils/roles'
import { api } from '@/utils/request'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

// 用 matchMedia 更优雅；用 resize 也可以，这里用 resize
const isPC = ref(false)
function checkSize() {
  isPC.value = window.innerWidth >= 768
}
onMounted(() => {
  checkSize()
  window.addEventListener('resize', checkSize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', checkSize)
})

const role = computed<Role>(() => (auth.user?.role as Role) || 'member')
const roleConfig = computed(() => ROLES[role.value])
const menuItems = computed(() => roleConfig.value?.cards || [])

// 移动端 tab 只显示前 4 个 + 首页
const tabItems = computed(() => {
  const home = {
    key: 'home',
    icon: '🏠',
    label: '首页',
    path: '/pages/index/index',
    desc: '',
    enabled: true,
  }
  return [home, ...menuItems.value.slice(0, 4)]
})

function isActive(path: string) {
  return route.path === path
}

async function onLogout() {
  try {
    await showConfirmDialog({
      title: '提示',
      message: '确定退出登录？',
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      confirmButtonColor: '#B22222',
    })
    // 用户点了「退出」
    auth.logout()
    // 清掉页面上残留的 toast（如之前 401 弹的 "Not authenticated"），避免跳到登录页后还显示
    try {
      const { closeToast } = await import('vant')
      closeToast()
    } catch {
      // ignore
    }
    // 跳到登录页
    await router.replace('/pages/login/index')
  } catch {
    // 用户点了「取消」，啥也不做
  }
}

// ===== 修改密码 =====
const showPwdDialog = ref(false)
const pwdForm = ref({ old: '', neu: '', confirm: '' })
const pwdSubmitting = ref(false)
const pwdError = ref('')
const pwdVisible = ref({ old: false, neu: false, confirm: false })

const pwdStrength = computed(() => {
  const p = pwdForm.value.neu
  if (!p) return 0
  let s = 0
  if (p.length >= 6) s++
  if (/[A-Z]/.test(p)) s++
  if (/[a-z]/.test(p)) s++
  if (/\d/.test(p)) s++
  if (/[^A-Za-z0-9]/.test(p)) s++
  return Math.min(s, 4) // 0-4
})
const pwdStrengthLabel = computed(() => ['', '弱', '一般', '良好', '强'][pwdStrength.value])
const pwdStrengthColor = computed(() =>
  ['', '#FF4D4F', '#FAAD14', '#52C41A', '#13C2C2'][pwdStrength.value],
)

function openPwdDialog() {
  pwdForm.value = { old: '', neu: '', confirm: '' }
  pwdError.value = ''
  pwdVisible.value = { old: false, neu: false, confirm: false }
  showPwdDialog.value = true
}

async function onSubmitPwd() {
  pwdError.value = ''
  if (pwdForm.value.old.length < 6) {
    pwdError.value = '请输入原密码'
    return
  }
  if (pwdForm.value.neu.length < 6) {
    pwdError.value = '新密码至少 6 位'
    return
  }
  if (pwdForm.value.neu !== pwdForm.value.confirm) {
    pwdError.value = '两次输入的新密码不一致'
    return
  }
  if (pwdForm.value.old === pwdForm.value.neu) {
    pwdError.value = '新密码不能与原密码相同'
    return
  }
  pwdSubmitting.value = true
  try {
    await api.post('/auth/change-password', {
      old_password: pwdForm.value.old,
      new_password: pwdForm.value.neu,
      confirm_password: pwdForm.value.confirm,
    })
    showSuccessToast({ message: '密码修改成功' })
    showPwdDialog.value = false
  } catch (e: any) {
    pwdError.value = e?.message || '修改失败'
    showToast({ message: pwdError.value, type: 'fail' })
  } finally {
    pwdSubmitting.value = false
  }
}

// 是否在首页（在首页时按钮置灰）
const isOnHome = computed(() => route.path === '/pages/index/index')
function goHome() {
  if (isOnHome.value) return
  router.push('/pages/index/index')
}
</script>

<template>
  <div class="app-shell" :class="{ pc: isPC, mobile: !isPC }">
    <!-- PC 顶部条（只在 PC 显示，只放品牌和用户信息） -->
    <header v-if="isPC" class="pc-topbar">
      <div class="brand-area">
        <button class="home-btn" :class="{ active: isOnHome }" @click="goHome" title="返回首页">
          🏠 首页
        </button>
        <div class="brand">
          <img src="/logo.jpg" class="brand-logo" alt="logo" />
          <span>党员学时统计系统</span>
        </div>
      </div>
      <div class="user-area">
        <span class="user-name">{{ auth.user?.name || '加载中…' }}</span>
        <span class="user-role" :style="{ color: roleConfig?.color }">
          {{ roleConfig?.label }} · {{ roleConfig?.scope }}
        </span>
        <button class="pwd-btn" @click="openPwdDialog" title="修改密码">
          🔒 修改密码
        </button>
        <button class="logout-btn" @click="onLogout">退出</button>
      </div>
    </header>

    <div class="body">
      <!-- PC 左侧栏 -->
      <aside v-if="isPC" class="pc-sidebar">
        <div class="sidebar-title">功能菜单</div>
        <nav class="menu">
          <router-link
            v-for="item in menuItems"
            :key="item.key"
            :to="item.path"
            class="menu-item"
            :class="{ active: isActive(item.path), disabled: !item.enabled }"
            @click="(e: Event) => { if (!item.enabled) { e.preventDefault(); window.uni.showToast({ title: '该功能后续开发', icon: 'none' }) } }"
          >
            <span class="menu-icon">{{ item.icon }}</span>
            <span class="menu-label">{{ item.label }}</span>
            <span class="menu-desc">{{ item.desc }}</span>
          </router-link>
        </nav>
        <div class="sidebar-foot">
          <div class="foot-line">集中学习培训管理</div>
        </div>
      </aside>

      <!-- 主内容区 -->
      <main class="content">
        <slot />
      </main>
    </div>

    <!-- H5 顶栏 -->
    <header v-if="!isPC" class="mobile-topbar">
      <div class="brand" @click="goHome">
        <img src="/logo.jpg" class="brand-logo" alt="logo" />
        <span>党员学时统计系统</span>
      </div>
      <div class="right">
        <button class="home-btn-mini" :class="{ active: isOnHome }" @click="goHome" title="返回首页">
          🏠
        </button>
        <span class="user-name">{{ auth.user?.name }}</span>
        <button class="pwd-btn-mini" @click="openPwdDialog" title="修改密码">🔒</button>
        <button class="logout-btn" @click="onLogout">退出</button>
      </div>
    </header>

    <!-- H5 底部 Tab -->
    <nav v-if="!isPC" class="tab-bar">
      <router-link
        v-for="item in tabItems"
        :key="item.key"
        :to="item.path"
        class="tab-item"
        :class="{ active: isActive(item.path) }"
      >
        <span class="tab-icon">{{ item.icon }}</span>
        <span class="tab-label">{{ item.label }}</span>
      </router-link>
    </nav>

    <!-- 修改密码弹窗 -->
    <van-dialog
      v-model:show="showPwdDialog"
      title="修改密码"
      show-cancel-button
      :before-close="(action) => { if (action === 'confirm') { onSubmitPwd() } else { showPwdDialog = false } }"
      close-on-click-overlay
    >
      <div class="pwd-dialog">
        <div class="pwd-field">
          <span class="pwd-label">原密码</span>
          <input
            v-model="pwdForm.old"
            :type="pwdVisible.old ? 'text' : 'password'"
            class="pwd-input"
            placeholder="请输入原密码"
            maxlength="64"
            autocomplete="current-password"
          />
          <button class="eye-btn" type="button" @click="pwdVisible.old = !pwdVisible.old">
            {{ pwdVisible.old ? '🙈' : '👁' }}
          </button>
        </div>

        <div class="pwd-field">
          <span class="pwd-label">新密码</span>
          <input
            v-model="pwdForm.neu"
            :type="pwdVisible.neu ? 'text' : 'password'"
            class="pwd-input"
            placeholder="6位以上，可含字母/数字/符号"
            maxlength="64"
            autocomplete="new-password"
          />
          <button class="eye-btn" type="button" @click="pwdVisible.neu = !pwdVisible.neu">
            {{ pwdVisible.neu ? '🙈' : '👁' }}
          </button>
        </div>

        <!-- 强度条 -->
        <div v-if="pwdForm.neu" class="strength-bar">
          <div class="strength-track">
            <div
              class="strength-fill"
              :style="{ width: (pwdStrength * 25) + '%', background: pwdStrengthColor }"
            />
          </div>
          <span class="strength-label" :style="{ color: pwdStrengthColor }">
            {{ pwdStrengthLabel }}
          </span>
        </div>

        <div class="pwd-field">
          <span class="pwd-label">确认新密码</span>
          <input
            v-model="pwdForm.confirm"
            :type="pwdVisible.confirm ? 'text' : 'password'"
            class="pwd-input"
            placeholder="再输入一次新密码"
            maxlength="64"
            autocomplete="new-password"
          />
          <button class="eye-btn" type="button" @click="pwdVisible.confirm = !pwdVisible.confirm">
            {{ pwdVisible.confirm ? '🙈' : '👁' }}
          </button>
        </div>

        <div v-if="pwdError" class="pwd-error">{{ pwdError }}</div>

        <div class="pwd-hint">
          密码至少 6 位，建议使用字母+数字+符号组合
        </div>
      </div>
    </van-dialog>
  </div>
</template>

<style scoped>
/* ================== 通用 ================== */
.app-shell {
  min-height: 100vh;
  background: #F7F8FA;
  color: #222;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ================== PC 布局 ================== */
.app-shell.pc {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.pc-topbar {
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.pc-topbar .brand-area {
  display: flex;
  align-items: center;
  gap: 16px;
}
.pc-topbar .home-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 32px;
  padding: 0 12px;
  background: #FFF0F0;
  color: #B22222;
  border: 1px solid #FFC8C8;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s;
}
.pc-topbar .home-btn:hover { background: #FFD9D9; }
.pc-topbar .home-btn.active {
  background: #B22222;
  color: #fff;
  border-color: #B22222;
  cursor: default;
  opacity: 0.85;
}
.pc-topbar .pwd-btn {
  height: 32px;
  padding: 0 12px;
  background: #fff;
  color: #666;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all .15s;
}
.pc-topbar .pwd-btn:hover {
  color: #B22222;
  border-color: #B22222;
  background: #FFF0F0;
}
.pc-topbar .brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
  color: #B22222;
  letter-spacing: 1px;
}
.brand-logo {
  height: 32px;
  width: 32px;
  object-fit: contain;
  border-radius: 4px;
}
.mobile-topbar .brand-logo {
  height: 26px;
  width: 26px;
}
.pc-topbar .user-area {
  display: flex;
  align-items: center;
  gap: 12px;
}
.pc-topbar .user-name {
  font-size: 14px;
  color: #333;
  font-weight: 600;
}
.pc-topbar .user-role {
  font-size: 12px;
  padding: 2px 8px;
  background: #f5f5f5;
  border-radius: 4px;
}
.pc-topbar .logout-btn {
  font-size: 13px;
  padding: 4px 12px;
  background: #fff;
  color: #B22222;
  border: 1px solid #B22222;
  border-radius: 4px;
  cursor: pointer;
}
.pc-topbar .logout-btn:hover {
  background: #FFF0F0;
}

.app-shell.pc .body {
  display: flex;
  flex: 1;
  min-height: 0;
}

.pc-sidebar {
  width: 240px;
  background: #fff;
  border-right: 1px solid #f0f0f0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
  position: sticky;
  top: 56px;
}
.sidebar-title {
  padding: 16px 20px 8px;
  font-size: 12px;
  color: #999;
  letter-spacing: 1px;
  font-weight: 600;
}
.menu {
  display: flex;
  flex-direction: column;
  padding: 4px 8px;
  gap: 2px;
  flex: 1;
  overflow-y: auto;
}
.menu-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  color: #333;
  text-decoration: none;
  transition: background .15s;
  gap: 10px;
}
.menu-item:hover {
  background: #f5f5f5;
}
.menu-item.active {
  background: #FFF0F0;
  color: #B22222;
  font-weight: 600;
}
.menu-item.disabled {
  opacity: 0.5;
}
.menu-icon {
  font-size: 18px;
  width: 24px;
  text-align: center;
}
.menu-label {
  font-size: 14px;
  flex-shrink: 0;
}
.menu-desc {
  font-size: 11px;
  color: #999;
  margin-left: auto;
}
.menu-item.active .menu-desc { color: #B22222; opacity: 0.7; }

.sidebar-foot {
  padding: 16px 20px;
  border-top: 1px solid #f0f0f0;
  font-size: 11px;
  color: #999;
}
.foot-line.muted { color: #ccc; margin-top: 2px; }

.app-shell.pc .content {
  flex: 1;
  min-width: 0;
  padding: 24px 0 48px;
  overflow-y: auto;
  /* 居中容器：所有页面在 PC 端最大宽度 1000px */
  display: flex;
  flex-direction: column;
  align-items: stretch;
}
.app-shell.pc .content > * {
  max-width: 1000px;
  width: 100%;
  margin: 0 auto;
  /* 让页面填充整个内容区高度 */
  flex: 1 0 auto;
}

/* ================== H5 布局 ================== */
.app-shell.mobile {
  display: flex;
  flex-direction: column;
  padding-top: 44px; /* 留出顶部 mobile-topbar 高度 */
  padding-bottom: 56px; /* 留出底部 tab 高度 */
  min-height: 100vh;
}

.mobile-topbar {
  height: 44px;
  background: linear-gradient(135deg, #B22222, #8B0000);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  flex-shrink: 0;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}
.mobile-topbar .brand {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 1px;
  cursor: pointer;
  user-select: none;
}
.mobile-topbar .right {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.mobile-topbar .home-btn-mini {
  font-size: 16px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}
.mobile-topbar .home-btn-mini:hover { background: rgba(255, 255, 255, 0.3); }
.mobile-topbar .home-btn-mini.active { opacity: 0.5; cursor: default; }
.mobile-topbar .pwd-btn-mini {
  font-size: 16px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}
.mobile-topbar .pwd-btn-mini:hover { background: rgba(255, 255, 255, 0.3); }
.mobile-topbar .user-name { opacity: 0.9; }
.mobile-topbar .logout-btn {
  font-size: 12px;
  padding: 3px 8px;
  background: rgba(255,255,255,0.2);
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.app-shell.mobile .content {
  flex: 1;
  min-height: 0;
  padding: 8px 8px 16px;
}

.tab-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  height: 56px;
  background: #fff;
  border-top: 1px solid #f0f0f0;
  display: flex;
  align-items: stretch;
  z-index: 20;
  box-shadow: 0 -2px 6px rgba(0,0,0,0.04);
}
.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  color: #999;
  font-size: 11px;
  gap: 2px;
}
.tab-item.active { color: #B22222; }
.tab-icon { font-size: 20px; line-height: 1; }
.tab-label { font-size: 11px; }

/* ===== 修改密码弹窗 ===== */
.pwd-dialog {
  padding: 16px 20px 20px;
}
.pwd-field {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  border-bottom: 1px solid #eee;
  padding: 4px 0;
}
.pwd-label {
  font-size: 14px;
  color: #666;
  min-width: 5.5em;
  flex-shrink: 0;
}
.pwd-input {
  flex: 1;
  height: 40px;
  border: none;
  outline: none;
  font-size: 15px;
  color: #222;
  background: transparent;
  font-family: inherit;
}
.pwd-input::placeholder { color: #bbb; }
.eye-btn {
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 18px;
  padding: 0;
  flex-shrink: 0;
}
.eye-btn:hover { opacity: 0.7; }

.strength-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: -4px 0 12px 5.5em;
}
.strength-track {
  flex: 1;
  height: 4px;
  background: #f0f0f0;
  border-radius: 2px;
  overflow: hidden;
}
.strength-fill {
  height: 100%;
  transition: width .25s, background .25s;
}
.strength-label {
  font-size: 12px;
  min-width: 32px;
  text-align: right;
}

.pwd-error {
  background: #FFF0F0;
  color: #B22222;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 13px;
  margin: 8px 0;
}

.pwd-hint {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
  text-align: center;
}
</style>
