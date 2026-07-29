<script setup lang="ts">
/**
 * 党员选择器 v3：先选人员范围（街道/社区/支部单选；多选支部）→ 加载该范围人员 → 多选
 *
 * props:
 *  - modelValue: number[] 已选党员 id
 *  - initialBranchId?: number 编辑模式默认选中范围 = 某个支部
 * emits:
 *  - update:modelValue
 *  - change
 */
import { ref, watch, computed } from 'vue'
import { membersApi, type MemberItem } from '@/api/members'
import { orgsApi, type StreetTreeNode, type Branch, type Community } from '@/api/orgs'

const props = defineProps<{
  modelValue: number[]
  initialBranchIds?: number[] | null
}>()

const emit = defineEmits<{
  'update:modelValue': [v: number[]]
  change: [v: number[]]
}>()

const showPicker = ref(false)
const tree = ref<StreetTreeNode[]>([])
const members = ref<MemberItem[]>([])
const selected = ref<Set<number>>(new Set(props.modelValue))
const loading = ref(false)
const keyword = ref('')

// ===== 范围选择 =====
// scope 形态：单选 street/community/branch（branch 可多选，街道/社区只能单选）
type ScopeType = 'street' | 'community' | 'branch'
const scopeType = ref<ScopeType>('branch')
const selectedBranchIds = ref<number[]>([])  // 单选时 [id]；多选 [id, id...]
const selectedCommunityId = ref<number>(0)
const selectedStreetId = ref<number>(0)

const showScopePicker = ref(false)
const scopePickerStep = ref<'street' | 'community' | 'branch'>('street')

const scopeBranches = computed<Branch[]>(() => {
  // 当前选中的所有社区 → 这些社区下的全部支部（用于「多选支部」）
  if (scopeType.value === 'branch') {
    // 选某个社区/街道下所有支部
    const result: Branch[] = []
    for (const s of tree.value) {
      if (scopeType.value === 'branch' && selectedStreetId.value && s.id !== selectedStreetId.value) continue
      for (const c of s.communities || []) {
        if (selectedCommunityId.value && c.id !== selectedCommunityId.value) continue
        for (const b of (c.branches || [])) result.push(b)
      }
    }
    return result
  }
  return []
})

const scopeText = computed(() => {
  if (scopeType.value === 'street' && selectedStreetId.value) {
    const s = tree.value.find(x => x.id === selectedStreetId.value)
    return s ? `街道：${s.name}（含全部社区/支部）` : ''
  }
  if (scopeType.value === 'community' && selectedCommunityId.value) {
    for (const s of tree.value) {
      const c = s.communities?.find(x => x.id === selectedCommunityId.value)
      if (c) return `社区：${s.name} / ${c.name}（含全部支部）`
    }
    return ''
  }
  if (scopeType.value === 'branch' && selectedBranchIds.value.length) {
    const names: string[] = []
    for (const s of tree.value) {
      for (const c of s.communities || []) {
        for (const b of (c.branches || [])) {
          if (selectedBranchIds.value.includes(b.id)) names.push(b.name)
        }
      }
    }
    return `支部（${selectedBranchIds.value.length}）：${names.join('、')}`
  }
  return ''
})

function openScopePicker() {
  scopePickerStep.value = 'street'
  showScopePicker.value = true
}

function onScopeTypeChange(t: ScopeType) {
  scopeType.value = t
  selectedBranchIds.value = []
  selectedCommunityId.value = 0
  selectedStreetId.value = 0
  // 切到街道/社区时直接加载全部人员；切到支部时不自动加载，等用户选完
  loadMembers()
}

function onStreetSelect(s: { id: number; name: string }) {
  if (scopeType.value === 'street') {
    selectedStreetId.value = s.id
    selectedCommunityId.value = 0
    selectedBranchIds.value = []
    showScopePicker.value = false
    loadMembers()
  } else {
    // 切到下一步：社区
    selectedStreetId.value = s.id
    selectedCommunityId.value = 0
    scopePickerStep.value = 'community'
  }
}

function onCommunitySelect(c: { id: number; name: string }) {
  if (scopeType.value === 'community') {
    selectedCommunityId.value = c.id
    selectedBranchIds.value = []
    showScopePicker.value = false
    loadMembers()
  } else if (scopeType.value === 'branch') {
    // 切到下一步：支部
    selectedCommunityId.value = c.id
    scopePickerStep.value = 'branch'
  }
}

