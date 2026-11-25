<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { toast } from '@/utils/toast'
import {
  approveRipple,
  banRipple,
  banUser,
  deleteRipple,
  getAdminStats,
  getReviewHistory,
  handleAdminAppeal,
  handleAdminReport,
  listAdminAppeals,
  listAdminReports,
  listAdminRipples,
  listAdminUsers,
  listPendingReviews,
  rejectRipple,
  unbanUser,
  type AdminRippleStatus,
  type AdminStats,
  type AdminUserStatus,
  type ReviewLog,
} from '@/api/admin'
import type { AppealOut, AppealStatus, ReportOut, ReportStatus, RippleOut, UserOut } from '@/api/types'

const activeTab = ref('stats')

const stats = ref<AdminStats | null>(null)
const users = ref<UserOut[]>([])
const ripples = ref<RippleOut[]>([])
const reviews = ref<RippleOut[]>([])
const reviewLogs = ref<ReviewLog[]>([])
const loading = ref(false)
const loadingUsers = ref(false)
const loadingRipples = ref(false)
const loadingLogs = ref(false)
const reports = ref<ReportOut[]>([])
const appeals = ref<AppealOut[]>([])
const loadingReports = ref(false)
const loadingAppeals = ref(false)
const reportStatus = ref<ReportStatus>('pending')
const appealStatus = ref<AppealStatus>('pending')

/* ---------------- 用户筛选（关键词 + 封禁状态） ---------------- */
const userKeyword = ref('')
const userStatus = ref<AdminUserStatus | ''>('')

/* ---------------- 内容筛选（关键词 + 状态 + 发布时间范围） ---------------- */
const rippleKeyword = ref('')
const rippleStatus = ref<AdminRippleStatus | ''>('')
const rippleRange = ref<[string, string] | null>(null)

const rangeShortcuts = [
  {
    text: '今天',
    value: () => {
      const e = new Date()
      return [e, e] as [Date, Date]
    },
  },
  {
    text: '近 7 天',
    value: () => {
      const e = new Date()
      const s = new Date()
      s.setDate(s.getDate() - 6)
      return [s, e] as [Date, Date]
    },
  },
  {
    text: '近 30 天',
    value: () => {
      const e = new Date()
      const s = new Date()
      s.setDate(s.getDate() - 29)
      return [s, e] as [Date, Date]
    },
  },
]

async function loadRipples() {
  loadingRipples.value = true
  try {
    ripples.value = await listAdminRipples({
      limit: 100,
      ...(rippleKeyword.value.trim() ? { keyword: rippleKeyword.value.trim() } : {}),
      ...(rippleStatus.value ? { status: rippleStatus.value } : {}),
      ...(rippleRange.value ? { start: rippleRange.value[0], end: rippleRange.value[1] } : {}),
    })
  } finally {
    loadingRipples.value = false
  }
}

function searchRipples() {
  loadRipples()
}

/* ---------------- 用户列表 / 审核记录 ---------------- */
async function loadUsers() {
  loadingUsers.value = true
  try {
    users.value = await listAdminUsers({
      limit: 100,
      ...(userKeyword.value.trim() ? { keyword: userKeyword.value.trim() } : {}),
      ...(userStatus.value ? { status: userStatus.value } : {}),
    })
  } finally {
    loadingUsers.value = false
  }
}

function searchUsers() {
  loadUsers()
}

async function loadReviewLogs() {
  loadingLogs.value = true
  try {
    reviewLogs.value = await getReviewHistory({ limit: 100 })
  } finally {
    loadingLogs.value = false
  }
}

/* ---------------- 封禁弹窗 ---------------- */
const banDialog = reactive({
  visible: false,
  targetType: '' as 'user' | 'ripple',
  target: null as UserOut | RippleOut | null,
  duration: 7 as number | null,
  reason: '',
})

const PRESET_DURATIONS = [
  { label: '1 天', value: 1 },
  { label: '7 天', value: 7 },
  { label: '30 天', value: 30 },
  { label: '永久', value: null },
]

function formatTime(iso: string | null): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

