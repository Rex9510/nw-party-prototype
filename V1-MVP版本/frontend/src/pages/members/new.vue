<script setup lang="ts">
/**
 * 新增人员 - 单选 Cascader（街道 / 社区 / 支部 任选一级）
 *
 * 角色规则（创建者的角色决定可选范围）：
 * - 社区组织员 (branch_secretary)：只能选到本支部（org_level=branch，3 级锁定）
 * - 社区组织委员 (community_organizer)：可选到本社区/本社区下任何支部（org_level=community 或 branch）
 * - 街道负责人 (street_lead)：可选到本街道/本街道下任何社区或支部（org_level=street/community/branch）
 * - 系统管理员 (system_admin)：3 级都可任选
 *
 * v3：表单只记录 org_level + 对应组织 ID，提交时由后端反查 community_id/street_id。
 */
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast, showSuccessToast } from 'vant'
import { membersApi } from '@/api/members'
import { orgsApi, type Street, type Community, type Branch, type StreetTreeNode } from '@/api/orgs'
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

type OrgLevel = '' | 'street' | 'community' | 'branch'

const form = ref({
  name: '',
  phone: '',
  id_card_no: '',
  gender: '' as '' | 'male' | 'female',
  join_date: '',
  org_level: '' as OrgLevel,   // 'street' | 'community' | 'branch'
  street_id: 0,
  community_id: 0,
  branch_id: 0,
  roles: [] as string[],
  identities: [] as string[],
  photo_urls: [] as string[],
  is_mobile_member: false as boolean,
  flow_in_date: '' as string,
})
const submitting = ref(false)
const errorMsg = ref('')

// ===== 组织树 =====
const tree = ref<StreetTreeNode[]>([])

async function loadTree() {
  try {
    const role = auth.user?.role
    if (role === 'system_admin') {
      tree.value = await orgsApi.tree()
    } else if (auth.user?.street_id) {
      // 其他角色：只加载本街道及以下
      const all = await orgsApi.tree()
      tree.value = all.filter((s) => s.id === auth.user!.street_id)
    } else {
      tree.value = await orgsApi.tree()
    }
  } catch (e) {
    console.warn('loadTree failed', e)
  }
}

const role = computed(() => auth.user?.role || '')

// 角色可选的 org_level 范围
const allowedLevels = computed<OrgLevel[]>(() => {
  const r = role.value
  if (r === 'system_admin' || r === 'street_lead') {
    return ['street', 'community', 'branch']
  }
  if (r === 'community_organizer') {
    return ['community', 'branch']
  }
  if (r === 'branch_secretary') {
    return ['branch']
  }
  return ['branch']
})

// ===== 3 步走组织选择（街道 → 社区 → 支部，每步可"选到这一级"立即提交） =====
type Action = { name: string; subname?: string; value: number; level?: OrgLevel }
const showOrgPicker = ref(false)
const pickerStep = ref<'street' | 'community' | 'branch'>('street')
const pickerBreadcrumb = ref<{ name: string; level: OrgLevel; value: number }[]>([])
// 当前级可选的 nodes（每 node 含 level）
const pickerActions = computed<Action[]>(() => {
  const list: Action[] = []
  const allowed = allowedLevels.value
  if (pickerStep.value === 'street') {
    for (const s of tree.value) {
      const actions: Action = { name: s.name, value: s.id, level: 'street' }
      if (s.id === form.value.street_id) actions.subname = '✓ 当前选中'
      if (allowed.includes('street')) {
        // 可以选到这一级：subname 给提示
        actions.subname = actions.subname ? `${actions.subname} · 选到街道` : '点此选到街道'
      }
      list.push(actions)
    }
  } else if (pickerStep.value === 'community') {
    const street = tree.value.find((s) => s.id === pickerBreadcrumb.value[0]?.value)
    const allowed2 = allowed
    for (const c of street?.communities || []) {
      const a: Action = { name: c.name, value: c.id, level: 'community' }
      if (c.id === form.value.community_id) a.subname = '✓ 当前选中'
      if (allowed2.includes('community')) {
        a.subname = a.subname ? `${a.subname} · 选到社区` : '点此选到社区'
      }
      list.push(a)
    }
  } else if (pickerStep.value === 'branch') {
    const street = tree.value.find((s) => s.id === pickerBreadcrumb.value[0]?.value)
    const community = street?.communities.find((c) => c.id === pickerBreadcrumb.value[1]?.value)
    for (const b of community?.branches || []) {
      const a: Action = { name: b.name, value: b.id, level: 'branch' }
      if (b.id === form.value.branch_id) a.subname = '✓ 当前选中'
      list.push(a)
    }
  }
  return list
})

