<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast } from 'vant'
import { activitiesApi, type Participant, type Attachment } from '@/api/activities'
import { orgsApi, type Branch, type Community } from '@/api/orgs'
import { dictsApi, type DictItem } from '@/api/dicts'
import { useAuthStore } from '@/stores/auth'
import MemberPicker from '@/components/MemberPicker.vue'

const auth = useAuthStore()
const router = useRouter()

const props = defineProps<{ id?: string }>()
const isEdit = computed(() => !!props.id)

const form = ref({
  organizer_branch_id: 0,
  training_at: '',
  training_time: '',
  location: '',
  lecturer_name: '',
  lecturer_bio: '',
  theme: '',
  participant_count: 0,
  online_offline: 'offline' as 'online' | 'offline' | 'hybrid',
  is_centralized: true,
  is_innovation_theory: true,
  source_type: 'self_organize' as 'upper_send' | 'self_organize',
  audience_category: 'community_member',
  study_hours: null as number | null,
})

const communities = ref<Community[]>([])
const branches = ref<Branch[]>([])
const categories = ref<DictItem[]>([])
const sources = ref<DictItem[]>([])

const selectedMemberIds = ref<number[]>([])
const photoList = ref<Attachment[]>([])
const signinList = ref<Attachment[]>([])

const errorMsg = ref('')
const submitting = ref(false)

async function loadOrgs() {
  try {
    if (auth.user?.street_id) {
      communities.value = await orgsApi.communities(auth.user.street_id)
    }
    branches.value = await orgsApi.branches()
    if (auth.user?.branch_id) {
      form.value.organizer_branch_id = auth.user.branch_id
    } else if (branches.value.length) {
      form.value.organizer_branch_id = branches.value[0].id
    }
  } catch (e) {
    console.warn('loadOrgs failed', e)
  }
}

async function loadDicts() {
  try {
    categories.value = await dictsApi.trainingCategories()
    sources.value = await dictsApi.trainingSources()
  } catch (e) {
    console.warn('loadDicts failed', e)
  }
}

// 编辑模式：加载已有活动数据
async function loadActivity(id: number) {
  try {
    const a = await activitiesApi.get(id)
    form.value.organizer_branch_id = a.organizer_branch_id
    // 从 ISO datetime 拆分日期和时间
    const dt = new Date(a.training_at)
    form.value.training_at = dt.toISOString().slice(0, 10)
    form.value.training_time = `${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`
    form.value.location = a.location
    form.value.lecturer_name = a.lecturer_name || ''
    form.value.lecturer_bio = a.lecturer_bio || ''
    form.value.theme = a.theme
    form.value.participant_count = a.participant_count
    form.value.online_offline = a.online_offline as any
    form.value.is_centralized = a.is_centralized
    form.value.is_innovation_theory = a.is_innovation_theory
    form.value.source_type = a.source_type as any
    form.value.audience_category = a.audience_category
    form.value.study_hours = a.study_hours
    // 关键：把已有 participants 同步给 selectedMemberIds，否则 MemberPicker 是空
    if (a.participants && a.participants.length) {
      selectedMemberIds.value = a.participants.map(p => p.member_id)
    }
    // 已有附件：直接回显到 photoList / signinList（带 id 标记），
    // 用户可以自由增删；提交时按 id 区分"保留 / 新增 / 删除"
    if (a.attachments && a.attachments.length) {
      const existingPhotos = a.attachments.filter(at => at.kind === 'photo')
      const existingSignin = a.attachments.filter(at => at.kind === 'signin')
      photoList.value = existingPhotos.map((p, i) => ({
        id: p.id,
        kind: 'photo',
        file_url: p.file_url,
        sort: i,
      }))
      signinList.value = existingSignin.map((p, i) => ({
        id: p.id,
        kind: 'signin',
        file_url: p.file_url,
        sort: i,
      }))
      // 记录原始文件名（用 id 兜底）
      for (const p of existingPhotos) {
        if (!fileNames.has(p.file_url)) {
          fileNames.set(p.file_url, `照片-${p.id}`)
        }
      }
      for (const s of existingSignin) {
        if (!fileNames.has(s.file_url)) {
          fileNames.set(s.file_url, `附件-${s.id}`)
        }
      }
    }
  } catch (e: any) {
    showToast({ message: '加载活动失败', type: 'fail' })
    router.back()
  }
}