function toggleBranch(b: { id: number; name: string }) {
  if (scopeType.value !== 'branch') return
  const idx = selectedBranchIds.value.indexOf(b.id)
  if (idx >= 0) selectedBranchIds.value.splice(idx, 1)
  else selectedBranchIds.value.push(b.id)
}

function confirmBranchScope() {
  if (selectedBranchIds.value.length === 0) return
  showScopePicker.value = false
  loadMembers()
}

function getStepActions() {
  if (scopePickerStep.value === 'street') {
    return tree.value.map(s => ({
      id: s.id,
      name: s.name,
      subname: s.communities?.length ? `${s.communities.length} 个社区` : '',
    }))
  }
  if (scopePickerStep.value === 'community') {
    const s = tree.value.find(x => x.id === selectedStreetId.value)
    return s?.communities?.map(c => ({
      id: c.id,
      name: c.name,
      subname: c.branches?.length ? `${c.branches.length} 个支部` : '',
    })) || []
  }
  // branch step
  const s = tree.value.find(x => x.id === selectedStreetId.value)
  const c = s?.communities?.find(x => x.id === selectedCommunityId.value)
  return c?.branches?.map(b => ({
    id: b.id,
    name: b.name,
    subname: selectedBranchIds.value.includes(b.id) ? '✓ 已选' : '',
  })) || []
}

const showConfirmBtn = computed(() => scopePickerStep.value === 'branch' && selectedBranchIds.value.length > 0)

function goBackScope() {
  if (scopePickerStep.value === 'branch') scopePickerStep.value = 'community'
  else if (scopePickerStep.value === 'community') scopePickerStep.value = 'street'
  else showScopePicker.value = false
}

// ===== 加载成员列表 =====
async function loadMembers() {
  loading.value = true
  try {
    let items: MemberItem[] = []
    if (scopeType.value === 'street' && selectedStreetId.value) {
      // 拉本街道所有人员（按 street_id 过滤，后端 list 接受）
      const r = await membersApi.list({ street_id: selectedStreetId.value, page_size: 100 })
      items = r.items
    } else if (scopeType.value === 'community' && selectedCommunityId.value) {
      const r = await membersApi.list({ community_id: selectedCommunityId.value, page_size: 100 })
      items = r.items
    } else if (scopeType.value === 'branch' && selectedBranchIds.value.length) {
      // 多选支部：分次拉，再合并去重
      const map = new Map<number, MemberItem>()
      for (const bid of selectedBranchIds.value) {
        const r = await membersApi.list({ branch_id: bid, page_size: 100 })
        for (const m of r.items) if (!map.has(m.id)) map.set(m.id, m)
      }
      items = Array.from(map.values())
    }
    members.value = items
  } catch (e) {
    console.warn('[MemberPicker] loadMembers failed', e)
    members.value = []
  } finally {
    loading.value = false
  }
}

const filteredMembers = computed(() => {
  if (!keyword.value) return members.value
  const k = keyword.value.toLowerCase()
  return members.value.filter(
    (m) => m.name.toLowerCase().includes(k) || m.phone.includes(k),
  )
})

// ===== 多选 =====
function toggle(id: number) {
  if (selected.value.has(id)) selected.value.delete(id)
  else selected.value.add(id)
  emitChange()
}

function emitChange() {
  const arr = Array.from(selected.value)
  emit('update:modelValue', arr)
  emit('change', arr)
}

function clearAll() {
  selected.value.clear()
  emitChange()
}

function selectAll() {
  members.value.forEach((m) => selected.value.add(m.id))
  emitChange()
}

// ===== 编辑模式回显：默认 scope = initialBranchIds 那些支部 =====
watch(
  () => props.modelValue,
  (v) => {
    const incoming = new Set(v)
    if (incoming.size !== selected.value.size || ![...incoming].every((id) => selected.value.has(id))) {
      selected.value = incoming
    }
  },
  { immediate: true },
)

// 编辑模式：initialBranchIds 异步进来时（从 loadActivity() 拿到活动数据后），
// 如果 scope 还是空的、tree 已经加载好，再跑一次回填
watch(
  () => props.initialBranchIds,
  async (ids) => {
    const branchIds = (ids || []).filter((x): x is number => typeof x === 'number')
    if (!branchIds.length) return
    if (selectedBranchIds.value.length) return  // 已经填过，不重复
    if (!tree.value.length) return  // tree 还没加载，等 loadTree 自己处理
    scopeType.value = 'branch'
    selectedBranchIds.value = [...branchIds]
    for (const s of tree.value) {
      for (const c of s.communities || []) {
        for (const b of (c.branches || [])) {
          if (b.id === branchIds[0]) {
            selectedStreetId.value = s.id
            selectedCommunityId.value = c.id
            break
          }
        }
        if (selectedCommunityId.value) break
      }
      if (selectedStreetId.value) break
    }
    await loadMembers()
  },
)

