<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { showToast } from 'vant'
import { studyApi, type StudyListItem, type StudyDetailItem } from '@/api/study'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const year = ref(new Date().getFullYear())
const list = ref<StudyListItem[]>([])
const totalMembers = ref(0)
const loading = ref(false)

const detailItems = ref<StudyDetailItem[]>([])
const detailMember = ref<StudyListItem | null>(null)
const detailTotalHours = ref(0)
const detailActivityCount = ref(0)
const showDetail = ref(false)

const canViewList = computed(() => {
  const r = auth.user?.role
  return r === 'street_lead' || r === 'community_organizer' || r === 'system_admin' || r === 'branch_secretary'
})

async function loadList() {
  loading.value = true
  try {
    const res = await studyApi.list({ year: year.value })
    list.value = res.items
    totalMembers.value = res.total_members
  } catch (e: any) {
    showToast({ message: e?.message || '加载失败', type: 'fail' })
  } finally {
    loading.value = false
  }
}

async function onMy() {
  loading.value = true
  try {
    const d = await studyApi.me(year.value)
    detailItems.value = d.items
    detailMember.value = {
      member_id: d.member_id,
      member_name: d.member_name,
      member_phone: '',
      branch_name: null,
      year: d.year,
      total_hours: d.total_hours,
      activity_count: d.activity_count,
    }
    detailTotalHours.value = d.total_hours
    detailActivityCount.value = d.activity_count
    showDetail.value = true
  } catch (e: any) {
    showToast({ message: e?.message || '加载失败', type: 'fail' })
  } finally {
    loading.value = false
  }
}

async function onMemberTap(m: StudyListItem) {
  detailMember.value = m
  showDetail.value = true
  loading.value = true
  try {
    const d = await studyApi.member(m.member_id, year.value)
    detailItems.value = d.items
    detailTotalHours.value = d.total_hours
    detailActivityCount.value = d.activity_count
  } catch (e: any) {
    showToast({ message: e?.message || '加载失败', type: 'fail' })
  } finally {
    loading.value = false
  }
}

// ===== 年份选择（action-sheet 列表） =====
const showYearPicker = ref(false)
const yearActions = computed(() => {
  const y = new Date().getFullYear()
  return Array.from({ length: 6 }, (_, i) => ({
    name: `${y - i} 年`,
    subname: y - i === year.value ? '✓ 当前选中' : '',
    value: y - i,
  }))
})
function onYearSelect(action: { value: number }) {
  year.value = action.value
  if (canViewList.value) loadList()
  else onMy()
}

onMounted(() => {
  if (canViewList.value) {
    loadList()
  } else {
    onMy()
  }
})
</script>

<template>
  <div class="form-page">
    <div class="page-header">
      <div class="title">学时档案</div>
      <van-button size="small" plain hairline type="primary" @click="showYearPicker = true">
        {{ year }} 年 ▾
      </van-button>
    </div>

    <!-- 党员视角：直接看自己的档案 -->
    <div v-if="!canViewList" class="my-card-wrap">
      <div class="my-card">
        <div class="my-title">我的学时</div>
        <div class="my-stats">
          <div class="stat-item">
            <div class="stat-num">{{ detailActivityCount }}</div>
            <div class="stat-label">活动数</div>
          </div>
          <div class="stat-item">
            <div class="stat-num primary">{{ detailTotalHours }}</div>
            <div class="stat-label">总学时</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 管理者视角：列表 -->
    <div v-else>
      <div class="sub-line">共 {{ totalMembers }} 名人员有学时记录</div>

      <div v-if="loading" class="status">加载中…</div>
      <div v-else-if="!list.length" class="status empty">
        <div class="empty-icon">🎓</div>
        <div>{{ year }} 年暂无学时记录</div>
      </div>

      <div v-else class="list">
        <div
          v-for="m in list"
          :key="m.member_id"
          class="item"
          @click="onMemberTap(m)"
        >
          <div class="item-info">
            <div class="name">{{ m.member_name }}</div>
            <div class="meta">
              <span>{{ m.branch_name || '-' }}</span>
              <span>· {{ m.member_phone }}</span>
            </div>
          </div>
          <div class="item-stats">
            <div class="hours">{{ m.total_hours }}</div>
            <div class="hours-label">学时 · {{ m.activity_count }} 场</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <van-dialog
      v-model:show="showDetail"
      :title="`${detailMember?.member_name || ''} · ${year}`"
      show-cancel-button
      :before-close="(action) => { if (action === 'confirm') showDetail = false; else showDetail = false }"
    >
      <div class="dialog-body">
        <div class="modal-stats">
          <div class="m-stat">
            <div class="m-stat-num">{{ detailActivityCount }}</div>
            <div class="m-stat-label">活动数</div>
          </div>
          <div class="m-stat">
            <div class="m-stat-num primary">{{ detailTotalHours }}</div>
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

    <!-- 年份选择（action-sheet 列表） -->
    <van-action-sheet
      v-model:show="showYearPicker"
      :actions="yearActions"
      cancel-text="取消"
      close-on-click-action
      @select="onYearSelect"
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
  align-items: center;
  justify-content: space-between;
  margin: 4px 16px 16px;
}
.title { font-size: 20px; font-weight: 700; color: #222; }

.sub-line { font-size: 13px; color: #888; padding: 0 16px 8px; }

.my-card-wrap { padding: 0 16px; }
.my-card {
  background: linear-gradient(135deg, #B22222, #8B0000);
  color: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(178, 34, 34, 0.2);
}
.my-title { font-size: 16px; font-weight: 700; margin-bottom: 12px; }
.my-stats { display: flex; gap: 12px; }
.stat-item {
  flex: 1;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}
.stat-num { font-size: 28px; font-weight: 800; line-height: 1.2; }
.stat-num.primary { color: #FFE4B5; }
.stat-label { font-size: 12px; opacity: 0.9; margin-top: 2px; }

.status {
  text-align: center;
  padding: 40px 16px;
  color: #888;
  font-size: 14px;
}
.status.empty .empty-icon { font-size: 48px; margin-bottom: 8px; }

.list { display: flex; flex-direction: column; gap: 8px; padding: 0 8px; }
.item {
  display: flex;
  background: #fff;
  border-radius: 8px;
  padding: 12px 16px;
  align-items: center;
  cursor: pointer;
  transition: transform .1s;
}
.item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.item:active { transform: scale(0.99); }
.item-info { flex: 1; min-width: 0; }
.name { font-size: 15px; font-weight: 600; color: #222; }
.meta { font-size: 12px; color: #888; margin-top: 3px; display: flex; gap: 4px; }
.item-stats { text-align: right; }
.hours { font-size: 20px; font-weight: 700; color: var(--primary); line-height: 1.2; }
.hours-label { font-size: 11px; color: #888; }

.dialog-body { padding: 12px 16px; }
.modal-stats {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
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
  color: var(--primary);
  font-weight: 600;
  margin-top: 3px;
}
.empty-mini { text-align: center; padding: 20px; color: #999; font-size: 13px; }
</style>
