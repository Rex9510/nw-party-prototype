<script setup lang="ts">
/**
 * 系统配置后台
 * - system_admin：完整权限（街道/社区/支部/字典全可管）
 * - street_lead：可进，只能管本街道下的社区/支部
 */
import { ref, computed, onMounted } from 'vue'
import { showToast, showSuccessToast, showConfirmDialog } from 'vant'
import {
  orgsApi,
  type Street,
  type Community,
  type Branch,
} from '@/api/orgs'
import {
  dictsApi,
  type DictItem,
} from '@/api/dicts'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const isAdmin = computed(() => auth.user?.role === 'system_admin')
const isStreetLead = computed(() => auth.user?.role === 'street_lead')

const activeTab = ref<'org' | 'category' | 'source'>('org')

// =================== 组织架构 ===================
const streets = ref<Street[]>([])
const communities = ref<Community[]>([])
const branches = ref<Branch[]>([])
const selectedStreetId = ref<number | null>(null)
const selectedCommunityId = ref<number | null>(null)
const orgLoading = ref(false)
const movingId = ref<number | null>(null)

const selectedStreet = computed(() =>
  streets.value.find((s) => s.id === selectedStreetId.value) || null,
)
const selectedCommunity = computed(() =>
  communities.value.find((c) => c.id === selectedCommunityId.value) || null,
)
const filteredCommunities = computed(() =>
  communities.value
    .filter((c) => c.street_id === selectedStreetId.value)
    .slice()
    .sort((a, b) => a.sort - b.sort || a.id - b.id),
)
const filteredBranches = computed(() =>
  branches.value
    .filter((b) => b.community_id === selectedCommunityId.value)
    .slice()
    .sort((a, b) => a.sort - b.sort || a.id - b.id),
)

const sortedStreets = computed(() =>
  streets.value.slice().sort((a, b) => a.sort - b.sort || a.id - b.id),
)
const sortedCommunities = computed(() =>
  communities.value.slice().sort((a, b) => a.sort - b.sort || a.id - b.id),
)
const sortedBranches = computed(() =>
  branches.value.slice().sort((a, b) => a.sort - b.sort || a.id - b.id),
)

async function loadOrg() {
  orgLoading.value = true
  try {
    // 街道：街道负责人只看自己这条
    const allStreets = await orgsApi.streets()
    if (isStreetLead.value && auth.user?.street_id) {
      streets.value = allStreets.filter((s) => s.id === auth.user!.street_id)
    } else {
      streets.value = allStreets
    }
    if (sortedStreets.value.length && !selectedStreetId.value) {
      selectedStreetId.value = sortedStreets.value[0].id
    }
    // 社区：街道负责人只看自己街道下的
    if (isStreetLead.value && auth.user?.street_id) {
      communities.value = await orgsApi.communities(auth.user.street_id)
    } else {
      communities.value = await orgsApi.communities()
    }
    // 支部：过滤到当前用户可见的社区下
    branches.value = await orgsApi.branches()
    if (isStreetLead.value) {
      const visibleCommunityIds = new Set(communities.value.map((c) => c.id))
      branches.value = branches.value.filter((b) => visibleCommunityIds.has(b.community_id))
    }
    if (filteredCommunities.value.length && !selectedCommunityId.value) {
      selectedCommunityId.value = filteredCommunities.value[0].id
    }
  } catch (e: any) {
    showToast({ message: e?.message || '加载失败', type: 'fail' })
  } finally {
    orgLoading.value = false
  }
}

function selectStreet(id: number) {
  selectedStreetId.value = id
  // 重置社区选中
  const first = filteredCommunities.value.find((c) => c.street_id === id)
  selectedCommunityId.value = first?.id || null
}

function communityCount(streetId: number) {
  return communities.value.filter((c) => c.street_id === streetId).length
}
function branchCount(communityId: number) {
  return branches.value.filter((b) => b.community_id === communityId).length
}

