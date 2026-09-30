<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  approveRipple,
  banRipple,
  banUser,
  deleteRipple,
  getAdminStats,
  listAdminRipples,
  listAdminUsers,
  listPendingReviews,
  rejectRipple,
  unbanUser,
  type AdminStats,
} from '@/api/admin'
import type { RippleOut, UserOut } from '@/api/types'

const activeTab = ref('stats')

const stats = ref<AdminStats | null>(null)
const users = ref<UserOut[]>([])
const ripples = ref<RippleOut[]>([])
const reviews = ref<RippleOut[]>([])
const loading = ref(false)
const loadingRipples = ref(false)

/* ---------------- 内容筛选（关键词 + 发布时间范围） ---------------- */
const rippleKeyword = ref('')
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
      ...(rippleRange.value ? { start: rippleRange.value[0], end: rippleRange.value[1] } : {}),
    })
  } finally {
    loadingRipples.value = false
  }
}

function searchRipples() {
  loadRipples()
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

function rippleStatus(row: RippleOut) {
  const map: Record<string, { type: 'success' | 'danger' | 'warning' | 'info'; text: string }> = {
    published: { type: 'success', text: '已发布' },
    banned: { type: 'danger', text: '已封禁' },
    pending: { type: 'warning', text: '审核中' },
  }
  return map[row.status] || { type: 'info', text: row.status }
}

async function loadBase() {
  loading.value = true
  try {
    const [s, u, rv] = await Promise.all([
      getAdminStats(),
      listAdminUsers({ limit: 100 }),
      listPendingReviews({ limit: 100 }),
    ])
    stats.value = s
    users.value = u
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
    ElMessage.success(`已封禁用户「${(target as UserOut).nickname}」`)
  } else {
    await banRipple(target.id, { reason: banDialog.reason || null })
    ElMessage.success(`已封禁微澜「${(target as RippleOut).content.slice(0, 12)}…」（仅作者可见）`)
  }
  banDialog.visible = false
  loadBase()
  loadRipples()
}

async function releaseUser(user: UserOut) {
  await unbanUser(user.id)
  ElMessage.success(`已解封「${user.nickname}」`)
  loadBase()
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
  ElMessage.success(`微澜「${r.content.slice(0, 12)}…」已通过审核，恢复公开`)
  loadBase()
}

async function rejectReview(r: RippleOut) {
  try {
    const { value } = await ElMessageBox.prompt('驳回原因（作者可见）', '驳回审核', {
      confirmButtonText: '驳回',
      cancelButtonText: '取消',
      inputType: 'textarea',
    })
    await rejectRipple(r.id, { reason: value || null })
    ElMessage.success(`微澜「${r.content.slice(0, 12)}…」已驳回（仅作者可见）`)
    loadBase()
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
  ElMessage.success('已删除')
  loadBase()
  loadRipples()
}

onMounted(() => {
  loadBase()
  loadRipples()
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
        </div>
        <p class="tip">审核队列中待处理 {{ reviews.length }} 条</p>
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

      <!-- 用户管理 -->
      <el-tab-pane label="用户管理" name="users">
        <div class="card">
          <el-table v-loading="loading" :data="users" size="small">
            <el-table-column prop="nickname" label="昵称" min-width="110" />
            <el-table-column prop="username" label="用户名" min-width="100" />
            <el-table-column label="角色" width="90">
              <template #default="{ row }">
                <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
                  {{ row.role === 'admin' ? '管理员' : '用户' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="封禁状态" width="180">
              <template #default="{ row }">
                <el-tag v-if="row.ban_status === 'banned'" type="danger" size="small">
                  封禁中{{ row.ban_until ? ` · 至 ${formatTime(row.ban_until)}` : '（永久）' }}
                </el-tag>
                <el-tag v-else type="success" size="small">正常</el-tag>
              </template>
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
                <el-tag :type="rippleStatus(row).type" size="small">
                  {{ rippleStatus(row).text }}
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
  grid-template-columns: repeat(5, 1fr);
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