const communityForBranch = (branchId: number) => {
  const b = branches.value.find((x) => x.id === branchId)
  if (!b) return ''
  return communities.value.find((c) => c.id === b.community_id)?.name || ''
}

// ===== 日期选择：Vant van-date-picker（年/月/日 3 滚轮，跟人员管理器一致） =====
const showDatePicker = ref(false)
const datePickerValue = ref<string[]>([])

const displayDate = computed(() => {
  if (!form.value.training_at) return ''
  const [y, m, d] = form.value.training_at.split('-')
  return `${y}年${Number(m)}月${Number(d)}日`
})

function openDatePicker() {
  const n = new Date()
  let y = n.getFullYear(), m = n.getMonth() + 1, d = n.getDate()
  if (form.value.training_at) {
    const [yy, mm, dd] = form.value.training_at.split('-')
    y = +yy; m = +mm; d = +dd
  }
  datePickerValue.value = [String(y), String(m).padStart(2, '0'), String(d).padStart(2, '0')]
  showDatePicker.value = true
}

function onDatePickerConfirm({ selectedValues }: { selectedValues: string[] }) {
  const [y, m, d] = selectedValues
  form.value.training_at = `${y}-${m}-${d}`
  showDatePicker.value = false
}

// 切年/月时若当前日超出新月最大天数，重置到 1 号
watch(datePickerValue, (v) => {
  if (!v || v.length !== 3) return
  const y = +v[0], m = +v[1], d = +v[2]
  const lastDay = new Date(y, m, 0).getDate()
  if (d > lastDay) {
    datePickerValue.value = [v[0], v[1], '01']
  }
})

// ===== 时间选择 =====
const showTimePicker = ref(false)
const timePickerValue = ref<string[]>(['09', '00'])
function openTimePicker() {
  if (form.value.training_time) {
    const [h, m] = form.value.training_time.split(':')
    timePickerValue.value = [h, m]
  }
  showTimePicker.value = true
}
function onTimeConfirm({ selectedValues }: { selectedValues: string[] }) {
  form.value.training_time = selectedValues.join(':')
  showTimePicker.value = false
}

// ===== 举办支部（action-sheet 列表，PC 友好） =====
const showBranchPicker = ref(false)
const branchActions = computed(() =>
  branches.value.map((b) => ({
    name: b.name,
    subname: communityForBranch(b.id),
    value: b.id,
  })),
)
const selectedBranchName = computed(() => {
  if (!form.value.organizer_branch_id) return ''
  const b = branches.value.find((x) => x.id === form.value.organizer_branch_id)
  if (!b) return ''
  return `${b.name} / ${communityForBranch(b.id)}`
})
function onBranchSelect(action: { value: number }) {
  form.value.organizer_branch_id = action.value
}

// ===== 字典项的 chip 行 =====
// 来源的合法 code（后端 schema 用 Literal 限定，避免字典里混入脏数据导致 422）
const ALLOWED_SOURCE_CODES = ['upper_send', 'self_organize']
const onlineOfflineOptions = [
  { v: 'online', l: '线上' },
  { v: 'offline', l: '线下' },
  { v: 'hybrid', l: '混合' },
]

// ===== 参加人员 =====
function onMemberChange(ids: number[]) {
  selectedMemberIds.value = ids
  form.value.participant_count = ids.length
}