function rippleStatusMeta(row: RippleOut) {
  const map: Record<string, { type: 'success' | 'danger' | 'warning' | 'info'; text: string }> = {
    published: { type: 'success', text: '已发布' },
    banned: { type: 'danger', text: '已封禁' },
    pending: { type: 'warning', text: '审核中' },
  }
  return map[row.status] || { type: 'info', text: row.status }
}

function reviewAction(action: string) {
  const map: Record<string, { type: 'success' | 'danger' | 'warning' | 'info'; text: string }> = {
    ban: { type: 'danger', text: '封禁' },
    reject: { type: 'warning', text: '驳回' },
    approve: { type: 'success', text: '通过' },
    appeal_approve: { type: 'success', text: '申诉通过' },
    appeal_reject: { type: 'warning', text: '申诉驳回' },
  }
  return map[action] || { type: 'info', text: action }
}

const reportReasonLabels: Record<string, string> = {
  spam: '广告 / 引流', abuse: '攻击 / 骚扰', misinformation: '不实信息',
  illegal: '违法违规', other: '其他',
}

function reportStatusMeta(value: ReportStatus) {
  const map: Record<ReportStatus, { type: 'success' | 'danger' | 'warning' | 'info'; text: string }> = {
    pending: { type: 'warning', text: '待处理' },
    uphold: { type: 'danger', text: '举报成立' },
    dismissed: { type: 'success', text: '未发现违规' },
  }
  return map[value]
}

function appealStatusMeta(value: AppealStatus) {
  const map: Record<AppealStatus, { type: 'success' | 'danger' | 'warning' | 'info'; text: string }> = {
    pending: { type: 'warning', text: '待处理' },
    approved: { type: 'success', text: '申诉通过' },
    rejected: { type: 'danger', text: '申诉驳回' },
  }
  return map[value]
}

async function loadReports() {
  loadingReports.value = true
  try {
    const page = await listAdminReports({ limit: 100, status: reportStatus.value })
    reports.value = page.items
  } finally {
    loadingReports.value = false
  }
}

async function loadAppeals() {
  loadingAppeals.value = true
  try {
    const page = await listAdminAppeals({ limit: 100, status: appealStatus.value })
    appeals.value = page.items
  } finally {
    loadingAppeals.value = false
  }
}

async function processReport(row: ReportOut, action: 'uphold' | 'dismiss') {
  let note: string | null = null
  try {
    const result = await ElMessageBox.prompt(
      action === 'uphold'
        ? '确认后该微澜将被下架，同一内容的其它待处理举报一并结案。可填写处理说明（举报人和作者都会看到）'
        : '可填写处理说明（举报人会看到）',
      action === 'uphold' ? '举报成立' : '举报不成立',
      {
        confirmButtonText: action === 'uphold' ? '成立并下架' : '不成立',
        cancelButtonText: '取消', inputType: 'textarea',
        inputPlaceholder: '处理说明（选填，最多 200 字）',
      },
    )
    note = result.value.trim() || null
  } catch { return }
  await handleAdminReport(row.id, { action, note })
  toast.success(action === 'uphold' ? '举报成立，内容已下架，已通知举报人与作者' : '举报已关闭，已通知举报人')
  loadReports()
  loadBase()
  loadRipples()
  loadReviewLogs()
  loadAppeals()
}

async function processAppeal(row: AppealOut, action: 'approve' | 'reject') {
  let note: string | null = null
  try {
    const result = await ElMessageBox.prompt(
      action === 'approve' ? '通过后该微澜将恢复公开。可填写处理说明（作者会看到）' : '驳回后该微澜维持下架。可填写处理说明（作者会看到）',
      action === 'approve' ? '申诉通过' : '申诉驳回',
      {
        confirmButtonText: action === 'approve' ? '恢复公开' : '维持下架',
        cancelButtonText: '取消', inputType: 'textarea',
        inputPlaceholder: '处理说明（选填，最多 200 字）',
      },
    )
    note = result.value.trim() || null
  } catch { return }
  await handleAdminAppeal(row.id, { action, note })
  toast.success(action === 'approve' ? '申诉通过，内容已恢复公开，已通知作者' : '申诉驳回，内容维持下架，已通知作者')
  loadAppeals()
  loadBase()
  loadRipples()
  loadReviewLogs()
  loadReports()
}

