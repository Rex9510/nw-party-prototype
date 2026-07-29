<script setup lang="ts">
// v2026-07-29: 给 keep-alive 用的组件名（编辑返回时保留筛选/分页/列表数据）
defineOptions({ name: 'MembersList' })

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showDialog, showSuccessToast } from 'vant'
import { membersApi, type MemberItem } from '@/api/members'
import { orgsApi, type Branch, type Community } from '@/api/orgs'
import { useAuthStore } from '@/stores/auth'
import { ROLES } from '@/utils/roles'
import QRCode from 'qrcode'

const auth = useAuthStore()
const router = useRouter()
const items = ref<MemberItem[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const filterCommunityId = ref<number | null>(null)
const filterBranchId = ref<number | null>(null)

const ROLE_LABEL: Record<string, string> = {
  system_admin: '管理员',
  street_lead: '街道负责人',
  community_organizer: '社区组织委员',
  branch_secretary: '社区组织员',
  party_member: '党员',
  member: '党员', // 兼容后端命名
}

const communities = ref<Community[]>([])
const branches = ref<Branch[]>([])

const filteredBranches = computed(() => {
  if (!filterCommunityId.value) return branches.value
  return branches.value.filter((b) => b.community_id === filterCommunityId.value)
})

async function load() {
  loading.value = true
  try {
    const res = await membersApi.list({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
      community_id: filterCommunityId.value || undefined,
      branch_id: filterBranchId.value || undefined,
    })
    items.value = res.items
    total.value = res.total
  } catch (e: any) {
    showToast({ message: e?.message || '加载失败', type: 'fail' })
  } finally {
    loading.value = false
  }
}

async function loadFilters() {
  try {
    if (auth.user?.role === 'system_admin' || auth.user?.role === 'street_lead') {
      communities.value = await orgsApi.communities()
    } else if (auth.user?.community_id) {
      communities.value = await orgsApi.communities(auth.user.street_id || undefined)
    }
    if (auth.user?.role !== 'branch_secretary' && auth.user?.role !== 'member') {
      branches.value = await orgsApi.branches()
    } else if (auth.user?.role === 'branch_secretary' && auth.user?.community_id) {
      // 社区组织员：加载本社区全部支部
      branches.value = await orgsApi.branches(auth.user.community_id)
    } else if (auth.user?.branch_id) {
      branches.value = [{ id: auth.user.branch_id, community_id: auth.user.community_id || 0, name: '本支部' }]
    }
  } catch (e) {
    console.warn('loadFilters failed', e)
  }
}

// ===== 搜索 =====
function onSearch() {
  page.value = 1
  load()
}

// ===== 筛选重置（用户主动点） =====
// v2026-07-29: keep-alive 保留组件状态，sessionStorage 不再需要
function onResetFilter() {
  page.value = 1
  pageSize.value = 20
  keyword.value = ''
  filterCommunityId.value = null
  filterBranchId.value = null
  load()
  showSuccessToast('已重置筛选')
}

// ===== 分页 =====
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

// 页码窗口（最多显示 5 个页码 + 首末省略）
const visiblePages = computed(() => {
  const tp = totalPages.value
  const cur = page.value
  if (tp <= 7) return Array.from({ length: tp }, (_, i) => i + 1)
  // 头尾 + 当前 ±2
  const set = new Set<number>([1, tp, cur, cur - 1, cur + 1, cur - 2, cur + 2])
  return [...set].filter((n) => n >= 1 && n <= tp).sort((a, b) => a - b)
})
function showEllipsisBefore(p: number): boolean {
  const cur = page.value
  const tp = totalPages.value
  if (tp <= 7) return false
  // 第一个显示的页码 > 2，且当前不在前 3 页
  if (p === visiblePages.value[1] && cur > 4) return true
  if (p === visiblePages.value[visiblePages.value.length - 2] && cur < tp - 3) return true
  return false
}

function goPage(p: number) {
  if (p < 1 || p > totalPages.value || p === page.value || loading.value) return
  page.value = p
  load()
  // 翻页后滚到列表顶部，体验更好
  const listEl = document.querySelector('.list')
  if (listEl) (listEl as HTMLElement).scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function onPageSizeChange() {
  page.value = 1
  load()
}

// ===== 社区选择（action-sheet 列表） =====
const showCommunityPicker = ref(false)
const communityActions = computed(() => {
  const list = communities.value.map((c) => ({
    name: c.name,
    subname: c.id === filterCommunityId.value ? '✓ 当前选中' : '',
    value: c.id,
  }))
  return [
    { name: '全部社区', subname: filterCommunityId.value === null ? '✓ 当前选中' : '', value: 0 },
    ...list,
  ]
})
function onCommunitySelect(action: { value: number }) {
  filterCommunityId.value = action.value === 0 ? null : action.value
  filterBranchId.value = null
  page.value = 1
  load()
}
const selectedCommunityName = computed(() => {
  if (filterCommunityId.value === null) return '全部社区'
  return communities.value.find((c) => c.id === filterCommunityId.value)?.name || '全部社区'
})

// ===== 支部选择（action-sheet 列表） =====
const showBranchPicker = ref(false)
const branchActions = computed(() => {
  const list = filteredBranches.value.map((b) => ({
    name: b.name,
    subname: b.id === filterBranchId.value ? '✓ 当前选中' : '',
    value: b.id,
  }))
  return [
    { name: '全部党组织', subname: filterBranchId.value === null ? '✓ 当前选中' : '', value: 0 },
    ...list,
  ]
})
function onBranchSelect(action: { value: number }) {
  filterBranchId.value = action.value === 0 ? null : action.value
  page.value = 1
  load()
}
const selectedBranchName = computed(() => {
  if (filterBranchId.value === null) return '全部党组织'
  return filteredBranches.value.find((b) => b.id === filterBranchId.value)?.name || '全部党组织'
})

// ===== 操作 =====
function onNew() {
  router.push('/pages/members/new')
}
function onEdit(m: MemberItem) {
  router.push(`/pages/members/edit/${m.id}`)
}

// ===== 公开名片（党员学时卡） =====
const showQRDialog = ref(false)
const qrMember = ref<MemberItem | null>(null)
const qrUrl = ref('')
const qrDataUrl = ref('')
const qrLoaded = ref(false)
async function onShowQR(m: MemberItem) {
  qrMember.value = m
  const url = `${window.location.origin}/public/member/${m.id}`
  qrUrl.value = url
  showQRDialog.value = true
  qrLoaded.value = false
  await new Promise(r => setTimeout(r, 100))
  try {
    qrDataUrl.value = await QRCode.toDataURL(url, { width: 320, margin: 1 })
    // 预加载图片，确保手绘 canvas 时已渲染完成
    const preload = new Image()
    preload.onload = () => { qrLoaded.value = true }
    preload.src = qrDataUrl.value
  } catch {
    console.warn('QR generate failed')
    qrLoaded.value = true
  }
}
async function onCopyUrl() {
  try {
    await navigator.clipboard.writeText(qrUrl.value)
    showSuccessToast('链接已复制，可发给党员本人或贴到公示栏')
  } catch {
    showToast('复制失败，请手动选择')
  }
}
function onOpenQR() {
  window.open(qrUrl.value, '_blank')
}

// ===== 保存图片 =====
const showSavePreview = ref(false)
const savePreviewUrl = ref('')

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.lineTo(x + w - r, y)
  ctx.quadraticCurveTo(x + w, y, x + w, y + r)
  ctx.lineTo(x + w, y + h - r)
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
  ctx.lineTo(x + r, y + h)
  ctx.quadraticCurveTo(x, y + h, x, y + h - r)
  ctx.lineTo(x, y + r)
  ctx.quadraticCurveTo(x, y, x + r, y)
  ctx.closePath()
}

async function saveCardAsImage() {
  const m = qrMember.value
  if (!m) return
  try {
    // 等 QR 预加载完成
    if (!qrLoaded.value) await new Promise(r => setTimeout(r, 300))

    // === 卡片尺寸（长方形比例，头像不会压扁） ===
    const W = 340
    const TOP_H = 155
    const BOTTOM_H = 245
    const H = TOP_H + BOTTOM_H  // 400px → 宽高比 ~1:1.18

    const canvas = document.createElement('canvas')
    canvas.width = W * 2
    canvas.height = H * 2
    const ctx = canvas.getContext('2d')!
    ctx.scale(2, 2)

    // ======== 1. 顶部红色渐变 ========
    const grad = ctx.createLinearGradient(0, 0, W, TOP_H)
    grad.addColorStop(0, '#B22222')
    grad.addColorStop(1, '#8B0000')
    ctx.fillStyle = grad
    ctx.fillRect(0, 0, W, TOP_H)

    // 顶部 "党员学时卡" 标题
    ctx.fillStyle = 'rgba(255,255,255,0.95)'
    ctx.font = 'bold 20px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.fillText('党员学时卡', W / 2, 10)

    // ======== 2. 头像 ========
    const AVATAR = 64
    const PAD = 20
    const avatarX = PAD
    // 顶部要留 38px 给"党员学时卡"标题（20px 字号 + 上下边距），头像从 38 位置开始居中剩余空间
    const avatarY = 38 + (TOP_H - 38 - AVATAR) / 2

    // 圆形裁剪
    ctx.save()
    ctx.beginPath()
    ctx.arc(avatarX + AVATAR / 2, avatarY + AVATAR / 2, AVATAR / 2, 0, Math.PI * 2)
    ctx.closePath()
    ctx.clip()

    if (m.photo_urls?.length) {
      try {
        const img = await loadImage(m.photo_urls[0])
        ctx.drawImage(img, avatarX, avatarY, AVATAR, AVATAR)
      } catch {
        drawAvatarFallback(ctx, m.name || '?', avatarX, avatarY, AVATAR)
      }
    } else {
      drawAvatarFallback(ctx, m.name || '?', avatarX, avatarY, AVATAR)
    }
    ctx.restore()

    // 白色边框
    ctx.strokeStyle = 'rgba(255,255,255,0.6)'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.arc(avatarX + AVATAR / 2, avatarY + AVATAR / 2, AVATAR / 2, 0, Math.PI * 2)
    ctx.stroke()

    // ======== 3. 右侧信息 ========
    const infoX = avatarX + AVATAR + 12
    let infoY = avatarY

    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'

    // 姓名
    ctx.fillStyle = '#fff'
    ctx.font = 'bold 18px sans-serif'
    ctx.fillText(m.name || '', infoX, infoY)
    infoY += 26

    // 身份标签
    if (m.identities?.length) {
      const tagH = 18
      let tagX = infoX
      for (const idn of m.identities) {
        ctx.font = '10px sans-serif'
        const tw = Math.round(ctx.measureText(idn).width + 10)
        // 半透明白色背景标签
        ctx.fillStyle = 'rgba(255,255,255,0.2)'
        roundRect(ctx, tagX, infoY + (tagH - 14) / 2, tw, 14, 3)
        ctx.fill()
        ctx.fillStyle = '#fff'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(idn, tagX + tw / 2, infoY + tagH / 2)
        ctx.textAlign = 'left'
        ctx.textBaseline = 'top'
        tagX += tw + 6
      }
      infoY += tagH + 6
    } else {
      infoY += 4  // 无标签时减少间距
    }

    // 入党时间
    ctx.fillStyle = 'rgba(255,255,255,0.85)'
    ctx.font = '12px sans-serif'
    if (m.join_date) {
      ctx.fillText('入党时间 ' + m.join_date.slice(0, 10), infoX, infoY)
      infoY += 18
    }

    // 组织归属
    const orgParts = [m.street_name, m.community_name, m.branch_name].filter(Boolean)
    if (orgParts.length) {
      ctx.fillStyle = 'rgba(255,255,255,0.7)'
      ctx.font = '11px sans-serif'
      ctx.fillText(orgParts.join(' / '), infoX, infoY)
    }

    // ======== 4. 底部白色区域 ========
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, TOP_H, W, BOTTOM_H)

    // ======== 5. 二维码 ========
    const QR_SIZE = 160
    const QR_PAD = 8
    const qrBoxW = QR_SIZE + QR_PAD * 2
    const qrBoxH = QR_SIZE + QR_PAD * 2
    const qrBoxX = (W - qrBoxW) / 2
    const qrBoxY = TOP_H + 28

    // QR 背景框
    ctx.fillStyle = '#fafafa'
    roundRect(ctx, qrBoxX, qrBoxY, qrBoxW, qrBoxH, 8)
    ctx.fill()
    ctx.strokeStyle = '#f0f0f0'
    ctx.lineWidth = 1
    roundRect(ctx, qrBoxX, qrBoxY, qrBoxW, qrBoxH, 8)
    ctx.stroke()

    // 生成 QR 并绘制
    const qrCanvas = document.createElement('canvas')
    qrCanvas.width = QR_SIZE * 2
    qrCanvas.height = QR_SIZE * 2
    await QRCode.toCanvas(qrCanvas, qrUrl.value, { width: QR_SIZE * 2, margin: 1 })
    ctx.drawImage(qrCanvas, qrBoxX + QR_PAD, qrBoxY + QR_PAD, QR_SIZE, QR_SIZE)

    // 提示文字
    ctx.fillStyle = '#888'
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.fillText('扫码查看个人信息和培训记录', W / 2, qrBoxY + qrBoxH + 12)

    // ======== 6. 生成最终图片 ========
    showQRDialog.value = false
    await new Promise(r => setTimeout(r, 200))
    savePreviewUrl.value = canvas.toDataURL('image/png')
    showSavePreview.value = true
  } catch (e) {
    showToast('生成失败')
    console.warn('saveCardAsImage error', e)
  }
}

