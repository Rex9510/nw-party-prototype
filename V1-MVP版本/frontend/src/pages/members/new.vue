<script setup lang="ts">
/**
 * 新增人员 - 3 级联动 picker（街道 → 社区 → 支部）
 *
 * 角色规则（创建者的角色决定可选范围）：
 * - 支部书记 (branch_secretary)：可加本支部成员。3 级全部自动锁定为本人所属。
 * - 社区组织委员 (community_organizer)：可加本社区下任意支部。街道+社区锁定，支部可选。
 * - 街道负责人 (street_lead)：可加本街道下任意支部。街道锁定，社区+支部可选。
 * - 系统管理员 (system_admin)：3 级全部可选。
 */
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast, showSuccessToast } from 'vant'
import { membersApi } from '@/api/members'
import { orgsApi, type Street, type Community, type Branch } from '@/api/orgs'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

// 是否编辑模式（路由有 :id 即为编辑）
const editingId = computed<number | null>(() => {
  const id = Number(route.params.id)
  return id > 0 ? id : null
})
const isEdit = computed(() => editingId.value !== null)

const form = ref({
  name: '',
  phone: '',
  id_card_no: '',
  gender: '' as '' | 'male' | 'female',
  join_date: '',
  street_id: 0,
  community_id: 0,
  branch_id: 0,
  roles: [] as string[],
  identities: [] as string[],
  photo_urls: [] as string[],
  is_mobile_member: false as boolean,        // 是否流动党员
  flow_in_date: '' as string,               // 流入日期（仅 is_mobile_member=true 时必填）
})
const submitting = ref(false)
const errorMsg = ref('')

const streets = ref<Street[]>([])
const communities = ref<Community[]>([])
const branches = ref<Branch[]>([])

const role = computed(() => auth.user?.role || '')

// 各角色 picker 是否可编辑
const streetEditable = computed(() => role.value === 'system_admin')
const communityEditable = computed(() => ['system_admin', 'street_lead'].includes(role.value))
const branchEditable = computed(() =>
  ['system_admin', 'street_lead', 'community_organizer'].includes(role.value),
)

// 3 级级联：上一级变化时，清空下级
watch(() => form.value.street_id, (v, old) => {
  if (v !== old) {
    form.value.community_id = 0
    form.value.branch_id = 0
  }
})
watch(() => form.value.community_id, (v, old) => {
  if (v !== old) {
    form.value.branch_id = 0
  }
})

// 根据当前选中的 street 过滤 community
const availableCommunities = computed(() => {
  if (!form.value.street_id) return []
  return communities.value.filter((c) => c.street_id === form.value.street_id)
})

// 根据当前选中的 community 过滤 branch
const availableBranches = computed(() => {
  if (!form.value.community_id) return []
  return branches.value.filter((b) => b.community_id === form.value.community_id)
})

async function loadOrgs() {
  try {
    // 街道：管理员看全部，其他角色看自己所在的（一般就 1 个）
    if (role.value === 'system_admin') {
      streets.value = await orgsApi.streets()
    } else if (auth.user?.street_id) {
      const all = await orgsApi.streets()
      streets.value = all.filter((s) => s.id === auth.user!.street_id)
    }

    // 社区：取所有（按 street_id 过滤）
    if (auth.user?.street_id) {
      communities.value = await orgsApi.communities(auth.user.street_id)
    } else {
      communities.value = await orgsApi.communities()
    }

    // 支部：取所有
    branches.value = await orgsApi.branches()

    // 预选：根据角色
    await nextTick()
    initFormByRole()

    // 调试：方便排查"为啥没默认加载"
    if (auth.user) {
      console.log('[members/new] user 组织信息', {
        role: auth.user.role,
        street_id: auth.user.street_id,
        community_id: auth.user.community_id,
        branch_id: auth.user.branch_id,
        streets_loaded: streets.value.length,
        communities_loaded: communities.value.length,
        branches_loaded: branches.value.length,
        form_after_init: { ...form.value },
      })
    }
  } catch (e) {
    console.warn('loadOrgs failed', e)
  }
}