async function loadBase() {
  loading.value = true
  try {
    const [s, rv] = await Promise.all([
      getAdminStats(),
      listPendingReviews({ limit: 100 }),
    ])
    stats.value = s
    reviews.value = rv
  } finally {
    loading.value = false
  }
}

/* ---------------- 用户封禁 / 解封 ---------------- */
function openBanUser(user: UserOut) {
  banDialog.visible = true
  banDialog.targetType = 'user'
  banDialog.target = user
  banDialog.duration = 7
  banDialog.reason = ''
}

async function confirmBan() {
  const target = banDialog.target
  if (!target) return
  if (banDialog.targetType === 'user') {
    await banUser(target.id, {
      duration_days: banDialog.duration,
      reason: banDialog.reason || null,
    })
    toast.success(`已封禁用户「${(target as UserOut).nickname}」，已通知本人`)
  } else {
    await banRipple(target.id, { reason: banDialog.reason || null })
    toast.success(`已封禁微澜「${(target as RippleOut).content.slice(0, 12)}…」（仅作者可见），已通知作者`)
  }
  banDialog.visible = false
  loadBase()
  loadUsers()
  loadRipples()
  loadReviewLogs()
}

async function releaseUser(user: UserOut) {
  await unbanUser(user.id)
  toast.success(`已解封「${user.nickname}」，已同步通知本人`)
  loadBase()
  loadUsers()
}

/* ---------------- 微澜审核 / 封禁 / 删除 ---------------- */
function openBanRipple(r: RippleOut) {
  banDialog.visible = true
  banDialog.targetType = 'ripple'
  banDialog.target = r
  banDialog.reason = ''
}

async function passReview(r: RippleOut) {
  await approveRipple(r.id)
  toast.success(`微澜「${r.content.slice(0, 12)}…」已通过审核，恢复公开，已通知作者`)
  loadBase()
  loadRipples()
  loadReviewLogs()
}

async function rejectReview(r: RippleOut) {
  try {
    const { value } = await ElMessageBox.prompt('驳回原因（作者可见）', '驳回审核', {
      confirmButtonText: '驳回',
      cancelButtonText: '取消',
      inputType: 'textarea',
    })
    await rejectRipple(r.id, { reason: value || null })
    toast.success(`微澜「${r.content.slice(0, 12)}…」已驳回（仅作者可见），已通知作者`)
    loadBase()
    loadRipples()
    loadReviewLogs()
  } catch {
    /* 取消 */
  }
}

