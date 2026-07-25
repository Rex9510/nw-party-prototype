<script setup lang="ts">
import { ref } from 'vue'
import { membersApi } from '@/api/members'
import { orgsApi, type Branch, type Community } from '@/api/orgs'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const branches = ref<Branch[]>([])
const communities = ref<Community[]>([])
const defaultBranchId = ref(0)
const fileUrl = ref('')
const totalRows = ref(0)
const successRows = ref(0)
const failedRows = ref(0)
const errorLog = ref<any[]>([])
const importing = ref(false)

async function loadBranches() {
  try {
    if (auth.user?.street_id) {
      communities.value = await orgsApi.communities(auth.user.street_id)
    }
    branches.value = await orgsApi.branches()
    if (auth.user?.branch_id) {
      defaultBranchId.value = auth.user.branch_id
    } else if (branches.value.length) {
      defaultBranchId.value = branches.value[0].id
    }
  } catch (e) {
    console.warn(e)
  }
}

function onPickFile() {
  // #ifdef H5
  uni.chooseFile 不会在 H5 自动用 file input，需要自己包
  // #endif
  uni.chooseMessageFile  // 选聊天文件
  // 简化：uni.chooseImage 不支持 xlsx，用 choosemessagefile
  // 实际：H5 下要用 input[type=file]
  // 这里我们用 uni.chooseFile 走兼容
  uni.chooseFile  // h5 默认会有
  // 跨平台：直接用 input 元素
}

const fileInputRef = ref<HTMLInputElement | null>(null)

function onPickFile2() {
  // H5 模式下直接打开 file dialog
  // #ifdef H5
  if (typeof document !== 'undefined') {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.xlsx,.xls'
    input.onchange = async (e: any) => {
      const file = e.target.files?.[0]
      if (file) await doUpload(file)
    }
    input.click()
  }
  // #endif
  // #ifndef H5
  uni.chooseMessageFile({
    count: 1,
    success: async (r) => {
      const f = r.tempFiles?.[0]
      if (f) await doUpload(f as any)
    },
  })
  // #endif
}

async function doUpload(file: File | { path: string; size: number; name?: string }) {
  if (!defaultBranchId.value) {
    uni.showToast({ title: '请先选择默认支部', icon: 'none' })
    return
  }
  importing.value = true
  try {
    // uni.uploadFile
    const res = await new Promise<any>((resolve, reject) => {
      uni.uploadFile({
        url: '/api/v1/members/import',
        filePath: (file as any).path || (file as any).tempFilePath,
        name: 'file',
        formData: { default_branch_id: String(defaultBranchId.value) },
        header: {
          Authorization: `Bearer ${auth.token}`,
        },
        success: (r) => {
          try {
            resolve(JSON.parse(r.data))
          } catch {
            reject(new Error('响应格式错误'))
          }
        },
        fail: (err) => reject(err),
      })
    })
    totalRows.value = res.total_rows || 0
    successRows.value = res.success_rows || 0
    failedRows.value = res.failed_rows || 0
    errorLog.value = res.error_log || []
    fileUrl.value = res.file_url || ''
    if (res.failed_rows === 0) {
      uni.showToast({ title: '导入成功', icon: 'success' })
    } else {
      uni.showToast({ title: `部分失败：成功 ${res.success_rows} / 失败 ${res.failed_rows}`, icon: 'none' })
    }
  } catch (e: any) {
    uni.showToast({ title: e?.message || '导入失败', icon: 'none' })
  } finally {
    importing.value = false
  }
}

function onDownloadTemplate() {
  // 后端导出模板 xlsx
  // #ifdef H5
  window.open(`/api/v1/members/template?access_token=${auth.token}`)
  // #endif
  // #ifndef H5
  uni.downloadFile({
    url: `/api/v1/members/template?access_token=${auth.token}`,
    success: (r) => {
      uni.openDocument({ filePath: r.tempFilePath })
    },
  })
  // #endif
}

