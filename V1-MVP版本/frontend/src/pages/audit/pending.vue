<script setup lang="ts">
// v2026-07-29: 给 keep-alive 用的组件名
defineOptions({ name: 'AuditPending' })

import { ref, onMounted, computed } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { auditsApi, type AuditItem } from '@/api/audits'
import { activitiesApi, type Activity } from '@/api/activities'
import { orgsApi, type StreetTreeNode } from '@/api/orgs'
import { dictsApi, type DictItem } from '@/api/dicts'
import { formatDateTime } from '@/utils/date'

// 缓存组织树（用于按 ids 查名字）
const orgTree = ref<StreetTreeNode[]>([])
// 培训对象字典（code → 中文名）
const categoryMap = ref<Record<string, string>>({})

// 把 co_organize_branch_ids 转 names
const coBranchNames = computed(() => {
  if (!detail.value?.co_organize_branch_ids?.length) return []
  const flat: { id: number; name: string }[] = []
  for (const s of orgTree.value) {
    for (const c of s.communities || []) {
      for (const b of c.branches || []) {
        flat.push({ id: b.id, name: `${s.name} / ${c.name} / ${b.name}` })
      }
    }
  }
  return detail.value.co_organize_branch_ids
    .map((id) => flat.find((b) => b.id === id)?.name)
    .filter(Boolean) as string[]
})

// 培训对象 code → 中文
const audienceCategoryText = computed(() => {
  const arr = detail.value?.audience_category || []
  if (!arr.length) return '-'
  return arr.map((c) => categoryMap.value[c] || c).join('、')
})

// 学习方式 code → label
const STUDY_METHOD_LABELS: Record<string, string> = {
  party_meeting: '党员大会',
  theme_day: '主题党日',
  onsite_teaching: '现场教学',
  special_lecture: '专题党课',
}

// 参加人员所属组织：按 org_level 取对应级别名字
function memberOrgName(p: { member_org_level?: string | null; member_branch_name?: string | null; member_community_name?: string | null; member_street_name?: string | null }): string {
  if (p.member_org_level === 'street' && p.member_street_name) return p.member_street_name
  if (p.member_org_level === 'community' && p.member_community_name) return p.member_community_name
  if (p.member_org_level === 'branch' && p.member_branch_name) return p.member_branch_name
  return ''
}
const studyMethodsText = computed(() => {
  const m = detail.value?.study_methods
  if (!m || !m.length) return '-'
  return m.map((c) => STUDY_METHOD_LABELS[c] || c).join('、')
})

const items = ref<AuditItem[]>([])
const loading = ref(false)
const actionItem = ref<AuditItem | null>(null)
const actionType = ref<'approve' | 'reject' | null>(null)
const comment = ref('')
const showActionDialog = ref(false)
const showLogsDialog = ref(false)
const showDetailDialog = ref(false)
const detailLoading = ref(false)
const detail = ref<Activity | null>(null)
const logs = ref<any[]>([])
const logsFor = ref<AuditItem | null>(null)

// 图片预览
const showImagePreview = ref(false)
const previewImageUrl = ref('')
const imageList = ref<string[]>([])  // 当前活动所有图片（用于显示数量）
const imgError = ref(false)

function isImage(url: string) {
  return url.startsWith('data:image') || /\.(png|jpg|jpeg|gif|webp|bmp)$/i.test(url)
}
function fileTypeIcon(url: string) {
  if (url.startsWith('data:application/pdf')) return '📄'
  if (url.includes('spreadsheet') || url.includes('ms-excel')) return '📊'
  if (url.includes('wordprocessingml') || url.includes('msword')) return '📝'
  if (url.startsWith('data:text/plain')) return '📃'
  return '📎'
}
function onPreviewImage(url: string) {
  console.log('[audit] preview image', url.slice(0, 40))
  imgError.value = false
  previewImageUrl.value = url
  // 收集所有图片用于计数
  if (detail.value?.attachments) {
    imageList.value = detail.value.attachments
      .filter(a => isImage(a.file_url))
      .map(a => a.file_url)
  }
  showImagePreview.value = true
}

function onImgLoad() {
  console.log('[audit] image loaded ok')
  imgError.value = false
}
function onImgError() {
  console.warn('[audit] image load failed', previewImageUrl.value.slice(0, 40))
  imgError.value = true
}

