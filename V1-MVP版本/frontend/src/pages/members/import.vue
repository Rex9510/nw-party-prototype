<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast } from 'vant'
import { orgsApi, type Branch, type Community } from '@/api/orgs'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const branches = ref<Branch[]>([])
const communities = ref<Community[]>([])
const defaultBranchId = ref(0)
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

const branchColumns = computed(() => branches.value.map((b) => ({ text: b.name, value: b.id })))
const selectedBranchIndex = computed(() =>
  branches.value.findIndex((b) => b.id === defaultBranchId.value),
)
const selectedBranchName = computed(() => {
  return branches.value.find((b) => b.id === defaultBranchId.value)?.name || '请选择'
})

const showBranchPicker = ref(false)
function onBranchConfirm({ selectedOptions }: { selectedOptions: Array<{ text: string; value: number }> }) {
  defaultBranchId.value = selectedOptions[0]?.value || 0
  showBranchPicker.value = false
}

function onPickFile() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.xlsx,.xls'
  input.onchange = async (e: any) => {
    const f = e.target.files?.[0]
    if (f) await doUpload(f)
  }
  input.click()
}

async function doUpload(file: File) {
  if (!defaultBranchId.value) {
    showToast({ message: '请先选择默认支部', type: 'fail' })
    return
  }
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('default_branch_id', String(defaultBranchId.value))

    const r = await fetch('/api/v1/members/import', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${auth.token}`,
      },
      body: formData,
    })
    const res = await r.json()
    totalRows.value = res.total_rows || 0
    successRows.value = res.success_rows || 0
    failedRows.value = res.failed_rows || 0
    errorLog.value = res.error_log || []
    if (res.failed_rows === 0) {
      showSuccessToast({ message: '导入成功' })
    } else {
      showToast({ message: `部分失败：成功 ${res.success_rows} / 失败 ${res.failed_rows}`, type: 'fail' })
    }
  } catch (e: any) {
    showToast({ message: e?.message || '导入失败', type: 'fail' })
  } finally {
    importing.value = false
  }
}

function onDownloadTemplate() {
  const token = auth.token
  const url = `/api/v1/members/template?access_token=${token}`
  window.open(url, '_blank')
}

onMounted(() => {
  loadBranches()
})
</script>

<template>
  <div class="form-page">
    <div class="page-header">
      <div class="back" @click="router.back()">‹ 返回</div>
      <div class="title">批量导入人员</div>
    </div>

    <van-cell-group inset title="操作步骤" class="cell-group">
      <van-cell title="1. 下载导入模板（xlsx）" />
      <van-cell title="2. 按模板填入人员信息" />
      <van-cell title="3. 选择默认支部 + 上传文件" />
      <div class="cell-actions">
        <van-button size="small" type="primary" plain hairline @click="onDownloadTemplate">
          下载模板
        </van-button>
      </div>
    </van-cell-group>

    <van-cell-group inset title="选择默认支部" class="cell-group">
      <van-field
        v-if="branches.length"
        :model-value="selectedBranchName"
        label="默认支部"
        placeholder="请选择"
        readonly
        is-link
        @click="showBranchPicker = true"
      />
    </van-cell-group>

    <van-cell-group inset title="上传文件" class="cell-group">
      <van-cell title="支持 .xlsx / .xls，单次最多 1000 行" />
      <div class="cell-actions">
        <van-button
          block
          type="primary"
          :loading="importing"
          :disabled="importing"
          @click="onPickFile"
        >
          {{ importing ? '导入中…' : '选择 xlsx 文件' }}
        </van-button>
      </div>
    </van-cell-group>

    <div v-if="totalRows" class="result-card">
      <div class="result-title">导入结果</div>
      <div class="result-row">
        <div class="result-item">
          <div class="num">{{ totalRows }}</div>
          <div class="label">总数</div>
        </div>
        <div class="result-item success">
          <div class="num">{{ successRows }}</div>
          <div class="label">成功</div>
        </div>
        <div class="result-item failed">
          <div class="num">{{ failedRows }}</div>
          <div class="label">失败</div>
        </div>
      </div>
      <div v-if="errorLog.length" class="error-list">
        <div class="error-title">错误明细：</div>
        <div v-for="(e, i) in errorLog" :key="i" class="error-item">
          第 {{ e.row }} 行: {{ e.errors?.join('; ') }}
        </div>
      </div>
    </div>

    <!-- 支部选择 -->
    <van-popup v-model:show="showBranchPicker" position="bottom" round>
      <van-picker
        :columns="branchColumns"
        :model-value="[selectedBranchIndex >= 0 ? selectedBranchIndex : 0]"
        title="选择默认支部"
        @confirm="onBranchConfirm"
        @cancel="showBranchPicker = false"
      />
    </van-popup>
  </div>
</template>

<style scoped>
.form-page {
  max-width: 720px;
  margin: 0 auto;
  padding: 16px 0 32px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 4px 16px 16px;
}
.back {
  color: var(--primary);
  font-size: 15px;
  cursor: pointer;
  user-select: none;
}
.title {
  font-size: 18px;
  font-weight: 700;
  color: #222;
}

.cell-group { margin-bottom: 12px; }
.cell-actions {
  padding: 12px 16px 16px;
}

.result-card {
  background: #fff;
  border-radius: 8px;
  margin: 12px 16px;
  padding: 16px;
}
.result-title {
  font-size: 16px;
  font-weight: 600;
  color: #222;
  margin-bottom: 12px;
}
.result-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.result-item {
  flex: 1;
  text-align: center;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 6px;
}
.result-item.success { background: #ECFDF5; }
.result-item.failed { background: #FFF0F0; }
.num { font-size: 24px; font-weight: 700; color: #222; }
.result-item.success .num { color: #059669; }
.result-item.failed .num { color: #B22222; }
.label { font-size: 12px; color: #888; margin-top: 2px; }

.error-list { margin-top: 12px; padding-top: 12px; border-top: 1px solid #f0f0f0; }
.error-title { font-size: 13px; color: var(--primary); font-weight: 600; margin-bottom: 8px; }
.error-item {
  font-size: 13px;
  color: #666;
  padding: 4px 0;
}
</style>
