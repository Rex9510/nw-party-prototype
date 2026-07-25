<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
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
    uni.showToast({ title: e?.message || '加载失败', icon: 'none' })
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
    uni.showToast({ title: e?.message || '加载失败', icon: 'none' })
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
    uni.showToast({ title: e?.message || '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function onPrevYear() {
  year.value--
  loadList()
}

function onNextYear() {
  year.value++
  loadList()
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
  <view class="page">
    <view class="year-bar">
      <view class="year-btn" @click="onPrevYear">‹</view>
      <view class="year-text">{{ year }} 年度</view>
      <view class="year-btn" @click="onNextYear">›</view>
    </view>

    <!-- 党员/支部视角：直接看自己的档案 -->
    <view v-if="!canViewList" class="my-section">
      <view class="my-card">
        <view class="my-title">我的学时</view>
        <view class="my-stats">
          <view class="stat-item">
            <view class="stat-num">{{ detailActivityCount }}</view>
            <view class="stat-label">活动数</view>
          </view>
          <view class="stat-item">
            <view class="stat-num primary">{{ detailTotalHours }}</view>
            <view class="stat-label">总学时</view>
          </view>
        </view>
      </view>
    </view>

    <!-- 管理者视角：列表 -->
    <view v-else>
      <view class="summary">
        <view class="total">共 {{ totalMembers }} 名党员有学时记录</view>
      </view>

      <view v-if="loading" class="loading">加载中…</view>
      <view v-else-if="!list.length" class="empty">
        <view class="empty-icon">🎓</view>
        <view>{{ year }} 年暂无学时记录</view>
      </view>

      <view v-else class="list">
        <view
          v-for="m in list"
          :key="m.member_id"
          class="item"
          @click="onMemberTap(m)"
        >
          <view class="item-info">
            <view class="name">{{ m.member_name }}</view>
            <view class="meta">
              <text>{{ m.branch_name || '-' }}</text>
              <text>· {{ m.member_phone }}</text>
            </view>
          </view>
          <view class="item-stats">
            <view class="hours">{{ m.total_hours }}</view>
            <view class="hours-label">学时 · {{ m.activity_count }} 场</view>
          </view>
        </view>
      </view>
    </view>

    <!-- 详情弹窗 -->
    <view v-if="showDetail" class="modal-mask" @click="showDetail = false">
      <view class="modal" @click.stop>
        <view class="modal-title">
          {{ detailMember?.member_name }} · {{ year }}
        </view>
        <view class="modal-stats">
          <view class="m-stat">
            <view class="m-stat-num">{{ detailActivityCount }}</view>
            <view class="m-stat-label">活动数</view>
          </view>
          <view class="m-stat">
            <view class="m-stat-num primary">{{ detailTotalHours }}</view>
            <view class="m-stat-label">总学时</view>
          </view>
        </view>
        <scroll-view scroll-y class="detail-list">
          <view v-if="!detailItems.length" class="empty-mini">本年暂无参与记录</view>
          <view v-for="i in detailItems" :key="i.activity_id" class="detail-item">
            <view class="detail-theme">{{ i.theme }}</view>
            <view class="detail-meta">
              <text>📅 {{ i.training_at }}</text>
              <text>📍 {{ i.location }}</text>
            </view>
            <view class="detail-hours">+{{ i.study_hours }} 学时</view>
          </view>
        </scroll-view>
        <view class="btn btn-secondary" @click="showDetail = false">关闭</view>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.page { min-height: 100vh; background: #F7F8FA; padding: 24rpx; }
.year-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32rpx;
  background: #fff;
  border-radius: 16rpx;
  padding: 20rpx;
  margin-bottom: 24rpx;
}
.year-btn {
  width: 64rpx;
  height: 64rpx;
  line-height: 60rpx;
  text-align: center;
  background: #f5f5f5;
  border-radius: 32rpx;
  font-size: 40rpx;
  color: #666;
}
.year-text { font-size: 36rpx; font-weight: 700; color: #222; min-width: 200rpx; text-align: center; }

.my-card {
  background: linear-gradient(135deg, #B22222, #8B0000);
  color: #fff;
  border-radius: 20rpx;
  padding: 40rpx 32rpx;
  box-shadow: 0 8rpx 24rpx rgba(178, 34, 34, 0.2);
}
.my-title { font-size: 32rpx; font-weight: 700; margin-bottom: 24rpx; }
.my-stats { display: flex; gap: 24rpx; }
.stat-item {
  flex: 1;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 12rpx;
  padding: 24rpx;
  text-align: center;
}
.stat-num { font-size: 56rpx; font-weight: 800; line-height: 1.2; }
.stat-num.primary { color: #FFE4B5; }
.stat-label { font-size: 24rpx; opacity: 0.9; margin-top: 4rpx; }

.summary { margin-bottom: 20rpx; }
.total { font-size: 24rpx; color: #888; padding: 0 8rpx; }
.loading, .empty { text-align: center; padding: 80rpx 0; color: #888; font-size: 28rpx; }
.empty-icon { font-size: 80rpx; margin-bottom: 16rpx; }

.list { display: flex; flex-direction: column; gap: 16rpx; }
.item {
  display: flex;
  background: #fff;
  border-radius: 14rpx;
  padding: 24rpx;
  align-items: center;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
}
.item-info { flex: 1; min-width: 0; }
.name { font-size: 30rpx; font-weight: 600; color: #222; }
.meta { font-size: 24rpx; color: #888; margin-top: 6rpx; display: flex; gap: 8rpx; }
.item-stats { text-align: right; }
.hours { font-size: 40rpx; font-weight: 700; color: #B22222; line-height: 1.2; }
.hours-label { font-size: 22rpx; color: #888; }

.modal-mask {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 60rpx;
}
.modal {
  background: #fff;
  border-radius: 16rpx;
  padding: 32rpx 28rpx;
  width: 100%;
  max-width: 600rpx;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}
.modal-title { font-size: 30rpx; font-weight: 700; color: #222; margin-bottom: 20rpx; text-align: center; }
.modal-stats {
  display: flex;
  gap: 16rpx;
  margin-bottom: 20rpx;
}
.m-stat {
  flex: 1;
  background: #FFF0F0;
  border-radius: 12rpx;
  padding: 16rpx;
  text-align: center;
}
.m-stat-num { font-size: 40rpx; font-weight: 700; color: #B22222; }
.m-stat-num.primary { color: #DC2626; }
.m-stat-label { font-size: 22rpx; color: #888; margin-top: 4rpx; }
.detail-list { max-height: 500rpx; margin-bottom: 20rpx; }
.detail-item {
  background: #f5f5f5;
  border-radius: 8rpx;
  padding: 16rpx;
  margin-bottom: 12rpx;
}
.detail-theme { font-size: 26rpx; font-weight: 600; color: #222; }
.detail-meta { display: flex; gap: 16rpx; font-size: 22rpx; color: #888; margin-top: 6rpx; }
.detail-hours {
  font-size: 24rpx;
  color: #B22222;
  font-weight: 600;
  margin-top: 6rpx;
}
.empty-mini { text-align: center; padding: 40rpx; color: #999; font-size: 24rpx; }
.btn {
  height: 72rpx;
  line-height: 72rpx;
  text-align: center;
  border-radius: 8rpx;
  font-size: 28rpx;
  font-weight: 600;
}
.btn-secondary { background: #f5f5f5; color: #666; }
</style>
