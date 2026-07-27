<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showDialog, showSuccessToast } from 'vant'
import { membersApi, type MemberItem } from '@/api/members'
import { orgsApi, type Branch, type Community } from '@/api/orgs'
import { useAuthStore } from '@/stores/auth'

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
  branch_secretary: '支部书记',
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
    { name: '全部支部', subname: filterBranchId.value === null ? '✓ 当前选中' : '', value: 0 },
    ...list,
  ]
})
function onBranchSelect(action: { value: number }) {
  filterBranchId.value = action.value === 0 ? null : action.value
  page.value = 1
  load()
}
const selectedBranchName = computed(() => {
  if (filterBranchId.value === null) return '全部支部'
  return filteredBranches.value.find((b) => b.id === filterBranchId.value)?.name || '全部支部'
})

// ===== 操作 =====
function onNew() {
  router.push('/pages/members/new')
}
function onEdit(m: MemberItem) {
  router.push(`/pages/members/edit/${m.id}`)
}

// ===== 公开名片（党员一人一码） =====
const showQRDialog = ref(false)
const qrMember = ref<MemberItem | null>(null)
const qrUrl = ref('')
function onShowQR(m: MemberItem) {
  qrMember.value = m
  qrUrl.value = `${window.location.origin}/public/member/${m.id}`
  showQRDialog.value = true
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

onMounted(() => {
  loadFilters()
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
        label="支部"
        placeholder="全部支部"
        readonly
        is-link
        @click="showBranchPicker = true"
      />
    </van-cell-group>

    <div class="action-row">
      <van-button size="small" type="primary" @click="onNew">
        + 新增人员
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
        </template>
        <template #label>
          {{ m.phone }}{{ m.branch_name ? ' · ' + m.branch_name : '' }}
        </template>
        <template #right-icon>
          <div class="row-actions">
            <button class="row-btn" @click.stop="onShowQR(m)">二维码</button>
            <button class="row-btn" @click.stop="onEdit(m)">编辑</button>
            <button class="row-btn row-btn--danger" @click.stop="onDelete(m)">删除</button>
          </div>
        </template>
      </van-cell>
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

    <!-- 党员一人一码（公开名片） -->
    <van-dialog
      v-model:show="showQRDialog"
      title="党员一人一码"
      :width="320"
      close-on-click-overlay
    >
      <div class="qr-box">
        <div class="qr-member-name">{{ qrMember?.name }}</div>
        <div class="qr-canvas">
          <img
            :src="`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(qrUrl)}`"
            alt="二维码"
          />
        </div>
        <div class="qr-tip">扫码查看个人信息和培训记录</div>
        <div class="qr-url">{{ qrUrl }}</div>
        <div class="qr-actions">
          <van-button size="small" type="primary" @click="onCopyUrl">复制链接</van-button>
          <van-button size="small" plain hairline @click="onOpenQR">打开</van-button>
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

/* 二维码弹窗 */
.qr-box {
  padding: 16px 20px;
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
  width: 200px;
  height: 200px;
}
.qr-tip {
  font-size: 12px;
  color: #888;
  margin-top: 8px;
}
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
</style>