function drawAvatarFallback(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, size: number) {
  ctx.fillStyle = 'rgba(255,255,255,0.2)'
  ctx.fillRect(x, y, size, size)
  ctx.fillStyle = '#fff'
  ctx.font = 'bold 26px sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(text.charAt(0), x + size / 2, y + size / 2)
}

async function onDelete(m: MemberItem) {
  try {
    await showDialog({
      title: '确认删除',
      message: `确定删除「${m.name}」？删除后该人员无法登录。`,
      confirmButtonText: '删除',
      confirmButtonColor: '#B22222',
    })
    await membersApi.remove(m.id)
    showSuccessToast({ message: '删除成功' })
    load()
  } catch (e: any) {
    if (e?.message) showToast({ message: e.message, type: 'fail' })
  }
}

onMounted(async () => {
  // v2026-07-29: keep-alive 保留组件状态，编辑返回时不会重走 onMounted
  // 这里只在首次进入或被强制刷新时执行
  await loadFilters()
  load()
})
</script>

<template>
  <div class="form-page">
    <div class="page-header">
      <div class="title">人员管理库</div>
      <div class="sub">共 {{ total }} 名人员</div>
    </div>

    <van-search
      v-model="keyword"
      placeholder="搜索姓名/手机号"
      shape="round"
      background="transparent"
      @search="onSearch"
    />

    <van-cell-group inset class="filter-group">
      <van-field
        v-if="communities.length"
        :model-value="selectedCommunityName"
        label="社区"
        placeholder="全部社区"
        readonly
        is-link
        @click="showCommunityPicker = true"
      />
      <van-field
        v-if="branches.length"
        :model-value="selectedBranchName"
        label="党组织"
        placeholder="全部党组织"
        readonly
        is-link
        @click="showBranchPicker = true"
      />
    </van-cell-group>

    <div class="action-row">
      <van-button size="small" type="primary" @click="onNew">
        + 新增人员
      </van-button>
      <van-button
        v-if="keyword || filterCommunityId !== null || filterBranchId !== null || page !== 1"
        size="small"
        plain
        hairline
        @click="onResetFilter"
        class="reset-filter-btn"
      >
        ↺ 重置筛选
      </van-button>
    </div>

    <div v-if="loading" class="status">加载中…</div>
    <div v-else-if="!items.length" class="status empty">
      <div class="empty-icon">👥</div>
      <div>暂无人员数据</div>
      <div class="empty-tip">点击右上角"新增人员"开始</div>
    </div>

    <div v-else class="list">
      <van-cell
        v-for="m in items"
        :key="m.id"
        center
      >
        <template #icon>
          <div class="avatar">
            <img
              v-if="m.photo_urls && m.photo_urls.length"
              :src="m.photo_urls[0]"
              class="avatar-img"
              alt="头像"
            />
            <span v-else>{{ m.name.charAt(0) }}</span>
          </div>
        </template>
        <template #title>
          <span class="member-name">{{ m.name }}</span>
          <span
            v-for="r in (m.roles || [])"
            :key="r"
            class="role-tag"
          >{{ ROLE_LABEL[r] || r }}</span>
          <span
            v-for="idn in (m.identities || [])"
            :key="idn"
            class="identity-tag"
          >{{ idn }}</span>
        </template>
        <template #label>
          {{ m.phone }}{{
            m.org_level === 'branch' && m.branch_name ? ' · ' + m.branch_name :
            m.org_level === 'community' && m.community_name ? ' · ' + m.community_name + '（社区级）' :
            m.org_level === 'street' && m.street_name ? ' · ' + m.street_name + '（街道级）' :
            m.branch_name ? ' · ' + m.branch_name : ''
          }}
        </template>
        <template #right-icon>
          <div class="row-actions">
            <button class="row-btn" @click.stop="onShowQR(m)">二维码</button>
            <button class="row-btn" @click.stop="onEdit(m)">编辑</button>
            <button class="row-btn row-btn--danger" @click.stop="onDelete(m)">删除</button>
          </div>
        </template>
      </van-cell>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="pagination">
        <div class="page-summary">
          共 {{ total }} 条 · 第 {{ page }} / {{ totalPages }} 页
        </div>
        <div class="page-buttons">
          <button
            class="page-btn"
            :disabled="page === 1 || loading"
            @click="goPage(page - 1)"
          >上一页</button>
          <template v-for="(p, idx) in visiblePages" :key="p">
            <span
              v-if="idx > 0 && showEllipsisBefore(p)"
              class="page-ellipsis"
            >…</span>
            <button
              class="page-btn"
              :class="{ active: p === page }"
              :disabled="loading"
              @click="goPage(p)"
            >{{ p }}</button>
          </template>
          <button
            class="page-btn"
            :disabled="page === totalPages || loading"
            @click="goPage(page + 1)"
          >下一页</button>
        </div>
        <div class="page-size">
          <span>每页</span>
          <van-dropdown-menu active-color="#B22222">
            <van-dropdown-item v-model="pageSize" :options="[
              { text: '10 条', value: 10 },
              { text: '20 条', value: 20 },
              { text: '50 条', value: 50 },
              { text: '100 条', value: 100 },
            ]" @change="onPageSizeChange" />
          </van-dropdown-menu>
        </div>
      </div>
    </div>

    <!-- 社区选择（action-sheet 列表，PC 也能用滚轮） -->
    <van-action-sheet
      v-model:show="showCommunityPicker"
      :actions="communityActions"
      cancel-text="取消"
      close-on-click-action
      @select="onCommunitySelect"
    />

    <!-- 支部选择（action-sheet 列表） -->
    <van-action-sheet
      v-model:show="showBranchPicker"
      :actions="branchActions"
      cancel-text="取消"
      close-on-click-action
      @select="onBranchSelect"
    />

    <!-- 党员学时卡（卡片身份） -->
    <van-dialog
      v-model:show="showQRDialog"
      title="党员学时卡"
      :width="340"
      close-on-click-overlay
    >
      <div class="id-card">
        <!-- 上半：头像 + 身份信息 -->
        <div class="id-card-top">
          <div class="id-avatar">
            <img v-if="qrMember?.photo_urls?.length" :src="qrMember.photo_urls[0]" class="id-avatar-img" alt="头像" />
            <span v-else class="id-avatar-fallback">{{ qrMember?.name?.charAt(0) || '?' }}</span>
          </div>
          <div class="id-info">
            <div class="id-name">{{ qrMember?.name }}</div>
            <div v-if="qrMember?.identities?.length" class="id-tags">
              <span v-for="idn in qrMember.identities" :key="idn" class="id-tag">{{ idn }}</span>
            </div>
            <div v-if="qrMember?.join_date" class="id-join">
              <span class="id-join-label">入党时间</span>
              <span class="id-join-value">{{ qrMember.join_date.slice(0, 10) }}</span>
            </div>
            <div class="id-org">
              <span v-if="qrMember?.street_name">{{ qrMember.street_name }}</span>
              <span v-if="qrMember?.community_name"> / {{ qrMember.community_name }}</span>
              <span v-if="qrMember?.branch_name"> / {{ qrMember.branch_name }}</span>
            </div>
          </div>
        </div>
        <!-- 下半：二维码 -->
        <div class="id-card-bottom">
          <div class="id-qr">
            <img v-if="qrDataUrl" :src="qrDataUrl" class="id-qr-img" alt="二维码" />
          </div>
          <div class="id-qr-tip">扫码查看个人信息和培训记录</div>
        </div>
      </div>
      <div class="id-actions">
        <van-button size="small" type="primary" @click="saveCardAsImage">保存图片</van-button>
        <van-button size="small" type="primary" @click="onCopyUrl">复制链接</van-button>
        <van-button size="small" plain hairline @click="onOpenQR">打开</van-button>
      </div>
    </van-dialog>

    <!-- 保存预览（手机端长按保存到相册） -->
    <van-overlay :show="showSavePreview" @click="showSavePreview = false" :z-index="2000">
      <div class="save-preview" @click.stop>
        <div class="save-preview-img-wrap">
          <img :src="savePreviewUrl" class="save-preview-img" alt="党员学时卡" />
          <!-- 关闭按钮：绝对定位到图片右上角，圆形深色背景，清晰可见 -->
          <button class="save-preview-close" @click="showSavePreview = false" aria-label="关闭">
            ✕
          </button>
        </div>
        <p class="save-preview-hint">👆 长按图片保存到相册</p>
      </div>
    </van-overlay>
  </div>
