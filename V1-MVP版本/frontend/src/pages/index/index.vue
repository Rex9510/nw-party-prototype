<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ROLES, type Role } from '@/utils/roles'

const auth = useAuthStore()
const router = useRouter()

const role = computed<Role>(() => (auth.user?.role as Role) || 'member')
const roleConfig = computed(() => ROLES[role.value])
const cards = computed(() => roleConfig.value?.cards || [])

onMounted(async () => {
  if (auth.token && !auth.user) {
    try {
      await auth.fetchMe()
    } catch (e) {
      console.warn('fetchMe failed', e)
    }
  }
})

function onCardTap(path: string, enabled: boolean) {
  if (!enabled) {
    // @ts-ignore
    window.uni.showToast({ title: '该功能后续开发', icon: 'none' })
    return
  }
  router.push(path).catch(() => {
    // @ts-ignore
    window.uni.showToast({ title: '页面打开失败', icon: 'none' })
  })
}
</script>

<template>
  <div class="dashboard">
    <!-- 欢迎条 -->
    <div class="welcome" :style="{ borderLeftColor: roleConfig?.color }">
      <div class="welcome-title">你好，{{ auth.user?.name || '加载中…' }} 👋</div>
      <div class="welcome-sub">
        {{ roleConfig?.label }} · {{ roleConfig?.scope }}
      </div>
    </div>

    <!-- 入口区 -->
    <div class="section-title">我的入口</div>
    <div class="grid">
      <div
        v-for="card in cards"
        :key="card.key"
        class="card"
        :class="{ disabled: !card.enabled }"
        @click="onCardTap(card.path, card.enabled)"
      >
        <div class="emoji">{{ card.icon }}</div>
        <div class="card-body">
          <div class="card-title">{{ card.label }}</div>
          <div class="card-sub">{{ card.desc }}</div>
        </div>
        <div class="tag" :class="{ enabled: card.enabled }">
          {{ card.enabled ? '可用' : '后续' }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  background: transparent;
  padding: 8px;
}

/* 欢迎条 */
.welcome {
  background: #fff;
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 16px;
  border-left: 4px solid #B22222;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.welcome-title {
  font-size: 18px;
  font-weight: 700;
  color: #222;
}
.welcome-sub {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin: 8px 4px 10px;
  padding-left: 4px;
  border-left: 3px solid #B22222;
  line-height: 1.2;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.card {
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  cursor: pointer;
  transition: transform .1s;
  position: relative;
  border: 1px solid #f5f5f5;
}
.card:active { transform: scale(0.98); }
.card:hover { border-color: #B22222; }
.card.disabled { opacity: 0.6; cursor: not-allowed; }

.emoji {
  font-size: 32px;
  line-height: 1;
  flex-shrink: 0;
}
.card-body {
  flex: 1;
  min-width: 0;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #222;
}
.card-sub {
  font-size: 12px;
  color: #888;
  margin-top: 2px;
}
.tag {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: #f5f5f5;
  color: #999;
}
.tag.enabled {
  background: #FFF0F0;
  color: #B22222;
}

/* ============ PC 端 ============ */
@media (min-width: 768px) {
  .dashboard {
    padding: 0;
  }
  .welcome {
    padding: 20px 28px;
    margin-bottom: 20px;
    border-radius: 12px;
  }
  .welcome-title {
    font-size: 22px;
  }
  .welcome-sub {
    font-size: 13px;
    margin-top: 6px;
  }
  .section-title {
    font-size: 15px;
    margin: 8px 4px 12px;
  }
  .grid {
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
  }
  .card {
    padding: 20px;
    flex-direction: column;
    align-items: flex-start;
    text-align: left;
  }
  .emoji {
    font-size: 36px;
  }
  .card-title {
    font-size: 16px;
  }
  .card-sub {
    font-size: 13px;
  }
  .tag {
    font-size: 11px;
    padding: 2px 8px;
  }
}
</style>