async function initFormByRole() {
  // 用本地变量避免响应式 trap（编辑模式 watch 抢着清空）
  const u = auth.user
  if (!u) return

  // 仅在"该字段可编辑"或"该字段未被接口回填过时"才覆盖
  // 这里采用：先按用户所属填，再用列表兜底
  // 街道
  if (!form.value.street_id && u.street_id) {
    form.value.street_id = u.street_id
  } else if (!form.value.street_id && streets.value.length) {
    form.value.street_id = streets.value[0].id
  }

  // 社区（依赖 street_id 已被设上）
  await nextTick()
  if (!form.value.community_id && u.community_id) {
    // 校验该 community 确实在可用列表里（避免用户跨组织时拉不到）
    if (availableCommunities.value.some((c) => c.id === u.community_id)) {
      form.value.community_id = u.community_id
    }
  }
  if (!form.value.community_id && availableCommunities.value.length) {
    form.value.community_id = availableCommunities.value[0].id
  }

  // 支部
  await nextTick()
  if (!form.value.branch_id && u.branch_id) {
    if (availableBranches.value.some((b) => b.id === u.branch_id)) {
      form.value.branch_id = u.branch_id
    }
  }
  if (!form.value.branch_id && availableBranches.value.length) {
    form.value.branch_id = availableBranches.value[0].id
  }
}

// ===== 选中的文本（显示用） =====
const selectedStreetName = computed(() => {
  return streets.value.find((s) => s.id === form.value.street_id)?.name || '未选择'
})
const selectedCommunityName = computed(() => {
  return communities.value.find((c) => c.id === form.value.community_id)?.name || '未选择'
})
const selectedBranchName = computed(() => {
  if (!form.value.branch_id) return ''
  const b = branches.value.find((x) => x.id === form.value.branch_id)
  return b?.name || ''
})

// ===== 街道 picker（action-sheet 列表，PC 友好） =====
const showStreetPicker = ref(false)
const streetActions = computed(() =>
  streets.value.map((s) => ({
    name: s.name,
    subname: s.id === form.value.street_id ? '✓ 当前选中' : '',
    value: s.id,
  })),
)
function onStreetSelect(action: { value: number }) {
  form.value.street_id = action.value
}

// ===== 社区 picker（action-sheet 列表） =====
const showCommunityPicker = ref(false)
const communityActions = computed(() =>
  availableCommunities.value.map((c) => ({
    name: c.name,
    subname: c.id === form.value.community_id ? '✓ 当前选中' : '',
    value: c.id,
  })),
)
function onCommunitySelect(action: { value: number }) {
  form.value.community_id = action.value
}

// ===== 支部 picker（action-sheet 列表） =====
const showBranchPicker = ref(false)
const branchActions = computed(() =>
  availableBranches.value.map((b) => ({
    name: b.name,
    subname: b.id === form.value.branch_id ? '✓ 当前选中' : '',
    value: b.id,
  })),
)
function onBranchSelect(action: { value: number }) {
  form.value.branch_id = action.value
}

// ===== 入党时间 picker：Vant van-date-picker（年/月/日 3 滚轮，更稳） =====
const showJoinDatePicker = ref(false)

// van-date-picker 接收的 selectedValues 格式是 ['YYYY', 'MM', 'DD']
const joinDatePickerValue = ref<string[]>([])

// van-date-picker 的列配置
const joinDatePickerColumns = computed(() => {
  const now = new Date().getFullYear()
  const years: { text: string; value: string }[] = []
  for (let y = now + 5; y >= 1950; y--) years.push({ text: `${y} 年`, value: String(y) })
  const months: { text: string; value: string }[] = []
  for (let m = 1; m <= 12; m++) months.push({ text: `${m} 月`, value: String(m).padStart(2, '0') })
  // 日期：根据当前选中年/月动态算（van-date-picker 会按 columnsFn 调）
  const [yStr, mStr] = joinDatePickerValue.value
  const y = yStr ? +yStr : now
  const m = mStr ? +mStr : new Date().getMonth() + 1
  const lastDay = new Date(y, m, 0).getDate()
  const days: { text: string; value: string }[] = []
  for (let d = 1; d <= lastDay; d++) days.push({ text: `${d} 日`, value: String(d).padStart(2, '0') })
  return [
    { values: years },
    { values: months },
    { values: days },
  ]
})

const displayDate = computed(() => {
  if (!form.value.join_date) return ''
  const [y, m, d] = form.value.join_date.split('-')
  return `${y}年${Number(m)}月${Number(d)}日`
})

