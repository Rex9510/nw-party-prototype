<script setup lang="ts">
/**
 * "我的" 页面（党员个人中心）
 *
 * 整合：个人信息 / 我的二维码 / 我的学时 / 修改密码
 *
 * 数据流：
 *  1. 顶部信息：从 /auth/me 拿 user（auth store 已有），从 /members/by-phone/{phone} 拿完整 member 档案
 *  2. 我的二维码：基于 member.id 生成 /public/member/{id} 的链接 + QR
 *  3. 我的学时：复用 studyApi.me()（已有逻辑，弹窗同 study-hours 页）
 */
import { ref, computed, onMounted } from 'vue'
import { showToast, showSuccessToast, showConfirmDialog } from 'vant'
import { membersApi, type MemberItem } from '@/api/members'
import { studyApi, type StudyDetailItem } from '@/api/study'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const member = ref<MemberItem | null>(null)
const loading = ref(true)
const errorMsg = ref('')

const meStats = ref({ total_hours: 0, activity_count: 0, year: new Date().getFullYear() })
const detailItems = ref<StudyDetailItem[]>([])
const showDetail = ref(false)

// ===== 加载我的档案 =====
async function loadMe() {
  loading.value = true
  errorMsg.value = ''
  try {
    if (!auth.user?.phone) {
      throw new Error('未登录或缺少手机号')
    }
    member.value = await membersApi.getByPhone(auth.user.phone)
  } catch (e: any) {
    errorMsg.value = e?.message || '加载个人信息失败'
  } finally {
    loading.value = false
  }
}

// ===== 加载我的学时 =====
async function loadMyHours() {
  try {
    const d = await studyApi.me(meStats.value.year)
    meStats.value.total_hours = d.total_hours
    meStats.value.activity_count = d.activity_count
    meStats.value.year = d.year
  } catch (e) {
    // 静默：顶部学时区不强制要求
    console.warn('loadMyHours failed', e)
  }
}

async function onOpenMyHours() {
  try {
    const d = await studyApi.me(meStats.value.year)
    detailItems.value = d.items
    meStats.value.total_hours = d.total_hours
    meStats.value.activity_count = d.activity_count
    showDetail.value = true
  } catch (e: any) {
    showToast({ message: e?.message || '加载失败', type: 'fail' })
  }
}

// ===== 我的二维码 =====
const showQRDialog = ref(false)
const qrUrl = computed(() => {
  if (!member.value) return ''
  return `${window.location.origin}/public/member/${member.value.id}`
})
const qrImgUrl = computed(() =>
  `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(qrUrl.value)}`,
)

async function onCopyUrl() {
  if (!qrUrl.value) return
  try {
    await navigator.clipboard.writeText(qrUrl.value)
    showSuccessToast({ message: '链接已复制' })
  } catch {
    showToast('复制失败，请手动选择')
  }
}
function onOpenQR() {
  if (qrUrl.value) window.open(qrUrl.value, '_blank')
}

// ===== 工具 =====
const genderLabel = (g: string | null | undefined) => {
  if (g === 'male') return '男'
  if (g === 'female') return '女'
  return g || '-'
}
const statusLabel = (s: string) => {
  if (s === 'active') return '正常'
  if (s === 'transferred') return '已转出'
  if (s === 'dimission') return '已离职'
  return s
}
const formatDate = (iso: string | null | undefined) => iso ? iso.slice(0, 10) : '-'
const roleLabel = (r: string) => ({
  system_admin: '系统管理员',
  street_lead: '街道负责人',
  community_organizer: '社区组织委员',
  branch_secretary: '支部书记',
  party_member: '党员',
  member: '党员',
  admin: '管理员',
}[r] || r)

onMounted(async () => {
  await loadMe()
  await loadMyHours()
})

// 改密码：复用 Layout 顶栏的弹窗，弹个提示告诉用户去哪
function onChangePwd() {
  showConfirmDialog({
    title: '修改密码',
    message: '请点击页面顶部的「🔒 修改密码」按钮。',
    confirmButtonText: '我知道了',
  }).catch(() => {})
}
</script>