import { onMounted } from 'vue'
onMounted(() => {
  loadBranches()
})
</script>

<template>
  <view class="page">
    <view class="card">
      <view class="card-title">操作步骤</view>
      <view class="step">1. 下载导入模板（xlsx）</view>
      <view class="step">2. 按模板填入党员信息</view>
      <view class="step">3. 选择默认支部 + 上传文件</view>
      <view class="btn btn-primary" @click="onDownloadTemplate">下载模板</view>
    </view>

    <view class="card">
      <view class="card-title">选择默认支部</view>
      <picker
        v-if="branches.length"
        :value="branches.findIndex((b) => b.id === defaultBranchId)"
        :range="branches.map((b) => b.name)"
        @change="(e: any) => defaultBranchId = branches[e.detail.value]?.id || 0"
      >
        <view class="picker-input">
          {{ branches.find((b) => b.id === defaultBranchId)?.name || '请选择' }}
        </view>
      </picker>
    </view>

    <view class="card">
      <view class="card-title">上传文件</view>
      <view class="btn btn-primary" :class="{ disabled: importing }" @click="onPickFile2">
        {{ importing ? '导入中…' : '选择 xlsx 文件' }}
      </view>
      <view class="hint">支持 .xlsx / .xls，单次最多 1000 行</view>
    </view>

    <view v-if="totalRows" class="card result">
      <view class="card-title">导入结果</view>
      <view class="result-row">
        <view class="result-item">
          <view class="num">{{ totalRows }}</view>
          <view class="label">总数</view>
        </view>
        <view class="result-item success">
          <view class="num">{{ successRows }}</view>
          <view class="label">成功</view>
        </view>
        <view class="result-item failed">
          <view class="num">{{ failedRows }}</view>
          <view class="label">失败</view>
        </view>
      </view>
      <view v-if="errorLog.length" class="error-list">
        <view class="error-title">错误明细：</view>
        <view v-for="(e, i) in errorLog" :key="i" class="error-item">
          第 {{ e.row }} 行: {{ e.errors?.join('; ') }}
        </view>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.page { min-height: 100vh; background: #F7F8FA; padding: 24rpx; }
.card {
  background: #fff;
  border-radius: 16rpx;
  padding: 28rpx 24rpx;
  margin-bottom: 20rpx;
}
.card-title { font-size: 30rpx; font-weight: 600; color: #222; margin-bottom: 16rpx; }
.step { font-size: 26rpx; color: #555; line-height: 1.8; }
.picker-input {
  height: 72rpx;
  line-height: 72rpx;
  font-size: 28rpx;
  color: #222;
  padding: 0 20rpx;
  background: #f5f5f5;
  border-radius: 10rpx;
}
.btn {
  display: block;
  text-align: center;
  height: 80rpx;
  line-height: 80rpx;
  font-size: 30rpx;
  font-weight: 600;
  border-radius: 12rpx;
  margin-top: 16rpx;
}
.btn-primary { background: #B22222; color: #fff; }
.btn-primary.disabled { opacity: 0.5; }
.hint { font-size: 22rpx; color: #888; margin-top: 8rpx; }

.result-row { display: flex; gap: 16rpx; margin: 16rpx 0; }
.result-item {
  flex: 1;
  text-align: center;
  padding: 20rpx;
  background: #f5f5f5;
  border-radius: 12rpx;
}
.result-item.success { background: #ECFDF5; }
.result-item.failed { background: #FFF0F0; }
.num { font-size: 40rpx; font-weight: 700; }
.result-item.success .num { color: #059669; }
.result-item.failed .num { color: #B22222; }
.label { font-size: 24rpx; color: #888; margin-top: 4rpx; }
.error-list { margin-top: 16rpx; }
.error-title { font-size: 26rpx; color: #B22222; font-weight: 600; margin-bottom: 8rpx; }
.error-item {
  font-size: 24rpx;
  color: #555;
  padding: 8rpx 0;
  border-bottom: 1rpx solid #f0f0f0;
}
</style>
