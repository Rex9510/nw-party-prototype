<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { auditsApi, type AuditItem } from '@/api/audits'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const items = ref<AuditItem[]>([])
const loading = ref(false)
const actionItem = ref<AuditItem | null>(null)
const actionType = ref<'approve' | 'reject' | null>(null)
const comment = ref('')
const showActionModal = ref(false)
const showLogsModal = ref(false)
const logs = ref<any[]>([])
const logsFor = ref<AuditItem | null>(null)

const NODE_LABEL: Record<string, string> = {
  community_review: '社区初审',
  street_review: '街道复审',
}

async function load() {
  loading.value = true
  try {
    const res = await auditsApi.pending()
    items.value = res.items
  } catch (e: any) {
    uni.showToast({ title: e?.message || '加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function onApprove(item: AuditItem) {
  actionItem.value = item
  actionType.value = 'approve'
  comment.value = ''
  showActionModal.value = true
}

function onReject(item: AuditItem) {
  actionItem.value = item
  actionType.value = 'reject'
  comment.value = ''
  showActionModal.value = true
}

async function onViewLogs(item: AuditItem) {
  logsFor.value = item
  showLogsModal.value = true
  try {
    logs.value = await auditsApi.logs(item.activity_id)
  } catch (e) {
    logs.value = []
  }
}

async function onConfirmAction() {
  if (!actionItem.value || !actionType.value) return
  if (actionType.value === 'reject' && !comment.value.trim()) {
    uni.showToast({ title: '驳回必须填意见', icon: 'none' })
    return
  }
  try {
    if (actionType.value === 'approve') {
      const r = await auditsApi.approve(actionItem.value.activity_id, comment.value)
      uni.showToast({ title: r.status === 'approved' ? '已通过' : '已转交街道', icon: 'success' })
    } else {
      await auditsApi.reject(actionItem.value.activity_id, comment.value)
      uni.showToast({ title: '已驳回', icon: 'success' })
    }
    showActionModal.value = false
    load()
  } catch (e: any) {
    uni.showToast({ title: e?.message || '操作失败', icon: 'none' })
  }
}

onMounted(() => {
  load()
})
</script>

<template>
  <view class="page">
    <view class="header">
      <view class="title">待审核</view>
      <view class="total">共 {{ items.length }} 条</view>
    </view>

    <view v-if="loading" class="loading">加载中…</view>
    <view v-else-if="!items.length" class="empty">
      <view class="empty-icon">✅</view>
      <view>暂无待审核活动</view>
    </view>

    <view v-else class="list">
      <view v-for="item in items" :key="item.activity_id" class="card">
        <view class="card-header">
          <view class="theme">{{ item.theme }}</view>
          <view class="node-tag">{{ NODE_LABEL[item.current_node] || item.current_node }}</view>
        </view>
        <view class="meta">
          <text>📅 {{ item.training_at }}</text>
          <text>📍 {{ item.location }}</text>
        </view>
        <view class="meta">
          <text>👤 提交人：{{ item.submitter_name || '-' }}</text>
          <text>🏛️ {{ item.community_name }}</text>
        </view>
        <view class="meta">
          <text>👥 {{ item.participant_count }} 人</text>
          <text>🎓 {{ item.study_hours }} 学时</text>
        </view>
        <view class="actions">
          <view class="btn btn-secondary" @click="onViewLogs(item)">查看日志</view>
          <view class="btn btn-danger" @click="onReject(item)">驳回</view>
          <view class="btn btn-primary" @click="onApprove(item)">通过</view>
        </view>
      </view>
    </view>

    <!-- 操作弹窗 -->
    <view v-if="showActionModal" class="modal-mask" @click="showActionModal = false">
      <view class="modal" @click.stop>
        <view class="modal-title">
          {{ actionType === 'approve' ? '审核通过' : '审核驳回' }}
        </view>
        <view class="modal-sub">{{ actionItem?.theme }}</view>
        <textarea
          v-model="comment"
          class="textarea"
          :placeholder="actionType === 'reject' ? '请填写驳回意见（必填）' : '审核意见（可选）'"
          maxlength="500"
        />
        <view class="modal-actions">
          <view class="btn btn-secondary" @click="showActionModal = false">取消</view>
          <view
            class="btn"
            :class="actionType === 'approve' ? 'btn-primary' : 'btn-danger'"
            @click="onConfirmAction"
          >
            确认{{ actionType === 'approve' ? '通过' : '驳回' }}
          </view>
        </view>
      </view>
    </view>

    <!-- 日志弹窗 -->
    <view v-if="showLogsModal" class="modal-mask" @click="showLogsModal = false">
      <view class="modal" @click.stop>
        <view class="modal-title">审核日志</view>
        <view class="modal-sub">{{ logsFor?.theme }}</view>
        <scroll-view scroll-y class="log-list">
          <view v-for="log in logs" :key="log.id" class="log-item">
            <view class="log-time">{{ log.created_at }}</view>
            <view class="log-action">
              <text class="log-action-tag" :class="'action-' + log.action">
                {{ log.action === 'submit' ? '提交' : log.action === 'approve' ? '通过' : '驳回' }}
              </text>
              <text class="log-operator">{{ log.operator_name }}</text>
            </view>
            <view v-if="log.comment" class="log-comment">{{ log.comment }}</view>
          </view>
          <view v-if="!logs.length" class="empty-mini">暂无日志</view>
        </scroll-view>
        <view class="modal-actions">
          <view class="btn btn-secondary" @click="showLogsModal = false">关闭</view>
        </view>
      </view>
    </view>
  </view>
</template>

<style lang="scss" scoped>
.page { min-height: 100vh; background: #F7F8FA; padding: 24rpx; }
.header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 20rpx; }
.title { font-size: 36rpx; font-weight: 700; color: #222; }
.total { font-size: 24rpx; color: #888; }
.loading, .empty { text-align: center; padding: 80rpx 0; color: #888; font-size: 28rpx; }
.empty-icon { font-size: 80rpx; margin-bottom: 16rpx; }

.list { display: flex; flex-direction: column; gap: 20rpx; }
.card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.04);
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}
.theme { font-size: 30rpx; font-weight: 600; color: #222; flex: 1; margin-right: 12rpx; }
.node-tag {
  background: #FFF0F0;
  color: #B22222;
  padding: 4rpx 12rpx;
  border-radius: 6rpx;
  font-size: 22rpx;
}
.meta {
  display: flex;
  gap: 24rpx;
  font-size: 24rpx;
  color: #888;
  margin-top: 6rpx;
}
.actions { display: flex; gap: 12rpx; margin-top: 16rpx; }
.btn {
  flex: 1;
  height: 64rpx;
  line-height: 64rpx;
  text-align: center;
  border-radius: 8rpx;
  font-size: 26rpx;
  font-weight: 600;
}
.btn-primary { background: #B22222; color: #fff; }
.btn-danger { background: #fff; color: #B22222; border: 1rpx solid #B22222; }
.btn-secondary { background: #f5f5f5; color: #666; }

.modal-mask {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 60rpx;
}
.modal {
  background: #fff;
  border-radius: 16rpx;
  padding: 32rpx 28rpx;
  width: 100%;
  max-width: 600rpx;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}
.modal-title { font-size: 32rpx; font-weight: 700; color: #222; margin-bottom: 8rpx; }
.modal-sub { font-size: 24rpx; color: #888; margin-bottom: 20rpx; }
.textarea {
  width: 100%;
  min-height: 160rpx;
  background: #f5f5f5;
  border-radius: 8rpx;
  padding: 16rpx;
  font-size: 26rpx;
  margin-bottom: 20rpx;
  box-sizing: border-box;
}
.modal-actions { display: flex; gap: 16rpx; }
.modal-actions .btn { flex: 1; height: 72rpx; line-height: 72rpx; }
.log-list { max-height: 500rpx; }
.log-item { padding: 16rpx 0; border-bottom: 1rpx solid #f0f0f0; }
.log-time { font-size: 22rpx; color: #999; }
.log-action { display: flex; align-items: center; gap: 12rpx; margin-top: 6rpx; }
.log-action-tag {
  padding: 2rpx 12rpx;
  border-radius: 4rpx;
  font-size: 22rpx;
  color: #fff;
}
.action-submit { background: #6B7280; }
.action-approve { background: #059669; }
.action-reject { background: #B22222; }
.log-operator { font-size: 26rpx; color: #222; }
.log-comment {
  margin-top: 6rpx;
  font-size: 24rpx;
  color: #666;
  background: #f5f5f5;
  padding: 8rpx 12rpx;
  border-radius: 4rpx;
}
.empty-mini { text-align: center; padding: 40rpx; color: #999; font-size: 24rpx; }
</style>