// 所属组织显示：按 org_level 取对应级别的名字
function memberOrg(m: MemberItem): string {
  if (m.org_level === 'street' && m.street_name) return m.street_name
  if (m.org_level === 'community' && m.community_name) return m.community_name
  if (m.org_level === 'branch' && m.branch_name) return m.branch_name
  return m.org_level || ''
}

// 加载组织树
async function loadTree() {
  try {
    tree.value = await orgsApi.tree()
    // 编辑模式：默认 scope 设为 initialBranchIds
    const branchIds = props.initialBranchIds?.filter((x): x is number => typeof x === 'number') || []
    if (branchIds.length) {
      scopeType.value = 'branch'
      selectedBranchIds.value = [...branchIds]
      // 反推 street/community（取第一个支部的父级）
      for (const s of tree.value) {
        for (const c of s.communities || []) {
          for (const b of (c.branches || [])) {
            if (b.id === branchIds[0]) {
              selectedStreetId.value = s.id
              selectedCommunityId.value = c.id
              break
            }
          }
          if (selectedCommunityId.value) break
        }
        if (selectedStreetId.value) break
      }
      // 加载这些支部的人员，这样展开时能直接看到已选 + 其他人员
      await loadMembers()
    }
  } catch (e) {
    console.warn('[MemberPicker] loadTree failed', e)
  }
}

loadTree()
</script>