// 通用：调 API 上下移某条（list 局部 reorder）
async function moveItem<T extends { id: number; sort: number }>(
  list: T[],
  item: T,
  direction: 'up' | 'down',
  apiCall: (id: number) => Promise<any>,
  reload: () => Promise<void>,
) {
  if (movingId.value) return
  movingId.value = item.id
  try {
    const updated = direction === 'up'
      ? await apiCall(item.id)
      : await apiCall(item.id)
    // 简单做法：调一次 reload，保证 sort 与服务端一致
    await reload()
  } catch (e: any) {
    showToast({ message: e?.message || '移动失败', type: 'fail' })
  } finally {
    movingId.value = null
  }
}

// 街道上下移（仅 admin 可见按钮，街道负责人看不到）
async function moveStreet(s: Street, dir: 'up' | 'down') {
  await moveItem(
    sortedStreets.value,
    s,
    dir,
    dir === 'up' ? orgsApi.moveStreetUp : orgsApi.moveStreetDown,
    async () => {
      const all = await orgsApi.streets()
      if (isStreetLead.value && auth.user?.street_id) {
        streets.value = all.filter((x) => x.id === auth.user!.street_id)
      } else {
        streets.value = all
      }
    },
  )
}

// 社区上下移
async function moveCommunity(c: Community, dir: 'up' | 'down') {
  await moveItem(
    filteredCommunities.value,
    c,
    dir,
    dir === 'up' ? orgsApi.moveCommunityUp : orgsApi.moveCommunityDown,
    async () => {
      if (isStreetLead.value && auth.user?.street_id) {
        communities.value = await orgsApi.communities(auth.user.street_id)
      } else {
        communities.value = await orgsApi.communities()
      }
    },
  )
}

// 支部上下移
async function moveBranch(b: Branch, dir: 'up' | 'down') {
  await moveItem(
    filteredBranches.value,
    b,
    dir,
    dir === 'up' ? orgsApi.moveBranchUp : orgsApi.moveBranchDown,
    async () => {
      branches.value = await orgsApi.branches()
      if (isStreetLead.value) {
        const visibleCommunityIds = new Set(communities.value.map((c) => c.id))
        branches.value = branches.value.filter((x) => visibleCommunityIds.has(x.community_id))
      }
    },
  )
}

// 街道
const streetDialog = ref<{ show: boolean; mode: 'add' | 'edit'; id?: number; name: string }>({
  show: false, mode: 'add', name: '',
})
function openAddStreet() {
  streetDialog.value = { show: true, mode: 'add', name: '' }
}
function openEditStreet(s: Street) {
  streetDialog.value = { show: true, mode: 'edit', id: s.id, name: s.name }
}
async function saveStreet() {
  if (!streetDialog.value.name.trim()) {
    showToast({ message: '请输入名称', type: 'fail' })
    return
  }
  try {
    if (streetDialog.value.mode === 'add') {
      const s = await orgsApi.createStreet(streetDialog.value.name.trim())
      streets.value.push(s)
      if (!selectedStreetId.value) selectedStreetId.value = s.id
    } else if (streetDialog.value.id) {
      await orgsApi.updateStreet(streetDialog.value.id, streetDialog.value.name.trim())
    }
    showSuccessToast({ message: '保存成功' })
    streetDialog.value.show = false
  } catch (e: any) {
    showToast({ message: e?.message || '保存失败', type: 'fail' })
  }
}
async function deleteStreet(s: Street) {
  try {
    await showConfirmDialog({
      title: '确认删除',
      message: `删除街道「${s.name}」？该街道下还有 ${communityCount(s.id)} 个社区将一并检查`,
    })
    await orgsApi.deleteStreet(s.id)
    streets.value = streets.value.filter((x) => x.id !== s.id)
    if (selectedStreetId.value === s.id) {
      selectedStreetId.value = streets.value[0]?.id || null
    }
    showSuccessToast({ message: '已删除' })
  } catch (e: any) {
    if (e?.message) showToast({ message: e.message, type: 'fail' })
  }
}

