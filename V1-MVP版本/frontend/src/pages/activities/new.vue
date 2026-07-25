<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { activitiesApi, type Participant, type Attachment } from '@/api/activities'
import { orgsApi, type Branch, type Community, type Street } from '@/api/orgs'
import { dictsApi, type Lecturer, type DictItem } from '@/api/dicts'
import { membersApi, type MemberItem } from '@/api/members'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const form = ref({
  organizer_branch_id: 0,
  training_at: '',
  training_time: '09:00',
  location: '',
  lecturer_id: 0,
  theme: '',
  participant_count: 0,
  online_offline: 'offline' as 'online' | 'offline' | 'hybrid',
  is_centralized: true,
  is_innovation_theory: true,
  source_type: 'self_organize' as 'upper_send' | 'self_organize',
  audience_category: 'community_member',
  study_hours: 4.0,
})

const communities = ref<Community[]>([])
const branches = ref<Branch[]>([])
const filteredBranches = computed(() => {
  // 简单版：全显示
  return branches.value
})
const lecturers = ref<Lecturer[]>([])
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
    lecturers.value = await dictsApi.lecturers()
    categories.value = await dictsApi.trainingCategories()
    sources.value = await dictsApi.trainingSources()
  } catch (e) {
    console.warn('loadDicts failed', e)
  }
}

function validate(): string {
  if (!form.value.organizer_branch_id) return '请选择举办支部'
  if (!form.value.training_at) return '请选择培训日期'
  if (!form.value.location.trim()) return '请填写培训地点'
  if (!form.value.theme.trim()) return '请填写主题'
  if (form.value.study_hours <= 0) return '请填写学时'
  return ''
}