</template>

<style scoped>
.form-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 8px 0 32px;
}

.page-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: 4px 16px 12px;
}
.title { font-size: 20px; font-weight: 700; color: #222; }
.sub { font-size: 13px; color: #888; }

.filter-group { margin-top: 4px; }

.action-row {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
}
.reset-filter-btn {
  color: #888 !important;
  border-color: #ddd !important;
}

.status {
  text-align: center;
  padding: 40px 16px;
  color: #888;
  font-size: 14px;
}
.status.empty .empty-icon { font-size: 48px; margin-bottom: 8px; }
.empty-tip { font-size: 12px; color: #bbb; margin-top: 4px; }

.list { padding: 0 8px; }
:deep(.van-cell) {
  background: #fff;
  margin-bottom: 8px;
  border-radius: 8px;
  padding: 12px 16px;
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #FFE4E1;
  color: #B22222;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  margin-right: 12px;
  flex-shrink: 0;
  overflow: hidden;
}
.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.member-name {
  margin-right: 6px;
}
.role-tag {
  display: inline-block;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: #FFF0F0;
  color: #B22222;
  margin-right: 4px;
  font-weight: 500;
  vertical-align: middle;
  line-height: 1.6;
}
.role-tag:last-child { margin-right: 0; }
.identity-tag {
  display: inline-block;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: #F0F5FF;
  color: #1E40AF;
  margin-right: 4px;
  font-weight: 500;
  vertical-align: middle;
  line-height: 1.6;
}

/* cell 右侧按钮留点空间 */
:deep(.van-cell__right-icon) {
  margin-left: 8px;
}

/* 列表行操作按钮 */
.row-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
.row-btn {
  font-size: 12px;
  padding: 4px 10px;
  border: 1px solid #B22222;
  background: #fff;
  color: #B22222;
  border-radius: 4px;
  cursor: pointer;
  line-height: 1.4;
  transition: all 0.15s;
}
.row-btn:hover {
  background: #FFF0F0;
}
.row-btn--danger {
  border-color: #ddd;
  color: #666;
}
.row-btn--danger:hover {
  border-color: #B22222;
  background: #FFF0F0;
  color: #B22222;
}

/* 二维码弹窗 — 卡片身份 */
.id-card {
  position: relative;
  padding: 0;
}
.id-card-top {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 20px 16px;
  background: linear-gradient(135deg, #B22222 0%, #8B0000 100%);
  color: #fff;
}
.id-avatar {
  flex-shrink: 0;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid rgba(255,255,255,0.6);
  background: rgba(255,255,255,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}
.id-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.id-avatar-fallback {
  font-size: 26px;
  font-weight: 700;
  color: #fff;
}
.id-info {
  flex: 1;
  min-width: 0;
}
.id-name {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 6px;
}
.id-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}
.id-tag {
  display: inline-block;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(255,255,255,0.2);
  color: #fff;
  font-weight: 500;
}
.id-join {
  font-size: 12px;
  opacity: 0.85;
}
.id-join-label {
  margin-right: 4px;
}
.id-join-value {
  font-weight: 500;
}
.id-org {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 4px;
}
.id-card-bottom {
  padding: 16px 20px 20px;
  text-align: center;
}
.id-qr {
  display: inline-block;
  border-radius: 8px;
  padding: 8px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  margin-bottom: 8px;
}
.id-qr img {
  display: block;
  width: 160px;
  height: 160px;
}
.id-qr-tip {
  font-size: 12px;
  color: #888;
}
.id-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  padding: 12px 20px 16px;
}

/* 分页 */
.pagination {
  margin: 16px 8px 24px;
  padding: 16px 12px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.page-summary {
  font-size: 12px;
  color: #888;
}
.page-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: center;
  align-items: center;
}
.page-btn {
  min-width: 36px;
  height: 32px;
  padding: 0 10px;
  font-size: 13px;
  border: 1px solid #ddd;
  background: #fff;
  color: #333;
  border-radius: 4px;
  cursor: pointer;
  transition: all .15s;
}
.page-btn:hover:not(:disabled) {
  border-color: #B22222;
  color: #B22222;
}
.page-btn.active {
  background: #B22222;
  border-color: #B22222;
  color: #fff;
  font-weight: 600;
}
.page-btn:disabled {
  background: #f5f5f5;
  color: #bbb;
  cursor: not-allowed;
}
.page-ellipsis {
  padding: 0 4px;
  color: #999;
  font-size: 13px;
  user-select: none;
}
.page-size {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #666;
}
:deep(.van-dropdown-menu__bar) {
  box-shadow: none;
  background: transparent;
}
:deep(.van-dropdown-menu__title) {
  font-size: 12px;
  color: #B22222;
  padding: 0 8px;
}

/* 保存图片预览 */
.save-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 40px 20px;
}
.save-preview-img-wrap {
  position: relative;  /* 让关闭按钮绝对定位基于此 */
  background: #fff;
  border-radius: 12px;
  padding: 8px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.3);
  max-width: 90vw;
}
.save-preview-img {
  display: block;
  max-width: 100%;
  height: auto;
  border-radius: 6px;
}
.save-preview-hint {
  color: #fff;
  font-size: 14px;
  margin: 20px 0;
  text-align: center;
}
/* 关闭按钮：固定在图片右上角，圆形深色半透明白色 X */
.save-preview-close {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.4);
  z-index: 1;
  transition: background 0.15s, transform 0.1s;
  font-family: inherit;
  padding: 0;
}
.save-preview-close:hover {
  background: rgba(0, 0, 0, 0.85);
  transform: scale(1.08);
}
.save-preview-close:active {
  transform: scale(0.95);
}
</style>