<template>
  <div class="me-page">
    <!-- 顶部红色 banner -->
    <div class="me-banner">
      <div class="banner-inner">
        <div class="me-avatar">
          <img
            v-if="member?.photo_urls && member.photo_urls.length"
            :src="member.photo_urls[0]"
            class="avatar-img"
            alt="头像"
          />
          <span v-else>{{ member?.name?.slice(0, 1) || auth.user?.name?.slice(0, 1) || '?' }}</span>
        </div>
        <div class="me-info">
          <div class="me-name">
            {{ member?.name || auth.user?.name || '加载中…' }}
          </div>
          <div class="me-meta">
            <span>{{ genderLabel(member?.gender) }}</span>
            <span v-if="member?.join_date" class="dot">·</span>
            <span v-if="member?.join_date">入党时间：{{ formatDate(member.join_date) }}</span>
            <span v-if="member?.status" class="status-tag" :class="member.status">
              {{ statusLabel(member.status) }}
            </span>
          </div>
          <div class="me-org" v-if="member">
            <span v-if="member.branch_name">📍 {{ member.branch_name }}</span>
          </div>
        </div>
        <button class="qr-btn" @click="showQRDialog = true" title="我的二维码">
          <span class="qr-icon">📱</span>
          <span class="qr-text">我的<br/>二维码</span>
        </button>
      </div>
    </div>

    <!-- 加载/错误 -->
    <div v-if="loading" class="status">加载中…</div>
    <div v-else-if="errorMsg" class="status error">{{ errorMsg }}</div>

    <template v-else>
      <!-- 学时统计 -->
      <div class="stats-card">
        <div class="stats-row">
          <div class="stat-cell">
            <div class="num">{{ meStats.activity_count }}</div>
            <div class="lbl">活动数</div>
          </div>
          <div class="stat-cell">
            <div class="num">{{ meStats.total_hours }}</div>
            <div class="lbl">总学时</div>
          </div>
          <div class="stat-cell highlight">
            <div class="num">{{ meStats.year }}</div>
            <div class="lbl">本年</div>
          </div>
        </div>
        <button class="view-detail" @click="onOpenMyHours">查看学时明细 ›</button>
      </div>

      <!-- 信息区 -->
      <div class="card">
        <div class="card-title">基本信息</div>
        <div class="kv">
          <span class="k">手机号</span>
          <span class="v">{{ member?.phone || '-' }}</span>
        </div>
        <div class="kv" v-if="member?.id_card_no">
          <span class="k">身份证号</span>
          <span class="v">{{ member.id_card_no }}</span>
        </div>
        <div class="kv" v-if="member?.identities && member.identities.length">
          <span class="k">身份</span>
          <span class="v tags">
            <span v-for="i in member.identities" :key="i" class="tag">{{ i }}</span>
          </span>
        </div>
        <div class="kv" v-if="member?.roles && member.roles.length">
          <span class="k">系统角色</span>
          <span class="v tags">
            <span v-for="r in member.roles" :key="r" class="tag tag-role">{{ roleLabel(r) }}</span>
          </span>
        </div>
      </div>

      <!-- 快捷入口 -->
      <div class="card">
        <div class="card-title">快捷入口</div>
        <div class="quick-list">
          <button class="quick-item" @click="onOpenMyHours">
            <span class="qi-icon">🎓</span>
            <span class="qi-label">我的学时</span>
            <span class="qi-arrow">›</span>
          </button>
          <button class="quick-item" @click="showQRDialog = true">
            <span class="qi-icon">📱</span>
            <span class="qi-label">我的二维码</span>
            <span class="qi-arrow">›</span>
          </button>
          <button class="quick-item" @click="onChangePwd">
            <span class="qi-icon">🔒</span>
            <span class="qi-label">修改密码</span>
            <span class="qi-arrow">›</span>
          </button>
        </div>
      </div>

      <div class="footer">本页数据由系统自动汇总 · 党员学时统计系统</div>
    </template>

    <!-- 我的二维码弹窗 -->
    <van-dialog
      v-model:show="showQRDialog"
      title="我的二维码"
      :width="340"
      close-on-click-overlay
    >
      <div class="qr-box">
        <div class="qr-member-name">{{ member?.name }}</div>
        <div class="qr-canvas">
          <img v-if="qrUrl" :src="qrImgUrl" alt="二维码" />
        </div>
        <div class="qr-tip">扫码查看个人信息和培训记录</div>
        <div class="qr-url">{{ qrUrl }}</div>
        <div class="qr-actions">
          <van-button size="small" type="primary" @click="onCopyUrl">复制链接</van-button>
          <van-button size="small" plain hairline @click="onOpenQR">打开</van-button>
        </div>
      </div>
    </van-dialog>

    <!-- 学时详情弹窗 -->
    <van-dialog
      v-model:show="showDetail"
      :title="`我的学时 · ${meStats.year}`"
      show-cancel-button
      :before-close="(action) => { showDetail = false; return false }"
    >
      <div class="dialog-body">
        <div class="modal-stats">
          <div class="m-stat">
            <div class="m-stat-num">{{ meStats.activity_count }}</div>
            <div class="m-stat-label">活动数</div>
          </div>
          <div class="m-stat">
            <div class="m-stat-num primary">{{ meStats.total_hours }}</div>
            <div class="m-stat-label">总学时</div>
          </div>
        </div>
        <div class="detail-list">
          <div v-if="!detailItems.length" class="empty-mini">本年暂无参与记录</div>
          <div v-for="i in detailItems" :key="i.activity_id" class="detail-item">
            <div class="detail-theme">{{ i.theme }}</div>
            <div class="detail-meta">
              <span>📅 {{ i.training_at }}</span>
              <span>📍 {{ i.location }}</span>
            </div>
            <div class="detail-hours">+{{ i.study_hours }} 学时</div>
          </div>
        </div>
      </div>
    </van-dialog>
  </div>
