<script setup lang="ts">
/**
 * 公开 H5 党员名片页
 * 路径：/public/member/:id
 * 无需登录。扫码即可查看党员基本信息和历史参加培训情况。
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { api } from '@/utils/request'

const route = useRoute()
const router = useRouter()
const memberId = Number(route.params.id)

// 返回/关闭按钮：H5/Pad 浏览器可 history.back()，否则跳到系统首页
function onBack() {
  // 优先 history.back()；如果 referrer 是当前站或同会话
  if (window.history.length > 1 && document.referrer && document.referrer !== window.location.href) {
    try {
      window.history.back()
      return
    } catch {
      // fallthrough
    }
  }
  // 退到系统登录页（公开页也允许无登录访问）
  router.push('/pages/login/index')
}

interface Training {
  activity_id: number
  theme: string
  training_at: string
  location: string
  lecturer_name: string | null
  lecturer_bio: string | null
  study_hours: number
  source_type: string
  attendance_status: string
  photos: string[]
  attachments: string[]
}

interface MemberInfo {
  id: number
  name: string
  phone: string | null
  id_card_no: string | null
  gender: string | null
  join_date: string | null
  status: string
  roles: string[]
  identities: string[]
  branch: { id: number; name: string } | null
  community: { id: number; name: string } | null
  street: { id: number; name: string } | null
}

const member = ref<MemberInfo | null>(null)
const trainings = ref<Training[]>([])
const stats = ref<{ total_sessions: number; total_hours: number; year_hours: number; year: number }>({
  total_sessions: 0, total_hours: 0, year_hours: 0, year: new Date().getFullYear(),
})
const loading = ref(true)
const errorMsg = ref('')
const previewImage = ref('')
const showPreview = ref(false)

const statusLabel = computed(() => {
  const s = member.value?.status
  if (s === 'active') return '正常'
  if (s === 'inactive') return '已转出'
  return s || ''
})

const sourceLabel = (s: string) => {
  return s === 'upper_send' ? '上级送课' : s === 'self_organize' ? '自行组织' : s
}

const genderLabel = (g: string | null | undefined) => {
  if (g === 'male') return '男'
  if (g === 'female') return '女'
  return g || '-'
}

const formatDate = (iso: string | null | undefined) => {
  if (!iso) return '-'
  return iso.slice(0, 10)
}

const formatDateTime = (iso: string | null | undefined) => {
  if (!iso) return ''
  return iso.replace('T', ' ').slice(0, 16)
}

// 党龄（入党至今多少年）
const partyAgeText = computed(() => {
  const jd = member.value?.join_date
  if (!jd) return ''
  const join = new Date(jd)
  if (isNaN(join.getTime())) return ''
  const now = new Date()
  let years = now.getFullYear() - join.getFullYear()
  // 没过今年生日的减 1
  if (
    now.getMonth() < join.getMonth() ||
    (now.getMonth() === join.getMonth() && now.getDate() < join.getDate())
  ) {
    years--
  }
  if (years < 0) years = 0
  return `${years} 年`
})

const isImage = (url: string) =>
  url.startsWith('data:image') || /\.(png|jpg|jpeg|gif|webp|bmp)$/i.test(url)

const fileTypeIcon = (url: string) => {
  if (url.startsWith('data:application/pdf')) return '📄'
  if (url.includes('spreadsheet') || url.includes('ms-excel')) return '📊'
  if (url.includes('wordprocessingml') || url.includes('msword')) return '📝'
  if (url.startsWith('data:text/plain')) return '📃'
  return '📎'
}

const MIME_EXT: Record<string, string> = {
  'application/pdf': 'pdf',
  'application/msword': 'doc',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
  'application/vnd.ms-excel': 'xls',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
  'text/plain': 'txt',
}

const downloadAttachment = (url: string) => {
  try {
    if (!url.startsWith('data:')) {
      window.open(url, '_blank')
      return
    }
    const [meta, b64] = url.split(',')
    const mime = meta.match(/data:([^;]+)/)?.[1] || 'application/octet-stream'
    const ext = MIME_EXT[mime] || mime.split('/')[1]?.split('+').pop()?.split('.').pop() || 'bin'
    const bin = atob(b64)
    const bytes = new Uint8Array(bin.length)
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
    const blob = new Blob([bytes], { type: mime })
    const objUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = objUrl
    a.download = `附件.${ext}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(objUrl)
  } catch (e) {
    showToast('下载失败')
  }
}

const onPhotoClick = (url: string) => {
  previewImage.value = url
  showPreview.value = true
}

async function load() {
  loading.value = true
  try {
    const data: any = await api.get<any>(`/public/members/${memberId}`)
    member.value = data.member
    trainings.value = data.trainings
    stats.value = data.stats
  } catch (e: any) {
    errorMsg.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
})
</script>

<template>
  <div class="public-page">
    <!-- 顶部红色 banner -->
    <div class="top-banner">
      <button class="back-btn" @click="onBack" title="返回">
        <span class="back-icon">‹</span>
        <span class="back-text">返回</span>
      </button>
      <div class="banner-sub">党员学时统计系统</div>
      <div class="banner-title">党员一人一码</div>
    </div>

    <!-- 加载 / 错误 -->
    <div v-if="loading" class="status">加载中…</div>
    <div v-else-if="errorMsg" class="status error">{{ errorMsg }}</div>

    <!-- 名片 -->
    <template v-else-if="member">
      <div class="card profile-card">
        <div class="profile-header">
          <div class="avatar">
            <img
              v-if="member.photo_urls && member.photo_urls.length"
              :src="member.photo_urls[0]"
              class="avatar-img"
              alt="头像"
            />
            <span v-else>{{ member.name?.slice(0, 1) || '?' }}</span>
          </div>
          <div class="info">
            <div class="name">{{ member.name }}</div>
            <div class="meta">
              <span class="gender">{{ genderLabel(member.gender) }}</span>
              <span class="status-tag" :class="member.status">{{ statusLabel }}</span>
            </div>
            <div class="org">
              <span v-if="member.street">📍 {{ member.street.name }}</span>
              <span v-if="member.community">/ {{ member.community.name }}</span>
              <span v-if="member.branch">/ {{ member.branch.name }}</span>
            </div>
          </div>
        </div>

        <!-- 入党时间 / 流入时间（独立醒目行） -->
        <div v-if="member.join_date" class="join-time">
          <span class="join-time-icon">🎉</span>
          <span class="join-time-label">入党时间</span>
          <span class="join-time-value">{{ formatDate(member.join_date) }}</span>
          <span class="join-time-dur">（党龄 {{ partyAgeText }}）</span>
        </div>
        <div v-if="member.roles && member.roles.length" class="tag-row">
          <span v-for="r in member.roles" :key="r" class="tag">{{ r }}</span>
        </div>
        <div v-if="member.phone" class="contact">
          <span class="contact-label">📞 电话：</span>
          <span>{{ member.phone }}</span>
        </div>
      </div>

      <!-- 统计 -->
      <div class="stats-row">
        <div class="stat-cell">
          <div class="num">{{ stats.total_sessions }}</div>
          <div class="lbl">累计培训</div>
        </div>
        <div class="stat-cell">
          <div class="num">{{ stats.total_hours }}</div>
          <div class="lbl">累计学时</div>
        </div>
        <div class="stat-cell highlight">
          <div class="num">{{ stats.year_hours }}</div>
          <div class="lbl">{{ stats.year }} 年学时</div>
        </div>
      </div>

      <!-- 培训记录 -->
      <div class="section-title">
        <span class="bar"></span>
        培训记录（{{ trainings.length }}）
      </div>

      <div v-if="!trainings.length" class="empty">
        <div class="empty-icon">📚</div>
        <div>暂无培训记录</div>
      </div>

      <div v-else class="training-list">
        <div v-for="t in trainings" :key="t.activity_id" class="training-item">
          <div class="t-header">
            <div class="t-theme">{{ t.theme }}</div>
            <div class="t-hours">+{{ t.study_hours }} 学时</div>
          </div>
          <div class="t-meta">
            <span>📅 {{ formatDateTime(t.training_at) }}</span>
            <span>📍 {{ t.location }}</span>
          </div>
          <div v-if="t.lecturer_name" class="t-meta">
            <span>🎤 讲师：{{ t.lecturer_name }}</span>
            <span class="t-source">来源：{{ sourceLabel(t.source_type) }}</span>
          </div>
          <div v-if="t.lecturer_bio" class="t-bio">
            {{ t.lecturer_bio }}
          </div>
          <div v-if="t.photos && t.photos.length" class="t-photos">
            <div
              v-for="(p, i) in t.photos"
              :key="i"
              class="t-photo"
              @click="onPhotoClick(p)"
            >
              <img v-if="isImage(p)" :src="p" />
            </div>
          </div>
          <div v-if="t.attachments && t.attachments.length" class="t-attachments">
            <div
              v-for="(a, i) in t.attachments"
              :key="i"
              class="t-attach"
              @click="downloadAttachment(a)"
            >
              <span class="t-attach-icon">{{ fileTypeIcon(a) }}</span>
              <span>附件 {{ i + 1 }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="footer">
        本页由系统自动生成 · 数据来源于党员学时统计系统
      </div>
    </template>

    <!-- 图片预览 -->
    <div v-if="showPreview" class="img-mask" @click.self="showPreview = false">
      <div class="img-toolbar">
        <span class="img-close" @click="showPreview = false">✕ 关闭</span>
      </div>
      <div class="img-content">
        <img :src="previewImage" class="preview-img" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.public-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #B22222 0%, #B22222 160px, #F7F8FA 160px, #F7F8FA 100%);
  padding-bottom: 40px;
}

.top-banner {
  padding: 20px 16px 30px;
  color: #fff;
  text-align: center;
  position: relative;
}
.back-btn {
  position: absolute;
  top: 16px;
  left: 12px;
  display: flex;
  align-items: center;
  gap: 2px;
  height: 32px;
  padding: 0 10px;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 16px;
  font-size: 13px;
  cursor: pointer;
  font-family: inherit;
  transition: background .15s;
}
.back-btn:hover { background: rgba(255, 255, 255, 0.3); }
.back-btn:active { background: rgba(255, 255, 255, 0.4); }
.back-icon {
  font-size: 18px;
  font-weight: 700;
  line-height: 1;
}
.banner-sub {
  font-size: 13px;
  opacity: 0.85;
  margin-bottom: 4px;
}
.banner-title {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 2px;
}

.status {
  text-align: center;
  padding: 60px 16px;
  color: #999;
  font-size: 14px;
}
.status.error { color: #B22222; }

/* 名片 */
.card {
  background: #fff;
  border-radius: 12px;
  margin: 0 16px 16px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
  padding: 16px;
}
.profile-card {
  margin-top: -10px;
}
.profile-header {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #B22222, #8B0000);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  flex-shrink: 0;
  overflow: hidden;
}
.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.info { flex: 1; min-width: 0; }
.name {
  font-size: 20px;
  font-weight: 700;
  color: #222;
  margin-bottom: 6px;
}
.meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #888;
  flex-wrap: wrap;
  align-items: center;
}
.gender { color: #555; }
.join { color: #666; }
.status-tag {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  background: #E6F7EC;
  color: #059669;
}
.status-tag.inactive { background: #FFE7E7; color: #B22222; }
.org {
  margin-top: 8px;
  font-size: 13px;
  color: #444;
}

/* 入党时间独立行（醒目） */
.join-time {
  margin-top: 12px;
  padding: 10px 12px;
  background: linear-gradient(90deg, #FFF8E1 0%, #FFF0F0 100%);
  border-left: 3px solid #B22222;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #333;
}
.join-time-icon { font-size: 16px; }
.join-time-label {
  color: #666;
  font-size: 13px;
}
.join-time-value {
  color: #B22222;
  font-weight: 700;
  font-size: 15px;
  font-family: 'Consolas', 'Monaco', monospace;
}
.join-time-dur {
  color: #888;
  font-size: 12px;
  margin-left: auto;
}
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #eee;
}
.tag {
  background: #FFF0F0;
  color: #B22222;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}
.contact {
  margin-top: 10px;
  font-size: 14px;
  color: #555;
}
.contact-label {
  color: #888;
  margin-right: 2px;
}

/* 统计 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin: 0 16px 16px;
}
.stat-cell {
  background: #fff;
  border-radius: 8px;
  padding: 14px 8px;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.stat-cell .num {
  font-size: 22px;
  font-weight: 800;
  color: #222;
  line-height: 1.2;
}
.stat-cell .lbl {
  font-size: 12px;
  color: #888;
  margin-top: 2px;
}
.stat-cell.highlight { background: linear-gradient(135deg, #B22222, #8B0000); }
.stat-cell.highlight .num { color: #fff; }
.stat-cell.highlight .lbl { color: rgba(255,255,255,0.85); }

/* 培训列表 */
.section-title {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 700;
  color: #222;
  margin: 16px 16px 12px;
}
.section-title .bar {
  width: 4px;
  height: 16px;
  background: #B22222;
  border-radius: 2px;
  margin-right: 8px;
}

.empty {
  text-align: center;
  padding: 40px 16px;
  color: #999;
}
.empty-icon { font-size: 48px; margin-bottom: 8px; }

.training-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0 16px;
}
.training-item {
  background: #fff;
  border-radius: 8px;
  padding: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.t-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
}
.t-theme {
  font-size: 15px;
  font-weight: 600;
  color: #222;
  flex: 1;
}
.t-hours {
  background: #FFF0F0;
  color: #B22222;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}
.t-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #888;
  margin-top: 4px;
  flex-wrap: wrap;
}
.t-source { color: #B22222; }
.t-bio {
  font-size: 12px;
  color: #666;
  background: #FAFAFA;
  border-left: 2px solid #B22222;
  padding: 6px 10px;
  border-radius: 0 4px 4px 0;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.t-photos {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-top: 10px;
}
.t-photo {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 4px;
  overflow: hidden;
  background: #f5f5f5;
  cursor: pointer;
}
.t-photo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.t-attachments {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.t-attach {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  background: #FFF7E6;
  color: #B22222;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
}
.t-attach-icon { font-size: 14px; }

.footer {
  text-align: center;
  font-size: 11px;
  color: #aaa;
  margin-top: 24px;
  padding: 0 16px;
}

/* 图片预览 */
.img-mask {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.92);
  z-index: 99999;
  display: flex;
  flex-direction: column;
  animation: fadeIn 0.2s;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.img-toolbar {
  display: flex;
  justify-content: flex-end;
  padding: 12px 20px;
  color: #fff;
}
.img-close {
  padding: 4px 12px;
  background: rgba(255,255,255,0.15);
  border-radius: 16px;
  font-size: 14px;
  cursor: pointer;
}
.img-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  overflow: auto;
}
.preview-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
</style>
