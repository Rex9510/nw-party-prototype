<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const phone = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function onSubmit() {
  if (!/^1[3-9]\d{9}$/.test(phone.value)) {
    errorMsg.value = '请输入正确的手机号'
    return
  }
  if (password.value.length < 6) {
    errorMsg.value = '密码至少 6 位'
    return
  }
  errorMsg.value = ''
  loading.value = true
  try {
    await auth.login(phone.value, password.value)
    uni.reLaunch({ url: '/pages/index/index' })
  } catch (e: any) {
    errorMsg.value = e?.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <view class="login-page">
    <view class="hero">
      <view class="brand">南湾党建</view>
      <view class="subtitle">党员集中学习培训管理 · V1-MVP</view>
    </view>

    <view class="form">
      <view class="field">
        <text class="label">手机号</text>
        <input
          v-model="phone"
          class="input"
          type="number"
          maxlength="11"
          placeholder="请输入手机号"
          placeholder-class="ph"
        />
      </view>
      <view class="field">
        <text class="label">密码</text>
        <input
          v-model="password"
          class="input"
          password
          placeholder="请输入密码（≥6位）"
          placeholder-class="ph"
        />
      </view>

      <view v-if="errorMsg" class="error">{{ errorMsg }}</view>

      <button
        class="submit"
        :loading="loading"
        :disabled="loading"
        @click="onSubmit"
      >
        登 录
      </button>

      <view class="tips">
        默认账号请联系街道负责人开通
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #B22222 0%, #8B0000 35%, #F7F8FA 35%);
  padding: 0 32rpx 64rpx;
  display: flex;
  flex-direction: column;
}

.hero {
  padding: 120rpx 0 80rpx;
  text-align: center;
  color: #fff;
}
.brand { font-size: 56rpx; font-weight: 700; letter-spacing: 4rpx; }
.subtitle { margin-top: 16rpx; font-size: 26rpx; opacity: 0.85; }

.form {
  background: #fff;
  border-radius: 24rpx;
  padding: 48rpx 36rpx;
  margin-top: 32rpx;
  box-shadow: 0 8rpx 32rpx rgba(0,0,0,0.08);
}

.field { margin-bottom: 32rpx; }
.label { display: block; font-size: 26rpx; color: #666; margin-bottom: 12rpx; }
.input {
  width: 100%;
  height: 88rpx;
  border-bottom: 1rpx solid #eee;
  font-size: 32rpx;
  color: #222;
}
.ph { color: #ccc; }

.error {
  background: #FFF0F0;
  color: #B22222;
  padding: 16rpx 24rpx;
  border-radius: 8rpx;
  font-size: 26rpx;
  margin-bottom: 24rpx;
}

.submit {
  width: 100%;
  height: 88rpx;
  background: #B22222;
  color: #fff;
  font-size: 32rpx;
  font-weight: 600;
  border-radius: 12rpx;
  margin-top: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}
.submit[disabled] { opacity: 0.6; }

.tips {
  text-align: center;
  color: #999;
  font-size: 24rpx;
  margin-top: 32rpx;
}
</style>
