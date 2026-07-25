<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { membersApi, type MemberItem } from '@/api/members'
import { orgsApi, type Branch, type Community } from '@/api/orgs'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const items = ref<MemberItem[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const filterCommunityId = ref<number | null>(null)
const filterBranchId = ref<number | null>(null)

const communities = ref<Community[]>([])
const branches = ref<Branch[]>([])
const filteredBranches = computed(() => {
  if (!filterCommunityId.value) return branches.value
  return branches.value.filter((b) => b.community_id === filterCommunityId.value)
})

async function load() {
  loading.value = true
  try {
    const res = await membersApi.list({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
      community_id: filterCommunityId.value || undefined,
      branch_id: filterBranchId.value || undefined,
    })
    items.value = res.items
    total.value = res.total
  } catch (e: any) {
    uni.showToast({ title: e?.message || '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

async function loadFilters() {
  try {
    if (auth.user?.role === 'system_admin' || auth.user?.role === 'street_lead') {
      communities.value = await orgsApi.communities()
    } else if (auth.user?.community_id) {
      communities.value = await orgsApi.communities(auth.user.street_id || undefined)
    }
    if (auth.user?.role !== 'branch_secretary' && auth.user?.role !== 'member') {
      branches.value = await orgsApi.branches()
    } else if (auth.user?.branch_id) {
      branches.value = [{ id: auth.user.branch_id, community_id: auth.user.community_id || 0, name: '本支部' }]
    }
  } catch (e) {
    console.warn('loadFilters failed', e)
  }
}

function onSearch() {
  page.value = 1
  load()
}

function onNew() {
  uni.navigateTo({ url: '/pages/members/new' })
}

function onImport() {
  uni.navigateTo({ url: '/pages/members/import' })
}

function onItemTap(m: MemberItem) {
  uni.showActionSheet({
    itemList: ['查看详情', '编辑'],
    success: (r) => {
      if (r.tapIndex === 0) {
        uni.showModal({ title: m.name, content: `${m.phone}\n${m.branch_name || ''}`, showCancel: false })
      } else if (r.tapIndex === 1) {
        uni.showToast({ title: '编辑功能待开发', icon: 'none' })
      }
    },
  })
}

onMounted(() => {
  loadFilters()
  load()
})
</script>

<template>
  <view class="page">
    <view class="search-bar">
      <input
        v-model="keyword"
        class="search-input"
        placeholder="搜索姓名/手机号"
        confirm-type="search"
        @confirm="onSearch"
      />
      <view class="search-btn" @click="onSearch">搜索</view>
    </view>

    <view class="filter-row">
      <picker
        v-if="communities.length"
        :value="filterCommunityId ? communities.findIndex((c) => c.id === filterCommunityId) : -1"
        :range="communities"
        range-key="name"
        @change="(e: any) => { filterCommunityId = communities[e.detail.value]?.id || null; filterBranchId = null; page = 1; load(); }"
      >
        <view class="picker">
          {{ communities.find((c) => c.id === filterCommunityId)?.name || '全部社区' }}
        </view>
      </picker>
      <picker
        v-if="branches.length"
        :value="filterBranchId ? filteredBranches.findIndex((b) => b.id === filterBranchId) : -1"
        :range="filteredBranches"
        range-key="name"
        @change="(e: any) => { filterBranchId = filteredBranches[e.detail.value]?.id || null; page = 1; load(); }"
      >
        <view class="picker">
          {{ filteredBranches.find((b) => b.id === filterBranchId)?.name || '全部支部' }}
        </view>
      </picker>
    </view>

    <view class="actions">
      <view class="total">共 {{ total }} 名党员</view>
      <view class="btn-row">
        <view class="btn btn-secondary" @click="onImport">批量导入</view>
        <view class="btn btn-primary" @click="onNew">+ 新增党员</view>
      </view>
    </view>

    <view v-if="loading" class="loading">加载中…</view>

    <view v-else-if="!items.length" class="empty">
      <view class="empty-icon">👥</view>
      <view>暂无党员数据</view>
      <view class="empty-tip">点击右上角"新增党员"开始</view>
    </view>

    <view v-else class="list">
      <view v-for="m in items" :key="m.id" class="item" @click="onItemTap(m)">
        <view class="avatar">{{ m.name.charAt(0) }}</view>
        <view class="info">
          <view class="name">{{ m.name }}</view>
          <view class="meta">
            <text class="phone">{{ m.phone }}</text>
            <text class="branch" v-if="m.branch_name"> · {{ m.branch_name }}</text>
          </view>
        </view>
        <view class="arrow">›</view>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  background: #F7F8FA;
  padding: 0 24rpx 32rpx;
}

.search-bar {
  display: flex;
  align-items: center;
  padding: 24rpx 0;
  gap: 16rpx;
}
.search-input {
  flex: 1;
  height: 72rpx;
  background: #fff;
  border-radius: 12rpx;
  padding: 0 24rpx;
  font-size: 28rpx;
  border: 1rpx solid #eee;
}
.search-btn {
  height: 72rpx;
  line-height: 72rpx;
  padding: 0 28rpx;
  background: #B22222;
  color: #fff;
  border-radius: 12rpx;
  font-size: 28rpx;
}

.filter-row {
  display: flex;
  gap: 16rpx;
  margin-bottom: 16rpx;
}
.picker {
  flex: 1;
  height: 64rpx;
  line-height: 64rpx;
  padding: 0 20rpx;
  background: #fff;
  border: 1rpx solid #eee;
  border-radius: 10rpx;
  font-size: 26rpx;
  color: #333;
}

.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20rpx;
}
.total { font-size: 24rpx; color: #888; }
.btn-row { display: flex; gap: 12rpx; }
.btn {
  height: 56rpx;
  line-height: 56rpx;
  padding: 0 20rpx;
  border-radius: 10rpx;
  font-size: 24rpx;
}
.btn-secondary {
  background: #fff;
  color: #B22222;
  border: 1rpx solid #B22222;
}
.btn-primary {
  background: #B22222;
  color: #fff;
}

.loading, .empty {
  text-align: center;
  padding: 80rpx 0;
  color: #888;
  font-size: 28rpx;
}
.empty-icon { font-size: 80rpx; margin-bottom: 16rpx; }
.empty-tip { font-size: 24rpx; color: #bbb; margin-top: 8rpx; }

.list { display: flex; flex-direction: column; gap: 16rpx; }
.item {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 14rpx;
  padding: 24rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
}
.avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  background: #FFE4E1;
  color: #B22222;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
  font-weight: 600;
  margin-right: 20rpx;
}
.info { flex: 1; min-width: 0; }
.name { font-size: 30rpx; font-weight: 600; color: #222; }
.meta { font-size: 24rpx; color: #888; margin-top: 6rpx; }
.arrow { color: #ccc; font-size: 40rpx; }
</style>
