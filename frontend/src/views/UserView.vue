<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchUserProfile, fetchUserRipples } from '@/api/users'
import type { CollectionOut, LikeOut, RippleOut, UserProfile } from '@/api/types'
import FollowButton from '@/components/FollowButton.vue'
import MyCollections from '@/components/MyCollections.vue'
import MyLikes from '@/components/MyLikes.vue'
import RippleCard from '@/components/RippleCard.vue'
import UserRelations from '@/components/UserRelations.vue'
import { useUserStore } from '@/stores/user'

type UserTab = 'ripples' | 'following' | 'followers' | 'likes' | 'collections'
type PrivacyFlag = 'hide_following' | 'hide_followers' | 'hide_likes' | 'hide_collections'

function tabFromQuery(value: unknown): UserTab {
  return value === 'following' || value === 'followers' || value === 'likes' || value === 'collections'
    ? value
    : 'ripples'
}

const route = useRoute()
const router = useRouter()
const store = useUserStore()
const profile = ref<UserProfile | null>(null)
const ripples = ref<RippleOut[]>([])
const loading = ref(false)
const failed = ref(false)
const more = ref(false)
const tab = ref<UserTab>(tabFromQuery(route.query.tab))
const relationsVersion = ref(0)
let version = 0

const isOwner = computed(() => !!profile.value && profile.value.id === store.user?.id)

function hidden(flag: PrivacyFlag) {
  return !!profile.value && !isOwner.value && profile.value[flag]
}

function updateProfile(user: UserProfile) {
  profile.value = user
  relationsVersion.value++
}

async function load() {
  const id = Number(route.params.id)
  const current = ++version
  loading.value = true
  failed.value = false
  profile.value = null
  ripples.value = []
  try {
    const [user, posts] = await Promise.all([fetchUserProfile(id), fetchUserRipples(id, { limit: 20, offset: 0 })])
    if (current !== version) return
    profile.value = user
    ripples.value = posts
    more.value = posts.length === 20
  } catch {
    if (current === version) failed.value = true
  } finally {
    if (current === version) loading.value = false
  }
}

async function loadMore() {
  if (!profile.value || loading.value) return
  const id = profile.value.id
  const current = version
  loading.value = true
  try {
    const posts = await fetchUserRipples(id, { limit: 20, offset: ripples.value.length })
    if (current !== version) return
    ripples.value.push(...posts)
    more.value = posts.length === 20
  } catch { /* 全局提示并允许重试 */ }
  finally { if (current === version) loading.value = false }
}

async function refreshProfile() {
  const id = profile.value?.id
  if (!id) return
  const current = version
  try {
    const user = await fetchUserProfile(id)
    if (current === version) profile.value = user
  } catch { /* 全局提示 */ }
}

function updateLike(state: LikeOut) {
  const ripple = ripples.value.find((item) => item.id === state.ripple_id)
  if (ripple) Object.assign(ripple, { is_liked: state.is_liked, like_count: state.like_count })
}
function updateCollection(state: CollectionOut) {
  const ripple = ripples.value.find((item) => item.id === state.ripple_id)
  if (ripple) ripple.is_collected = state.is_collected
}
function changeTab(value: string | number) {
  const name = String(value)
  void router.replace({ query: { ...route.query, tab: name === 'ripples' ? undefined : name } })
}
watch(() => route.params.id, () => { void load() }, { immediate: true })
watch(() => route.query.tab, (value) => {
  tab.value = tabFromQuery(value)
}, { immediate: true })
onBeforeUnmount(() => { version++ })
</script>