function openJoinDatePicker() {
  const n = new Date()
  let y = n.getFullYear(), m = n.getMonth() + 1, d = n.getDate()
  if (form.value.join_date) {
    const [yy, mm, dd] = form.value.join_date.split('-')
    y = +yy; m = +mm; d = +dd
  }
  joinDatePickerValue.value = [String(y), String(m).padStart(2, '0'), String(d).padStart(2, '0')]
  showJoinDatePicker.value = true
}

function onJoinDateConfirm({ selectedValues }: { selectedValues: string[] }) {
  const [y, m, d] = selectedValues
  form.value.join_date = `${y}-${m}-${d}`
  showJoinDatePicker.value = false
}

// 切年/月时如果当前日超出新月最大天数，重置到 1 号
watch(joinDatePickerValue, (v) => {
  if (!v || v.length !== 3) return
  const y = +v[0], m = +v[1], d = +v[2]
  const lastDay = new Date(y, m, 0).getDate()
  if (d > lastDay) {
    joinDatePickerValue.value = [v[0], v[1], '01']
  }
})

// ===== 流动党员 / 流入日期 picker（Vant van-date-picker） =====
const showFlowInDatePicker = ref(false)
const flowInDatePickerValue = ref<string[]>([])

const flowInDatePickerColumns = computed(() => {
  const now = new Date().getFullYear()
  const years: { text: string; value: string }[] = []
  for (let y = now + 5; y >= 1950; y--) years.push({ text: `${y} 年`, value: String(y) })
  const months: { text: string; value: string }[] = []
  for (let m = 1; m <= 12; m++) months.push({ text: `${m} 月`, value: String(m).padStart(2, '0') })
  const [yStr, mStr] = flowInDatePickerValue.value
  const y = yStr ? +yStr : now
  const m = mStr ? +mStr : new Date().getMonth() + 1
  const lastDay = new Date(y, m, 0).getDate()
  const days: { text: string; value: string }[] = []
  for (let d = 1; d <= lastDay; d++) days.push({ text: `${d} 日`, value: String(d).padStart(2, '0') })
  return [
    { values: years },
    { values: months },
    { values: days },
  ]
})

const flowInDisplayDate = computed(() => {
  if (!form.value.flow_in_date) return ''
  const [y, m, d] = form.value.flow_in_date.split('-')
  return `${y}年${Number(m)}月${Number(d)}日`
})

function openFlowInDatePicker() {
  const n = new Date()
  let y = n.getFullYear(), m = n.getMonth() + 1, d = n.getDate()
  if (form.value.flow_in_date) {
    const [yy, mm, dd] = form.value.flow_in_date.split('-')
    y = +yy; m = +mm; d = +dd
  }
  flowInDatePickerValue.value = [String(y), String(m).padStart(2, '0'), String(d).padStart(2, '0')]
  showFlowInDatePicker.value = true
}

function onFlowInDateConfirm({ selectedValues }: { selectedValues: string[] }) {
  const [y, m, d] = selectedValues
  form.value.flow_in_date = `${y}-${m}-${d}`
  showFlowInDatePicker.value = false
}

watch(flowInDatePickerValue, (v) => {
  if (!v || v.length !== 3) return
  const y = +v[0], m = +v[1], d = +v[2]
  const lastDay = new Date(y, m, 0).getDate()
  if (d > lastDay) {
    flowInDatePickerValue.value = [v[0], v[1], '01']
  }
})

// 流动党员 = false 时清空 flow_in_date
watch(() => form.value.is_mobile_member, (v) => {
  if (!v) form.value.flow_in_date = ''
})

// 切月份时如果当前日超出新月天数，重置到 1 号
//（已迁移到 flowInDatePickerValue 的 watch，见下方）

