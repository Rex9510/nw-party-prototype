<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showDialog, showToast, showSuccessToast } from 'vant'
import { activitiesApi, type ActivityListItem } from '@/api/activities'

const router = useRouter()
const items = ref<ActivityListItem[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')

const STATUS_LABEL: Record<string, { text: string; color: string }> = {
  draft: { text: '草稿', color: '#999' },
  pending_community: { text: '待社区审核', color: '#EA580C' },
  pending_street: { text: '待街道审核', color: '#EA580C' },
  approved: { text: '已通过', color: '#059669' },
  rejected: { text: '已驳回', color: '#B22222' },
}

const statusOptions = [
  { v: '', l: '全部' },
  { v: 'draft', l: '草稿' },
  { v: 'pending_community', l: '待社区' },
  { v: 'pending_street', l: '待街道' },
  { v: 'approved', l: '已通过' },
  { v: 'rejected', l: '已驳回' },
]

async function load() {
  loading.value = true
  try {
    const res = await activitiesApi.list({
      page: page.value,
      page_size: pageSize.value,
      status: statusFilter.value || undefined,
    })
    items.value = res.items
    total.value = res.total
  } catch (e: any) {
    showToast({ message: e?.message || '加载失败', type: 'fail' })
  } finally {
    loading.value = false
  }
}

function onNew() {
  router.push('/pages/activities/new')
}

async function onItemTap(a: ActivityListItem) {
  try {
    await showDialog({
      title: a.theme,
      message: `时间：${a.training_at}\n地点：${a.location}\n人数：${a.participant_count}\n学时：${a.study_hours}`,
      confirmButtonText: '关闭',
      showCancelButton: false,
    })
  } catch {}
}

// 草稿/驳回 → 编辑 / 删除
function onEdit(id: number) {
  router.push(`/pages/activities/edit/${id}`)
}

async function onDelete(id: number) {
  try {
    await showConfirmDialog({
      title: '确认删除',
      message: '确定删除该培训活动？删除后不可恢复。',
      confirmButtonText: '删除',
      confirmButtonColor: '#B22222',
    })
    await activitiesApi.remove(id)
    showSuccessToast('已删除')
    load()
  } catch {
    // 用户取消
  }
}

// ===== 状态筛选（action-sheet 列表） =====
const showStatusPicker = ref(false)
const statusActions = computed(() =>
  statusOptions.map((o) => ({
    name: o.l,
    subname: o.v === statusFilter.value ? '✓ 当前选中' : '',
    value: o.v,
  })),
)
const selectedStatusLabel = computed(() => {
  return statusOptions.find((o) => o.v === statusFilter.value)?.l || '全部'
})
function onStatusSelect(action: { value: string }) {
  statusFilter.value = action.value
  page.value = 1
  load()
}

onMounted(() => {
  load()
})
</script>

<template>
  <div class="form-page">
    <div class="page-header">
      <div class="title">培训活动</div>
      <div class="sub">共 {{ total }} 场</div>
    </div>

    <van-cell-group inset class="filter-group">
      <van-field
        :model-value="selectedStatusLabel"
        label="状态"
        placeholder="全部"
        readonly
        is-link
        @click="showStatusPicker = true"
      />
    </van-cell-group>

    <div class="action-row">
      <van-button size="small" type="primary" @click="onNew">
        + 录入培训
      </van-button>
    </div>

    <div v-if="loading" class="status">加载中…</div>
    <div v-else-if="!items.length" class="status empty">
      <div class="empty-icon">📋</div>
      <div>暂无培训活动</div>
    </div>

    <div v-else class="list">
      <div
        v-for="a in items"
        :key="a.id"
        class="card"
        @click="onItemTap(a)"
      >
        <div class="card-header">
          <div class="theme">{{ a.theme }}</div>
          <div
            class="status"
            :style="{ background: (STATUS_LABEL[a.status] || { color: '#999' }).color }"
          >
            {{ (STATUS_LABEL[a.status] || { text: a.status }).text }}
          </div>
        </div>
        <div class="meta">
          <span>📅 {{ a.training_at }}</span>
          <span>📍 {{ a.location }}</span>
        </div>
        <div class="meta">
          <span>👥 {{ a.participant_count }} 人</span>
          <span>🎓 {{ a.study_hours }} 学时</span>
        </div>
        <div v-if="a.status === 'draft' || a.status === 'rejected'" class="card-actions">
          <van-button size="mini" plain hairline type="primary" @click.stop="onEdit(a.id)">
            编辑
          </van-button>
          <van-button size="mini" plain hairline type="danger" @click.stop="onDelete(a.id)">
            删除
          </van-button>
        </div>
      </div>
    </div>

    <!-- 状态选择（action-sheet 列表，PC 友好） -->
    <van-action-sheet
      v-model:show="showStatusPicker"
      :actions="statusActions"
      cancel-text="取消"
      close-on-click-action
      @select="onStatusSelect"
    />
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
  padding: 12px 16px;
}

.status {
  text-align: center;
  padding: 40px 16px;
  color: #888;
  font-size: 14px;
}
.status.empty .empty-icon { font-size: 48px; margin-bottom: 8px; }

.list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 8px;
}
.card {
  background: #fff;
  border-radius: 8px;
  padding: 14px 16px;
  cursor: pointer;
  transition: transform .1s;
}
.card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.card:active { transform: scale(0.99); }
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.theme {
  font-size: 15px;
  font-weight: 600;
  color: #222;
  flex: 1;
  margin-right: 8px;
}
.card .status {
  padding: 2px 8px;
  color: #fff;
  font-size: 12px;
  border-radius: 4px;
  flex-shrink: 0;
}
.meta {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: #888;
  margin-top: 4px;
}
.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}
</style>
