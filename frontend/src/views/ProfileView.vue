<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/stores/user'
import { deleteMyRipple, fetchMyRipples, updateRipple } from '@/api/ripples'
import type { LikeOut, MyRippleOut, MyRippleStatus, RippleOut, UserProfile } from '@/api/types'
import { fetchUserProfile } from '@/api/users'
import ImageViewer from '@/components/ImageViewer.vue'
import MyCollections from '@/components/MyCollections.vue'

const userStore = useUserStore()
const { isLoggedIn, user } = storeToRefs(userStore)
const route = useRoute()
const router = useRouter()
const activeTab = ref(route.query.tab === 'collections' ? 'collections' : 'ripples')

function changeTab(name: string | number) {
  void router.replace({
    query: { ...route.query, tab: name === 'collections' ? 'collections' : undefined },
  })
}

watch(() => route.query.tab, (tab) => {
  activeTab.value = tab === 'collections' ? 'collections' : 'ripples'
})

const myRipples = ref<MyRippleOut[]>([])
const loading = ref(true)
const failed = ref(false)
const social = ref<UserProfile | null>(null)
const filter = ref<MyRippleStatus | ''>('')
const keyword = ref('')
const submittedKeyword = ref('')
const page = ref(1)
const pageSize = 10
const hasNext = ref(false)
let listVersion = 0

const filters: { value: MyRippleStatus | ''; label: string }[] = [
  { value: '', label: '全部' },
  { value: 'published', label: '已发布' },
  { value: 'pending', label: '审核中' },
  { value: 'banned', label: '需修改' },
]

const reviewLabels = { ban: '管理员已下架', reject: '审核未通过', approve: '审核通过' }

function updateLike(state: LikeOut) {
  const ripple = myRipples.value.find((item) => item.id === state.ripple_id)
  if (ripple) {
    ripple.is_liked = state.is_liked
    ripple.like_count = state.like_count
  }
}

/* ---------- 图片放大预览 ---------- */
const viewer = reactive({
  visible: false,
  urls: [] as string[],
  index: 0,
})

function openViewer(urls: string[], index: number) {
  viewer.urls = urls
  viewer.index = index
  viewer.visible = true
}

const editDialog = reactive({
  visible: false,
  target: null as MyRippleOut | null,
  content: '',
})
const submitting = ref(false)
const deleting = ref<number | null>(null)
const resubmitting = computed(() => editDialog.target?.status === 'banned')

function statusTag(row: RippleOut) {
  const map: Record<string, { type: 'success' | 'danger' | 'warning'; text: string }> = {
    published: { type: 'success', text: '已发布' },
    banned: { type: 'danger', text: '已封禁 · 仅自己可见' },
    pending: { type: 'warning', text: '修改后待审核' },
  }
  return map[row.status] || { type: 'warning', text: row.status }
}

async function loadMyRipples() {
  if (!isLoggedIn.value) return
  const version = ++listVersion
  loading.value = true
  failed.value = false
  try {
    const items = await fetchMyRipples({
      limit: pageSize + 1,
      offset: (page.value - 1) * pageSize,
      status: filter.value || undefined,
      keyword: submittedKeyword.value || undefined,
    })
    if (version !== listVersion) return
    if (!items.length && page.value > 1) {
      page.value--
      return
    }
    hasNext.value = items.length > pageSize
    myRipples.value = items.slice(0, pageSize)
  } catch {
    if (version === listVersion) failed.value = true
  } finally {
    if (version === listVersion) loading.value = false
  }
}

function search() {
  submittedKeyword.value = keyword.value.trim()
  page.value = 1
}

function changeStatus(status: MyRippleStatus | '') {
  filter.value = status
  page.value = 1
}

function openEdit(r: MyRippleOut) {
  editDialog.visible = true
  editDialog.target = r
  editDialog.content = r.content
}

async function submitEdit() {
  const target = editDialog.target
  if (!target || submitting.value || (target.status !== 'published' && target.status !== 'banned')) return
  if (!editDialog.content.trim()) {
    ElMessage.warning('内容不能为空')
    return
  }
  submitting.value = true
  try {
    const updated = await updateRipple(target.id, {
      content: editDialog.content.trim(),
      expected_status: target.status,
    })
    ElMessage.success(updated.status === 'pending' ? '已重新提交审核' : '微澜已更新')
    editDialog.visible = false
    await loadMyRipples()
  } catch (error) {
    if ((error as { response?: { status?: number } }).response?.status === 409) {
      editDialog.visible = false
      await loadMyRipples()
    }
  } finally {
    submitting.value = false
  }
}