// ===== 角色 & 身份选项 =====
// 全集（按权限从高到低排）
const ALL_ROLE_OPTIONS = [
  { label: '系统管理员', value: 'system_admin' },
  { label: '街道负责人', value: 'street_lead' },
  { label: '社区组织委员', value: 'community_organizer' },
  { label: '支部书记', value: 'branch_secretary' },
  { label: '党员', value: 'party_member' },
]
// 按"创建者自己的角色"裁剪可选项 —— 只能给自己及以下的角色：
// - 系统管理员 → 5 个全选
// - 街道负责人 → 4 个（街道、社区、支部、党员）
// - 社区组织委员 → 3 个（社区、支部、党员）
// - 支部书记 → 2 个（支部、党员）
// - 党员 → 0 个（无法给任何人赋角色）
const ROLE_RANK: Record<string, number> = {
  system_admin: 0,
  street_lead: 1,
  community_organizer: 2,
  branch_secretary: 3,
  party_member: 4,
}
const roleOptions = computed(() => {
  const fromIdx = ROLE_RANK[role.value]
  if (fromIdx === undefined) return []
  // 从自己所在 rank 开始，往下取所有（包含自己）
  return ALL_ROLE_OPTIONS.slice(fromIdx)
})
// 角色权限变化时，把已选但不属于自己的角色剔掉（避免脏数据）
watch(roleOptions, (opts) => {
  const allowed = new Set(opts.map((o) => o.value))
  form.value.roles = form.value.roles.filter((r) => allowed.has(r))
})
const identityOptions = [
  { label: '普通党员' },
  { label: '党支部书记' },
  { label: '党委副书记' },
  { label: '党委委员' },
  { label: '支委会委员' },
]

// ===== 角色提示 =====
const roleHint = computed(() => {
  switch (role.value) {
    case 'branch_secretary': return '你只能在本支部添加人员'
    case 'community_organizer': return '你只能在本社区下添加人员'
    case 'street_lead': return '你只能在本街道下添加人员'
    case 'system_admin': return '你可以选择任何街道/社区/支部'
    case 'member': return '你没有添加人员的权限，即将跳转回首页……'
    default: return '当前角色暂不支持添加人员'
  }
})

// 无权限角色拦截
const allowedRoles = ['system_admin', 'street_lead', 'community_organizer', 'branch_secretary']
const canAccess = computed(() => allowedRoles.includes(role.value))

// ===== 校验 + 提交 =====
function validate(): string {
  if (!form.value.name.trim()) return '请输入姓名'
  if (!/^1[3-9]\d{9}$/.test(form.value.phone)) return '手机号格式错误'
  if (form.value.id_card_no && !/^\d{17}[\dXx]$/.test(form.value.id_card_no)) return '身份证号格式错误'
  if (!form.value.gender) return '请选择性别'
  if (!form.value.join_date) return '请选择入党时间'
  // 角色：仅当操作人有赋权资格时才校验
  if (roleOptions.value.length && !form.value.roles.length) return '请至少选择一个角色'
  if (!form.value.branch_id) return '请选择支部'
  // 流动党员 = 是 时必填流入日期
  if (form.value.is_mobile_member && !form.value.flow_in_date) return '请选择流入日期'
  return ''
}

async function onSubmit() {
  errorMsg.value = validate()
  if (errorMsg.value) {
    showToast({ message: errorMsg.value, type: 'fail' })
    return
  }
  submitting.value = true
  try {
    const payload = {
      name: form.value.name.trim(),
      phone: form.value.phone,
      id_card_no: form.value.id_card_no || undefined,
      gender: form.value.gender,
      join_date: form.value.join_date,
      roles: form.value.roles,
      identities: form.value.identities,
      branch_id: form.value.branch_id,
      photo_urls: form.value.photo_urls,
      is_mobile_member: form.value.is_mobile_member,
      flow_in_date: form.value.is_mobile_member ? form.value.flow_in_date : null,
    }
    if (isEdit.value) {
      await membersApi.update(editingId.value!, payload)
      showSuccessToast({ message: '保存成功' })
    } else {
      await membersApi.create(payload)
      showSuccessToast({ message: '新增成功' })
    }
    setTimeout(() => router.back(), 800)
  } catch (e: any) {
    errorMsg.value = e?.message || (isEdit.value ? '保存失败' : '新增失败')
    showToast({ message: errorMsg.value, type: 'fail' })
  } finally {
    submitting.value = false
  }
}

// ===== 风采照片上传 =====
// 业务规则：只允许 1 张（覆盖原"主图"），大小不限制
function onAddMemberPhoto() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = (e: any) => {
    const f = e.target.files?.[0]
    if (!f) return
    const reader = new FileReader()
    reader.onload = () => {
      // 单张：直接替换，不追加
      form.value.photo_urls = [reader.result as string]
    }
    reader.readAsDataURL(f)
  }
  input.click()
}
function removeMemberPhoto(i: number) {
  form.value.photo_urls.splice(i, 1)
}