function onAddPhoto() {
  // H5 选图
  if (typeof document !== 'undefined') {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*'
    input.onchange = (e: any) => {
      const f = e.target.files?.[0]
      if (f) {
        // 简化：用 FileReader 拿到 dataURL 模拟上传
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
    }
    input.click()
  }
}

function onAddSignin() {
  if (typeof document !== 'undefined') {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*,application/pdf'
    input.onchange = (e: any) => {
      const f = e.target.files?.[0]
      if (f) {
        const reader = new FileReader()
        reader.onload = () => {
          signinList.value.push({
            kind: 'signin',
            file_url: reader.result as string,
            sort: signinList.value.length,
          })
        }
        reader.readAsDataURL(f)
      }
    }
    input.click()
  }
}

function removePhoto(i: number) {
  photoList.value.splice(i, 1)
}

function removeSignin(i: number) {
  signinList.value.splice(i, 1)
}

function onMemberChange(ids: number[]) {
  selectedMemberIds.value = ids
  form.value.participant_count = ids.length
}

async function onSave(asDraft: boolean) {
  errorMsg.value = validate()
  if (errorMsg.value) return

  submitting.value = true
  try {
    const trainingAt = `${form.value.training_at}T${form.value.training_time}:00`
    const participants: Participant[] = selectedMemberIds.value.map((mid) => ({
      member_id: mid,
      study_hours: form.value.study_hours,
      attendance_status: 'signed',
    }))

    const body = {
      organizer_branch_id: form.value.organizer_branch_id,
      training_at: trainingAt,
      location: form.value.location,
      lecturer_id: form.value.lecturer_id || null,
      theme: form.value.theme,
      participant_count: form.value.participant_count,
      online_offline: form.value.online_offline,
      is_centralized: form.value.is_centralized,
      is_innovation_theory: form.value.is_innovation_theory,
      source_type: form.value.source_type,
      audience_category: form.value.audience_category,
      study_hours: form.value.study_hours,
      participants,
      photo_count: photoList.value.length,
    }

    const created = await activitiesApi.create(body as any)
    // 上传附件
    for (const att of [...photoList.value, ...signinList.value]) {
      await activitiesApi.addAttachment(created.id, {
        kind: att.kind,
        file_url: att.file_url,
        sort: att.sort,
      })
    }

    if (!asDraft) {
      await activitiesApi.submit(created.id)
      uni.showToast({ title: '已提交审核', icon: 'success' })
    } else {
      uni.showToast({ title: '草稿已保存', icon: 'success' })
    }
    setTimeout(() => uni.navigateBack(), 800)
  } catch (e: any) {
    errorMsg.value = e?.message || '保存失败'
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadOrgs()
  loadDicts()
})
</script>

<template>
  <view class="page">
    <view class="form">
      <!-- 13+ 字段 -->
      <view class="section-title">基础信息</view>

      <view class="field">
        <text class="label">举办支部 *</text>
        <picker
          v-if="filteredBranches.length"
          :value="filteredBranches.findIndex((b) => b.id === form.organizer_branch_id)"
          :range="filteredBranches.map((b) => b.name)"
          @change="(e: any) => form.organizer_branch_id = filteredBranches[e.detail.value]?.id || 0"
        >
          <view class="picker-input">
            {{ filteredBranches.find((b) => b.id === form.organizer_branch_id)?.name || '请选择' }}
          </view>
        </picker>
      </view>

      <view class="field-row">
        <view class="field half">
          <text class="label">培训日期 *</text>
          <picker mode="date" :value="form.training_at" @change="(e: any) => form.training_at = e.detail.value">
            <view class="picker-input">{{ form.training_at || '选择日期' }}</view>
          </picker>
        </view>
        <view class="field half">
          <text class="label">时间</text>
          <picker mode="time" :value="form.training_time" @change="(e: any) => form.training_time = e.detail.value">
            <view class="picker-input">{{ form.training_time }}</view>
          </picker>
        </view>
      </view>

      <view class="field">
        <text class="label">培训地点 *</text>
        <input v-model="form.location" class="input" placeholder="如：南湾街道6楼会议室" maxlength="255" />
      </view>

      <view class="field">
        <text class="label">主题 *</text>
        <input v-model="form.theme" class="input" placeholder="培训主题" maxlength="255" />
      </view>

      <view class="field">
        <text class="label">讲师</text>
        <picker
          v-if="lecturers.length"
          :value="form.lecturer_id ? lecturers.findIndex((l) => l.id === form.lecturer_id) - 1 : -1"
          :range="['暂不指定', ...lecturers.map((l) => l.name)]"
          @change="(e: any) => form.lecturer_id = e.detail.value === 0 ? 0 : lecturers[e.detail.value - 1]?.id || 0"
        >
          <view class="picker-input">
            {{ form.lecturer_id ? lecturers.find((l) => l.id === form.lecturer_id)?.name : '暂不指定' }}
          </view>
        </picker>
      </view>

      <view class="field">
        <text class="label">线上/线下</text>
        <view class="chip-row">
          <view
            v-for="o in [{v:'online',l:'线上'},{v:'offline',l:'线下'},{v:'hybrid',l:'混合'}]"
            :key="o.v"
            class="chip"
            :class="{ active: form.online_offline === o.v }"
            @click="form.online_offline = o.v as any"
          >{{ o.l }}</view>
        </view>
      </view>

      <view class="field">
        <text class="label">集中学习</text>
        <view class="chip-row">
          <view class="chip" :class="{ active: form.is_centralized === true }" @click="form.is_centralized = true">是</view>
          <view class="chip" :class="{ active: form.is_centralized === false }" @click="form.is_centralized = false">否</view>
        </view>
      </view>

      <view class="field">
        <text class="label">党的创新理论教育</text>
        <view class="chip-row">
          <view class="chip" :class="{ active: form.is_innovation_theory === true }" @click="form.is_innovation_theory = true">是</view>
          <view class="chip" :class="{ active: form.is_innovation_theory === false }" @click="form.is_innovation_theory = false">否</view>
        </view>
      </view>

      <view class="field">
        <text class="label">来源</text>
        <view class="chip-row">
          <view
            v-for="s in sources"
            :key="s.code"
            class="chip"
            :class="{ active: form.source_type === s.code }"
            @click="form.source_type = s.code as any"
          >{{ s.name }}</view>
        </view>
      </view>

      <view class="field">
        <text class="label">培训对象</text>
        <view class="chip-row">
          <view
            v-for="c in categories"
            :key="c.code"
            class="chip"
            :class="{ active: form.audience_category === c.code }"
            @click="form.audience_category = c.code"
          >{{ c.name }}</view>
        </view>
      </view>

      <view class="field">
        <text class="label">学时 *</text>
        <input
          v-model.number="form.study_hours"
          class="input"
          type="digit"
          placeholder="如 4"
        />
      </view>

      <!-- 参加人员 -->
      <view class="section-title">参加人员</view>
      <MemberPicker v-model="selectedMemberIds" :branch-id="form.organizer_branch_id" @change="onMemberChange" />

      <!-- 现场照片 -->
      <view class="section-title">现场照片 * <text class="hint">（至少 1 张）</text></view>
      <view class="upload-grid">
        <view v-for="(p, i) in photoList" :key="i" class="upload-item">
          <image :src="p.file_url" mode="aspectFill" class="thumb" />
          <view class="remove" @click="removePhoto(i)">×</view>
        </view>
        <view v-if="photoList.length < 9" class="upload-add" @click="onAddPhoto">+</view>
      </view>

      <!-- 签到表 -->
      <view class="section-title">签到表 <text class="hint">（可选，9 张内）</text></view>
      <view class="upload-grid">
        <view v-for="(p, i) in signinList" :key="i" class="upload-item">
          <image :src="p.file_url" mode="aspectFill" class="thumb" />
          <view class="remove" @click="removeSignin(i)">×</view>
        </view>
        <view v-if="signinList.length < 9" class="upload-add" @click="onAddSignin">+</view>
      </view>

      <view v-if="errorMsg" class="error">{{ errorMsg }}</view>

      <view class="btn-row">
        <button class="btn btn-secondary" :disabled="submitting" @click="onSave(true)">保存草稿</button>
        <button class="btn btn-primary" :disabled="submitting" @click="onSave(false)">提交审核</button>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.page { min-height: 100vh; background: #F7F8FA; padding: 24rpx; padding-bottom: 80rpx; }
.form { background: #fff; border-radius: 16rpx; padding: 24rpx; }
.section-title {
  font-size: 30rpx;
  font-weight: 700;
  color: #222;
  margin: 32rpx 0 16rpx;
  padding-left: 8rpx;
  border-left: 6rpx solid #B22222;
}
.section-title:first-of-type { margin-top: 0; }
.hint { font-size: 22rpx; color: #999; font-weight: 400; }
.field { margin-bottom: 24rpx; }
.field-row { display: flex; gap: 16rpx; }
.field.half { flex: 1; }
.label {
  display: block;
  font-size: 26rpx;
  color: #666;
  margin-bottom: 10rpx;
}
.input {
  width: 100%;
  height: 72rpx;
  font-size: 28rpx;
  color: #222;
  background: #f5f5f5;
  border-radius: 8rpx;
  padding: 0 16rpx;
}
.picker-input {
  height: 72rpx;
  line-height: 72rpx;
  font-size: 28rpx;
  color: #222;
  background: #f5f5f5;
  border-radius: 8rpx;
  padding: 0 16rpx;
}
.chip-row { display: flex; gap: 12rpx; flex-wrap: wrap; }
.chip {
  padding: 12rpx 24rpx;
  background: #f5f5f5;
  color: #666;
  border-radius: 32rpx;
  font-size: 24rpx;
}
.chip.active { background: #B22222; color: #fff; }

.upload-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16rpx;
}
.upload-item {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  border-radius: 8rpx;
  overflow: hidden;
}
.thumb { width: 100%; height: 100%; }
.remove {
  position: absolute;
  top: 4rpx;
  right: 4rpx;
  width: 40rpx;
  height: 40rpx;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
  line-height: 1;
}
.upload-add {
  width: 100%;
  aspect-ratio: 1;
  background: #f5f5f5;
  border: 2rpx dashed #ccc;
  border-radius: 8rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 60rpx;
  color: #999;
}

.error {
  background: #FFF0F0;
  color: #B22222;
  padding: 16rpx 24rpx;
  border-radius: 8rpx;
  font-size: 26rpx;
  margin: 16rpx 0;
}

.btn-row { display: flex; gap: 16rpx; margin-top: 32rpx; }
.btn {
  flex: 1;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 30rpx;
  font-weight: 600;
  border-radius: 12rpx;
  text-align: center;
  border: none;
}
.btn-secondary { background: #fff; color: #B22222; border: 1rpx solid #B22222; }
.btn-primary { background: #B22222; color: #fff; }
.btn[disabled] { opacity: 0.6; }
</style>