async function removeRipple(ripple: MyRippleOut) {
  if (deleting.value !== null) return
  deleting.value = ripple.id
  try {
    await ElMessageBox.confirm(
      '删除后，这条微澜和它的回声将退出社区展示，无法从个人主页恢复。',
      '删除微澜',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await deleteMyRipple(ripple.id)
    ElMessage.success('微澜已删除')
    await loadMyRipples()
  } catch { /* 取消或请求失败时保留当前列表。 */ }
  finally { deleting.value = null }
}

watch([filter, submittedKeyword, page], loadMyRipples)
onBeforeUnmount(() => { listVersion++ })

onMounted(async () => {
  await userStore.refreshMe()
  if (!user.value) return
  void loadMyRipples()
  try { social.value = await fetchUserProfile(user.value.id) }
  catch { /* 全局提示 */ }
})
</script>

<template>
  <div>
    <!-- 个人信息 -->
    <div class="card profile-card">
      <template v-if="isLoggedIn && user">
        <div class="me">
          <div class="me-avatar">{{ user.nickname.slice(0, 1) }}</div>
          <div class="me-info">
            <div class="me-nickname">{{ user.nickname }}</div>
            <div class="me-meta">
              @{{ user.username }} · {{ user.role === 'admin' ? '管理员' : '普通用户' }}
            </div>
            <div class="me-bio">{{ user.bio || '还没有签名，去写一句吧。' }}</div>
            <div v-if="social" class="me-meta">
              <router-link :to="`/users/${user.id}?tab=following`">关注 {{ social.following_count }}</router-link>
              · <router-link :to="`/users/${user.id}?tab=followers`">粉丝 {{ social.follower_count }}</router-link>
            </div>
          </div>
        </div>
      </template>
      <div v-else class="empty-tip">请先登录再访问个人主页</div>
    </div>

    <!-- 个人内容与收藏 -->
    <template v-if="isLoggedIn && user">
      <el-tabs v-model="activeTab" class="profile-tabs" @tab-change="changeTab">
        <el-tab-pane label="我的微澜" name="ripples">
          <div class="card creator-controls">
            <form class="creator-search" role="search" @submit.prevent="search">
              <input v-model="keyword" aria-label="搜索我的微澜" placeholder="搜索我的微澜" type="search" maxlength="100" @search="!keyword && search()" />
              <button type="submit">搜索</button>
            </form>
            <div class="creator-filters" role="group" aria-label="按发布状态筛选">
              <button v-for="item in filters" :key="item.value" type="button"
                :aria-pressed="filter === item.value" @click="changeStatus(item.value)">{{ item.label }}</button>
            </div>
          </div>
          <div :aria-busy="loading">
            <div v-if="loading" role="status" class="empty-tip">正在读取我的微澜…</div>
            <div v-else-if="failed" class="empty-tip">
              微澜加载失败。<el-button text @click="loadMyRipples">重试</el-button>
            </div>
            <template v-else>
            <article v-for="r in myRipples" :key="r.id" class="card my-ripple">
              <div class="mr-head">
                <el-tag :type="statusTag(r).type" size="small">{{ statusTag(r).text }}</el-tag>
                <span class="mr-time">{{ new Date(r.created_at).toLocaleString('zh-CN') }}</span>
                <span class="mr-stats">💬{{ r.echo_count }} ❤{{ r.like_count }}</span>
              </div>
              <p class="mr-content">{{ r.content }}</p>
              <div v-if="r.images?.length" class="mr-images">
                <img
                  v-for="(url, i) in r.images.slice(0, 4)"
                  :key="i"
                  :src="url"
                  class="mr-img"
                  alt="配图"
                  @click="openViewer(r.images, i)"
                />
              </div>
              <p v-if="r.status === 'pending'" class="mr-hint">新版内容正在审核，审核通过后会重新公开。</p>
              <p v-else-if="r.latest_review" class="mr-review">
                <strong>{{ reviewLabels[r.latest_review.action] }}</strong>
                <span v-if="r.latest_review.reason">{{ r.latest_review.reason }}</span>
              </p>
              <div class="mr-action">
                <router-link :to="{ name: 'ripple-detail', params: { id: r.id } }">查看详情</router-link>
                <el-button v-if="r.status === 'published' || r.status === 'banned'" type="primary" plain size="small"
                  :disabled="deleting !== null" @click="openEdit(r)">
                  {{ r.status === 'banned' ? '修改并重新提交审核' : '编辑正文' }}
                </el-button>
                <el-button type="danger" text size="small" :loading="deleting === r.id"
                  :disabled="deleting !== null" @click="removeRipple(r)">删除微澜</el-button>
              </div>
            </article>
            <div v-if="!myRipples.length" class="empty-tip">
              {{ filter || submittedKeyword ? '没有符合当前筛选的微澜。' : '你还没有发布微澜。' }}
            </div>
            <nav v-if="page > 1 || hasNext" class="creator-pagination" aria-label="我的微澜分页">
              <button type="button" :disabled="page === 1" @click="page--">上一页</button>
              <span>第 {{ page }} 页</span>
              <button type="button" :disabled="!hasNext" @click="page++">下一页</button>
            </nav>
            </template>
          </div>
        </el-tab-pane>
        <el-tab-pane label="我的收藏" name="collections">
          <MyCollections v-if="activeTab === 'collections'" @like-updated="updateLike" />
        </el-tab-pane>
      </el-tabs>
    </template>

    <ImageViewer
      v-if="viewer.visible"
      :urls="viewer.urls"
      :index="viewer.index"
      @close="viewer.visible = false"
    />

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editDialog.visible" :title="resubmitting ? '修改并重新提交审核' : '编辑正文'"
      width="min(480px, calc(100% - 32px))" :close-on-click-modal="!submitting" :close-on-press-escape="!submitting"
      :show-close="!submitting">
      <el-input
        v-model="editDialog.content"
        type="textarea"
        :rows="4"
        maxlength="200"
        show-word-limit
        aria-label="微澜正文"
        :disabled="submitting"
        placeholder="修改后的内容"
      />
      <template #footer>
        <el-button :disabled="submitting" @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitEdit">
          {{ resubmitting ? '提交审核' : '保存修改' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.profile-card {
  max-width: 640px;
}

.me {
  display: flex;
  gap: 16px;
  align-items: center;
}

.me-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1f7a8c, #4fb3c4);
  color: #fff;
  font-size: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.me-nickname {
  font-size: 18px;
  font-weight: 700;
}

.me-meta {
  font-size: 12px;
  color: #90a4ae;
  margin: 4px 0;
}

.me-bio {
  color: #546e7a;
  font-size: 14px;
}

.profile-tabs {
  margin-top: 24px;
}

.my-ripple {
  padding: 14px 16px;
}

.mr-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.mr-time {
  font-size: 12px;
  color: #90a4ae;
}

.mr-stats {
  margin-left: auto;
  font-size: 13px;
  color: #78909c;
}

.mr-content {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  margin: 0 0 8px;
  font-size: 14px;
  line-height: 1.7;
}

.mr-images {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.mr-img {
  width: 64px;
  height: 64px;
  border-radius: 6px;
  /* contain：保持原始比例，不裁切 */
  object-fit: contain;
  background: #f2f6f8;
  cursor: zoom-in;
}

.mr-action {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.mr-action a { color: var(--wl-primary); font-size: 13px; }
.mr-action :deep(.el-button + .el-button) { margin-left: 0; }
.mr-hint, .mr-review { font-size: 13px; color: var(--wl-muted); margin: 8px 0 12px; }
.mr-review span { margin-left: 8px; overflow-wrap: anywhere; }
.creator-controls, .creator-filters, .creator-search, .creator-pagination {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.creator-controls { justify-content: space-between; }
.creator-search { flex-wrap: nowrap; max-width: 100%; }
.creator-search input, .creator-controls button, .creator-pagination button {
  border: 1px solid var(--wl-border);
  border-radius: 8px;
  padding: 7px 10px;
  color: var(--wl-ink);
  background: white;
  font: inherit;
  font-size: 13px;
}
.creator-search input { min-width: 0; }
.creator-controls button, .creator-pagination button { cursor: pointer; white-space: nowrap; }
.creator-controls button[aria-pressed='true'] { background: #e1efe6; color: var(--wl-primary); }
.creator-pagination { justify-content: center; font-size: 13px; }
.creator-pagination button:disabled { color: var(--wl-muted); cursor: default; }
</style>
