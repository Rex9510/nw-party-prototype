<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const roleLabel = computed(() => {
  const map: Record<string, string> = {
    street_lead: '街道负责人',
    community_organizer: '社区组织委员',
    branch_secretary: '支部书记',
    member: '党员',
    system_admin: '系统管理员',
  }
  return auth.user ? map[auth.user.role] || auth.user.role : ''
})

onMounted(() => {
  if (!auth.user) {
    auth.fetchMe().catch(() => {})
  }
})

function onLogout() {
  uni.showModal({
    title: '提示',
    content: '确定退出登录？',
    success: (r) => {
      if (r.confirm) {
        auth.logout()
        uni.reLaunch({ url: '/pages/login/index' })
      }
    },
  })
}
</script>

<template>
  <view class="dashboard">
    <view class="header">
      <view class="greet">
        <view class="hi">你好，{{ auth.user?.name || '用户' }}</view>
        <view class="role">{{ roleLabel }}</view>
      </view>
      <view class="logout" @click="onLogout">退出</view>
    </view>

    <view class="welcome">
      <view class="title">V1-MVP 工作台</view>
      <view class="sub">Day 1 脚手架就绪 · 后续功能陆续开放</view>
    </view>

    <view class="grid">
      <view class="card disabled">
        <view class="card-title">党员库</view>
        <view class="card-sub">手动新增 · 批量导入</view>
        <view class="tag">D3</view>
      </view>
      <view class="card disabled">
        <view class="card-title">培训活动</view>
        <view class="card-sub">13+ 字段录入</view>
        <view class="tag">D6-D7</view>
      </view>
      <view class="card disabled">
        <view class="card-title">两级审核</view>
        <view class="card-sub">社区初审 · 街道复审</view>
        <view class="tag">D8-D10</view>
      </view>
      <view class="card disabled">
        <view class="card-title">学时档案</view>
        <view class="card-sub">个人汇总 · 明细</view>
        <view class="tag">D11</view>
      </view>
      <view class="card disabled">
        <view class="card-title">年度统计</view>
        <view class="card-sub">Excel 导出</view>
        <view class="tag">D12</view>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.dashboard {
  min-height: 100vh;
  background: #F7F8FA;
  padding: 0 32rpx 64rpx;
}

.header {
  padding: 40rpx 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.greet .hi { font-size: 40rpx; font-weight: 700; color: #222; }
.greet .role { font-size: 26rpx; color: #B22222; margin-top: 8rpx; }
.logout { font-size: 28rpx; color: #888; padding: 8rpx 16rpx; }

.welcome {
  background: linear-gradient(135deg, #B22222, #8B0000);
  color: #fff;
  border-radius: 24rpx;
  padding: 40rpx;
  margin-bottom: 32rpx;
}
.welcome .title { font-size: 36rpx; font-weight: 700; }
.welcome .sub { font-size: 24rpx; opacity: 0.85; margin-top: 8rpx; }

.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24rpx;
}

.card {
  background: #fff;
  border-radius: 20rpx;
  padding: 32rpx 28rpx;
  position: relative;
  box-shadow: 0 4rpx 16rpx rgba(0,0,0,0.04);
}
.card.disabled { opacity: 0.6; }
.card-title { font-size: 30rpx; font-weight: 600; color: #222; }
.card-sub { font-size: 24rpx; color: #888; margin-top: 8rpx; }
.tag {
  position: absolute;
  top: 16rpx;
  right: 16rpx;
  background: #FFF0F0;
  color: #B22222;
  font-size: 20rpx;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
}
</style>
