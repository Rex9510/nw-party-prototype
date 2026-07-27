<script setup lang="ts">
/**
 * 党员选择器：按支部筛选 + 多选
 * props: modelValue (number[]), branchId
 * emits: update:modelValue, change
 */
import { ref, watch, computed } from 'vue'
import { membersApi, type MemberItem } from '@/api/members'

const props = defineProps<{
  modelValue: number[]
  branchId: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [v: number[]]
  change: [v: number[]]
}>()

const showPicker = ref(false)
const members = ref<MemberItem[]>([])
const selected = ref<Set<number>>(new Set(props.modelValue))
const loading = ref(false)
const keyword = ref('')

// 调试日志：把关键状态打到 console，方便排查"回显丢失"
if (typeof window !== 'undefined') {
  console.log('[MemberPicker] setup: modelValue=', props.modelValue, 'branchId=', props.branchId, 'selectedInit=', Array.from(selected.value))
}

watch(
  () => props.modelValue,
  (v) => {
    const incoming = new Set(v)
    console.log('[MemberPicker] modelValue changed ->', v, 'current selected=', Array.from(selected.value))
    if (
      incoming.size !== selected.value.size ||
      ![...incoming].every((id) => selected.value.has(id))
    ) {
      selected.value = incoming
      console.log('[MemberPicker] selected updated ->', Array.from(selected.value))
    }
  },
  { immediate: true },
)

watch(
  () => props.branchId,
  async (b) => {
    console.log('[MemberPicker] branchId changed ->', b)
    if (b) {
      loading.value = true
      try {
        const res = await membersApi.list({ branch_id: b, page_size: 100 })
        members.value = res.items
        console.log('[MemberPicker] members loaded, count=', res.items.length, 'selected=', Array.from(selected.value))
      } catch (e) {
        console.warn(e)
      } finally {
        loading.value = false
      }
    } else {
      members.value = []
    }
  },
  { immediate: true },
)

function toggle(id: number) {
  if (selected.value.has(id)) {
    selected.value.delete(id)
  } else {
    selected.value.add(id)
  }
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

const filteredMembers = computed(() => {
  if (!keyword.value) return members.value
  const k = keyword.value.toLowerCase()
  return members.value.filter(
    (m) => m.name.toLowerCase().includes(k) || m.phone.includes(k),
  )
})
</script>

<template>
  <div class="picker">
    <div class="picker-header" @click="showPicker = !showPicker">
      <span class="label">选择参加人员</span>
      <span class="count">已选 {{ selected.size }} 人</span>
    </div>

    <div v-if="showPicker" class="picker-body">
      <div class="picker-toolbar">
        <input v-model="keyword" class="search" placeholder="搜索姓名/手机号" />
        <div class="toolbar-btn" @click="selectAll">全选</div>
        <div class="toolbar-btn" @click="clearAll">清空</div>
      </div>

      <div v-if="!branchId" class="empty">请先选择支部</div>
      <div v-else-if="loading" class="empty">加载中…</div>
      <div v-else-if="!members.length" class="empty">该支部暂无人员</div>

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
            <div class="name">{{ m.name }}</div>
            <div class="phone">{{ m.phone }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.picker {
  background: #fff;
  border-radius: 6px;
  border: 1px solid #f0f0f0;
}
.picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  cursor: pointer;
}
.label { font-size: 14px; color: #222; font-weight: 600; }
.count {
  font-size: 12px;
  color: #B22222;
  background: #FFF0F0;
  padding: 2px 8px;
  border-radius: 4px;
}
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
.phone { font-size: 12px; color: #999; margin-top: 2px; }
</style>
