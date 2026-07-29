<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { showToast } from 'vant'
import { statsApi, type StatItem, type Period } from '@/api/stats'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// 当前用户的数据范围徽章（让"我看到的是不是全街道"一目了然）
const scopeBadge = computed(() => {
  const u = auth.user
  if (!u) return ''
  const role = u.role
  if (role === 'system_admin') return '🌐 全部'
  if (role === 'street_lead') {
    return u.street_name ? `📍 ${u.street_name}（街道全部）` : '📍 街道全部'
  }
  if (role === 'community_organizer' || role === 'branch_secretary') {
    return u.community_name ? `📍 ${u.community_name}` : '📍 本社区'
  }
  return ''
})

// ===== 维度：年 / 月 / 日 =====
const period = ref<Period>('year')
const now = new Date()
const year = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)        // 1-12
const day = ref(now.toISOString().slice(0, 10))  // YYYY-MM-DD

const items = ref<StatItem[]>([])
const totalSessions = ref(0)
const totalParticipants = ref(0)
const periodLabel = ref('')
const loading = ref(false)
const showGlobalHint = ref(false)
const hintStates = ref<Record<string, boolean>>({})

// 当前查询条件（按 period 不同只带相关字段）
function currentQuery() {
  if (period.value === 'year') return { period: 'year' as const, year: year.value }
  if (period.value === 'month') return { period: 'month' as const, year: year.value, month: month.value }
  return { period: 'day' as const, day: day.value }
}

async function load() {
  loading.value = true
  try {
    const r = await statsApi.stats(currentQuery())
    items.value = r.items
    totalSessions.value = r.total_sessions
    totalParticipants.value = r.total_participants
    periodLabel.value = r.label
  } catch (e: any) {
    showToast({ message: e?.message || '加载失败', type: 'fail' })
  } finally {
    loading.value = false
  }
}

function onExport() {
  const token = auth.token
  const url = statsApi.exportUrl(currentQuery(), token)
  window.open(url, '_blank')
}

// 切换维度时加载
function onPeriodChange() {
  load()
}

// ===== 6 类口径说明（hover/点击 ? 弹） =====
const CATEGORY_HINTS: Record<string, { icon: string; oneLine: string; example: string }> = {
  '党建组': {
    icon: '🏛️',
    oneLine: '街道自己办的课，给机关单位的党员上。',
    example: '例：街道机关支部组织的十九大精神学习。',
  },
  '人事组': {
    icon: '👥',
    oneLine: '街道自己办的课，给两新组织（"两新"=新经济组织、新社会组织）的党员上。',
    example: '例：辖区非公企业党支部的培训。',
  },
  '党群服务中心': {
    icon: '🏘️',
    oneLine: '街道自己办的课，给社区里的党员上。',
    example: '例：社区党员集中学习、过组织生活。',
  },
  '其他部门': {
    icon: '📂',
    oneLine: '街道自己办的课，培训对象不属于以上 3 类（选"其他"的）。',
    example: '例：街道临时扩大的非典型培训。',
  },
  '市区送课': {
    icon: '⬇️',
    oneLine: '由市里或区里派老师来讲的课，给机关党员听。',
    example: '例：区委组织部安排的"送课下基层"。',
  },
  '送课到社区': {
    icon: '⬇️🏘️',
    oneLine: '由市里或区里派老师来讲的课，下到社区给党员听。',
    example: '例：市委党校老师到社区讲党课。',
  },
}

const GLOBAL_HINT_ICON = '📖'
const GLOBAL_HINT_ONELINE = computed(() => {
  if (period.value === 'year') return '本表统计本年度（1月1日-12月31日）所有"已通过审核"的培训活动。'
  if (period.value === 'month') return `本表统计 ${year.value} 年 ${month.value} 月（1日-${lastDayOfMonth.value}日）所有"已通过审核"的培训活动。`
  return `本表统计 ${day.value} 当天所有"已通过审核"的培训活动。`
})
const GLOBAL_HINT_RULES = [
  '【场次】= 这一类有几场活动（一行一条活动记录）',
  '【培训人数】= 这几场活动的参训人数加在一起',
  '【不统计】草稿、驳回的、还没过审的活动',
  '【可见范围】你只能看到你权限范围内的活动（街道/社区/支部自动过滤）',
]