<template>
  <div class="picker">
    <div class="picker-row">
      <div class="picker-label">参加人员范围</div>
      <div class="picker-scope" :class="{ empty: !scopeText }" @click="openScopePicker">
        <span>{{ scopeText || '点击选择范围' }}</span>
        <span class="arrow">›</span>
      </div>
    </div>
    <div class="picker-row">
      <div class="picker-label">选择人员</div>
      <div class="picker-toggle" @click="showPicker = !showPicker">
        <span class="count">已选 {{ selected.size }} 人</span>
        <span class="arrow">{{ showPicker ? '收起' : '展开' }} ▾</span>
      </div>
    </div>

    <div v-if="showPicker" class="picker-body">
      <div class="picker-toolbar">
        <input v-model="keyword" class="search" placeholder="搜索姓名/手机号" />
        <div class="toolbar-btn" @click="selectAll">全选</div>
        <div class="toolbar-btn" @click="clearAll">清空</div>
      </div>

      <div v-if="!scopeText" class="empty">请先选择人员范围</div>
      <div v-else-if="loading" class="empty">加载中…</div>
      <div v-else-if="!members.length" class="empty">该范围暂无人员</div>

      <div v-else class="member-list">
        <div
          v-for="m in filteredMembers"
          :key="m.id"
          class="member-row"
          :class="{ active: selected.has(m.id) }"
          @click="toggle(m.id)"
        >
          <div class="check">{{ selected.has(m.id) ? '✓' : '' }}</div>
          <div class="info">
            <div class="name">
              {{ m.name }}
              <span v-if="memberOrg(m)" class="org">{{ memberOrg(m) }}</span>
            </div>
            <div class="phone">{{ m.phone }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 范围选择器：3 步走 popup（街道 → 社区 → 支部），中间弹窗 -->
  <van-popup v-model:show="showScopePicker" position="center" round :style="{ width: '90%', maxWidth: '500px', maxHeight: '70vh' }">
    <div class="scope-picker">
      <div class="scope-header">
        <span class="scope-back" @click="goBackScope">
          {{ scopePickerStep === 'street' ? '取消' : '‹ 返回上一级' }}
        </span>
        <span class="scope-title">
          {{ scopePickerStep === 'street' ? '选择街道' : scopePickerStep === 'community' ? '选择社区' : '选择支部（可多选）' }}
        </span>
        <span v-if="showConfirmBtn" class="scope-confirm" @click="confirmBranchScope">确定</span>
        <span v-else></span>
      </div>

      <!-- scope 类型选择 tab（仅 street step 显示） -->
      <div v-if="scopePickerStep === 'street'" class="scope-tabs">
        <div
          v-for="t in [{k:'street',l:'按街道'},{k:'community',l:'按社区'},{k:'branch',l:'按支部'}]"
          :key="t.k"
          class="scope-tab"
          :class="{ active: scopeType === t.k }"
          @click="onScopeTypeChange(t.k as ScopeType)"
        >{{ t.l }}</div>
      </div>

      <div class="scope-list">
        <div
          v-for="a in getStepActions()"
          :key="a.id"
          class="scope-item"
          :class="{ active: scopePickerStep === 'branch' && selectedBranchIds.includes(a.id) }"
          @click="scopePickerStep === 'street' ? onStreetSelect(a)
                : scopePickerStep === 'community' ? onCommunitySelect(a)
                : toggleBranch(a)"
        >
          <div class="scope-item-name">{{ a.name }}</div>
          <div v-if="a.subname" class="scope-item-sub">{{ a.subname }}</div>
        </div>
        <div v-if="!getStepActions().length" class="empty">无数据</div>
      </div>

      <div v-if="scopePickerStep === 'branch' && selectedBranchIds.length" class="scope-selected">
        已选 {{ selectedBranchIds.length }} 个支部
      </div>
    </div>
  </van-popup>
</template>

<style scoped>
.picker {
  background: #fff;
  border-radius: 6px;
  border: 1px solid #f0f0f0;
}
.picker-row {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid #f5f5f5;
  gap: 8px;
}
.picker-row:last-child { border-bottom: none; }
.picker-label {
  font-size: 13px;
  color: #666;
  flex-shrink: 0;
  min-width: 80px;
}
.picker-scope {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  color: #222;
  cursor: pointer;
  min-height: 22px;
}
.picker-scope.empty { color: #999; }
.picker-toggle {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  color: #222;
  cursor: pointer;
}
.count {
  font-size: 12px;
  color: #B22222;
  background: #FFF0F0;
  padding: 2px 8px;
  border-radius: 4px;
}
.arrow { color: #999; font-size: 12px; }
.picker-body {
  border-top: 1px solid #f0f0f0;
  max-height: 300px;
  display: flex;
  flex-direction: column;
}
.picker-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
}
.search {
  flex: 1;
  height: 30px;
  background: #f5f5f5;
  border-radius: 4px;
  padding: 0 8px;
  font-size: 13px;
  border: none;
  outline: none;
}
.toolbar-btn {
  font-size: 12px;
  color: #B22222;
  padding: 4px 8px;
  background: #FFF0F0;
  border-radius: 4px;
  cursor: pointer;
}
.empty {
  text-align: center;
  padding: 30px;
  color: #999;
  font-size: 13px;
}
.member-list { max-height: 250px; overflow-y: auto; }
.member-row {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
}
.member-row:hover { background: #fafafa; }
.member-row.active { background: #FFF0F0; }
.check {
  width: 18px;
  height: 18px;
  border: 1px solid #ddd;
  border-radius: 50%;
  margin-right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: transparent;
  background: #fff;
  flex-shrink: 0;
}
.member-row.active .check {
  background: #B22222;
  border-color: #B22222;
  color: #fff;
}
.info { flex: 1; min-width: 0; }
.name { font-size: 14px; color: #222; }
.org {
  font-size: 11px;
  color: #888;
  background: #f5f5f5;
  padding: 1px 6px;
  border-radius: 3px;
  margin-left: 6px;
  font-weight: normal;
  vertical-align: middle;
}
.phone { font-size: 12px; color: #999; margin-top: 2px; }

/* 范围选择器 */
.scope-picker {
  background: #fff;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
}
.scope-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #eee;
  font-size: 14px;
}
.scope-back { color: #666; cursor: pointer; min-width: 90px; }
.scope-title { color: #222; font-weight: 600; flex: 1; text-align: center; }
.scope-confirm {
  color: #B22222;
  cursor: pointer;
  min-width: 90px;
  text-align: right;
  font-weight: 600;
}
.scope-tabs {
  display: flex;
  border-bottom: 1px solid #eee;
}
.scope-tab {
  flex: 1;
  text-align: center;
  padding: 10px;
  font-size: 14px;
  color: #666;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}
.scope-tab.active {
  color: #B22222;
  border-bottom-color: #B22222;
  font-weight: 600;
}
.scope-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  max-height: 50vh;
}
.scope-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  font-size: 14px;
}
.scope-item:hover { background: #fafafa; }
.scope-item.active { background: #FFF0F0; }
.scope-item-name { color: #222; }
.scope-item-sub { color: #999; font-size: 12px; }
.scope-selected {
  text-align: center;
  padding: 8px;
  font-size: 12px;
  color: #B22222;
  border-top: 1px solid #f0f0f0;
  background: #FFF0F0;
}
</style>