function levelLabel(l: OrgLevel): string {
  if (l === 'street') return '街道级'
  if (l === 'community') return '社区级'
  if (l === 'branch') return '支部级'
  return ''
}

// 顶部"面包屑"，可点击回退
const pickerTitle = computed(() => {
  if (pickerStep.value === 'street') return '选择街道'
  if (pickerStep.value === 'community') {
    const b = pickerBreadcrumb.value[0]
    return `选择社区（${b?.name || ''}）`
  }
  const b = pickerBreadcrumb.value[1]
  return `选择支部（${b?.name || ''}）`
})

const selectedOrgText = computed(() => {
  if (form.value.org_level === 'branch' && form.value.branch_id) {
    const s = tree.value.find((x) => x.communities?.some((c) => c.branches?.some((b) => b.id === form.value.branch_id)))
    const c = s?.communities.find((x) => x.branches?.some((b) => b.id === form.value.branch_id))
    const b = c?.branches.find((x) => x.id === form.value.branch_id)
    return b ? `${s?.name} / ${c?.name} / ${b.name}（${levelLabel('branch')}）` : ''
  }
  if (form.value.org_level === 'community' && form.value.community_id) {
    const s = tree.value.find((x) => x.communities?.some((c) => c.id === form.value.community_id))
    const c = s?.communities.find((x) => x.id === form.value.community_id)
    return c ? `${s?.name} / ${c.name}（${levelLabel('community')}）` : ''
  }
  if (form.value.org_level === 'street' && form.value.street_id) {
    const s = tree.value.find((x) => x.id === form.value.street_id)
    return s ? `${s.name}（${levelLabel('street')}）` : ''
  }
  return ''
})

function openOrgPicker() {
  // 重置到第 1 步
  pickerStep.value = 'street'
  pickerBreadcrumb.value = []
  showOrgPicker.value = true
}

function commitOrg(level: OrgLevel, value: number) {
  form.value.street_id = 0
  form.value.community_id = 0
  form.value.branch_id = 0
  form.value.org_level = level
  if (level === 'street') form.value.street_id = value
  if (level === 'community') form.value.community_id = value
  if (level === 'branch') form.value.branch_id = value
  showOrgPicker.value = false
}

function onOrgActionSelect(action: Action) {
  // 默认：点 item = 选到该级（commit）
  commitOrg(action.level as OrgLevel, action.value)
}

function onOrgItemGotoChildren(action: Action) {
  // 点右侧箭头 = 进下一步（不 commit）
  if (action.level === 'street') {
    pickerBreadcrumb.value = [{ name: action.name, level: 'street', value: action.value }]
    pickerStep.value = 'community'
  } else if (action.level === 'community') {
    pickerBreadcrumb.value.push({ name: action.name, level: 'community', value: action.value })
    pickerStep.value = 'branch'
  }
}

function onOrgPickerCancel() {
  showOrgPicker.value = false
}

function goBackOrgStep() {
  if (pickerStep.value === 'branch') {
    pickerStep.value = 'community'
    pickerBreadcrumb.value.pop()
  } else if (pickerStep.value === 'community') {
    pickerStep.value = 'street'
    pickerBreadcrumb.value = []
  } else {
    showOrgPicker.value = false
  }
}

// 顶部"选到 XX 级"按钮
const canPickThisLevel = computed(() => {
  if (pickerStep.value === 'street') return allowedLevels.value.includes('street')
  if (pickerStep.value === 'community') return allowedLevels.value.includes('community')
  return false // branch 没有更上级
})

