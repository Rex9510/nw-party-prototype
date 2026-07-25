<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { statsApi, type StatItem } from '@/api/stats'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const year = ref(new Date().getFullYear())
const items = ref<StatItem[]>([])
const totalSessions = ref(0)
const totalParticipants = ref(0)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const r = await statsApi.yearly(year.value)
    items.value = r.items
    totalSessions.value = r.total_sessions
    totalParticipants.value = r.total_participants
  } catch (e: any) {
    uni.showToast({ title: e?.message || '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function onExport() {
  // H5 直接打开
  // #ifdef H5
  const token = uni.getStorageSync('nwparty_auth')?.token || ''
  const url = statsApi.exportYearlyUrl(year.value, token)
  window.open(url)
  // #endif
  // #ifndef H5
  uni.downloadFile({
    url: `/api/v1/stats/yearly/export?year=${year.value}&access_token=${uni.getStorageSync('nwparty_auth')?.token || ''}`,
    success: (r) => {
      uni.openDocument({ filePath: r.tempFilePath, showMenu: true })
    },
  })
  // #endif
}

function onPrev() {
  year.value--
  load()
}
function onNext() {
  year.value++
  load()
}

onMounted(() => {
  load()
})
</script>

<template>
  <view class="page">
    <view class="year-bar">
      <view class="year-btn" @click="onPrev">‹</view>
      <view class="year-text">{{ year }} 年度统计</view>
      <view class="year-btn" @click="onNext">›</view>
    </view>

    <!-- 汇总卡 -->
    <view class="summary">
      <view class="summary-card">
        <view class="stat-item">
          <view class="stat-num">{{ totalSessions }}</view>
          <view class="stat-label">总场次</view>
        </view>
        <view class="divider" />
        <view class="stat-item">
          <view class="stat-num">{{ totalParticipants }}</view>
          <view class="stat-label">培训人数</view>
        </view>
      </view>
    </view>

    <!-- 分类明细 -->
    <view class="section-title">分类明细</view>
    <view v-if="loading" class="loading">加载中…</view>
    <view v-else class="list">
      <view v-for="(item, i) in items" :key="item.label" class="row">
        <view class="row-index">{{ i + 1 }}</view>
        <view class="row-label">{{ item.label }}</view>
        <view class="row-num">
          <view class="num-cell">{{ item.session_count }}</view>
          <view class="num-cell primary">{{ item.participant_count }}</view>
        </view>
      </view>
    </view>

    <!-- 导出按钮 -->
    <view class="export-btn" @click="onExport">
      📥 导出 Excel
    </view>
  </view>
</template>

<style lang="scss" scoped>
.page { min-height: 100vh; background: #F7F8FA; padding: 24rpx; padding-bottom: 120rpx; }
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
.year-text { font-size: 32rpx; font-weight: 700; color: #222; min-width: 240rpx; text-align: center; }

.summary { margin-bottom: 32rpx; }
.summary-card {
  display: flex;
  background: linear-gradient(135deg, #B22222, #8B0000);
  color: #fff;
  border-radius: 20rpx;
  padding: 40rpx 32rpx;
  box-shadow: 0 8rpx 24rpx rgba(178, 34, 34, 0.2);
}
.stat-item { flex: 1; text-align: center; }
.stat-num { font-size: 72rpx; font-weight: 800; line-height: 1.1; }
.stat-label { font-size: 24rpx; opacity: 0.9; margin-top: 4rpx; }
.divider { width: 1rpx; background: rgba(255, 255, 255, 0.3); margin: 0 24rpx; }

.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #333;
  margin-bottom: 16rpx;
  padding-left: 4rpx;
}
.loading { text-align: center; padding: 60rpx 0; color: #888; }

.list { background: #fff; border-radius: 16rpx; overflow: hidden; }
.row {
  display: flex;
  align-items: center;
  padding: 24rpx;
  border-bottom: 1rpx solid #f0f0f0;
}
.row:last-of-type { border-bottom: none; }
.row-index {
  width: 48rpx;
  height: 48rpx;
  line-height: 48rpx;
  text-align: center;
  background: #f5f5f5;
  color: #666;
  border-radius: 8rpx;
  font-size: 24rpx;
  font-weight: 600;
  margin-right: 20rpx;
}
.row-label { flex: 1; font-size: 28rpx; color: #222; }
.row-num { display: flex; gap: 16rpx; }
.num-cell {
  min-width: 80rpx;
  text-align: center;
  font-size: 32rpx;
  font-weight: 700;
  color: #666;
}
.num-cell.primary { color: #B22222; }

.export-btn {
  position: fixed;
  bottom: 40rpx;
  left: 32rpx;
  right: 32rpx;
  height: 96rpx;
  line-height: 96rpx;
  text-align: center;
  background: #B22222;
  color: #fff;
  font-size: 32rpx;
  font-weight: 600;
  border-radius: 16rpx;
  box-shadow: 0 8rpx 24rpx rgba(178, 34, 34, 0.3);
}
</style>