function onAttClick(a: any) {
  console.log('[audit] att clicked', a.id, a.kind, a.file_url.slice(0, 40))
  if (isImage(a.file_url)) {
    onPreviewImage(a.file_url)
  } else {
    // 附件下载：data URL 转 blob 再下载
    try {
      const url = a.file_url
      if (url.startsWith('data:')) {
        const [meta, b64] = url.split(',')
        const mime = meta.match(/data:([^;]+)/)?.[1] || 'application/octet-stream'
        // MIME → 常用扩展名
        const MIME_EXT: Record<string, string> = {
          'application/pdf': 'pdf',
          'application/msword': 'doc',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
          'application/vnd.ms-excel': 'xls',
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
          'application/vnd.ms-powerpoint': 'ppt',
          'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
          'text/plain': 'txt',
          'text/csv': 'csv',
          'application/zip': 'zip',
          'application/json': 'json',
          'image/png': 'png',
          'image/jpeg': 'jpg',
          'image/gif': 'gif',
          'image/webp': 'webp',
          'image/svg+xml': 'svg',
        }
        const ext = MIME_EXT[mime]
          || mime.split('/')[1]?.split('+').pop()?.split('.').pop()
          || 'bin'
        const bin = atob(b64)
        const bytes = new Uint8Array(bin.length)
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
        const blob = new Blob([bytes], { type: mime })
        const objUrl = URL.createObjectURL(blob)
        const a2 = document.createElement('a')
        a2.href = objUrl
        a2.download = `附件-${a.id}.${ext}`
        document.body.appendChild(a2)
        a2.click()
        document.body.removeChild(a2)
        URL.revokeObjectURL(objUrl)
      } else {
        window.open(url, '_blank')
      }
    } catch (e) {
      console.error('[audit] download failed', e)
    }
  }
}

const NODE_LABEL: Record<string, string> = {
  community_review: '社区初审',
  street_review: '街道复审',
}

const ACTION_LABEL: Record<string, { text: string; cls: string }> = {
  submit: { text: '提交', cls: 'action-submit' },
  approve: { text: '通过', cls: 'action-approve' },
  reject: { text: '驳回', cls: 'action-reject' },
}

async function load() {
  loading.value = true
  try {
    const res = await auditsApi.pending()
    items.value = res.items
  } catch (e: any) {
    showToast({ message: e?.message || '加载失败', type: 'fail' })
  } finally {
    loading.value = false
  }
}

async function loadOrgs() {
  try {
    orgTree.value = await orgsApi.tree()
  } catch (e) {
    console.warn('[audit] loadOrgs failed', e)
  }
}

async function loadCategories() {
  try {
    const list: DictItem[] = await dictsApi.trainingCategories()
    categoryMap.value = Object.fromEntries(list.map((c) => [c.code, c.name]))
  } catch (e) {
    console.warn('[audit] loadCategories failed', e)
  }
}

function onApprove(item: AuditItem) {
  actionItem.value = item
  actionType.value = 'approve'
  comment.value = ''
  showActionDialog.value = true
}
function onReject(item: AuditItem) {
  actionItem.value = item
  actionType.value = 'reject'
  comment.value = ''
  showActionDialog.value = true
}

async function onViewLogs(item: AuditItem) {
  logsFor.value = item
  showLogsDialog.value = true
  try {
    logs.value = await auditsApi.logs(item.activity_id)
  } catch (e) {
    logs.value = []
  }
}

async function onViewDetail(item: AuditItem) {
  detail.value = null
  showDetailDialog.value = true
  detailLoading.value = true
  try {
    detail.value = await activitiesApi.get(item.activity_id)
  } catch (e: any) {
    showToast({ message: e?.message || '加载详情失败', type: 'fail' })
    showDetailDialog.value = false
  } finally {
    detailLoading.value = false
  }
}

async function onConfirmAction() {
  if (!actionItem.value || !actionType.value) return
  if (actionType.value === 'reject' && !comment.value.trim()) {
    showToast({ message: '驳回必须填意见', type: 'fail' })
    return
  }
  try {
    if (actionType.value === 'approve') {
      const r = await auditsApi.approve(actionItem.value.activity_id, comment.value)
      showSuccessToast({ message: r.status === 'approved' ? '已通过' : '已转交街道' })
    } else {
      await auditsApi.reject(actionItem.value.activity_id, comment.value)
      showSuccessToast({ message: '已驳回' })
    }
    showActionDialog.value = false
    load()
  } catch (e: any) {
    showToast({ message: e?.message || '操作失败', type: 'fail' })
  }
}