// 编辑模式：拉详情回显
async function loadForEdit() {
  if (!editingId.value) return
  try {
    const m = await membersApi.get(editingId.value)
    form.value.name = m.name
    form.value.phone = m.phone
    form.value.id_card_no = m.id_card_no || ''
    form.value.gender = (m.gender as any) || ''
    form.value.join_date = m.join_date || ''
    form.value.branch_id = m.branch_id
    form.value.roles = Array.isArray(m.roles) ? [...m.roles] : []
    form.value.identities = Array.isArray(m.identities) ? [...m.identities] : []
    form.value.photo_urls = Array.isArray(m.photo_urls) ? [...m.photo_urls] : []
    form.value.is_mobile_member = !!m.is_mobile_member
    form.value.flow_in_date = m.flow_in_date || ''
  } catch (e: any) {
    showToast({ message: e?.message || '加载失败', type: 'fail' })
    router.replace('/pages/members/list')
  }
}

onMounted(async () => {
  if (!canAccess.value) {
    showToast({ message: '你没有编辑人员的权限', type: 'fail' })
    setTimeout(() => router.replace('/pages/index/index'), 1000)
    return
  }
  await loadOrgs()
  if (isEdit.value) {
    await loadForEdit()
  }
})
</script>

<template>
  <div class="form-page">
    <div class="page-header">
      <div class="back" @click="router.back()">‹ 返回</div>
      <div class="title">{{ isEdit ? '编辑人员' : '新增人员' }}</div>
    </div>

    <div v-if="roleHint" class="role-hint">{{ roleHint }}</div>

    <van-form v-if="canAccess" @submit="onSubmit" class="form">
      <van-cell-group inset title="基本信息">
        <van-field
          v-model="form.name"
          label="姓名"
          placeholder="请输入姓名"
          maxlength="64"
          required
          :rules="[{ required: true, message: '请填写姓名' }]"
        />
        <van-field
          v-model="form.phone"
          label="手机号"
          type="tel"
          placeholder="11位手机号"
          maxlength="11"
          required
          :rules="[{ required: true, message: '请填写手机号' }]"
        />
        <van-field
          v-model="form.id_card_no"
          label="身份证号"
          placeholder="可选，18位"
          maxlength="18"
        />
      </van-cell-group>

      <van-cell-group inset title="所属组织" class="cell-group-spaced">
        <van-field
          :model-value="selectedStreetName || '—'"
          label="① 街道"
          placeholder="加载中…"
          readonly
          :is-link="streetEditable"
          :disabled="!streetEditable"
          :class="['field-required', !form.street_id ? 'field-missing' : '']"
          @click="streetEditable && (showStreetPicker = true)"
        />
        <van-field
          :model-value="selectedCommunityName || '—'"
          label="② 社区"
          :placeholder="communityEditable ? '点击选择' : '已锁定'"
          readonly
          :is-link="communityEditable && !!form.street_id"
          :disabled="!communityEditable || !form.street_id"
          :class="['field-required', !form.community_id ? 'field-missing' : '']"
          @click="communityEditable && form.street_id && (showCommunityPicker = true)"
        />
        <van-field
          :model-value="selectedBranchName || '—'"
          label="③ 支部"
          :placeholder="branchEditable ? '点击选择' : '已锁定'"
          readonly
          :is-link="branchEditable && !!form.community_id"
          required
          :rules="[{ required: true, message: '请选择支部' }]"
          :disabled="!branchEditable || !form.community_id"
          :class="['field-required', !form.branch_id ? 'field-missing' : '']"
          @click="branchEditable && form.community_id && (showBranchPicker = true)"
        />
      </van-cell-group>

      <van-cell-group inset title="其他信息" class="cell-group-spaced">
        <van-cell title="性别" required>
          <template #value>
            <van-radio-group v-model="form.gender" direction="horizontal">
              <van-radio name="male">男</van-radio>
              <van-radio name="female">女</van-radio>
            </van-radio-group>
          </template>
        </van-cell>

        <van-field label="入党时间" required>
          <template #input>
            <button type="button" class="date-btn" @click.prevent="openJoinDatePicker">
              {{ displayDate || '点击选择日期' }}
            </button>
          </template>
        </van-field>

        <van-cell title="角色（权限控制）">
          <template #value>
            <div class="check-group">
              <template v-if="roleOptions.length">
                <van-checkbox-group v-model="form.roles" direction="horizontal" :max="5">
                  <van-checkbox
                    v-for="r in roleOptions"
                    :key="r.value"
                    :name="r.value"
                    shape="square"
                  >{{ r.label }}</van-checkbox>
                </van-checkbox-group>
              </template>
              <span v-else class="role-no-perm">当前角色无赋权资格</span>
            </div>
          </template>
        </van-cell>

        <van-cell title="身份">
          <template #value>
            <div class="check-group">
              <van-checkbox-group v-model="form.identities" direction="horizontal" :max="5">
                <van-checkbox
                  v-for="id in identityOptions"
                  :key="id.label"
                  :name="id.label"
                  shape="square"
                >{{ id.label }}</van-checkbox>
              </van-checkbox-group>
            </div>
          </template>
        </van-cell>

        <van-cell title-class="req" required>
          <template #title>
            <span class="req">是否流动党员</span>
          </template>
          <template #value>
            <van-radio-group v-model="form.is_mobile_member" direction="horizontal">
              <van-radio :name="true">是</van-radio>
              <van-radio :name="false">否</van-radio>
            </van-radio-group>
          </template>
        </van-cell>

        <van-field
          v-if="form.is_mobile_member"
          label="流入日期"
          required
          :rules="[{ required: true, message: '请选择流入日期' }]"
        >
          <template #input>
            <button type="button" class="date-btn" @click.prevent="openFlowInDatePicker">
              {{ flowInDisplayDate || '点击选择日期' }}
            </button>
          </template>
        </van-field>
      </van-cell-group>

      <van-cell-group inset title="风采照片" class="cell-group-spaced">
        <van-cell :title="form.photo_urls.length ? '已上传 1 张（主图）' : '未上传（建议尺寸 800×800，大小不限）'">
          <template #value>
            <van-button size="mini" type="primary" plain hairline @click="onAddMemberPhoto">
              {{ form.photo_urls.length ? '替换' : '上传' }}
            </van-button>
          </template>
        </van-cell>
        <div v-if="form.photo_urls.length" class="member-photo-grid">
          <div v-for="(p, i) in form.photo_urls" :key="i" class="member-photo-item">
            <img :src="p" />
            <div class="remove" @click="removeMemberPhoto(i)">×</div>
            <div v-if="i === 0" class="cover-tag">主图</div>
          </div>
        </div>
      </van-cell-group>

      <div class="actions">
        <van-button
          block
          type="primary"
          native-type="submit"
          :loading="submitting"
          :disabled="submitting"
        >
          {{ isEdit ? '保存修改' : '保存' }}
        </van-button>
      </div>
    </van-form>

    <!-- 街道选择（action-sheet） -->
    <van-action-sheet
      v-model:show="showStreetPicker"
      :actions="streetActions"
      cancel-text="取消"
      close-on-click-action
      @select="onStreetSelect"
    />

    <!-- 社区选择（action-sheet） -->
    <van-action-sheet
      v-model:show="showCommunityPicker"
      :actions="communityActions"
      cancel-text="取消"
      close-on-click-action
      @select="onCommunitySelect"
    />

    <!-- 支部选择（action-sheet） -->
    <van-action-sheet
      v-model:show="showBranchPicker"
      :actions="branchActions"
      cancel-text="取消"
      close-on-click-action
      @select="onBranchSelect"
    />

    <!-- 入党时间 picker（Vant van-date-picker） -->
    <van-popup v-model:show="showJoinDatePicker" position="bottom" round>
      <van-date-picker
        v-model="joinDatePickerValue"
        :columns-type="['year', 'month', 'day']"
        :min-date="new Date(1950, 0, 1)"
        :max-date="new Date(new Date().getFullYear() + 5, 11, 31)"
        title="选择入党时间"
        @confirm="onJoinDateConfirm"
        @cancel="showJoinDatePicker = false"
      />
    </van-popup>

    <!-- 流入日期 picker（Vant van-date-picker） -->
    <van-popup v-model:show="showFlowInDatePicker" position="bottom" round>
      <van-date-picker
        v-model="flowInDatePickerValue"
        :columns-type="['year', 'month', 'day']"
        :min-date="new Date(1950, 0, 1)"
        :max-date="new Date(new Date().getFullYear() + 5, 11, 31)"
        title="选择流入日期"
        @confirm="onFlowInDateConfirm"
        @cancel="showFlowInDatePicker = false"
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
.back:hover { color: var(--primary-dark); }
.title {
  font-size: 18px;
  font-weight: 700;
  color: #222;
}