// 社区
const communityDialog = ref<{ show: boolean; mode: 'add' | 'edit'; id?: number; name: string }>({
  show: false, mode: 'add', name: '',
})
function openAddCommunity() {
  if (!selectedStreetId.value) {
    showToast({ message: '请先选择街道', type: 'fail' })
    return
  }
  communityDialog.value = { show: true, mode: 'add', name: '' }
}
function openEditCommunity(c: Community) {
  communityDialog.value = { show: true, mode: 'edit', id: c.id, name: c.name }
}
async function saveCommunity() {
  if (!communityDialog.value.name.trim()) {
    showToast({ message: '请输入名称', type: 'fail' })
    return
  }
  if (!selectedStreetId.value) return
  try {
    if (communityDialog.value.mode === 'add') {
      const c = await orgsApi.createCommunity(selectedStreetId.value, communityDialog.value.name.trim())
      communities.value.push(c)
      if (!selectedCommunityId.value) selectedCommunityId.value = c.id
    } else if (communityDialog.value.id) {
      await orgsApi.updateCommunity(communityDialog.value.id, communityDialog.value.name.trim())
    }
    showSuccessToast({ message: '保存成功' })
    communityDialog.value.show = false
  } catch (e: any) {
    showToast({ message: e?.message || '保存失败', type: 'fail' })
  }
}
async function deleteCommunity(c: Community) {
  try {
    await showConfirmDialog({
      title: '确认删除',
      message: `删除社区「${c.name}」？该社区下还有 ${branchCount(c.id)} 个支部将一并检查`,
    })
    await orgsApi.deleteCommunity(c.id)
    communities.value = communities.value.filter((x) => x.id !== c.id)
    if (selectedCommunityId.value === c.id) {
      selectedCommunityId.value = filteredCommunities.value[0]?.id || null
    }
    showSuccessToast({ message: '已删除' })
  } catch (e: any) {
    if (e?.message) showToast({ message: e.message, type: 'fail' })
  }
}

// 支部
const branchDialog = ref<{ show: boolean; mode: 'add' | 'edit'; id?: number; name: string }>({
  show: false, mode: 'add', name: '',
})
function openAddBranch() {
  if (!selectedCommunityId.value) {
    showToast({ message: '请先选择社区', type: 'fail' })
    return
  }
  branchDialog.value = { show: true, mode: 'add', name: '' }
}
function openEditBranch(b: Branch) {
  branchDialog.value = { show: true, mode: 'edit', id: b.id, name: b.name }
}
async function saveBranch() {
  if (!branchDialog.value.name.trim()) {
    showToast({ message: '请输入名称', type: 'fail' })
    return
  }
  if (!selectedCommunityId.value) return
  try {
    if (branchDialog.value.mode === 'add') {
      await orgsApi.createBranch(selectedCommunityId.value, branchDialog.value.name.trim())
    } else if (branchDialog.value.id) {
      await orgsApi.updateBranch(branchDialog.value.id, branchDialog.value.name.trim())
    }
    showSuccessToast({ message: '保存成功' })
    branchDialog.value.show = false
    await loadOrg()
  } catch (e: any) {
    showToast({ message: e?.message || '保存失败', type: 'fail' })
  }
}
async function deleteBranch(b: Branch) {
  try {
    await showConfirmDialog({
      title: '确认删除',
      message: `删除支部「${b.name}」？该支部下如有人员将无法删除`,
    })
    await orgsApi.deleteBranch(b.id)
    branches.value = branches.value.filter((x) => x.id !== b.id)
    showSuccessToast({ message: '已删除' })
  } catch (e: any) {
    if (e?.message) showToast({ message: e.message, type: 'fail' })
  }
}