// ===== 上传图片 =====
function onAddPhoto() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = (e: any) => {
    const f = e.target.files?.[0]
    if (!f) return
    const reader = new FileReader()
    reader.onload = () => {
      photoList.value.push({
        kind: 'photo',
        file_url: reader.result as string,
        sort: photoList.value.length,
      })
    }
    reader.readAsDataURL(f)
  }
  input.click()
}
function onAddSignin() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.doc,.docx,.xls,.xlsx,.txt,.pdf,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/plain,image/*'
  input.onchange = (e: any) => {
    const f = e.target.files?.[0]
    if (!f) return
    const reader = new FileReader()
    reader.onload = () => {
      const url = reader.result as string
      signinList.value.push({ kind: 'signin', file_url: url, sort: signinList.value.length })
      fileNames.set(url, f.name)
    }
    reader.readAsDataURL(f)
  }
  input.click()
}
function removePhoto(i: number) { photoList.value.splice(i, 1) }
function removeSignin(i: number) { signinList.value.splice(i, 1) }

// 附件文件元信息（按 dataURL 索引原始文件名）
const fileNames = new Map<string, string>()

// 附件文件图标
function fileIcon(url: string): string {
  if (url.startsWith('data:application/pdf')) return '📄'
  if (url.includes('spreadsheet') || url.includes('ms-excel')) return '📊'
  if (url.includes('wordprocessingml') || url.includes('msword')) return '📝'
  if (url.startsWith('data:text/plain')) return '📃'
  return '📎'
}
function fileName(url: string): string {
  return fileNames.get(url) || '附件'
}

// ===== 提交 =====
function validate(asDraft: boolean): string {
  if (!form.value.organizer_branch_id) return '请选择举办支部'
  if (!form.value.training_at) return '请选择培训日期'
  if (!form.value.training_time) return '请选择培训时间'
  if (!form.value.location.trim()) return '请填写培训地点'
  if (!form.value.theme.trim()) return '请填写主题'
  if (selectedMemberIds.value.length < 1) return '请选择参加人员'
  // 草稿模式下学时和现场照片都不强制
  if (!asDraft) {
    if (form.value.study_hours === null || form.value.study_hours === undefined || form.value.study_hours <= 0) {
      return '请填写学时'
    }
    if (!isEdit.value && photoList.value.length < 1) return '请至少上传 1 张现场照片'
  }
  return ''
}

async function onSave(asDraft: boolean) {
  console.log('[save] start, isEdit=', isEdit.value, 'asDraft=', asDraft, 'members=', selectedMemberIds.value.length, 'photos=', photoList.value.length, 'att=', signinList.value.length)
  errorMsg.value = validate(asDraft)
  if (errorMsg.value) {
    showToast({ message: errorMsg.value, type: 'fail' })
    return
  }
  submitting.value = true
  try {
    const trainingAt = `${form.value.training_at}T${form.value.training_time}:00`
    const participants: Participant[] = selectedMemberIds.value.map((mid) => ({
      member_id: mid,
      // 草稿模式下学时可空；非草稿至少有 1
      study_hours: form.value.study_hours ?? null,
      attendance_status: 'signed',
    }))

    // 兜底：v-model.number 清空时会存空字符串，转成 null（草稿模式）
    // 非草稿时 validate() 已经拦住，不会到这里
    const rawHours = form.value.study_hours
    const studyHoursNum: number | null =
      (rawHours === null || rawHours === undefined || rawHours === '' || Number.isNaN(Number(rawHours)))
        ? null
        : Number(rawHours)

    const body = {
      organizer_branch_id: form.value.organizer_branch_id,
      training_at: trainingAt,
      location: form.value.location,
      lecturer_name: form.value.lecturer_name || null,
      lecturer_bio: form.value.lecturer_bio || null,
      theme: form.value.theme,
      participant_count: form.value.participant_count,
      online_offline: form.value.online_offline,
      is_centralized: form.value.is_centralized,
      is_innovation_theory: form.value.is_innovation_theory,
      source_type: form.value.source_type,
      audience_category: form.value.audience_category,
      study_hours: studyHoursNum,
      participants: selectedMemberIds.value.map((mid) => ({
        member_id: mid,
        study_hours: studyHoursNum,
        attendance_status: 'signed',
      })),
      photo_count: photoList.value.length,
    }

    if (isEdit.value) {
      // 编辑模式：更新已有活动
      const aid = Number(props.id)
      console.log('[edit] PATCH body:', JSON.stringify(body, null, 2))
      try {
        await activitiesApi.update(aid, body as any)
        console.log('[edit] PATCH OK')
      } catch (e: any) {
        console.error('[edit] PATCH failed:', e?.message, e)
        throw e
      }
      // 附件处理：按 id 区分保留 / 新增 / 删除
      // 拉一次最新详情，拿到原附件 id 集合
      const latest = await activitiesApi.get(aid)
      const origPhotoIds = new Set(
        (latest.attachments || []).filter(at => at.kind === 'photo').map(at => at.id)
      )
      const origSigninIds = new Set(
        (latest.attachments || []).filter(at => at.kind === 'signin').map(at => at.id)
      )
      const keptPhotoIds = new Set(photoList.value.filter(p => p.id).map(p => p.id!))
      const keptSigninIds = new Set(signinList.value.filter(s => s.id).map(s => s.id!))
      try {
        // 删除被用户删掉的旧附件
        for (const id of origPhotoIds) {
          if (!keptPhotoIds.has(id)) {
            await activitiesApi.removeAttachment(aid, id)
          }
        }
        for (const id of origSigninIds) {
          if (!keptSigninIds.has(id)) {
            await activitiesApi.removeAttachment(aid, id)
          }
        }
        // 上传新增的附件
        for (const p of photoList.value.filter(p => !p.id)) {
          await activitiesApi.addAttachment(aid, { kind: 'photo', file_url: p.file_url, sort: p.sort })
        }
        for (const s of signinList.value.filter(s => !s.id)) {
          await activitiesApi.addAttachment(aid, { kind: 'signin', file_url: s.file_url, sort: s.sort })
        }
      } catch (e: any) {
        console.error('[edit] attachment sync failed:', e)
      }
      if (!asDraft) {
        await activitiesApi.submit(aid)
        showSuccessToast({ message: '已更新并提交审核' })
      } else {
        showSuccessToast({ message: '草稿已更新' })
      }
    } else {
      // 新增模式
      const created = await activitiesApi.create(body as any)
      for (const att of [...photoList.value, ...signinList.value]) {
        await activitiesApi.addAttachment(created.id, {
          kind: att.kind,
          file_url: att.file_url,
          sort: att.sort,
        })
      }
      if (!asDraft) {
        await activitiesApi.submit(created.id)
        showSuccessToast({ message: '已提交审核' })
      } else {
        showSuccessToast({ message: '草稿已保存' })
      }
    }
    setTimeout(() => router.back(), 800)
  } catch (e: any) {
    errorMsg.value = e?.message || '保存失败'
    showToast({ message: errorMsg.value, type: 'fail' })
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  loadOrgs()
  loadDicts()
  if (isEdit.value) {
    await loadActivity(Number(props.id))
  }
})
</script>

<template>
  <div class="form-page">
    <div class="page-header">
      <div class="back" @click="router.back()">‹ 返回</div>
      <div class="title">{{ isEdit ? '编辑培训' : '录入培训' }}</div>
    </div>

    <van-form @submit="onSave(false)">
      <van-cell-group inset title="基础信息" class="cell-group">
        <van-field
          :model-value="selectedBranchName"
          label="举办支部"
          placeholder="点击选择"
          readonly
          is-link
          required
          :rules="[{ required: true, message: '请选择举办支部' }]"
          @click="showBranchPicker = true"
        />
        <van-field label="培训日期" required>
          <template #input>
            <button type="button" class="date-btn" @click.prevent="openDatePicker">
              {{ displayDate || '点击选择日期' }}
            </button>
          </template>
        </van-field>
        <van-field
          :model-value="form.training_time"
          label="时间"
          placeholder="点击选择"
          readonly
          is-link
          required
          :rules="[{ required: true, message: '请选择时间' }]"
          @click="openTimePicker"
        />
        <van-field
          v-model="form.location"
          label="培训地点"
          placeholder="如：南湾街道6楼会议室"
          maxlength="255"
          required
          :rules="[{ required: true, message: '请填写培训地点' }]"
        />
        <van-field
          v-model="form.theme"
          label="主题"
          placeholder="培训主题"
          maxlength="255"
          required
          :rules="[{ required: true, message: '请填写主题' }]"
        />
        <van-field
          v-model="form.lecturer_name"
          label="讲师"
          placeholder="直接输入讲师姓名，如：王教授"
          maxlength="64"
        />
        <van-field
          v-model="form.lecturer_bio"
          label="讲师简介"
          type="textarea"
          rows="3"
          autosize
          maxlength="500"
          show-word-limit
          placeholder="选填，可介绍讲师背景、擅长方向等（最多 500 字）"
        />
      </van-cell-group>

      <van-cell-group inset class="cell-group">
        <template #title><span class="req">*</span> 培训属性</template>
        <van-cell>
          <template #title><span class="req">*</span> 线上/线下</template>
          <template #value>
            <van-radio-group v-model="form.online_offline" direction="horizontal">
              <van-radio v-for="o in onlineOfflineOptions" :key="o.v" :name="o.v">{{ o.l }}</van-radio>
            </van-radio-group>
          </template>
        </van-cell>
        <van-cell>
          <template #title><span class="req">*</span> 集中学习</template>
          <template #value>
            <van-radio-group v-model="form.is_centralized" direction="horizontal">
              <van-radio :name="true">是</van-radio>
              <van-radio :name="false">否</van-radio>
            </van-radio-group>
          </template>
        </van-cell>
        <van-cell>
          <template #title><span class="req">*</span> 创新理论教育</template>
          <template #value>
            <van-radio-group v-model="form.is_innovation_theory" direction="horizontal">
              <van-radio :name="true">是</van-radio>
              <van-radio :name="false">否</van-radio>
            </van-radio-group>
          </template>
        </van-cell>
        <van-cell>
          <template #title><span class="req">*</span> 来源</template>
          <template #value>
            <van-radio-group v-model="form.source_type" direction="horizontal">
              <van-radio
                v-for="s in sources.filter((x) => ALLOWED_SOURCE_CODES.includes(x.code))"
                :key="s.code"
                :name="s.code"
              >{{ s.name }}</van-radio>
            </van-radio-group>
          </template>
        </van-cell>
        <van-cell>
          <template #title><span class="req">*</span> 培训对象</template>
          <template #value>
            <van-radio-group v-model="form.audience_category" direction="horizontal">
              <van-radio v-for="c in categories" :key="c.code" :name="c.code">{{ c.name }}</van-radio>
            </van-radio-group>
          </template>
        </van-cell>
        <van-field
          v-model.number="form.study_hours"
          label="学时"
          type="digit"
          placeholder="如 4"
          required
        />
      </van-cell-group>

      <van-cell-group inset class="cell-group">
        <template #title><span class="req">*</span> 参加人员</template>
        <div class="picker-cell">
          <MemberPicker v-model="selectedMemberIds" :branch-id="form.organizer_branch_id" @change="onMemberChange" />
        </div>
      </van-cell-group>

      <van-cell-group inset class="cell-group">
        <template #title><span class="req">*</span> 现场照片</template>
        <van-cell title="至少 1 张，最多 9 张">
          <template #value>
            <van-button size="mini" type="primary" plain hairline @click="onAddPhoto">
              + 添加
            </van-button>
          </template>
        </van-cell>
        <div v-if="photoList.length" class="upload-grid">
          <div v-for="(p, i) in photoList" :key="i" class="upload-item">
            <img :src="p.file_url" class="thumb" />
            <div class="remove" @click="removePhoto(i)">×</div>
          </div>
        </div>
      </van-cell-group>

      <van-cell-group inset class="cell-group">
        <template #title>附件（签到表或活动通知，可选）</template>
        <van-cell title="最多 9 个，支持 Word/Excel/TXT/PDF/图片">
          <template #value>
            <van-button size="mini" type="primary" plain hairline @click="onAddSignin">
              + 添加
            </van-button>
          </template>
        </van-cell>
        <div v-if="signinList.length" class="upload-grid">
          <div v-for="(p, i) in signinList" :key="i" class="upload-item">
            <div v-if="p.file_url.startsWith('data:image')" class="thumb-wrap">
              <img :src="p.file_url" class="thumb" />
              <div class="remove" @click="removeSignin(i)">×</div>
            </div>
            <div v-else class="file-card">
              <div class="file-icon">{{ fileIcon(p.file_url) }}</div>
              <div class="file-name">{{ fileName(p.file_url) }}</div>
              <div class="remove" @click="removeSignin(i)">×</div>
            </div>
          </div>
        </div>
      </van-cell-group>

      <div class="actions">
        <van-button
          block
          plain
          hairline
          type="primary"
          :loading="submitting"
          :disabled="submitting"
          @click="onSave(true)"
        >
          保存草稿
        </van-button>
        <van-button
          block
          type="primary"
          :loading="submitting"
          :disabled="submitting"
          @click="onSave(false)"
        >
          提交审核
        </van-button>
      </div>
    </van-form>

    <!-- 培训日期 picker（Vant van-date-picker，跟人员管理器一致） -->
    <van-popup v-model:show="showDatePicker" position="bottom" round>
      <van-date-picker
        v-model="datePickerValue"
        :columns-type="['year', 'month', 'day']"
        :min-date="new Date(2000, 0, 1)"
        :max-date="new Date(new Date().getFullYear() + 5, 11, 31)"
        title="选择培训日期"
        @confirm="onDatePickerConfirm"
        @cancel="showDatePicker = false"
      />
    </van-popup>

    <!-- 时间 -->
    <van-popup v-model:show="showTimePicker" position="bottom" round>
      <van-time-picker
        v-model="timePickerValue"
        title="选择时间"
        @confirm="onTimeConfirm"
        @cancel="showTimePicker = false"
      />
    </van-popup>

    <!-- 支部（action-sheet） -->
    <van-action-sheet
      v-model:show="showBranchPicker"
      :actions="branchActions"
      cancel-text="取消"
      close-on-click-action
      @select="onBranchSelect"
    />
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
.picker-cell { padding: 12px 16px; }

.actions {
  display: flex;
  gap: 8px;
  padding: 20px 16px 0;
}
.actions > * { flex: 1; }

.upload-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 0 16px 16px;
}
.upload-item {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  border-radius: 4px;
  overflow: hidden;
  background: #f5f5f5;
}
.thumb { width: 100%; height: 100%; object-fit: cover; }
.thumb-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  border-radius: 4px;
  overflow: hidden;
  background: #f5f5f5;
}
.thumb-wrap .thumb { position: absolute; inset: 0; }

.file-card {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  border-radius: 4px;
  background: #FFF0F0;
  border: 1px dashed #B22222;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 6px;
  overflow: hidden;
}
.file-icon { font-size: 32px; line-height: 1; margin-bottom: 4px; }
.file-name {
  font-size: 11px;
  color: #555;
  text-align: center;
  word-break: break-all;
  line-height: 1.2;
  max-height: 2.4em;
  overflow: hidden;
}
.remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 22px;
  height: 22px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}

:deep(.van-cell-group--inset) {
  margin-left: 0;
  margin-right: 0;
  overflow: hidden;
}
:deep(.van-field__label),
:deep(.van-cell__title) {
  color: #666;
  min-width: 5.5em;
}

/* 必填红*：用 span.req 包住，CSS 染色 */
.req {
  color: #ee0a24;
  font-size: 14px;
  margin-right: 2px;
  font-weight: 600;
}
/* 组标题里的 * 也变红 */
.cell-group :deep(.van-cell-group__title) .req {
  color: #ee0a24;
}
.existing-tip {
  font-size: 12px;
  color: #FA8C16;
  background: #FFF7E6;
  padding: 8px 16px;
  border-bottom: 1px solid #FFE7BA;
}

/* 日期按钮：原生 button 确保 click 可靠 */
.date-btn {
  width: 100%;
  border: none;
  background: none;
  font: inherit;
  font-size: 14px;
  color: #333;
  text-align: left;
  padding: 0;
  cursor: pointer;
  outline: none;
}
.date-btn:empty::after {
  content: '点击选择日期';
  color: #c8c9cc;
}
</style>