</template>

<script lang="ts">
// 单独写一个普通 script 块（setup 外）以避免 setup 中调用 confirm 的限制
import { showConfirmDialog as _showConfirmDialog } from 'vant'
export default {
  methods: {
    async onChangePwd() {
      // 跳到系统修改密码：复用 Layout 里已有的修改密码弹窗逻辑
      // 简单做法：直接打开浏览器原生 prompt（最稳）
      // 更优：在 Layout 已经做了修改密码弹窗；这里给个 toast 提示去顶栏
      _showConfirmDialog({
        title: '修改密码',
        message: '请点击页面顶部的「🔒 修改密码」按钮。',
        confirmButtonText: '我知道了',
      }).catch(() => {})
    },
  },
}
</script>

<style scoped>
.me-page {
  background: #F7F8FA;
  padding-bottom: 32px;
}

/* 顶部 banner */
.me-banner {
  background: linear-gradient(135deg, #B22222, #8B0000);
  color: #fff;
  padding: 24px 16px 32px;
  position: relative;
  margin: 0 0 0 0;
}
.banner-inner {
  display: flex;
  gap: 14px;
  align-items: center;
  max-width: 1000px;
  margin: 0 auto;
}
.me-avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: rgba(255,255,255,0.2);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 700;
  flex-shrink: 0;
  overflow: hidden;
  border: 2px solid rgba(255,255,255,0.3);
}
.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.me-info { flex: 1; min-width: 0; }
.me-name {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 4px;
  letter-spacing: 1px;
}
.me-meta {
  display: flex;
  gap: 6px;
  font-size: 13px;
  opacity: 0.9;
  flex-wrap: wrap;
  align-items: center;
}
.me-meta .dot { opacity: 0.5; }
.status-tag {
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 11px;
  background: rgba(255,255,255,0.25);
  margin-left: 4px;
}
.me-org {
  margin-top: 4px;
  font-size: 12px;
  opacity: 0.85;
}

.qr-btn {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  background: #fff;
  color: #B22222;
  border: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  transition: transform .15s;
}
.qr-btn:hover { transform: translateY(-2px); }
.qr-icon { font-size: 22px; line-height: 1; }
.qr-text {
  font-size: 10px;
  font-weight: 600;
  margin-top: 2px;
  line-height: 1.2;
  text-align: center;
}