// =================== 通用字典 ===================
function useDictTab(
  loader: () => Promise<DictItem[]>,
  create: (code: string, name: string, sort: number) => Promise<DictItem>,
  update: (id: number, body: { name?: string; sort?: number }) => Promise<DictItem>,
  remove: (id: number) => Promise<any>,
  moveUp: (id: number) => Promise<DictItem>,
  moveDown: (id: number) => Promise<DictItem>,
  label: string,
) {
  const items = ref<DictItem[]>([])
  const loading = ref(false)
  const movingId = ref<number | null>(null)
  const dialog = ref<{ show: boolean; mode: 'add' | 'edit'; id?: number; code: string; name: string; sort: number }>({
    show: false, mode: 'add', code: '', name: '', sort: 0,
  })

  async function load() {
    loading.value = true
    try {
      items.value = await loader()
    } catch (e: any) {
      showToast({ message: e?.message || '加载失败', type: 'fail' })
    } finally {
      loading.value = false
    }
  }

  function openAdd() {
    dialog.value = { show: true, mode: 'add', code: '', name: '', sort: (items.value.length + 1) * 10 }
  }
  function openEdit(item: DictItem) {
    dialog.value = { show: true, mode: 'edit', id: item.id, code: item.code, name: item.name, sort: item.sort }
  }
  async function save() {
    if (!dialog.value.name.trim()) {
      showToast({ message: '请输入名称', type: 'fail' })
      return
    }
    if (dialog.value.mode === 'add' && !dialog.value.code.trim()) {
      showToast({ message: '请输入编码', type: 'fail' })
      return
    }
    try {
      if (dialog.value.mode === 'add') {
        await create(dialog.value.code.trim(), dialog.value.name.trim(), dialog.value.sort)
      } else if (dialog.value.id) {
        await update(dialog.value.id, { name: dialog.value.name.trim(), sort: dialog.value.sort })
      }
      showSuccessToast({ message: '保存成功' })
      dialog.value.show = false
      await load()
    } catch (e: any) {
      showToast({ message: e?.message || '保存失败', type: 'fail' })
    }
  }
  async function removeItem(item: DictItem) {
    try {
      await showConfirmDialog({ title: '确认删除', message: `删除${label}「${item.name}」？` })
      await remove(item.id)
      items.value = items.value.filter((x) => x.id !== item.id)
      showSuccessToast({ message: '已删除' })
    } catch (e: any) {
      if (e?.message) showToast({ message: e.message, type: 'fail' })
    }
  }
  async function move(item: DictItem, dir: 'up' | 'down') {
    if (movingId.value) return
    movingId.value = item.id
    try {
      if (dir === 'up') await moveUp(item.id)
      else await moveDown(item.id)
      await load()
    } catch (e: any) {
      showToast({ message: e?.message || '移动失败', type: 'fail' })
    } finally {
      movingId.value = null
    }
  }

  return { items, loading, movingId, dialog, load, openAdd, openEdit, save, removeItem, move }
}

const cat = useDictTab(
  () => dictsApi.trainingCategories(),
  (code, name, sort) => dictsApi.createTrainingCategory(code, name, sort),
  (id, body) => dictsApi.updateTrainingCategory(id, body),
  (id) => dictsApi.deleteTrainingCategory(id),
  (id) => dictsApi.moveTrainingCategoryUp(id),
  (id) => dictsApi.moveTrainingCategoryDown(id),
  '培训对象',
)
const src = useDictTab(
  () => dictsApi.trainingSources(),
  (code, name, sort) => dictsApi.createTrainingSource(code, name, sort),
  (id, body) => dictsApi.updateTrainingSource(id, body),
  (id) => dictsApi.deleteTrainingSource(id),
  (id) => dictsApi.moveTrainingSourceUp(id),
  (id) => dictsApi.moveTrainingSourceDown(id),
  '培训来源',
)

