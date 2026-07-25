<script setup lang="ts">
import { computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useAuthStore } from '@/stores/auth'
import { ROLES, type Role } from '@/utils/roles'

const auth = useAuthStore()

const role = computed<Role>(() => (auth.user?.role as Role) || 'member')
const roleConfig = computed(() => ROLES[role.value])
const cards = computed(() => roleConfig.value?.cards || [])

onShow(async () => {
  if (auth.token && !auth.user) {
    try {
      await auth.fetchMe()
    } catch (e) {
      console.warn('fetchMe failed', e)
    }
  }
})

function onCardTap(path: string, enabled: boolean) {
  if (!enabled) {
    uni.showToast({ title: '该功能后续开发', icon: 'none' })
    return
  }
  uni.navigateTo({ url: path, fail: () => uni.showToast({ title: '页面打开失败', icon: 'none' }) })
}

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
      <view class="user-card" :style="{ background: roleConfig?.color || '#B22222' }">
        <view class="avatar">{{ (auth.user?.name || 'U').charAt(0) }}</view>
        <view class="info">
          <view class="name">{{ auth.user?.name || '加载中…' }}</view>
          <view class="role">{{ roleConfig?.label }} · {{ roleConfig?.scope }}</view>
        </view>
        <view class="logout" @click="onLogout">退出</view>
      </view>
    </view>

    <view class="welcome">
      <view class="title">V1-MVP 工作台</view>
      <view class="sub">Day 2 已就绪 · 角色权限联调通过</view>
    </view>

    <view class="section-title">我的入口</view>
    <view class="grid">
      <view
        v-for="card in cards"
        :key="card.key"
        class="card"
        :class="{ disabled: !card.enabled }"
        @click="onCardTap(card.path, card.enabled)"
      >
        <view class="emoji">{{ card.icon }}</view>
        <view class="card-title">{{ card.label }}</view>
        <view class="card-sub">{{ card.desc }}</view>
        <view class="tag">后续开放</view>
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
  padding: 24rpx 0 32rpx;
}
.user-card {
  display: flex;
  align-items: center;
  padding: 32rpx 28rpx;
  border-radius: 24rpx;
  color: #fff;
  box-shadow: 0 8rpx 24rpx rgba(178, 34, 34, 0.18);
}
.avatar {
  width: 88rpx;
  height: 88rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  font-weight: 700;
  margin-right: 24rpx;
}
.info { flex: 1; min-width: 0; }
.name { font-size: 34rpx; font-weight: 700; }
.role { font-size: 24rpx; opacity: 0.9; margin-top: 6rpx; }
.logout {
  font-size: 26rpx;
  padding: 12rpx 20rpx;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12rpx;
}

.welcome {
  background: #fff;
  border-radius: 16rpx;
  padding: 28rpx 32rpx;
  margin-bottom: 32rpx;
  border: 1rpx solid #f0f0f0;
}
.welcome .title { font-size: 32rpx; font-weight: 700; color: #222; }
.welcome .sub { font-size: 24rpx; color: #888; margin-top: 6rpx; }

.section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #333;
  margin-bottom: 20rpx;
  padding-left: 4rpx;
}

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
  border: 1rpx solid #f0f0f0;
}
.card.disabled { opacity: 0.65; }
.emoji { font-size: 56rpx; line-height: 1; margin-bottom: 12rpx; }
.card-title { font-size: 30rpx; font-weight: 600; color: #222; }
.card-sub { font-size: 24rpx; color: #888; margin-top: 6rpx; }
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