// ===== 选择器数据 =====
const lastDayOfMonth = computed(() => {
  return new Date(year.value, month.value, 0).getDate()
})

const showYearPicker = ref(false)
const showMonthPicker = ref(false)
const showDayPicker = ref(false)

const yearActions = computed(() => {
  const y = new Date().getFullYear()
  return Array.from({ length: 6 }, (_, i) => ({
    name: `${y - i} 年`,
    subname: y - i === year.value ? '✓ 当前选中' : '',
    value: y - i,
  }))
})
function onYearSelect(action: { value: number }) {
  year.value = action.value
  load()
}

const monthActions = computed(() =>
  Array.from({ length: 12 }, (_, i) => i + 1).map((m) => ({
    name: `${m} 月`,
    subname: m === month.value ? '✓ 当前选中' : '',
    value: m,
  })),
)
function onMonthSelect(action: { value: number }) {
  month.value = action.value
  load()
}

const dayActions = computed(() => {
  const out: { name: string; value: number; subname: string }[] = []
  for (let d = 1; d <= lastDayOfMonth.value; d++) {
    const ds = `${year.value}-${String(month.value).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    out.push({ name: ds, subname: ds === day.value ? '✓ 当前选中' : '', value: d })
  }
  return out
})
function onDaySelect(action: { value: number }) {
  const ds = `${year.value}-${String(month.value).padStart(2, '0')}-${String(action.value).padStart(2, '0')}`
  day.value = ds
  load()
}

// 切换"日"维度时若当前 day 超出当月，自动重置到 1 号
function onDayPickerOpen() {
  const dayNum = Number(day.value.slice(-2))
  if (!dayNum || dayNum > lastDayOfMonth.value) {
    day.value = `${year.value}-${String(month.value).padStart(2, '0')}-01`
  }
  showDayPicker.value = true
}

onMounted(() => {
  load()
})
</script>

<template>
  <div class="form-page">
    <div class="page-header">
      <div class="title-wrap">
        <div class="title">统计</div>
        <div v-if="scopeBadge" class="scope-badge">{{ scopeBadge }}</div>
      </div>
      <div class="period-pills">
        <span
          class="pill"
          :class="{ active: period === 'year' }"
          @click="period = 'year'; onPeriodChange()"
        >年</span>
        <span
          class="pill"
          :class="{ active: period === 'month' }"
          @click="period = 'month'; onPeriodChange()"
        >月</span>
        <span
          class="pill"
          :class="{ active: period === 'day' }"
          @click="period = 'day'; onPeriodChange()"
        >日</span>
      </div>
    </div>

    <div class="range-bar">
      <template v-if="period === 'year'">
        <van-button size="small" plain hairline type="primary" @click="showYearPicker = true">
          {{ year }} 年 ▾
        </van-button>
      </template>
      <template v-else-if="period === 'month'">
        <van-button size="small" plain hairline type="primary" @click="showYearPicker = true">
          {{ year }} 年 ▾
        </van-button>
        <van-button size="small" plain hairline type="primary" @click="showMonthPicker = true">
          {{ month }} 月 ▾
        </van-button>
      </template>
      <template v-else>
        <van-button size="small" plain hairline type="primary" @click="showYearPicker = true">
          {{ year }} 年 ▾
        </van-button>
        <van-button size="small" plain hairline type="primary" @click="showMonthPicker = true">
          {{ month }} 月 ▾
        </van-button>
        <van-button size="small" plain hairline type="primary" @click="onDayPickerOpen">
          {{ Number(day.slice(-2)) }} 日 ▾
        </van-button>
      </template>
    </div>

    <div class="summary">
      <div class="summary-card">
        <div class="stat-item">
          <div class="stat-num">{{ totalSessions }}</div>
          <div class="stat-label">总场次</div>
        </div>
        <div class="divider" />
        <div class="stat-item">
          <div class="stat-num">{{ totalParticipants }}</div>
          <div class="stat-label">培训人数</div>
        </div>
      </div>
    </div>

    <div class="section-title">
      <span>分类明细</span>
      <van-popover
        v-model:show="showGlobalHint"
        placement="bottom-end"
        :offset="[0, 12]"
        teleport="body"
        trigger="click"
      >
        <template #reference>
          <button type="button" class="help-chip">📖 统计口径说明</button>
        </template>
        <div class="hint-card">
          <div class="hint-head">{{ GLOBAL_HINT_ICON }} 这张表怎么算的？</div>
          <div class="hint-summary">{{ GLOBAL_HINT_ONELINE }}</div>
          <ul class="hint-rules">
            <li v-for="r in GLOBAL_HINT_RULES" :key="r">{{ r }}</li>
          </ul>
        </div>
      </van-popover>
    </div>
    <div v-if="loading" class="status">加载中…</div>
    <div v-else class="list">
      <div v-for="(item, i) in items" :key="item.label" class="row">
        <div class="row-index">{{ i + 1 }}</div>
        <div class="row-label">{{ item.label }}</div>
        <div class="row-num">
          <div class="num-cell">{{ item.session_count }} 场</div>
          <div class="num-cell primary">{{ item.participant_count }} 人</div>
        </div>
        <van-popover
          v-model:show="hintStates[item.label]"
          placement="top-end"
          :offset="[0, 8]"
          teleport="body"
          trigger="click"
        >
          <template #reference>
            <span
              class="help-btn"
              role="button"
              :aria-label="`${item.label} 口径说明`"
            >?</span>
          </template>
          <div class="hint-card">
            <div class="hint-head">
              <span class="hint-icon">{{ CATEGORY_HINTS[item.label]?.icon || '❓' }}</span>
              {{ item.label }} = ?
            </div>
            <div class="hint-summary">{{ CATEGORY_HINTS[item.label]?.oneLine || '（暂无说明）' }}</div>
            <div class="hint-example" v-if="CATEGORY_HINTS[item.label]?.example">
              {{ CATEGORY_HINTS[item.label]?.example }}
            </div>
          </div>
        </van-popover>
      </div>
    </div>

    <div class="export-btn-wrap">
      <van-button block type="primary" @click="onExport">
        📥 导出 Excel
      </van-button>
    </div>

    <!-- 年份选择（action-sheet 列表） -->
    <van-action-sheet
      v-model:show="showYearPicker"
      :actions="yearActions"
      cancel-text="取消"
      close-on-click-action
      @select="onYearSelect"
    />

    <!-- 月份选择 -->
    <van-action-sheet
      v-model:show="showMonthPicker"
      :actions="monthActions"
      cancel-text="取消"
      close-on-click-action
      @select="onMonthSelect"
    />

    <!-- 日期选择（基于当月天数） -->
    <van-action-sheet
      v-model:show="showDayPicker"
      :actions="dayActions"
      cancel-text="取消"
      close-on-click-action
      @select="onDaySelect"
    />
  </div>
</template>

<style scoped>
.form-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 8px 0 32px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 4px 16px 12px;
}
.title { font-size: 20px; font-weight: 700; color: #222; }
.title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.scope-badge {
  font-size: 11px;
  font-weight: 500;
  color: var(--primary);
  background: #FFF0F0;
  border: 1px solid #FFD0D0;
  border-radius: 10px;
  padding: 2px 8px;
  white-space: nowrap;
  max-width: 50vw;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 维度切换器（年/月/日） */
.period-pills {
  display: inline-flex;
  background: #f5f5f5;
  border-radius: 18px;
  padding: 3px;
  gap: 2px;
}
.pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  padding: 4px 12px;
  font-size: 13px;
  color: #666;
  border-radius: 16px;
  cursor: pointer;
  user-select: none;
  transition: all 0.15s;
}
.pill.active {
  background: var(--primary);
  color: #fff;
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(178,34,34,0.3);
}
.pill:not(.active):hover { color: var(--primary); }

/* 范围条（按当前维度显示 年/月/日 选择器） */
.range-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 4px 16px 12px;
  flex-wrap: wrap;
}

.summary { padding: 0 8px 16px; }
.summary-card {
  display: flex;
  background: linear-gradient(135deg, #B22222, #8B0000);
  color: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(178, 34, 34, 0.2);
}
.stat-item { flex: 1; text-align: center; }
.stat-num { font-size: 32px; font-weight: 800; line-height: 1.1; }
.stat-label { font-size: 12px; opacity: 0.9; margin-top: 2px; }
.divider { width: 1px; background: rgba(255, 255, 255, 0.3); margin: 0 12px; }

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #222;
  margin: 12px 16px 10px;
  padding-left: 8px;
  border-left: 4px solid var(--primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

/* 顶部 "统计口径说明" 醒目按钮 */
.help-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  color: var(--primary);
  background: #FFF0F0;
  border: 1px solid #FFD0D0;
  border-radius: 16px;
  padding: 4px 12px;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
}
.help-chip:hover {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}
.help-chip:active { transform: scale(0.97); }

/* 每行末尾的小 ? 按钮 */
.help-btn {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #FFF0F0;
  color: var(--primary);
  font-size: 13px;
  font-weight: 700;
  border: 1px solid #FFD0D0;
  cursor: pointer;
  flex-shrink: 0;
  margin-left: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  line-height: 1;
  transition: all 0.15s;
  user-select: none;
}
.help-btn:hover {
  background: var(--primary);
  color: #fff;
  transform: scale(1.1);
}
.help-btn:active { transform: scale(0.95); }

/* Popover 卡片样式（覆盖 Vant 默认白底） */
:deep(.van-popover__content) {
  padding: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}
.hint-card {
  background: #fff;
  border-radius: 10px;
  padding: 12px 14px;
  min-width: 240px;
  max-width: 320px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
  border: 1px solid #f0f0f0;
}
.hint-head {
  font-size: 14px;
  font-weight: 700;
  color: var(--primary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.hint-icon {
  font-size: 18px;
  margin-right: 2px;
}
.hint-summary {
  font-size: 14px;
  line-height: 1.6;
  color: #333;
  margin-bottom: 8px;
}
.hint-example {
  font-size: 12px;
  line-height: 1.5;
  color: #888;
  background: #FFF8E1;
  border-left: 3px solid #FFB74D;
  padding: 6px 8px;
  border-radius: 3px;
}
.hint-rules {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 12px;
  line-height: 1.7;
  color: #555;
}
.hint-rules li {
  padding: 2px 0;
  border-bottom: 1px dashed #f0f0f0;
}
.hint-rules li:last-child { border-bottom: none; }

.status {
  text-align: center;
  padding: 30px 16px;
  color: #888;
  font-size: 14px;
}

.list {
  background: #fff;
  border-radius: 8px;
  margin: 0 8px;
  overflow: hidden;
}
.row {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f5f5f5;
  transition: background 0.12s;
}
.row:hover { background: #fafafa; }
.row:last-child { border-bottom: none; }
.row-index {
  width: 24px;
  height: 24px;
  line-height: 24px;
  text-align: center;
  background: #f5f5f5;
  color: #666;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  margin-right: 10px;
  flex-shrink: 0;
}
.row-label { flex: 1; font-size: 14px; color: #222; }
.row-num { display: flex; gap: 8px; }
.num-cell {
  min-width: 56px;
  text-align: center;
  font-size: 13px;
  color: #666;
}
.num-cell.primary { color: var(--primary); font-weight: 600; }

.export-btn-wrap {
  padding: 20px 16px 0;
}
</style>