onMounted(() => {
  loadOrg()
  cat.load()
  src.load()
})
</script>

<template>
  <div class="form-page">
    <div class="page-header">
      <div class="title">系统配置</div>
      <div class="sub">
        <template v-if="isAdmin">系统管理员 - 完整权限</template>
        <template v-else-if="isStreetLead">街道负责人 - 只能管理本街道的社区/支部</template>
        <template v-else>仅系统管理员可编辑</template>
      </div>
    </div>

    <van-tabs v-model:active="activeTab" sticky offset-top="44" line-width="20px" color="#B22222" title-active-color="#B22222">
      <!-- ========== 组织架构 ========== -->
      <van-tab title="组织架构" name="org">
        <div class="org-hint">
          <span>组织层级：</span>
          <span class="lvl">街道</span>
          <span class="arrow">›</span>
          <span class="lvl">社区</span>
          <span class="arrow">›</span>
          <span class="lvl">支部</span>
        </div>
        <div class="org-path">
          <span>当前：</span>
          <span class="path-item" :class="{ active: !selectedStreet }" @click="streets.length && (selectedStreetId = null)">
            全街道
          </span>
          <template v-if="selectedStreet">
            <span class="arrow-sm">›</span>
            <span class="path-item active">{{ selectedStreet.name }}</span>
          </template>
          <template v-if="selectedStreet && filteredCommunities.length">
            <span class="arrow-sm">/</span>
          </template>
          <template v-if="selectedCommunityId && selectedCommunity">
            <span class="path-item active">{{ selectedCommunity.name }}</span>
          </template>
        </div>

        <div class="org-board">
          <!-- 街道 -->
          <div class="col">
            <div class="col-header">
              <span class="col-title">① 街道</span>
              <van-button
                v-if="isAdmin"
                size="mini"
                type="primary"
                @click="openAddStreet"
              >+ 新增</van-button>
            </div>
            <div class="col-list">
              <div v-if="orgLoading" class="status">加载中…</div>
              <div v-else-if="!streets.length" class="status empty-hint">
                还没有街道<br/>点右上「+ 新增」开始
              </div>
              <div
                v-for="(s, sIdx) in sortedStreets"
                :key="s.id"
                class="row"
                :class="{ active: selectedStreetId === s.id }"
                @click="selectStreet(s.id)"
              >
                <div class="row-main">
                  <div class="row-name">{{ s.name }}</div>
                  <div class="row-meta">{{ communityCount(s.id) }} 个社区</div>
                </div>
                <div class="row-actions">
                  <template v-if="isAdmin">
                    <van-button
                      size="mini" plain icon="arrow-up"
                      :disabled="sIdx === 0 || movingId === s.id"
                      :loading="movingId === s.id"
                      @click.stop="moveStreet(s, 'up')"
                    />
                    <van-button
                      size="mini" plain icon="arrow-down"
                      :disabled="sIdx === sortedStreets.length - 1 || movingId === s.id"
                      :loading="movingId === s.id"
                      @click.stop="moveStreet(s, 'down')"
                    />
                    <van-button size="mini" plain @click.stop="openEditStreet(s)">改</van-button>
                    <van-button size="mini" plain type="danger" @click.stop="deleteStreet(s)">删</van-button>
                  </template>
                  <span v-else class="readonly-tip">只读</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 社区 -->
          <div class="col">
            <div class="col-header">
              <span class="col-title">② 社区</span>
              <van-button
                size="mini"
                type="primary"
                :disabled="!selectedStreetId"
                @click="openAddCommunity"
              >+ 新增</van-button>
            </div>
            <div class="col-list">
              <div v-if="!selectedStreet" class="status empty-hint">
                ← 请先选择左侧的街道
              </div>
              <div v-else-if="!filteredCommunities.length" class="status empty-hint">
                「{{ selectedStreet.name }}」下暂无社区<br/>点右上「+ 新增」开始
              </div>
              <div
                v-for="(c, cIdx) in filteredCommunities"
                :key="c.id"
                class="row"
                :class="{ active: selectedCommunityId === c.id }"
                @click="selectedCommunityId = c.id"
              >
                <div class="row-main">
                  <div class="row-name">{{ c.name }}</div>
                  <div class="row-meta">{{ branchCount(c.id) }} 个支部</div>
                </div>
                <div class="row-actions">
                  <van-button
                    size="mini" plain icon="arrow-up"
                    :disabled="cIdx === 0 || movingId === c.id"
                    :loading="movingId === c.id"
                    @click.stop="moveCommunity(c, 'up')"
                  />
                  <van-button
                    size="mini" plain icon="arrow-down"
                    :disabled="cIdx === filteredCommunities.length - 1 || movingId === c.id"
                    :loading="movingId === c.id"
                    @click.stop="moveCommunity(c, 'down')"
                  />
                  <van-button size="mini" plain @click.stop="openEditCommunity(c)">改</van-button>
                  <van-button size="mini" plain type="danger" @click.stop="deleteCommunity(c)">删</van-button>
                </div>
              </div>
            </div>
          </div>

          <!-- 支部 -->
          <div class="col">
            <div class="col-header">
              <span class="col-title">③ 支部</span>
              <van-button
                size="mini"
                type="primary"
                :disabled="!selectedCommunityId"
                @click="openAddBranch"
              >+ 新增</van-button>
            </div>
            <div class="col-list">
              <div v-if="!selectedCommunityId" class="status empty-hint">
                ← 请先选择中间的社区
              </div>
              <div v-else-if="!filteredBranches.length" class="status empty-hint">
                「{{ selectedCommunity?.name }}」下暂无支部<br/>点右上「+ 新增」开始
              </div>
              <div v-for="(b, bIdx) in filteredBranches" :key="b.id" class="row">
                <div class="row-main">
                  <div class="row-name">{{ b.name }}</div>
                </div>
                <div class="row-actions">
                  <van-button
                    size="mini" plain icon="arrow-up"
                    :disabled="bIdx === 0 || movingId === b.id"
                    :loading="movingId === b.id"
                    @click.stop="moveBranch(b, 'up')"
                  />
                  <van-button
                    size="mini" plain icon="arrow-down"
                    :disabled="bIdx === filteredBranches.length - 1 || movingId === b.id"
                    :loading="movingId === b.id"
                    @click.stop="moveBranch(b, 'down')"
                  />
                  <van-button size="mini" plain @click="openEditBranch(b)">改</van-button>
                  <van-button size="mini" plain type="danger" @click="deleteBranch(b)">删</van-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </van-tab>

      <!-- ========== 培训对象 ========== -->
      <van-tab title="培训对象" name="category">
        <div class="list-page">
          <div class="action-bar">
            <van-button size="small" type="primary" @click="cat.openAdd()">+ 新增类别</van-button>
          </div>
          <div v-if="cat.loading.value" class="status">加载中…</div>
          <div v-else-if="!cat.items.value.length" class="status">暂无类别</div>
          <div v-else class="card-list">
            <div v-for="(i, iIdx) in cat.items.value" :key="i.id" class="row-card">
              <div class="row-main">
                <div class="row-name">{{ i.name }} <span class="code">({{ i.code }})</span></div>
                <div class="row-meta">排序：{{ i.sort }}</div>
              </div>
              <div class="row-actions">
                <van-button
                  size="mini" plain icon="arrow-up"
                  :disabled="iIdx === 0 || cat.movingId.value === i.id"
                  :loading="cat.movingId.value === i.id"
                  @click="cat.move(i, 'up')"
                />
                <van-button
                  size="mini" plain icon="arrow-down"
                  :disabled="iIdx === cat.items.value.length - 1 || cat.movingId.value === i.id"
                  :loading="cat.movingId.value === i.id"
                  @click="cat.move(i, 'down')"
                />
                <van-button size="mini" plain @click="cat.openEdit(i)">改</van-button>
                <van-button size="mini" plain type="danger" @click="cat.removeItem(i)">删</van-button>
              </div>
            </div>
          </div>
        </div>
      </van-tab>

      <!-- ========== 培训来源 ========== -->
      <van-tab title="培训来源" name="source">
        <div class="list-page">
          <div class="action-bar">
            <van-button size="small" type="primary" @click="src.openAdd()">+ 新增来源</van-button>
          </div>
          <div v-if="src.loading.value" class="status">加载中…</div>
          <div v-else-if="!src.items.value.length" class="status">暂无来源</div>
          <div v-else class="card-list">
            <div v-for="(i, iIdx) in src.items.value" :key="i.id" class="row-card">
              <div class="row-main">
                <div class="row-name">{{ i.name }} <span class="code">({{ i.code }})</span></div>
                <div class="row-meta">排序：{{ i.sort }}</div>
              </div>
              <div class="row-actions">
                <van-button
                  size="mini" plain icon="arrow-up"
                  :disabled="iIdx === 0 || src.movingId.value === i.id"
                  :loading="src.movingId.value === i.id"
                  @click="src.move(i, 'up')"
                />
                <van-button
                  size="mini" plain icon="arrow-down"
                  :disabled="iIdx === src.items.value.length - 1 || src.movingId.value === i.id"
                  :loading="src.movingId.value === i.id"
                  @click="src.move(i, 'down')"
                />
                <van-button size="mini" plain @click="src.openEdit(i)">改</van-button>
                <van-button size="mini" plain type="danger" @click="src.removeItem(i)">删</van-button>
              </div>
            </div>
          </div>
        </div>
      </van-tab>
    </van-tabs>

    <!-- 街道编辑 -->
    <van-dialog
      v-model:show="streetDialog.show"
      :title="streetDialog.mode === 'add' ? '新增街道' : '编辑街道'"
      show-cancel-button
      @confirm="saveStreet"
    >
      <div class="dialog-pad">
        <van-field v-model="streetDialog.name" label="街道名" placeholder="如：南湾街道" maxlength="64" />
      </div>
    </van-dialog>

    <!-- 社区编辑 -->
    <van-dialog
      v-model:show="communityDialog.show"
      :title="communityDialog.mode === 'add' ? '新增社区' : '编辑社区'"
      show-cancel-button
      @confirm="saveCommunity"
    >
      <div class="dialog-pad">
        <van-field v-model="communityDialog.name" label="社区名" placeholder="如：南岭社区" maxlength="64" />
      </div>
    </van-dialog>

    <!-- 支部编辑 -->
    <van-dialog
      v-model:show="branchDialog.show"
      :title="branchDialog.mode === 'add' ? '新增支部' : '编辑支部'"
      show-cancel-button
      @confirm="saveBranch"
    >
      <div class="dialog-pad">
        <van-field v-model="branchDialog.name" label="支部名" placeholder="如：南岭社区第一党支部" maxlength="128" />
      </div>
    </van-dialog>

    <!-- 通用字典编辑 -->
    <van-dialog
      v-model:show="cat.dialog.value.show"
      :title="cat.dialog.value.mode === 'add' ? '新增培训对象' : '编辑培训对象'"
      show-cancel-button
      @confirm="cat.save"
    >
      <div class="dialog-pad">
        <van-field
          v-model="cat.dialog.value.code"
          label="编码"
          placeholder="英文，唯一"
          maxlength="32"
          :disabled="cat.dialog.value.mode === 'edit'"
        />
        <van-field v-model="cat.dialog.value.name" label="名称" placeholder="显示名" maxlength="64" />
        <van-field v-model.number="cat.dialog.value.sort" label="排序" type="digit" placeholder="数字小靠前" />
      </div>
    </van-dialog>

    <van-dialog
      v-model:show="src.dialog.value.show"
      :title="src.dialog.value.mode === 'add' ? '新增培训来源' : '编辑培训来源'"
      show-cancel-button
      @confirm="src.save"
    >
      <div class="dialog-pad">
        <van-field
          v-model="src.dialog.value.code"
          label="编码"
          placeholder="英文，唯一"
          maxlength="32"
          :disabled="src.dialog.value.mode === 'edit'"
        />
        <van-field v-model="src.dialog.value.name" label="名称" placeholder="显示名" maxlength="64" />
        <van-field v-model.number="src.dialog.value.sort" label="排序" type="digit" placeholder="数字小靠前" />
      </div>
    </van-dialog>
  </div>
