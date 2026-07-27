<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const phone = ref('13800000010')
const password = ref('pass1234')
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
    showToast({ message: '登录成功', type: 'success' })
    const redirect = router.currentRoute.value.query.redirect as string
    router.push(redirect || '/pages/index/index')
  } catch (e: any) {
    errorMsg.value = e?.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-bg" />

    <div class="login-shell">
      <div class="hero">
        <img src="/logo.jpg" class="hero-logo" alt="logo" />
        <div class="brand">党员学时统计系统</div>
      </div>

      <div class="form-card">
        <div class="form-title">账号登录</div>

        <div class="field">
          <label class="label">手机号</label>
          <input
            v-model="phone"
            class="input"
            type="text"
            inputmode="numeric"
            maxlength="11"
            placeholder="请输入手机号"
          />
        </div>
        <div class="field">
          <label class="label">密码</label>
          <input
            v-model="password"
            class="input"
            type="password"
            placeholder="请输入密码（≥6位）"
            @keyup.enter="onSubmit"
          />
        </div>

        <div v-if="errorMsg" class="error">{{ errorMsg }}</div>

        <button
          class="submit"
          :disabled="loading"
          @click="onSubmit"
        >
          {{ loading ? '登录中…' : '登 录' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  background: #F7F8FA;
  overflow: hidden;
}

/* 顶部红色 banner（仅 H5 顶部一块） */
.login-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 35vh;
  min-height: 220px;
  background: linear-gradient(180deg, #B22222 0%, #8B0000 100%);
  z-index: 0;
}

.login-shell {
  position: relative;
  z-index: 1;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 16px;
}

.hero {
  text-align: center;
  color: #fff;
  padding: 48px 0 24px;
  width: 100%;
  max-width: 480px;
}
.hero-logo {
  width: 96px;
  height: 96px;
  object-fit: contain;
  border-radius: 12px;
  background: rgba(255,255,255,0.12);
  padding: 6px;
  margin-bottom: 16px;
}
.brand {
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 3px;
}

.form-card {
  background: #fff;
  border-radius: 12px;
  padding: 24px 20px;
  width: 100%;
  max-width: 360px;
  margin-top: 8px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
}
.form-title {
  font-size: 16px;
  font-weight: 600;
  color: #222;
  margin-bottom: 16px;
  text-align: center;
}

.field { margin-bottom: 14px; }
.label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
}
.input {
  width: 100%;
  height: 40px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  font-size: 14px;
  color: #222;
  outline: none;
  padding: 0 12px;
  box-sizing: border-box;
  background: #fafafa;
  transition: border-color .15s, background .15s;
}
.input:focus {
  border-color: #B22222;
  background: #fff;
}
.input::placeholder { color: #bbb; }

.error {
  background: #FFF0F0;
  color: #B22222;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  margin-bottom: 12px;
}

.submit {
  width: 100%;
  height: 44px;
  background: #B22222;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  border: none;
  border-radius: 6px;
  margin-top: 8px;
  cursor: pointer;
  transition: background .15s;
}
.submit:hover { background: #8B0000; }
.submit:disabled { opacity: 0.6; cursor: not-allowed; }

/* ============ PC 端 ============ */
@media (min-width: 768px) {
  .login-page {
    background: linear-gradient(135deg, #B22222 0%, #8B0000 100%);
  }
  .login-bg {
    display: none;  /* PC 端红色铺满整页，logo 和 form 居中显示 */
  }
  .login-shell {
    flex-direction: row;
    align-items: center;
    justify-content: center;
    padding: 32px;
    gap: 64px;
  }
  .hero {
    color: #fff;
    text-align: left;
    padding: 0;
    flex: 0 0 auto;
  }
  .brand {
    font-size: 48px;
    letter-spacing: 4px;
  }
  .hero-logo {
    width: 140px;
    height: 140px;
    margin-bottom: 24px;
  }
  .form-card {
    margin-top: 0;
    max-width: 400px;
    padding: 32px 32px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.18);
  }
  .form-title {
    font-size: 18px;
    margin-bottom: 24px;
  }
  .field { margin-bottom: 18px; }
  .input { height: 44px; font-size: 15px; }
  .submit { height: 48px; font-size: 16px; margin-top: 12px; }
  .tips { font-size: 12px; margin-top: 16px; }
}

/* ============ 大屏 PC (>1200px) ============ */
@media (min-width: 1200px) {
  .brand { font-size: 56px; }
  .subtitle { font-size: 18px; }
  .form-card { max-width: 440px; padding: 40px 36px; }
}
</style>