onMounted(() => {
  load()
  loadOrgs()
  loadCategories()
})
</script>

<template>
  <div class="form-page">
    <div class="page-header">
      <div class="title">待审核</div>
      <div class="sub">共 {{ items.length }} 条</div>
    </div>

    <div v-if="loading" class="status">加载中…</div>
    <div v-else-if="!items.length" class="status empty">
      <div class="empty-icon">✅</div>
      <div>暂无待审核活动</div>
    </div>

    <div v-else class="list">
      <div v-for="item in items" :key="item.activity_id" class="card">
        <div class="card-header">
          <div class="theme" @click="onViewDetail(item)">{{ item.theme }}</div>
          <div class="node-tag">{{ NODE_LABEL[item.current_node] || item.current_node }}</div>
        </div>
        <div class="meta">
          <span>📅 {{ formatDateTime(item.training_at) }}</span>
          <span>📍 {{ item.location }}</span>
        </div>
        <div class="meta">
          <span>👤 提交人：{{ item.submitter_name || '-' }}</span>
          <span>🏛️ {{ item.community_name }}</span>
        </div>
        <div class="meta">
          <span>👥 {{ item.participant_count }} 人</span>
          <span>🎓 {{ item.study_hours }} 学时</span>
        </div>
        <div class="actions">
          <van-button size="small" plain hairline type="primary" @click="onViewDetail(item)">查看详情</van-button>
          <van-button size="small" plain hairline @click="onViewLogs(item)">查看日志</van-button>
          <van-button size="small" plain hairline type="danger" @click="onReject(item)">驳回</van-button>
          <van-button size="small" type="primary" @click="onApprove(item)">通过</van-button>
        </div>
      </div>
    </div>

    <!-- 审核操作弹窗 -->
    <van-dialog
      v-model:show="showActionDialog"
      :title="actionType === 'approve' ? '审核通过' : '审核驳回'"
      show-cancel-button
      :before-close="async (action) => { if (action === 'confirm') await onConfirmAction(); else showActionDialog = false }"
    >
      <div class="dialog-body">
        <div class="dialog-sub">{{ actionItem?.theme }}</div>
        <van-field
          v-model="comment"
          type="textarea"
          rows="4"
          :placeholder="actionType === 'reject' ? '请填写驳回意见（必填）' : '审核意见（可选）'"
          maxlength="500"
          autosize
        />
      </div>
    </van-dialog>

    <!-- 详情弹窗 -->
    <van-popup
      v-model:show="showDetailDialog"
      position="bottom"
      round
      :style="{ maxHeight: '85vh' }"
      closeable
    >
      <div class="detail-popup">
        <div class="detail-title">活动详情</div>
        <div v-if="detailLoading" class="detail-status">加载中…</div>
        <div v-else-if="detail" class="detail-body">
          <div class="detail-theme">{{ detail.theme }}</div>
          <div class="detail-row"><span class="lbl">📅 培训时间</span><span>{{ formatDateTime(detail.training_at) }}</span></div>
          <div class="detail-row"><span class="lbl">📍 培训地点</span><span>{{ detail.location }}</span></div>
          <div class="detail-row"><span class="lbl">🎤 讲师</span><span>{{ detail.lecturer_name || '-' }}</span></div>
          <div class="detail-row"><span class="lbl">🌐 形式</span><span>{{ detail.online_offline === 'online' ? '线上' : detail.online_offline === 'offline' ? '线下' : '混合' }}</span></div>
          <div class="detail-row"><span class="lbl">📚 集中学习</span><span>{{ detail.is_centralized ? '是' : '否' }}</span></div>
          <div v-if="detail.is_centralized" class="detail-row"><span class="lbl">📋 学习方式</span><span>{{ studyMethodsText }}</span></div>
          <div class="detail-row"><span class="lbl">💡 创新理论教育</span><span>{{ detail.is_innovation_theory ? '是' : '否' }}</span></div>
          <!-- v3: 举办单位 + 二级字段 -->
          <div class="detail-row"><span class="lbl">🏢 举办单位</span><span>{{ detail.organize_type === 'upper_send' ? '上级送课' : '自行组织' }}</span></div>
          <div v-if="detail.organize_type === 'self_organize' && coBranchNames.length" class="detail-row">
            <span class="lbl">🏛️ 协办支部</span>
            <span class="branch-list">
              <span v-for="(n, i) in coBranchNames" :key="i" class="branch-chip">{{ n }}</span>
            </span>
          </div>
          <div v-else-if="detail.organize_type === 'self_organize' && !coBranchNames.length" class="detail-row">
            <span class="lbl">🏛️ 协办支部</span><span class="muted">未选择</span>
          </div>
          <div v-if="detail.organize_type === 'upper_send'" class="detail-row"><span class="lbl">📋 具体部门</span><span>{{ detail.upper_org || '-' }}</span></div>
          <!-- v2: 培训对象多选 -->
          <div class="detail-row"><span class="lbl">👥 培训对象</span><span>{{ audienceCategoryText }}</span></div>
          <div class="detail-row"><span class="lbl">🧑‍🤝‍🧑 参加人数</span><span>{{ detail.participant_count }} 人</span></div>
          <div class="detail-row"><span class="lbl">⏱️ 学时</span><span>{{ detail.study_hours || '-' }} 学时</span></div>

          <div v-if="detail.participants && detail.participants.length" class="detail-section">
            <div class="section-title">参加人员（{{ detail.participants.length }}）</div>
            <div class="member-list">
              <div v-for="p in detail.participants" :key="p.id" class="member-item">
                <span>👤 {{ p.member_name || '党员 #' + p.member_id }}
                  <span v-if="memberOrgName(p)" class="member-org">{{ memberOrgName(p) }}</span>
                </span>
                <span class="member-phone" v-if="p.member_phone">{{ p.member_phone }}</span>
                <span class="member-hours">+{{ p.study_hours }} 学时</span>
              </div>
            </div>
          </div>

          <div v-if="detail.attachments && detail.attachments.length" class="detail-section">
            <div class="section-title">现场照片 / 附件（{{ detail.attachments.length }}）</div>
            <div class="att-grid">
              <div
                v-for="a in detail.attachments"
                :key="a.id"
                class="att-item"
                @click.stop="onAttClick(a)"
              >
                <img v-if="isImage(a.file_url)" :src="a.file_url" class="att-thumb" />
                <div v-else class="att-file">
                  <div class="att-icon">{{ fileTypeIcon(a.file_url) }}</div>
                  <div class="att-kind">{{ a.kind === 'photo' ? '照片' : '附件' }}</div>
                  <div class="att-download">点击下载</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="detail-status">暂无数据</div>
      </div>
    </van-popup>

    <!-- 图片预览全屏（自实现，直接渲染 img，避免 van-image-preview 的覆盖问题） -->
    <div v-if="showImagePreview" class="img-preview-mask" @click.self="showImagePreview = false">
      <div class="img-preview-toolbar">
        <span class="img-counter">{{ imageList.length }} 张</span>
        <span class="img-close" @click="showImagePreview = false">✕ 关闭</span>
      </div>
      <div class="img-preview-content">
        <img :src="previewImageUrl" class="img-preview-img" @load="onImgLoad" @error="onImgError" />
        <div v-if="imgError" class="img-error">图片加载失败</div>
      </div>
    </div>

    <!-- 日志弹窗 -->
    <van-dialog
      v-model:show="showLogsDialog"
      title="审核日志"
      show-cancel-button
      :before-close="(action) => { if (action !== 'confirm') showLogsDialog = false; else showLogsDialog = false }"
    >
      <div class="dialog-body">
        <div class="dialog-sub">{{ logsFor?.theme }}</div>
        <div class="log-list">
          <div v-if="!logs.length" class="empty-mini">暂无日志</div>
          <div v-for="log in logs" :key="log.id" class="log-item">
            <div class="log-time">{{ formatDateTime(log.created_at) }}</div>
            <div class="log-action">
              <span class="log-action-tag" :class="ACTION_LABEL[log.action]?.cls || ''">
                {{ ACTION_LABEL[log.action]?.text || log.action }}
              </span>
              <span class="log-operator">{{ log.operator_name }}</span>
            </div>
            <div v-if="log.comment" class="log-comment">{{ log.comment }}</div>
          </div>
        </div>
      </div>
    </van-dialog>
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
  margin: 4px 16px 16px;
}
.title { font-size: 20px; font-weight: 700; color: #222; }
.sub { font-size: 13px; color: #888; }

.status {
  text-align: center;
  padding: 40px 16px;
  color: #888;
  font-size: 14px;
}
.status.empty .empty-icon { font-size: 48px; margin-bottom: 8px; }

.list { display: flex; flex-direction: column; gap: 10px; padding: 0 8px; }
.card {
  background: #fff;
  border-radius: 8px;
  padding: 14px 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.theme { font-size: 15px; font-weight: 600; color: #222; flex: 1; margin-right: 8px; }
.node-tag {
  background: #FFF0F0;
  color: var(--primary);
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
  flex-shrink: 0;
}
.meta {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: #888;
  margin-top: 4px;
}
.actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.actions > * { flex: 1; }

.dialog-body { padding: 12px 16px; }
.dialog-sub { font-size: 13px; color: #888; margin-bottom: 12px; }
.log-list { max-height: 50vh; overflow-y: auto; }
.log-item { padding: 8px 0; border-bottom: 1px solid #f5f5f5; }
.log-item:last-child { border-bottom: none; }
.log-time { font-size: 11px; color: #999; }
.log-action { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
.log-action-tag {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  color: #fff;
}
.action-submit { background: #6B7280; }
.action-approve { background: #059669; }
.action-reject { background: #B22222; }
.log-operator { font-size: 13px; color: #222; }
.log-comment {
  margin-top: 4px;
  font-size: 12px;
  color: #666;
  background: #f5f5f5;
  padding: 4px 8px;
  border-radius: 3px;
}
.empty-mini { text-align: center; padding: 20px; color: #999; font-size: 13px; }

/* 详情弹窗 */
.detail-popup {
  padding: 20px 16px 32px;
  max-height: 85vh;
  overflow-y: auto;
}
.detail-title {
  font-size: 18px;
  font-weight: 700;
  color: #222;
  text-align: center;
  margin-bottom: 16px;
}
.detail-status { text-align: center; padding: 40px 0; color: #999; }
.detail-theme {
  font-size: 17px;
  font-weight: 600;
  color: #B22222;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f0f0;
}
.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  padding: 8px 0;
  border-bottom: 1px dashed #f5f5f5;
}
.detail-row .lbl { color: #888; }
.detail-row > span:last-child { color: #222; max-width: 60%; text-align: right; }
.detail-section { margin-top: 16px; }
.section-title { font-size: 14px; font-weight: 600; color: #222; margin-bottom: 8px; }
.member-list { background: #f9f9f9; border-radius: 6px; padding: 8px 12px; max-height: 200px; overflow-y: auto; }
.member-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
  color: #555;
  border-bottom: 1px dashed #eee;
  gap: 8px;
}
.member-item:last-child { border-bottom: none; }
.member-phone { color: #888; font-size: 12px; }
.member-hours { color: #B22222; font-weight: 600; flex-shrink: 0; }
.member-org {
  font-size: 11px;
  color: #888;
  background: #f5f5f5;
  padding: 1px 6px;
  border-radius: 3px;
  margin-left: 6px;
  font-weight: normal;
  vertical-align: middle;
}
.muted { color: #999 !important; }
.branch-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: flex-end;
  max-width: 60%;
}
.branch-chip {
  font-size: 12px;
  background: #FFF0F0;
  color: #B22222;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}
.att-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.att-item {
  display: block;
  cursor: pointer;
  position: relative;
}
.att-item:hover { opacity: 0.85; }
.att-thumb {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 4px;
  background: #f5f5f5;
}
.att-file {
  width: 100%;
  aspect-ratio: 1;
  background: #FFF0F0;
  border: 1px dashed #B22222;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.att-icon { font-size: 32px; }
.att-kind { font-size: 11px; color: #B22222; margin-top: 2px; }
.att-download { font-size: 10px; color: #999; margin-top: 2px; }
.card-header .theme { cursor: pointer; }
.card-header .theme:hover { color: var(--primary); }

/* 自实现图片全屏预览 */
.img-preview-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.92);
  z-index: 99999;
  display: flex;
  flex-direction: column;
  animation: previewFade 0.2s ease;
}
@keyframes previewFade { from { opacity: 0; } to { opacity: 1; } }
.img-preview-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  color: #fff;
  font-size: 14px;
  flex-shrink: 0;
}
.img-close {
  cursor: pointer;
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  user-select: none;
}
.img-close:hover { background: rgba(255, 255, 255, 0.25); }
.img-counter { opacity: 0.7; }
.img-preview-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  overflow: auto;
}
.img-preview-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  background: #000;
  border-radius: 4px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.5);
}
.img-error {
  color: #aaa;
  font-size: 14px;
  padding: 20px;
}
</style>
