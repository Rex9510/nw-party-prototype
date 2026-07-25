<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { activitiesApi, type ActivityListItem } from '@/api/activities'

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
    uni.showToast({ title: e?.message || '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function onNew() {
  uni.navigateTo({ url: '/pages/activities/new' })
}

function onItemTap(a: ActivityListItem) {
  uni.showModal({
    title: a.theme,
    content: `时间：${a.training_at}\n地点：${a.location}\n人数：${a.participant_count}\n学时：${a.study_hours}`,
    showCancel: false,
  })
}

const statusOptions = [
  { v: '', l: '全部' },
  { v: 'draft', l: '草稿' },
  { v: 'pending_community', l: '待社区' },
  { v: 'pending_street', l: '待街道' },
  { v: 'approved', l: '已通过' },
  { v: 'rejected', l: '已驳回' },
]

function onPickStatus(e: any) {
  statusFilter.value = statusOptions[e.detail.value]?.v || ''
  page.value = 1
  load()
}

onMounted(() => {
  load()
})
</script>

<template>
  <view class="page">
    <view class="filter-row">
      <picker
        :value="statusOptions.findIndex((o) => o.v === statusFilter)"
        :range="statusOptions.map((o) => o.l)"
        @change="onPickStatus"
      >
        <view class="picker">
          状态：{{ statusOptions.find((o) => o.v === statusFilter)?.l }}
        </view>
      </picker>
    </view>

    <view class="actions">
      <view class="total">共 {{ total }} 场</view>
      <view class="btn btn-primary" @click="onNew">+ 录入培训</view>
    </view>

    <view v-if="loading" class="loading">加载中…</view>
    <view v-else-if="!items.length" class="empty">
      <view class="empty-icon">📋</view>
      <view>暂无培训活动</view>
    </view>

    <view v-else class="list">
      <view v-for="a in items" :key="a.id" class="item" @click="onItemTap(a)">
        <view class="item-header">
          <view class="theme">{{ a.theme }}</view>
          <view
            class="status"
            :style="{ background: (STATUS_LABEL[a.status] || { color: '#999' }).color }"
          >
            {{ (STATUS_LABEL[a.status] || { text: a.status }).text }}
          </view>
        </view>
        <view class="meta">
          <text>📅 {{ a.training_at }}</text>
          <text>📍 {{ a.location }}</text>
        </view>
        <view class="meta">
          <text>👥 {{ a.participant_count }} 人</text>
          <text>🎓 {{ a.study_hours }} 学时</text>
        </view>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.page { min-height: 100vh; background: #F7F8FA; padding: 0 24rpx 32rpx; }
.filter-row { display: flex; gap: 16rpx; padding: 16rpx 0; }
.picker {
  flex: 1;
  height: 64rpx;
  line-height: 64rpx;
  padding: 0 20rpx;
  background: #fff;
  border-radius: 10rpx;
  font-size: 26rpx;
  border: 1rpx solid #eee;
}
.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16rpx;
}
.total { font-size: 24rpx; color: #888; }
.btn {
  height: 60rpx;
  line-height: 60rpx;
  padding: 0 24rpx;
  border-radius: 10rpx;
  font-size: 26rpx;
  font-weight: 600;
}
.btn-primary { background: #B22222; color: #fff; }
.loading, .empty { text-align: center; padding: 80rpx 0; color: #888; font-size: 28rpx; }
.empty-icon { font-size: 80rpx; margin-bottom: 16rpx; }
.list { display: flex; flex-direction: column; gap: 16rpx; }
.item {
  background: #fff;
  border-radius: 14rpx;
  padding: 24rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
}
.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12rpx;
}
.theme {
  font-size: 30rpx;
  font-weight: 600;
  color: #222;
  flex: 1;
  margin-right: 12rpx;
}
.status {
  padding: 4rpx 16rpx;
  color: #fff;
  font-size: 22rpx;
  border-radius: 8rpx;
  flex-shrink: 0;
}
.meta {
  display: flex;
  gap: 24rpx;
  font-size: 24rpx;
  color: #888;
  margin-top: 6rpx;
}
</style>