</template>

<style scoped>
.form-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 8px 0 32px;
}

.page-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: 4px 16px 12px;
}
.title { font-size: 20px; font-weight: 700; color: #222; }
.sub { font-size: 12px; color: #999; }

/* 组织架构：3 栏 */
.org-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  font-size: 12px;
  color: #888;
  background: #FFF8E1;
  border-bottom: 1px solid #FFE0B2;
}
.org-hint .lvl {
  padding: 2px 8px;
  background: #fff;
  border: 1px solid #FFB74D;
  border-radius: 4px;
  font-weight: 600;
  color: #E65100;
}
.org-hint .arrow { color: #FFB74D; font-size: 14px; }

.org-path {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px 16px;
  font-size: 12px;
  color: #666;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
}
.org-path .path-item {
  padding: 2px 6px;
  border-radius: 3px;
  cursor: pointer;
  color: #888;
}
.org-path .path-item.active { color: #B22222; font-weight: 600; background: #FFF0F0; }
.org-path .path-item:hover { color: #B22222; }
.org-path .arrow-sm { color: #ccc; }

.org-board {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  padding: 8px;
  min-height: 400px;
}
.col {
  background: #f5f5f5;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.col-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: #fff;
  border-radius: 8px 8px 0 0;
  border-bottom: 1px solid #eee;
  position: sticky;
  top: 0;
  z-index: 1;
}
.col-title {
  font-size: 14px;
  font-weight: 700;
  color: #222;
}

.status.empty-hint {
  color: #aaa;
  font-size: 12px;
  line-height: 1.6;
}

.readonly-tip {
  font-size: 11px;
  color: #999;
  padding: 2px 6px;
  background: #f5f5f5;
  border-radius: 3px;
}
.col-list {
  flex: 1;
  padding: 8px;
  overflow-y: auto;
  max-height: calc(100vh - 240px);
}

.status {
  text-align: center;
  padding: 40px 16px;
  color: #999;
  font-size: 13px;
}

.row {
  background: #fff;
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: border-color .15s, transform .1s;
}
.row:hover { border-color: #ffd1d1; }
.row.active {
  border-color: #B22222;
  background: #FFF0F0;
}
.row-main { margin-bottom: 4px; }
.row-name {
  font-size: 14px;
  font-weight: 600;
  color: #222;
}
.row-meta {
  font-size: 12px;
  color: #888;
  margin-top: 2px;
}
.row-actions {
  display: flex;
  gap: 4px;
  margin-top: 4px;
}

.code {
  font-size: 11px;
  color: #999;
  font-weight: 400;
}
.tag {
  margin-left: 6px;
  vertical-align: middle;
}

/* 列表 tab */
.list-page {
  padding: 8px;
}
.action-bar {
  display: flex;
  justify-content: flex-end;
  padding: 4px 8px 12px;
}
.card-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.row-card {
  background: #fff;
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid #f0f0f0;
}
.row-card.inactive { opacity: 0.55; }

.dialog-pad {
  padding: 12px 0;
}

@media (max-width: 768px) {
  .org-board {
    grid-template-columns: 1fr;
  }
  .col-list {
    max-height: 200px;
  }
}
</style>
