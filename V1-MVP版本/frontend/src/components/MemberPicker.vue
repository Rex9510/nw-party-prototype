<script setup lang="ts">
/**
 * 党员选择器：按支部筛选 + 多选
 * props: modelValue (number[]), branchId
 * emits: update:modelValue, change
 */
import { ref, watch } from 'vue'
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

watch(
  () => props.modelValue,
  (v) => {
    selected.value = new Set(v)
  },
)

watch(
  () => props.branchId,
  async (b) => {
    if (b) {
      loading.value = true
      try {
        const res = await membersApi.list({ branch_id: b, page_size: 100 })
        members.value = res.items
      } catch (e) {
        console.warn(e)
      } finally {
        loading.value = false
      }
    } else {
      members.value = []
    }
    selected.value = new Set()
    emitChange()
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

const filteredMembers = () => {
  if (!keyword.value) return members.value
  const k = keyword.value.toLowerCase()
  return members.value.filter(
    (m) => m.name.toLowerCase().includes(k) || m.phone.includes(k),
  )
}
</script>

<template>
  <view class="picker">
    <view class="picker-header" @click="showPicker = !showPicker">
      <text class="label">选择参加党员</text>
      <text class="count">已选 {{ selected.size }} 人</text>
    </view>

    <view v-if="showPicker" class="picker-body">
      <view class="picker-toolbar">
        <input v-model="keyword" class="search" placeholder="搜索姓名/手机号" />
        <view class="toolbar-btn" @click="selectAll">全选</view>
        <view class="toolbar-btn" @click="clearAll">清空</view>
      </view>

      <view v-if="!branchId" class="empty">请先选择支部</view>
      <view v-else-if="loading" class="empty">加载中…</view>
      <view v-else-if="!members.length" class="empty">该支部暂无党员</view>

      <scroll-view v-else scroll-y class="member-list">
        <view
          v-for="m in filteredMembers()"
          :key="m.id"
          class="member-row"
          :class="{ active: selected.has(m.id) }"
          @click="toggle(m.id)"
        >
          <view class="check">{{ selected.has(m.id) ? '✓' : '' }}</view>
          <view class="info">
            <view class="name">{{ m.name }}</view>
            <view class="phone">{{ m.phone }}</view>
          </view>
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.picker {
  background: #fff;
  border-radius: 12rpx;
  border: 1rpx solid #f0f0f0;
}
.picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24rpx;
  cursor: pointer;
}
.label { font-size: 28rpx; color: #222; font-weight: 600; }
.count {
  font-size: 24rpx;
  color: #B22222;
  background: #FFF0F0;
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
}
.picker-body {
  border-top: 1rpx solid #f0f0f0;
  max-height: 600rpx;
  display: flex;
  flex-direction: column;
}
.picker-toolbar {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 16rpx 24rpx;
  border-bottom: 1rpx solid #f0f0f0;
}
.search {
  flex: 1;
  height: 60rpx;
  background: #f5f5f5;
  border-radius: 8rpx;
  padding: 0 16rpx;
  font-size: 26rpx;
}
.toolbar-btn {
  font-size: 24rpx;
  color: #B22222;
  padding: 8rpx 16rpx;
  background: #FFF0F0;
  border-radius: 8rpx;
}
.empty {
  text-align: center;
  padding: 60rpx;
  color: #999;
  font-size: 26rpx;
}
.member-list { max-height: 500rpx; }
.member-row {
  display: flex;
  align-items: center;
  padding: 20rpx 24rpx;
  border-bottom: 1rpx solid #f5f5f5;
  cursor: pointer;
}
.member-row.active { background: #FFF0F0; }
.check {
  width: 36rpx;
  height: 36rpx;
  border: 2rpx solid #ddd;
  border-radius: 50%;
  margin-right: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  color: #fff;
  background: #fff;
}
.member-row.active .check {
  background: #B22222;
  border-color: #B22222;
  color: #fff;
}
.info { flex: 1; }
.name { font-size: 28rpx; color: #222; }
.phone { font-size: 22rpx; color: #999; margin-top: 4rpx; }
</style>