/* 状态 */
.status {
  text-align: center;
  padding: 40px 16px;
  color: #999;
  font-size: 14px;
}
.status.error { color: #B22222; }

/* 统计 */
.stats-card {
  background: #fff;
  margin: -16px 16px 16px;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
  position: relative;
  z-index: 1;
}
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}
.stat-cell {
  text-align: center;
  padding: 8px;
  background: #FFF7F7;
  border-radius: 8px;
}
.stat-cell.highlight { background: linear-gradient(135deg, #B22222, #8B0000); color: #fff; }
.stat-cell .num { font-size: 22px; font-weight: 800; color: #B22222; line-height: 1.2; }
.stat-cell.highlight .num { color: #fff; }
.stat-cell .lbl { font-size: 12px; color: #888; margin-top: 2px; }
.stat-cell.highlight .lbl { color: rgba(255,255,255,0.85); }
.view-detail {
  width: 100%;
  height: 36px;
  border-radius: 6px;
  border: 1px solid #B22222;
  background: #fff;
  color: #B22222;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s;
}
.view-detail:hover { background: #FFF0F0; }

/* 卡片 */
.card {
  background: #fff;
  margin: 0 16px 16px;
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.card-title {
  font-size: 15px;
  font-weight: 700;
  color: #222;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}
.kv {
  display: flex;
  align-items: flex-start;
  font-size: 14px;
  padding: 6px 0;
  gap: 12px;
}
.kv .k {
  color: #888;
  min-width: 5.5em;
  flex-shrink: 0;
}
.kv .v {
  color: #222;
  flex: 1;
  word-break: break-all;
}
.tags { display: flex; flex-wrap: wrap; gap: 4px; }
.tag {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  background: #FFF0F0;
  color: #B22222;
  border-radius: 3px;
}
.tag-role { background: #F0F4FF; color: #1E40AF; }

/* 快捷入口 */
.quick-list {
  display: flex;
  flex-direction: column;
}
.quick-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  background: none;
  border: none;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  font: inherit;
  color: #333;
  text-align: left;
  transition: background .15s;
}
.quick-item:last-child { border-bottom: none; }
.quick-item:hover { background: #fafafa; }
.qi-icon { font-size: 18px; width: 24px; text-align: center; }
.qi-label { flex: 1; font-size: 14px; }
.qi-arrow { color: #ccc; font-size: 20px; line-height: 1; }

.footer {
  text-align: center;
  font-size: 11px;
  color: #aaa;
  margin-top: 24px;
  padding: 0 16px;
}

/* 二维码弹窗 */
.qr-box {
  padding: 16px 20px 20px;
  text-align: center;
}
.qr-member-name {
  font-size: 16px;
  font-weight: 600;
  color: #222;
  margin-bottom: 12px;
}
.qr-canvas {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 12px;
  display: inline-block;
}
.qr-canvas img {
  display: block;
  width: 240px;
  height: 240px;
}
.qr-tip { font-size: 12px; color: #888; margin-top: 8px; }
.qr-url {
  margin-top: 12px;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 4px;
  font-size: 11px;
  color: #666;
  word-break: break-all;
  font-family: monospace;
  text-align: left;
}
.qr-actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  justify-content: center;
}

/* 学时详情弹窗 */
.dialog-body { padding: 12px 16px; }
.modal-stats { display: flex; gap: 8px; margin-bottom: 12px; }
.m-stat {
  flex: 1;
  background: #FFF0F0;
  border-radius: 6px;
  padding: 10px;
  text-align: center;
}
.m-stat-num { font-size: 20px; font-weight: 700; color: #B22222; }
.m-stat-num.primary { color: #DC2626; }
.m-stat-label { font-size: 11px; color: #888; margin-top: 2px; }
.detail-list { max-height: 50vh; overflow-y: auto; }
.detail-item {
  background: #f5f5f5;
  border-radius: 4px;
  padding: 8px 10px;
  margin-bottom: 6px;
}
.detail-theme { font-size: 13px; font-weight: 600; color: #222; }
.detail-meta { display: flex; gap: 8px; font-size: 11px; color: #888; margin-top: 3px; }
.detail-hours {
  font-size: 12px;
  color: var(--primary, #B22222);
  font-weight: 600;
  margin-top: 3px;
}
.empty-mini { text-align: center; padding: 20px; color: #999; font-size: 13px; }
</style>
