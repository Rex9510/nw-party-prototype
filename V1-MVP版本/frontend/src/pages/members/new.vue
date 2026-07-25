<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { membersApi } from '@/api/members'
import { orgsApi, type Branch, type Community } from '@/api/orgs'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const form = ref({
  name: '',
  phone: '',
  id_card_no: '',
  gender: '' as '' | 'male' | 'female' | 'other',
  join_date: '',
  branch_id: 0,
})
const submitting = ref(false)
const errorMsg = ref('')

const communities = ref<Community[]>([])
const branches = ref<Branch[]>([])
const filteredBranches = computed(() => {
  if (!form.value.branch_id) {
    // 默认按用户所属社区过滤
    if (auth.user?.community_id) {
      return branches.value.filter((b) => b.community_id === auth.user!.community_id)
    }
  }
  return branches.value
})

async function loadOrgs() {
  try {
    if (auth.user?.street_id) {
      communities.value = await orgsApi.communities(auth.user.street_id)
    }
    branches.value = await orgsApi.branches()
  } catch (e) {
    console.warn('loadOrgs failed', e)
  }
}

const communityForBranch = (branchId: number) => {
  const b = branches.value.find((x) => x.id === branchId)
  if (!b) return ''
  const c = communities.value.find((x) => x.id === b.community_id)
  return c?.name || ''
}

function validate(): string {
  if (!form.value.name.trim()) return '请输入姓名'
  if (!/^1[3-9]\d{9}$/.test(form.value.phone)) return '手机号格式错误'
  if (form.value.id_card_no && !/^\d{17}[\dXx]$/.test(form.value.id_card_no)) return '身份证号格式错误'
  if (!form.value.branch_id) return '请选择支部'
  return ''
}

async function onSubmit() {
  errorMsg.value = validate()
  if (errorMsg.value) return

  submitting.value = true
  try {
    await membersApi.create({
      name: form.value.name.trim(),
      phone: form.value.phone,
      id_card_no: form.value.id_card_no || undefined,
      gender: form.value.gender || undefined,
      join_date: form.value.join_date || undefined,
      branch_id: form.value.branch_id,
    })
    uni.showToast({ title: '新增成功', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 800)
  } catch (e: any) {
    errorMsg.value = e?.message || '新增失败'
  } finally {
    submitting.value = false
  }
}

function onPickBranch(e: any) {
  const idx = e.detail.value as number
  form.value.branch_id = filteredBranches.value[idx]?.id || 0
}

onMounted(() => {
  loadOrgs()
})
</script>

<template>
  <view class="page">
    <view class="form">
      <view class="field">
        <text class="label">姓名 *</text>
        <input v-model="form.name" class="input" placeholder="请输入党员姓名" maxlength="64" />
      </view>

      <view class="field">
        <text class="label">手机号 *</text>
        <input
          v-model="form.phone"
          class="input"
          type="number"
          maxlength="11"
          placeholder="11位手机号"
        />
      </view>

      <view class="field">
        <text class="label">身份证号</text>
        <input
          v-model="form.id_card_no"
          class="input"
          maxlength="18"
          placeholder="可选，18位"
        />
      </view>

      <view class="field">
        <text class="label">性别</text>
        <view class="gender-row">
          <view
            v-for="g in [{ v: 'male', l: '男' }, { v: 'female', l: '女' }, { v: 'other', l: '其他' }]"
            :key="g.v"
            class="chip"
            :class="{ active: form.gender === g.v }"
            @click="form.gender = g.v as any"
          >
            {{ g.l }}
          </view>
        </view>
      </view>

      <view class="field">
        <text class="label">入党时间</text>
        <picker mode="date" :value="form.join_date" @change="(e: any) => form.join_date = e.detail.value">
          <view class="picker-input">{{ form.join_date || '选择日期' }}</view>
        </picker>
      </view>

      <view class="field">
        <text class="label">所属支部 *</text>
        <picker
          v-if="filteredBranches.length"
          :value="form.branch_id ? filteredBranches.findIndex((b) => b.id === form.branch_id) : 0"
          :range="filteredBranches.map((b) => b.name + ' / ' + communityForBranch(b.id))"
          @change="onPickBranch"
        >
          <view class="picker-input">
            {{ filteredBranches.find((b) => b.id === form.branch_id)?.name || '请选择支部' }}
          </view>
        </picker>
        <view v-else class="picker-input empty">暂无可选支部</view>
      </view>

      <view v-if="errorMsg" class="error">{{ errorMsg }}</view>

      <button
        class="submit"
        :loading="submitting"
        :disabled="submitting"
        @click="onSubmit"
      >
        保存
      </button>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  background: #F7F8FA;
  padding: 24rpx;
}
.form {
  background: #fff;
  border-radius: 16rpx;
  padding: 32rpx 28rpx;
}
.field {
  margin-bottom: 32rpx;
  border-bottom: 1rpx solid #f0f0f0;
  padding-bottom: 20rpx;
}
.field:last-of-type { border-bottom: none; }
.label {
  display: block;
  font-size: 26rpx;
  color: #666;
  margin-bottom: 12rpx;
}
.input {
  width: 100%;
  height: 72rpx;
  font-size: 30rpx;
  color: #222;
}
.picker-input {
  width: 100%;
  height: 72rpx;
  line-height: 72rpx;
  font-size: 30rpx;
  color: #222;
}
.picker-input.empty { color: #ccc; }
.gender-row { display: flex; gap: 16rpx; }
.chip {
  padding: 12rpx 28rpx;
  background: #f5f5f5;
  color: #666;
  border-radius: 32rpx;
  font-size: 26rpx;
}
.chip.active {
  background: #B22222;
  color: #fff;
}
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
  margin-top: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}
.submit[disabled] { opacity: 0.6; }
</style>
