<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/stores/user'
import { fetchMyRipples, updateRipple } from '@/api/ripples'
import type { LikeOut, RippleOut, UserProfile } from '@/api/types'
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

const myRipples = ref<RippleOut[]>([])
const loading = ref(false)
const social = ref<UserProfile | null>(null)

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

/* ---------------- 编辑被封禁微澜 ---------------- */
const editDialog = reactive({
  visible: false,
  target: null as RippleOut | null,
  content: '',
})
const submitting = ref(false)

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
  loading.value = true
  try {
    myRipples.value = await fetchMyRipples({ limit: 50 })
  } finally {
    loading.value = false
  }
}

function openEdit(r: RippleOut) {
  editDialog.visible = true
  editDialog.target = r
  editDialog.content = r.content
}

async function submitEdit() {
  const target = editDialog.target
  if (!target) return
  if (!editDialog.content.trim()) {
    ElMessage.warning('内容不能为空')
    return
  }
  submitting.value = true
  try {
    const updated = await updateRipple(target.id, {
      content: editDialog.content.trim(),
      images: target.images || [],
    })
    ElMessage.success('已重新提交审核，等待管理员通过后恢复公开')
    editDialog.visible = false
    // 局部更新状态
    const idx = myRipples.value.findIndex((r) => r.id === target.id)
    if (idx >= 0) myRipples.value[idx] = updated
  } finally {
    submitting.value = false
  }
}

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
          <div v-loading="loading">
            <div v-for="r in myRipples" :key="r.id" class="card my-ripple">
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
              <div v-if="r.status === 'banned'" class="mr-action">
                <el-button type="primary" size="small" @click="openEdit(r)">
                  修改并重新提交审核
                </el-button>
                <span class="mr-hint">修改后需管理员审核通过才会重新公开</span>
              </div>
              <div v-else-if="r.status === 'pending'" class="mr-hint">
                内容正在审核中，请耐心等待
              </div>
            </div>
            <div v-if="!loading && myRipples.length === 0" class="empty-tip">
              还没有发过微澜，去记录第一朵涟漪吧
            </div>
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
    <el-dialog v-model="editDialog.visible" title="修改并重新提交审核" width="480px">
      <el-input
        v-model="editDialog.content"
        type="textarea"
        :rows="4"
        maxlength="200"
        show-word-limit
        placeholder="修改后的内容"
      />
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitEdit">
          提交审核
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
}

.mr-hint {
  font-size: 12px;
  color: #90a4ae;
}
</style>
