/**
 * 角色配置：每个角色能看到的入口。
 */
export const ROLES = {
  street_lead: {
    label: '街道负责人',
    color: '#B22222',
    scope: '全街道',
    cards: [
      { key: 'members', icon: '👥', label: '党员库', desc: '管理全街道党员', path: '/pages/members/list', enabled: false },
      { key: 'activities', icon: '📋', label: '培训活动', desc: '查看全街道活动', path: '/pages/activities/list', enabled: false },
      { key: 'audit', icon: '✅', label: '待审核', desc: '街道复审', path: '/pages/audit/pending', enabled: false },
      { key: 'stats', icon: '📊', label: '年度统计', desc: '导出 Excel', path: '/pages/stats/yearly', enabled: false },
    ],
  },
  community_organizer: {
    label: '社区组织委员',
    color: '#1E40AF',
    scope: '本社区',
    cards: [
      { key: 'activities', icon: '📋', label: '培训活动', desc: '录入/提交', path: '/pages/activities/list', enabled: false },
      { key: 'members', icon: '👥', label: '党员库', desc: '本社区党员', path: '/pages/members/list', enabled: false },
      { key: 'audit', icon: '✅', label: '待审核', desc: '社区初审', path: '/pages/audit/pending', enabled: false },
    ],
  },
  branch_secretary: {
    label: '支部书记',
    color: '#15803D',
    scope: '本支部',
    cards: [
      { key: 'members', icon: '👥', label: '党员库', desc: '本支部党员', path: '/pages/members/list', enabled: false },
      { key: 'study', icon: '🎓', label: '学时档案', desc: '本支部汇总', path: '/pages/study-hours/index', enabled: false },
    ],
  },
  member: {
    label: '党员',
    color: '#7C3AED',
    scope: '个人',
    cards: [
      { key: 'study', icon: '🎓', label: '我的学时', desc: '查看个人档案', path: '/pages/study-hours/index', enabled: false },
    ],
  },
  system_admin: {
    label: '系统管理员',
    color: '#0F766E',
    scope: '全系统',
    cards: [
      { key: 'members', icon: '👥', label: '党员库', desc: '全街道管理', path: '/pages/members/list', enabled: false },
      { key: 'activities', icon: '📋', label: '培训活动', desc: '全街道活动', path: '/pages/activities/list', enabled: false },
      { key: 'stats', icon: '📊', label: '年度统计', desc: '导出 Excel', path: '/pages/stats/yearly', enabled: false },
    ],
  },
} as const

export type Role = keyof typeof ROLES