.role-hint {
  margin: 0 16px 12px;
  padding: 8px 12px;
  background: #FFF8E1;
  border: 1px solid #FFE0B2;
  border-radius: 6px;
  font-size: 12px;
  color: #E65100;
}

.form { background: transparent; }
.cell-group-spaced { margin-top: 12px; }

.actions {
  padding: 20px 16px 0;
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
:deep(.van-field--disabled .van-field__label) {
  color: #999;
}
:deep(.van-radio__label) {
  font-size: 14px;
}

/* 必填红星（在 field label 前面） */
:deep(.field-required .van-field__label::before) {
  content: '*';
  color: #B22222;
  font-weight: 700;
  margin-right: 3px;
  font-size: 14px;
}
/* 缺值时 label 红色（更醒目） */
:deep(.field-missing .van-field__label) {
  color: #B22222 !important;
}

/* 日历遮罩 + 弹窗 */
.calendar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 2000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  animation: calFadeIn 0.2s ease;
}
@keyframes calFadeIn { from { opacity: 0; } to { opacity: 1; } }

.calendar {
  width: 100%;
  max-width: 500px;
  background: #fff;
  border-radius: 16px 16px 0 0;
  padding: 20px 16px 16px;
  user-select: none;
  animation: calSlideUp 0.25s ease;
}
@keyframes calSlideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
.cal-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-bottom: 12px;
}
.cal-nav {
  border: none;
  background: #f5f5f5;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #333;
  transition: background 0.15s;
}
.cal-nav:hover { background: #e8e8e8; }
.cal-nav:active { background: #ddd; }
.cal-title {
  font-size: 16px;
  font-weight: 600;
  color: #222;
  min-width: 100px;
  text-align: center;
}
.cal-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  color: #999;
  font-size: 12px;
  margin-bottom: 4px;
  padding: 4px 0;
}
.cal-weekdays span {
  padding: 4px 0;
}
.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}
.cal-day {
  border: none;
  background: none;
  aspect-ratio: 1;
  font-size: 14px;
  border-radius: 8px;
  cursor: pointer;
  color: #333;
  transition: all 0.12s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cal-day:hover:not(:disabled) { background: #f0f5ff; }
.cal-day:active:not(:disabled) { background: #d6e4ff; }
.cal-day--muted {
  color: #ccc;
  cursor: default;
}
.cal-day--today {
  font-weight: 700;
  color: var(--primary, #165dff);
}
.cal-day--selected {
  background: var(--primary, #165dff);
  color: #fff;
  font-weight: 600;
}
.cal-day--selected:hover {
  background: var(--primary-dark, #0e42c7);
}
.cal-footer {
  display: flex;
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
.cal-today, .cal-close {
  flex: 1;
  height: 36px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  border: none;
  transition: all 0.12s;
}
.cal-today {
  background: var(--primary, #165dff);
  color: #fff;
  font-weight: 500;
}
.cal-today:hover { background: var(--primary-dark, #0e42c7); }
.cal-close {
  background: #f5f5f5;
  color: #666;
}
.cal-close:hover { background: #e8e8e8; }

/* 多选 checkbox 组 */
.check-group {
  width: 100%;
}
.role-no-perm {
  color: #999;
  font-size: 13px;
}
.check-group :deep(.van-checkbox-group--horizontal) {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
}
.check-group :deep(.van-checkbox) {
  margin-bottom: 2px;
}
.check-group :deep(.van-checkbox__label) {
  font-size: 13px;
  white-space: nowrap;
}

/* 风采照片网格（最多 1 张，但留 3 列布局兼容历史） */
.member-photo-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 0 16px 16px;
}
.member-photo-grid:has(.member-photo-item:only-child) {
  grid-template-columns: 1fr;
  max-width: 200px;
}
.member-photo-item {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  border-radius: 6px;
  overflow: hidden;
  background: #f5f5f5;
}
.member-photo-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.member-photo-item .remove {
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
.member-photo-item .cover-tag {
  position: absolute;
  bottom: 4px;
  left: 4px;
  background: rgba(178, 34, 34, 0.9);
  color: #fff;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px;
}
</style>