function pickCurrentLevel() {
  if (pickerStep.value === 'street' && pickerBreadcrumb.value[0]) {
    commitOrg('street', pickerBreadcrumb.value[0].value)
  } else if (pickerStep.value === 'community' && pickerBreadcrumb.value[1]) {
    commitOrg('community', pickerBreadcrumb.value[1].value)
  }
}

// ===== 入党时间 picker =====
const showJoinDatePicker = ref(false)
const joinDatePickerValue = ref<string[]>([])
const joinDatePickerColumns = computed(() => {
  const now = new Date()
  const curYear = now.getFullYear()
  const years: { text: string; value: string }[] = []
  for (let y = curYear + 5; y >= 1950; y--) years.push({ text: `${y} 年`, value: String(y) })
  const months: { text: string; value: string }[] = []
  for (let m = 1; m <= 12; m++) months.push({ text: `${m} 月`, value: String(m).padStart(2, '0') })
  // 拿当前 picker 选中的 y/m，没有就默认当前
  const val = joinDatePickerValue.value || []
  const yStr = val[0]
  const mStr = val[1]
  const y = yStr && !isNaN(+yStr) ? +yStr : curYear
  const m = mStr && !isNaN(+mStr) ? +mStr : (now.getMonth() + 1)
  const lastDay = new Date(y, m, 0).getDate()
  const days: { text: string; value: string }[] = []
  for (let d = 1; d <= lastDay; d++) days.push({ text: `${d} 日`, value: String(d).padStart(2, '0') })
  return [years, months, days]
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
watch(joinDatePickerValue, (v) => {
  if (!v || v.length !== 3) return
  const y = +v[0], m = +v[1], d = +v[2]
  const lastDay = new Date(y, m, 0).getDate()
  if (d > lastDay) joinDatePickerValue.value = [v[0], v[1], '01']
})

// ===== 流动党员 / 流入日期 =====
const showFlowInDatePicker = ref(false)
const flowInDatePickerValue = ref<string[]>([])
const flowInDatePickerColumns = computed(() => {
  const now = new Date()
  const curYear = now.getFullYear()
  const years: { text: string; value: string }[] = []
  for (let y = curYear; y >= 1950; y--) years.push({ text: `${y} 年`, value: String(y) })
  const months: { text: string; value: string }[] = []
  for (let m = 1; m <= 12; m++) months.push({ text: `${m} 月`, value: String(m).padStart(2, '0') })
  const val = flowInDatePickerValue.value || []
  const yStr = val[0]
  const mStr = val[1]
  const y = yStr && !isNaN(+yStr) ? +yStr : curYear
  const m = mStr && !isNaN(+mStr) ? +mStr : (now.getMonth() + 1)
  const lastDay = new Date(y, m, 0).getDate()
  const days: { text: string; value: string }[] = []
  for (let d = 1; d <= lastDay; d++) days.push({ text: `${d} 日`, value: String(d).padStart(2, '0') })
  return [years, months, days]
})
const displayFlowInDate = computed(() => {
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
  const m = +v[1], d = +v[2]
  const lastDay = new Date(+v[0], m, 0).getDate()
  if (d > lastDay) flowInDatePickerValue.value = [v[0], v[1], '01']
})

// 流动党员开关联动：开启时清空
watch(() => form.value.is_mobile_member, (v) => {
  if (!v) form.value.flow_in_date = ''
})

// ===== 角色/身份 选项（仅展示） =====
const ROLE_OPTIONS = [
  { label: '系统管理员', value: 'system_admin' },
  { label: '街道负责人', value: 'street_lead' },
  { label: '社区组织委员', value: 'community_organizer' },
  { label: '社区组织员', value: 'branch_secretary' },
  { label: '党员', value: 'party_member' },
]
const IDENTITY_OPTIONS = [
  { label: '普通党员', value: '普通党员' },
  { label: '党组织书记', value: '党组织书记' },
  { label: '副书记', value: '副书记' },
  { label: '委员', value: '委员' },
  { label: '流动党员', value: '流动党员' },
]
function identityLabel(v: string) {
  return v
}
function roleLabel(v: string) {
  const o = ROLE_OPTIONS.find((r) => r.value === v)
  return o?.label || v
}

// 角色提示：能选什么
const orgHint = computed(() => {
  const r = role.value
  if (r === 'system_admin') return '你可以选择任何街道/社区/支部'
  if (r === 'street_lead') return '你只能在本街道下选择（街道/社区/支部）'
  if (r === 'community_organizer') return '你只能在本社区下选择（社区/支部）'
  if (r === 'branch_secretary') return '你只能在本支部添加人员'
  return ''
})

// ===== 提交 =====
async function onSubmit() {
  if (submitting.value) return
  errorMsg.value = ''
  if (!form.value.name?.trim()) return void showToast('请填写姓名')
  if (!form.value.phone) return void showToast('请填写手机号')
  if (!form.value.gender) return void showToast('请选择性别')
  if (!form.value.org_level) return void showToast('请选择所属组织')
  if (form.value.is_mobile_member && !form.value.flow_in_date) return void showToast('流动党员必须填写流入日期')

  const payload: any = {
    name: form.value.name.trim(),
    phone: form.value.phone.trim(),
    id_card_no: form.value.id_card_no || null,
    gender: form.value.gender,
    join_date: form.value.join_date || null,
    org_level: form.value.org_level,
    is_mobile_member: form.value.is_mobile_member,
    flow_in_date: form.value.is_mobile_member ? form.value.flow_in_date : null,
    roles: form.value.roles.length ? form.value.roles : null,
    identities: form.value.identities,
    photo_urls: form.value.photo_urls,
  }
  if (form.value.org_level === 'branch') payload.branch_id = form.value.branch_id
  if (form.value.org_level === 'community') payload.community_id = form.value.community_id
  if (form.value.org_level === 'street') payload.street_id = form.value.street_id

  submitting.value = true
  try {
    if (isEdit.value) {
      await membersApi.update(editingId.value!, payload)
      showSuccessToast('已保存')
    } else {
      await membersApi.create(payload)
      showSuccessToast('已创建')
    }
    setTimeout(() => router.replace('/pages/members/list'), 600)
  } catch (e: any) {
    errorMsg.value = e?.message || '保存失败'
  } finally {
    submitting.value = false
  }
}

// ===== 编辑模式：加载现有数据 =====

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

async function loadForEdit() {
  if (!isEdit.value) return
  try {
    const m = await membersApi.get(editingId.value!) as any
    form.value.name = m.name || ''
    form.value.phone = m.phone || ''
    form.value.id_card_no = m.id_card_no || ''
    form.value.gender = m.gender || ''
    form.value.join_date = m.join_date || ''
    form.value.org_level = m.org_level || 'branch'
    form.value.street_id = m.street_id || 0
    form.value.community_id = m.community_id || 0
    form.value.branch_id = m.branch_id || 0
    form.value.roles = Array.isArray(m.roles) ? m.roles : []
    form.value.identities = Array.isArray(m.identities) ? m.identities : []
    form.value.photo_urls = Array.isArray(m.photo_urls) ? [...m.photo_urls] : []
    form.value.is_mobile_member = !!m.is_mobile_member
    form.value.flow_in_date = m.flow_in_date || ''
  } catch (e: any) {
    showToast(e?.message || '加载失败')
  }
}

// 编辑时回填组织选中状态（org_level + id 已经在 loadForEdit 设上）

onMounted(async () => {
  await loadTree()
  await loadForEdit()
})
</script>

<template>
  <div class="page">
    <van-nav-bar
      :title="isEdit ? '编辑人员' : '新增人员'"
      left-text="返回"
      left-arrow
      @click-left="$router.back()"
    />

    <van-cell-group inset title="基本信息" class="cell-group-spaced">
      <van-field
        v-model="form.name"
        label="姓名"
        placeholder="请输入"
        required
        :rules="[{ required: true, message: '请填写姓名' }]"
        maxlength="64"
      />
      <van-field
        v-model="form.phone"
        label="手机号"
        placeholder="11 位手机号"
        type="tel"
        required
        :rules="[{ required: true, message: '请填写手机号' }]"
        maxlength="11"
      />
      <van-field
        v-model="form.id_card_no"
        label="身份证号"
        placeholder="选填"
        maxlength="32"
      />
    </van-cell-group>

    <van-cell-group inset title="所属组织" class="cell-group-spaced">
      <van-cell
        :title="selectedOrgText || '点击选择'"
        :value="orgHint"
        :class="['field-required', !form.org_level ? 'field-missing' : '']"
        is-link
        @click="openOrgPicker"
      />
      <van-cell title="提示" :value="`可选项：${allowedLevels.map(levelLabel).join(' / ')}`" />
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

      <van-cell title="是否流动党员">
        <template #value>
          <van-switch v-model="form.is_mobile_member" />
        </template>
      </van-cell>

      <van-field
        v-if="form.is_mobile_member"
        label="流入日期"
        required
        :rules="[{ required: true, message: '请填写流入日期' }]"
      >
        <template #input>
          <button type="button" class="date-btn" @click.prevent="openFlowInDatePicker">
            {{ displayFlowInDate || '点击选择日期' }}
          </button>
        </template>
      </van-field>
    </van-cell-group>

    <van-cell-group inset title="身份与角色" class="cell-group-spaced">
      <van-cell title="身份标签（多选）">
        <template #value>
          <van-checkbox-group v-model="form.identities" direction="horizontal" style="display:flex;gap:8px;flex-wrap:wrap;">
            <van-checkbox
              v-for="o in IDENTITY_OPTIONS"
              :key="o.value"
              :name="o.value"
              shape="square"
            >{{ o.label }}</van-checkbox>
          </van-checkbox-group>
        </template>
      </van-cell>
      <van-cell title="登录角色（多选）">
        <template #value>
          <van-checkbox-group v-model="form.roles" direction="horizontal" style="display:flex;gap:8px;flex-wrap:wrap;">
            <van-checkbox
              v-for="o in ROLE_OPTIONS"
              :key="o.value"
              :name="o.value"
              shape="square"
            >{{ o.label }}</van-checkbox>
          </van-checkbox-group>
        </template>
      </van-cell>
      <van-cell v-if="form.identities.length" title="已选身份">
        <template #value>
          <span style="font-size:12px;color:#888">{{ form.identities.map(identityLabel).join('、') }}</span>
        </template>
      </van-cell>
      <van-cell v-if="form.roles.length" title="已选角色">
        <template #value>
          <span style="font-size:12px;color:#888">{{ form.roles.map(roleLabel).join('、') }}</span>
        </template>
      </van-cell>
    </van-cell-group>

    <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

    
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

<div class="submit-bar">
      <van-button
        type="primary"
        block
        :loading="submitting"
        :disabled="submitting"
        @click="onSubmit"
      >{{ isEdit ? '保存' : '提交审核' }}</van-button>
    </div>

    <!-- 入党时间选择 -->
    <van-popup
      v-model:show="showJoinDatePicker"
      position="bottom"
      round
      teleport="body"
      :style="{ zIndex: 9999 }"
    >
      <van-picker
        v-model="joinDatePickerValue"
        :columns="joinDatePickerColumns"
        title="选择入党时间"
        @confirm="onJoinDateConfirm"
        @cancel="showJoinDatePicker = false"
      />
    </van-popup>

    <!-- 流入日期选择 -->
    <van-popup
      v-model:show="showFlowInDatePicker"
      position="bottom"
      round
      teleport="body"
      :style="{ zIndex: 9999 }"
    >
      <van-picker
        v-model="flowInDatePickerValue"
        :columns="flowInDatePickerColumns"
        title="选择流入日期"
        @confirm="onFlowInDateConfirm"
        @cancel="showFlowInDatePicker = false"
      />
    </van-popup>

    <!-- 所属组织选择（街道/社区/支部任选一级） -->
    <van-popup v-model:show="showOrgPicker" position="bottom" round>
      <div class="org-picker">
        <div class="org-picker-header">
          <span class="org-picker-back" @click="goBackOrgStep">
            {{ pickerStep === 'street' ? '取消' : '‹ 返回上一级' }}
          </span>
          <span class="org-picker-title">{{ pickerTitle }}</span>
          <span v-if="canPickThisLevel" class="org-picker-pick" @click="pickCurrentLevel">
            选到{{ levelLabel(pickerStep) }}
          </span>
          <span v-else></span>
        </div>
        <div class="org-picker-list">
          <div
            v-for="action in pickerActions"
            :key="`${action.level}-${action.value}`"
            class="org-picker-item"
            :class="{ 'is-current': action.value === (pickerStep === 'street' ? form.street_id : pickerStep === 'community' ? form.community_id : form.branch_id) }"
            @click="onOrgActionSelect(action)"
          >
            <div class="org-picker-item-name">
              {{ action.name }}
              <span v-if="action.subname" class="org-picker-item-sub-inline">{{ action.subname }}</span>
            </div>
            <div
              v-if="(action.level === 'street' && (allowedLevels.includes('community') || allowedLevels.includes('branch'))) ||
                   (action.level === 'community' && allowedLevels.includes('branch'))"
              class="org-picker-item-arrow"
              @click.stop="onOrgItemGotoChildren(action)"
            >›</div>
          </div>
          <div v-if="!pickerActions.length" class="org-picker-empty">无数据</div>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: #F7F8FA;
  padding-bottom: 140px;  /* H5：submit-bar + tab-bar */
}
@media (min-width: 768px) {
  .page { padding-bottom: 80px; }  /* PC：只有 submit-bar */
}
.cell-group-spaced { margin-top: 12px; }
.field-required :deep(.van-field__label::before) {
  content: '*';
  color: #ee0a24;
  margin-right: 2px;
}
.field-missing :deep(.van-cell__title),
.field-missing :deep(.van-field__control) {
  color: #ee0a24 !important;
}
.error-msg {
  margin: 12px 16px;
  padding: 8px 12px;
  background: #FFF1F0;
  color: #B22222;
  border-radius: 6px;
  font-size: 13px;
}
.submit-bar {
  position: fixed;
  left: 0; right: 0;
  bottom: calc(56px + env(safe-area-inset-bottom, 0px));
  background: #fff;
  padding: 8px 16px 16px;
  border-top: 1px solid #eee;
  z-index: 15;
}
/* PC：没有底部 tab 栏，直接贴合底部 */
@media (min-width: 768px) {
  .submit-bar { bottom: 0; }
}
.date-btn {
  border: none;
  background: transparent;
  color: #333;
  font-size: 14px;
  padding: 0;
  cursor: pointer;
  text-align: left;
  width: 100%;
  font-family: inherit;
}

/* 自建组织选择器 */
.org-picker {
  background: #fff;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
}
.org-picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #eee;
  font-size: 14px;
}
.org-picker-back {
  color: #666;
  cursor: pointer;
  min-width: 90px;
  text-align: left;
}
.org-picker-title {
  color: #222;
  font-weight: 600;
  flex: 1;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.org-picker-pick {
  color: #B22222;
  cursor: pointer;
  min-width: 90px;
  text-align: right;
  font-weight: 600;
}
.org-picker-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  max-height: 60vh;
}
.org-picker-item {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background .15s;
}
.org-picker-item:active { background: #f5f5f5; }
.org-picker-item.is-current { background: #FFF0F0; }
.org-picker-item-name {
  flex: 1;
  font-size: 15px;
  color: #222;
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}
.org-picker-item-sub {
  display: none; /* 旧的 subname 独立 div 弃用 */
}
.org-picker-item-sub-inline {
  font-size: 11px;
  color: #B22222;
  font-weight: normal;
}
.org-picker-item-arrow {
  color: #c8c9cc;
  font-size: 22px;
  font-weight: 600;
  flex-shrink: 0;
  padding: 0 4px;
  user-select: none;
}
.org-picker-empty {
  text-align: center;
  color: #999;
  padding: 40px 16px;
  font-size: 14px;
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