async function removeRipple(r: RippleOut) {
  try {
    await ElMessageBox.confirm(
      `确认删除微澜「${r.content.slice(0, 20)}…」？相关回声与点赞将一并删除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await deleteRipple(r.id)
  toast.success('已删除，已通知作者')
  loadBase()
  loadRipples()
  loadReviewLogs()
}

onMounted(() => {
  loadBase()
  loadUsers()
  loadRipples()
  loadReviewLogs()
  loadReports()
  loadAppeals()
})
</script>

<template>
  <div>
    <h2 class="page-title">管理后台</h2>

    <el-tabs v-model="activeTab">
      <!-- 概览 -->
      <el-tab-pane label="平台概览" name="stats">
        <div class="stat-grid">
          <div class="stat-card">
            <div class="stat-num">{{ stats?.users ?? '-' }}</div>
            <div class="stat-label">用户</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{{ stats?.ripples ?? '-' }}</div>
            <div class="stat-label">微澜</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{{ stats?.echoes ?? '-' }}</div>
            <div class="stat-label">回声</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{{ stats?.likes ?? '-' }}</div>
            <div class="stat-label">点赞</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{{ stats?.topics ?? '-' }}</div>
            <div class="stat-label">话题</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{{ stats?.pending ?? '-' }}</div>
            <div class="stat-label">待审核</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{{ stats?.banned_users ?? '-' }}</div>
            <div class="stat-label">封禁用户</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{{ stats?.banned_ripples ?? '-' }}</div>
            <div class="stat-label">封禁微澜</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{{ stats?.pending_reports ?? '-' }}</div>
            <div class="stat-label">待处理举报</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">{{ stats?.pending_appeals ?? '-' }}</div>
            <div class="stat-label">待处理申诉</div>
          </div>
        </div>
        <p class="tip">审核队列中待处理 {{ stats?.pending ?? reviews.length }} 条 · 举报 {{ stats?.pending_reports ?? 0 }} 条 · 申诉 {{ stats?.pending_appeals ?? 0 }} 条</p>
      </el-tab-pane>

      <!-- 审核队列 -->
      <el-tab-pane :label="`审核队列${reviews.length ? `（${reviews.length}）` : ''}`" name="reviews">
        <div class="card">
          <el-table v-loading="loading" :data="reviews" size="small">
            <el-table-column label="内容" min-width="240">
              <template #default="{ row }">{{ row.content }}</template>
            </el-table-column>
            <el-table-column label="作者" width="110">
              <template #default="{ row }">{{ row.user.nickname }}</template>
            </el-table-column>
            <el-table-column label="提交时间" min-width="150">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button type="success" size="small" @click="passReview(row)">通过</el-button>
                <el-button type="warning" size="small" @click="rejectReview(row)">驳回</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!loading && reviews.length === 0" class="empty-tip">暂无待审核内容</div>
        </div>
      </el-tab-pane>

      <!-- 审核记录 -->
      <el-tab-pane label="审核记录" name="history">
        <div class="card">
          <el-table v-loading="loadingLogs" :data="reviewLogs" size="small">
            <el-table-column label="内容" min-width="220">
              <template #default="{ row }">{{ row.content }}</template>
            </el-table-column>
            <el-table-column label="作者" width="100">
              <template #default="{ row }">{{ row.author_name }}</template>
            </el-table-column>
            <el-table-column label="处理" width="90">
              <template #default="{ row }">
                <el-tag :type="reviewAction(row.action).type" size="small">{{ reviewAction(row.action).text }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="原因" min-width="180">
              <template #default="{ row }">
                <span :class="{ muted: !row.reason }">{{ row.reason || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="审核人" width="110">
              <template #default="{ row }">{{ row.reviewer_name }}</template>
            </el-table-column>
            <el-table-column label="处理时间" min-width="150">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <div v-if="!loadingLogs && reviewLogs.length === 0" class="empty-tip">还没有审核记录</div>
        </div>
      </el-tab-pane>

      <!-- 举报处理 -->
      <el-tab-pane :label="`举报处理${reports.length ? `（${reports.length}）` : ''}`" name="reports">
        <div class="filter-bar">
          <el-select v-model="reportStatus" style="width: 150px" @change="loadReports">
            <el-option label="待处理" value="pending" />
            <el-option label="举报成立" value="uphold" />
            <el-option label="未发现违规" value="dismissed" />
          </el-select>
          <span class="muted">举报成立会下架微澜，并同时通知举报人与作者</span>
        </div>
        <div class="card">
          <el-table v-loading="loadingReports" :data="reports" size="small">
            <el-table-column label="被举报内容" min-width="220">
              <template #default="{ row }">{{ row.ripple_content }}</template>
            </el-table-column>
            <el-table-column label="作者" width="105">
              <template #default="{ row }">{{ row.author_name }}</template>
            </el-table-column>
            <el-table-column label="举报人" width="105">
              <template #default="{ row }">{{ row.reporter_name }}</template>
            </el-table-column>
            <el-table-column label="理由" width="100">
              <template #default="{ row }">{{ reportReasonLabels[row.reason_code] || row.reason_code }}</template>
            </el-table-column>
            <el-table-column label="补充说明" min-width="150">
              <template #default="{ row }">
                <span :class="{ muted: !row.detail }">{{ row.detail || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="105">
              <template #default="{ row }">
                <el-tag :type="reportStatusMeta(row.status).type" size="small">{{ reportStatusMeta(row.status).text }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="处理说明" min-width="140">
              <template #default="{ row }">
                <span :class="{ muted: !row.handle_note }">{{ row.handle_note || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="举报时间" min-width="150">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <template v-if="row.status === 'pending'">
                  <el-button type="danger" size="small" link @click="processReport(row, 'uphold')">成立并下架</el-button>
                  <el-button type="success" size="small" link @click="processReport(row, 'dismiss')">不成立</el-button>
                </template>
                <span v-else class="muted">已处理</span>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!loadingReports && reports.length === 0" class="empty-tip">当前没有该状态的举报</div>
        </div>
      </el-tab-pane>

      <!-- 申诉处理 -->
      <el-tab-pane :label="`申诉处理${appeals.length ? `（${appeals.length}）` : ''}`" name="appeals">
        <div class="filter-bar">
          <el-select v-model="appealStatus" style="width: 150px" @change="loadAppeals">
            <el-option label="待处理" value="pending" />
            <el-option label="申诉通过" value="approved" />
            <el-option label="申诉驳回" value="rejected" />
          </el-select>
          <span class="muted">只有被下架内容的作者可以申诉；通过后恢复公开</span>
        </div>
        <div class="card">
          <el-table v-loading="loadingAppeals" :data="appeals" size="small">
            <el-table-column label="申诉内容" min-width="220">
              <template #default="{ row }">{{ row.ripple_content }}</template>
            </el-table-column>
            <el-table-column label="作者" width="105">
              <template #default="{ row }">{{ row.user_name }}</template>
            </el-table-column>
            <el-table-column label="申诉理由" min-width="190">
              <template #default="{ row }">{{ row.reason }}</template>
            </el-table-column>
            <el-table-column label="状态" width="105">
              <template #default="{ row }">
                <el-tag :type="appealStatusMeta(row.status).type" size="small">{{ appealStatusMeta(row.status).text }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="处理说明" min-width="140">
              <template #default="{ row }">
                <span :class="{ muted: !row.handle_note }">{{ row.handle_note || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="申诉时间" min-width="150">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <template v-if="row.status === 'pending'">
                  <el-button type="success" size="small" link @click="processAppeal(row, 'approve')">通过</el-button>
                  <el-button type="warning" size="small" link @click="processAppeal(row, 'reject')">驳回</el-button>
                </template>
                <span v-else class="muted">已处理</span>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!loadingAppeals && appeals.length === 0" class="empty-tip">当前没有该状态的申诉</div>
        </div>
      </el-tab-pane>

      <!-- 用户管理 -->
      <el-tab-pane label="用户管理" name="users">
        <div class="filter-bar">
          <el-input
            v-model="userKeyword"
            placeholder="按昵称 / 用户名搜索"
            clearable
            style="width: 240px"
            @keyup.enter="searchUsers"
            @clear="searchUsers"
          >
            <template #append>
              <el-button @click="searchUsers">搜索</el-button>
            </template>
          </el-input>
          <el-select v-model="userStatus" placeholder="全部状态" clearable style="width: 140px" @change="searchUsers">
            <el-option label="全部状态" value="" />
            <el-option label="正常" value="active" />
            <el-option label="封禁中" value="banned" />
          </el-select>
        </div>

        <div class="card">
          <el-table v-loading="loadingUsers" :data="users" size="small">
            <el-table-column prop="nickname" label="昵称" min-width="110" />
            <el-table-column prop="username" label="用户名" min-width="100" />
            <el-table-column label="角色" width="90">
              <template #default="{ row }">
                <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
                  {{ row.role === 'admin' ? '管理员' : '用户' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="封禁状态" width="190">
              <template #default="{ row }">
                <el-tag v-if="row.ban_status === 'banned'" type="danger" size="small">
                  封禁中{{ row.ban_until ? ` · 至 ${formatTime(row.ban_until)}` : '（永久）' }}
                </el-tag>
                <el-tag v-else type="success" size="small">正常</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="封禁原因" min-width="160">
              <template #default="{ row }">
                <span :class="{ muted: !row.ban_reason }">{{ row.ban_reason || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="注册时间" min-width="150">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <template v-if="row.role !== 'admin'">
                  <el-button
                    v-if="row.ban_status !== 'banned'"
                    type="danger"
                    size="small"
                    link
                    @click="openBanUser(row)"
                  >封禁</el-button>
                  <el-button
                    v-else
                    type="success"
                    size="small"
                    link
                    @click="releaseUser(row)"
                  >解封</el-button>
                </template>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!loadingUsers && users.length === 0" class="empty-tip">没有符合条件的用户</div>
        </div>
      </el-tab-pane>

      <!-- 内容管理 -->
      <el-tab-pane label="内容管理" name="ripples">
        <div class="filter-bar">
          <el-input
            v-model="rippleKeyword"
            placeholder="按内容关键词搜索"
            clearable
            style="width: 240px"
            @keyup.enter="searchRipples"
            @clear="searchRipples"
          >
            <template #append>
              <el-button @click="searchRipples">搜索</el-button>
            </template>
          </el-input>
          <el-select v-model="rippleStatus" placeholder="全部状态" clearable style="width: 140px" @change="searchRipples">
            <el-option label="全部状态" value="" />
            <el-option label="已发布" value="published" />
            <el-option label="审核中" value="pending" />
            <el-option label="已封禁" value="banned" />
            <el-option label="已删除" value="deleted" />
          </el-select>
          <el-date-picker
            v-model="rippleRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD"
            :shortcuts="rangeShortcuts"
            style="width: 320px"
            @change="searchRipples"
          />
          <span class="muted">按发布时间筛选</span>
        </div>

        <div class="card">
          <el-table v-loading="loadingRipples" :data="ripples" size="small">
            <el-table-column label="内容" min-width="240">
              <template #default="{ row }">{{ row.content }}</template>
            </el-table-column>
            <el-table-column label="作者" width="110">
              <template #default="{ row }">{{ row.user.nickname }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="rippleStatusMeta(row).type" size="small">
                  {{ rippleStatusMeta(row).text }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="互动" width="90">
              <template #default="{ row }">💬{{ row.echo_count }} ❤{{ row.like_count }}</template>
            </el-table-column>
            <el-table-column label="发布时间" min-width="150">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.status !== 'banned'"
                  type="warning"
                  size="small"
                  link
                  @click="openBanRipple(row)"
                >封禁</el-button>
                <el-button type="danger" size="small" link @click="removeRipple(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!loadingRipples && ripples.length === 0" class="empty-tip">
            没有符合条件的内容
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 封禁弹窗（用户 / 微澜共用） -->
    <el-dialog
      v-model="banDialog.visible"
      :title="banDialog.targetType === 'user' ? `封禁用户「${(banDialog.target as UserOut)?.nickname}」` : '封禁微澜'"
      width="420px"
    >
      <template v-if="banDialog.targetType === 'user'">
        <div class="dialog-label">封禁时长</div>
        <el-radio-group v-model="banDialog.duration">
          <el-radio-button v-for="d in PRESET_DURATIONS" :key="d.label" :value="d.value">
            {{ d.label }}
          </el-radio-button>
        </el-radio-group>
      </template>

      <div class="dialog-label">原因（展示给用户）</div>
      <el-input
        v-model="banDialog.reason"
        type="textarea"
        :rows="3"
        maxlength="200"
        show-word-limit
        placeholder="例：发布违规内容，多次警告无效"
      />

      <template #footer>
        <el-button @click="banDialog.visible = false">取消</el-button>
        <el-button type="danger" @click="confirmBan">
          {{ banDialog.targetType === 'user' ? '确认封禁' : '确认封禁微澜' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  background: #fff;
  border: 1px solid var(--wl-border);
  border-radius: 12px;
  padding: 18px 12px;
  text-align: center;
}

.stat-num {
  font-size: 28px;
  font-weight: 700;
  color: var(--wl-primary);
}

.stat-label {
  font-size: 13px;
  color: #78909c;
  margin-top: 4px;
}

.tip {
  color: #78909c;
  font-size: 13px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.dialog-label {
  font-size: 13px;
  color: #546e7a;
  margin: 12px 0 8px;
}

.muted {
  color: #b0bec5;
  font-size: 12px;
}
</style>