<template>
  <div v-loading="loading">
    <div v-if="failed" class="empty-tip"><p>用户不存在或加载失败</p><el-button @click="load">重试</el-button></div>
    <template v-if="profile">
      <section class="card user-profile">
        <div class="user-heading">
          <div class="avatar">
            <img v-if="profile.avatar_url" :src="profile.avatar_url" alt="" class="avatar-img" />
            <template v-else>{{ profile.nickname.slice(0, 1) }}</template>
          </div>
          <div><h1>{{ profile.nickname }}</h1><span>@{{ profile.username }}</span></div>
          <FollowButton :profile="profile" @updated="updateProfile" />
          <router-link v-if="profile.id === store.user?.id" to="/profile">我的个人中心</router-link>
        </div>
        <p>{{ profile.bio || '这个人还没有写签名' }}</p>
        <div class="relations-summary">
          <button @click="changeTab('following')">关注 {{ profile.following_count }}<span v-if="hidden('hide_following')">（私密）</span></button>
          <button @click="changeTab('followers')">粉丝 {{ profile.follower_count }}<span v-if="hidden('hide_followers')">（私密）</span></button>
          <span v-if="profile.follows_you && profile.id !== store.user?.id">{{ profile.is_following ? '你们已互相关注' : 'TA 关注了你' }}</span>
        </div>
      </section>
      <el-tabs v-model="tab" @tab-change="changeTab">
        <el-tab-pane label="微澜" name="ripples">
          <RippleCard v-for="ripple in ripples" :key="ripple.id" :ripple="ripple" @like-updated="updateLike" @collection-updated="updateCollection" />
          <div v-if="!loading && !ripples.length" class="empty-tip">还没有公开的微澜</div>
          <el-button v-if="more" :loading="loading" @click="loadMore">加载更多</el-button>
        </el-tab-pane>
        <el-tab-pane :label="hidden('hide_following') ? '关注（私密）' : '关注'" name="following">
          <div v-if="tab === 'following' && hidden('hide_following')" class="private-notice">
            <strong>{{ profile.nickname }} 的关注列表不对外开放</strong>
            <span>对方在个人主页设置了仅自己可见。</span>
          </div>
          <UserRelations v-else-if="tab === 'following'" :key="relationsVersion" :user-id="profile.id" kind="following" @changed="refreshProfile" />
        </el-tab-pane>
        <el-tab-pane :label="hidden('hide_followers') ? '粉丝（私密）' : '粉丝'" name="followers">
          <div v-if="tab === 'followers' && hidden('hide_followers')" class="private-notice">
            <strong>{{ profile.nickname }} 的粉丝列表不对外开放</strong>
            <span>对方在个人主页设置了仅自己可见。</span>
          </div>
          <UserRelations v-else-if="tab === 'followers'" :key="relationsVersion" :user-id="profile.id" kind="followers" @changed="refreshProfile" />
        </el-tab-pane>
        <el-tab-pane :label="hidden('hide_likes') ? '喜欢（私密）' : '喜欢'" name="likes">
          <div v-if="tab === 'likes' && hidden('hide_likes')" class="private-notice">
            <strong>{{ profile.nickname }} 的喜欢列表不对外开放</strong>
            <span>对方在个人主页设置了仅自己可见。</span>
          </div>
          <MyLikes v-else-if="tab === 'likes'" :user-id="profile.id" :own="isOwner" @like-updated="updateLike" />
        </el-tab-pane>
        <el-tab-pane :label="hidden('hide_collections') ? '收藏（私密）' : '收藏'" name="collections">
          <div v-if="tab === 'collections' && hidden('hide_collections')" class="private-notice">
            <strong>{{ profile.nickname }} 的收藏列表不对外开放</strong>
            <span>对方在个人主页设置了仅自己可见。</span>
          </div>
          <MyCollections v-else-if="tab === 'collections'" :user-id="profile.id" :own="isOwner" @like-updated="updateLike" />
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<style scoped>
.user-heading { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.user-heading h1 { margin: 0 0 5px; font-size: 22px; }
.user-heading span { color: #78909c; font-size: 13px; }
.user-profile p { color: #546e7a; }
.avatar { width: 60px; height: 60px; border-radius: 50%; background: var(--wl-primary); color: white; display: grid; place-items: center; font-size: 24px; overflow: hidden; }
.avatar-img { width: 100%; height: 100%; object-fit: cover; }
.relations-summary { display: flex; gap: 20px; align-items: center; flex-wrap: wrap; }
.relations-summary button { border: 0; background: transparent; color: var(--wl-primary); cursor: pointer; padding: 6px 0; font: inherit; }
.relations-summary span { color: #78909c; font-size: 13px; }
.private-notice {
  display: grid;
  gap: 6px;
  margin: 18px 0;
  padding: 22px 20px;
  border: 1px dashed var(--wl-border);
  border-radius: 10px;
  background: #f7fbfc;
  color: var(--wl-muted);
  text-align: center;
}
.private-notice strong { color: var(--wl-ink); font-size: 15px; }
.private-notice span { font-size: 13px; }
</style>
