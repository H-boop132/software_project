<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/stores/user'
import { deleteMyRipple, fetchMyRipples, getMoodTones, updateRipple } from '@/api/ripples'
import type { EmotionOut, LikeOut, MyRippleOut, MyRippleStatus, RippleOut, UserProfile } from '@/api/types'
import { changeMyPassword, deleteMyAccount, fetchUserProfile, updateMyPrivacy, updateMyProfile } from '@/api/users'
import { cleanupUpload, uploadImage } from '@/api/upload'
import ImageViewer from '@/components/ImageViewer.vue'
import MyCollections from '@/components/MyCollections.vue'
import MyLikes from '@/components/MyLikes.vue'

const userStore = useUserStore()
const { isLoggedIn, user } = storeToRefs(userStore)
const route = useRoute()
const router = useRouter()

function tabFromQuery(tab: unknown): 'ripples' | 'likes' | 'collections' {
  return tab === 'likes' || tab === 'collections' ? tab : 'ripples'
}

const activeTab = ref(tabFromQuery(route.query.tab))

function changeTab(name: string | number) {
  const tab = name === 'likes' || name === 'collections' ? name : undefined
  void router.replace({ query: { ...route.query, tab } })
}

watch(() => route.query.tab, (tab) => {
  activeTab.value = tabFromQuery(tab)
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

/* ---------- 资料编辑 ---------- */
const moodTones = ref<EmotionOut[]>([])
const profileDialog = reactive({
  visible: false,
  nickname: '',
  bio: '',
  mood_tone: '',
  avatar_url: '',
})
const savingProfile = ref(false)
const uploadingAvatar = ref(false)

function openProfileEdit() {
  if (!user.value) return
  profileDialog.nickname = user.value.nickname
  profileDialog.bio = user.value.bio || ''
  profileDialog.mood_tone = user.value.mood_tone || ''
  profileDialog.avatar_url = user.value.avatar_url || ''
  profileDialog.visible = true
}

async function handleAvatarUpload(options: {
  file: File
  onSuccess?: (response?: unknown) => void
  onError?: (error: unknown) => void
}) {
  uploadingAvatar.value = true
  try {
    const previous = profileDialog.avatar_url
    const { url } = await uploadImage(options.file)
    profileDialog.avatar_url = url
    // 替换了尚未保存的头像：把前一张"传了但没用到"的文件清理掉
    if (previous && previous !== user.value?.avatar_url) void cleanupUpload(previous)
    options.onSuccess?.()
  } catch (error) {
    options.onError?.(error) /* 全局提示 */
  } finally { uploadingAvatar.value = false }
}

async function submitProfile() {
  if (!user.value || savingProfile.value) return
  const nickname = profileDialog.nickname.trim()
  if (!nickname) {
    ElMessage.warning('昵称不能为空')
    return
  }
  savingProfile.value = true
  try {
    await updateMyProfile({
      nickname,
      bio: profileDialog.bio.trim() || null,
      mood_tone: profileDialog.mood_tone || null,
      avatar_url: profileDialog.avatar_url || null,
    })
    await userStore.refreshMe()
    if (user.value) {
      try { social.value = await fetchUserProfile(user.value.id) } catch { /* 忽略统计刷新失败 */ }
    }
    profileDialog.visible = false
    ElMessage.success('资料已更新')
  } catch { /* 全局提示 */ }
  finally { savingProfile.value = false }
}

/** 关闭编辑资料弹窗时，清掉本次上传但未保存的头像文件 */
function handleProfileDialogClosed() {
  const draftAvatar = profileDialog.avatar_url
  if (draftAvatar && draftAvatar !== user.value?.avatar_url) void cleanupUpload(draftAvatar)
}

/* ---------- 账号设置：主页可见范围 ---------- */
const privacyDialog = reactive({
  visible: false,
  hide_following: false,
  hide_followers: false,
  hide_likes: false,
  hide_collections: false,
})
const savingPrivacy = ref(false)

function openPrivacyDialog() {
  if (!user.value) return
  privacyDialog.hide_following = user.value.hide_following
  privacyDialog.hide_followers = user.value.hide_followers
  privacyDialog.hide_likes = user.value.hide_likes
  privacyDialog.hide_collections = user.value.hide_collections
  privacyDialog.visible = true
}

async function submitPrivacy() {
  if (savingPrivacy.value) return
  savingPrivacy.value = true
  try {
    await updateMyPrivacy({
      hide_following: privacyDialog.hide_following,
      hide_followers: privacyDialog.hide_followers,
      hide_likes: privacyDialog.hide_likes,
      hide_collections: privacyDialog.hide_collections,
    })
    await userStore.refreshMe()
    if (user.value) {
      try { social.value = await fetchUserProfile(user.value.id) } catch { /* 忽略统计刷新失败 */ }
    }
    privacyDialog.visible = false
    ElMessage.success('主页可见范围已更新')
  } catch { /* 全局提示 */ }
  finally { savingPrivacy.value = false }
}

/* ---------- 账号设置：修改密码 / 注销账号 ---------- */
const passwordDialog = reactive({ visible: false, oldPassword: '', newPassword: '', confirm: '' })
const changingPassword = ref(false)

function openPasswordDialog() {
  passwordDialog.oldPassword = ''
  passwordDialog.newPassword = ''
  passwordDialog.confirm = ''
  passwordDialog.visible = true
}

async function submitPassword() {
  if (changingPassword.value) return
  if (!passwordDialog.oldPassword) {
    ElMessage.warning('请输入原密码')
    return
  }
  if (passwordDialog.newPassword.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (passwordDialog.newPassword !== passwordDialog.confirm) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  changingPassword.value = true
  try {
    await changeMyPassword({
      old_password: passwordDialog.oldPassword,
      new_password: passwordDialog.newPassword,
    })
    passwordDialog.visible = false
    userStore.logout()
    ElMessage.success('密码已修改，请用新密码重新登录')
    await router.push('/login')
  } catch { /* 全局提示 */ }
  finally { changingPassword.value = false }
}

const deleteDialog = reactive({ visible: false, password: '' })
const deletingAccount = ref(false)

function openDeleteDialog() {
  deleteDialog.password = ''
  deleteDialog.visible = true
}

async function submitDeleteAccount() {
  if (deletingAccount.value) return
  if (!deleteDialog.password) {
    ElMessage.warning('请输入当前密码')
    return
  }
  try {
    await ElMessageBox.confirm(
      '注销后你的微澜、回声、关注关系都会被删除，且无法恢复。确定继续？',
      '注销账号',
      { type: 'warning', confirmButtonText: '确认注销', cancelButtonText: '再想想' },
    )
  } catch {
    return
  }
  deletingAccount.value = true
  try {
    await deleteMyAccount({ password: deleteDialog.password })
    deleteDialog.visible = false
    userStore.logout()
    ElMessage.success('账号已注销')
    router.push('/login')
  } catch { /* 全局提示 */ }
  finally { deletingAccount.value = false }
}

onMounted(async () => {
  await userStore.refreshMe()
  if (!user.value) return
  void loadMyRipples()
  getMoodTones().then((items) => { moodTones.value = items }).catch(() => { /* 下拉缺省为空 */ })
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
          <div class="me-avatar">
            <img v-if="user.avatar_url" :src="user.avatar_url" class="me-avatar-img" alt="头像" />
            <template v-else>{{ user.nickname.slice(0, 1) }}</template>
          </div>
          <div class="me-info">
            <div class="me-nickname-row">
              <div class="me-nickname">{{ user.nickname }}</div>
              <el-button size="small" text type="primary" @click="openProfileEdit">编辑资料</el-button>
            </div>
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

    <!-- 账号设置 -->
    <div v-if="isLoggedIn && user" class="card account-card">
      <h3>账号设置</h3>
      <div class="account-row">
        <div class="account-copy">
          <strong>修改密码</strong>
          <span>修改后当前登录状态不受影响，下次登录使用新密码。</span>
        </div>
        <el-button @click="openPasswordDialog">修改密码</el-button>
      </div>
      <div class="account-row">
        <div class="account-copy">
          <strong>主页可见范围</strong>
          <span>关注、粉丝、喜欢、收藏列表可分别隐藏；隐藏后仅自己可见，关注/粉丝数量仍会显示。</span>
        </div>
        <el-button @click="openPrivacyDialog">设置可见范围</el-button>
      </div>
      <div class="account-row">
        <div class="account-copy">
          <strong>注销账号</strong>
          <span v-if="user.role === 'admin'">管理员账号不支持自助注销，需先移交管理权限。</span>
          <span v-else>账号及其微澜、回声、关注关系会被永久删除，不可恢复。</span>
        </div>
        <el-button v-if="user.role !== 'admin'" type="danger" plain @click="openDeleteDialog">注销账号</el-button>
      </div>
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
        <el-tab-pane label="我的喜欢" name="likes">
          <MyLikes v-if="activeTab === 'likes'" @like-updated="updateLike" />
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

    <!-- 资料编辑弹窗 -->
    <el-dialog v-model="profileDialog.visible" title="编辑资料"
      width="min(520px, calc(100% - 32px))" :close-on-click-modal="!savingProfile"
      :close-on-press-escape="!savingProfile" :show-close="!savingProfile"
      @closed="handleProfileDialogClosed">
      <el-form label-width="76px" label-position="left" class="profile-form">
        <el-form-item label="头像">
          <div class="avatar-edit">
            <img v-if="profileDialog.avatar_url" :src="profileDialog.avatar_url" class="avatar-preview" alt="头像预览" />
            <div v-else class="avatar-preview avatar-placeholder">
              {{ profileDialog.nickname.trim().slice(0, 1) || '?' }}
            </div>
            <div class="avatar-actions">
              <el-upload
                :show-file-list="false"
                :http-request="handleAvatarUpload"
                accept="image/jpeg,image/png,image/webp,image/gif"
              >
                <el-button size="small" :loading="uploadingAvatar" :disabled="savingProfile">上传头像</el-button>
              </el-upload>
              <el-button v-if="profileDialog.avatar_url" size="small" text
                :disabled="savingProfile" @click="profileDialog.avatar_url = ''">移除</el-button>
              <div class="avatar-hint">jpg/png/webp/gif，≤5MB</div>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="昵称" required>
          <el-input v-model="profileDialog.nickname" maxlength="50" show-word-limit
            placeholder="大家怎么称呼你" :disabled="savingProfile" />
        </el-form-item>
        <el-form-item label="签名">
          <el-input v-model="profileDialog.bio" type="textarea" :rows="3" maxlength="200"
            show-word-limit placeholder="一句话介绍自己" :disabled="savingProfile" />
        </el-form-item>
        <el-form-item label="情绪色调">
          <el-select v-model="profileDialog.mood_tone" clearable placeholder="不设置"
            :disabled="savingProfile" style="width: 100%">
            <el-option v-for="tone in moodTones" :key="tone.code"
              :label="`${tone.name}（${tone.code}）`" :value="tone.code" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="savingProfile" @click="profileDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="savingProfile" @click="submitProfile">保存</el-button>
      </template>
    </el-dialog>
    <!-- 主页可见范围弹窗 -->
    <el-dialog v-model="privacyDialog.visible" title="主页可见范围"
      width="min(500px, calc(100% - 32px))" :close-on-click-modal="!savingPrivacy"
      :close-on-press-escape="!savingPrivacy" :show-close="!savingPrivacy">
      <p class="privacy-hint">关闭的列表仅自己可见，访客打开时会看到「该用户的某个列表不对外开放」。</p>
      <div class="privacy-row">
        <div class="privacy-copy"><strong>关注列表</strong><span>你关注的人</span></div>
        <el-switch v-model="privacyDialog.hide_following" active-text="仅自己可见" inactive-text="公开" :disabled="savingPrivacy" />
      </div>
      <div class="privacy-row">
        <div class="privacy-copy"><strong>粉丝列表</strong><span>关注你的人</span></div>
        <el-switch v-model="privacyDialog.hide_followers" active-text="仅自己可见" inactive-text="公开" :disabled="savingPrivacy" />
      </div>
      <div class="privacy-row">
        <div class="privacy-copy"><strong>喜欢列表</strong><span>你点过爱心的微澜</span></div>
        <el-switch v-model="privacyDialog.hide_likes" active-text="仅自己可见" inactive-text="公开" :disabled="savingPrivacy" />
      </div>
      <div class="privacy-row">
        <div class="privacy-copy"><strong>收藏列表</strong><span>你收藏的微澜</span></div>
        <el-switch v-model="privacyDialog.hide_collections" active-text="仅自己可见" inactive-text="公开" :disabled="savingPrivacy" />
      </div>
      <template #footer>
        <el-button :disabled="savingPrivacy" @click="privacyDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="savingPrivacy" @click="submitPrivacy">保存可见范围</el-button>
      </template>
    </el-dialog>
    <!-- 修改密码弹窗 -->
    <el-dialog v-model="passwordDialog.visible" title="修改密码"
      width="min(440px, calc(100% - 32px))" :close-on-click-modal="!changingPassword"
      :close-on-press-escape="!changingPassword" :show-close="!changingPassword">
      <el-form label-width="88px" label-position="left">
        <el-form-item label="原密码" required>
          <el-input v-model="passwordDialog.oldPassword" type="password" show-password
            autocomplete="current-password" :disabled="changingPassword" />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input v-model="passwordDialog.newPassword" type="password" show-password
            maxlength="64" autocomplete="new-password" placeholder="至少 6 位" :disabled="changingPassword" />
        </el-form-item>
        <el-form-item label="确认新密码" required>
          <el-input v-model="passwordDialog.confirm" type="password" show-password
            maxlength="64" autocomplete="new-password" :disabled="changingPassword" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="changingPassword" @click="passwordDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="changingPassword" @click="submitPassword">保存新密码</el-button>
      </template>
    </el-dialog>

    <!-- 注销账号弹窗 -->
    <el-dialog v-model="deleteDialog.visible" title="注销账号"
      width="min(440px, calc(100% - 32px))" :close-on-click-modal="!deletingAccount"
      :close-on-press-escape="!deletingAccount" :show-close="!deletingAccount">
      <el-alert type="warning" :closable="false" show-icon
        title="注销不可恢复，账号下的微澜与回声会被一并删除。" />
      <el-form label-width="88px" label-position="left" style="margin-top: 16px">
        <el-form-item label="当前密码" required>
          <el-input v-model="deleteDialog.password" type="password" show-password
            autocomplete="current-password" :disabled="deletingAccount" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="deletingAccount" @click="deleteDialog.visible = false">取消</el-button>
        <el-button type="danger" :loading="deletingAccount" @click="submitDeleteAccount">确认注销</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<style scoped>
.profile-card {
  max-width: 640px;
}

.account-card {
  max-width: 640px;
}

.account-card h3 {
  margin: 0 0 6px;
  font-size: 18px;
}

.account-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  border-top: 1px solid var(--wl-border);
  flex-wrap: wrap;
}

.account-row + .account-row {
  border-top: 1px solid var(--wl-border);
}

.account-copy {
  display: grid;
  gap: 4px;
  min-width: 220px;
}

.account-copy strong {
  font-size: 14px;
}

.account-copy span {
  color: var(--wl-muted);
  font-size: 12.5px;
}

.privacy-hint {
  margin: 0 0 10px;
  color: var(--wl-muted);
  font-size: 13px;
}

.privacy-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 0;
  border-top: 1px solid var(--wl-border);
  flex-wrap: wrap;
}

.privacy-copy {
  display: grid;
  gap: 3px;
}

.privacy-copy strong { font-size: 14px; }
.privacy-copy span { color: var(--wl-muted); font-size: 12.5px; }

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
  overflow: hidden;
}

.me-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.me-nickname-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.avatar-edit {
  display: flex;
  align-items: center;
  gap: 16px;
}

.avatar-preview {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.avatar-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f7a8c, #4fb3c4);
  color: #fff;
  font-size: 24px;
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
}

.avatar-hint {
  font-size: 12px;
  color: #90a4ae;
}

.profile-form {
  margin-top: 4px;
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
