<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { ArrowRight, ArrowLeft, Compass, EditPen, Search, CollectionTag } from '@element-plus/icons-vue'
import RippleCard from '@/components/RippleCard.vue'
import CommunityPulse from '@/components/CommunityPulse.vue'
import heroImage from '@/assets/ripple-dawn.webp'
import { listRipples, listFollowingRipples, listSubscribedTopicRipples, getHotTides, getMoodSummary } from '@/api/ripples'
import { getTopic, getSubscribedTopics, setTopicSubscription, type TopicDetail } from '@/api/topics'
import type { CollectionOut, LikeOut, MoodOut, RippleOut, TideOut, TopicOut } from '@/api/types'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const exploring = computed(() => route.name === 'explore')
const topicPage = computed(() => route.name === 'topic')
const detailedFilters = computed(() => exploring.value || topicPage.value)
const ripples = ref<RippleOut[]>([])
const tides = ref<TideOut[]>([])
const moods = ref<MoodOut[]>([])
const loadingPulse = ref(true)
const loading = ref(true)
const failed = ref(false)
const hasNext = ref(false)
const keyword = ref('')
const results = ref<HTMLElement>()
const pageSize = 10
let requestVersion = 0
let detailVersion = 0
let subscriptionsVersion = 0
const topicDetail = ref<TopicDetail | null>(null)
const topicLoading = ref(false)
const topicError = ref('')
const changingSubscription = ref(false)
const subscriptions = ref<TopicOut[]>([])

function stringQuery(value: unknown) {
  return typeof value === 'string' ? value : ''
}

function positiveId(value: string) {
  const number = Number(value)
  return Number.isSafeInteger(number) && number > 0 ? number : undefined
}

const topic = computed(() => positiveId(stringQuery(topicPage.value ? route.params.id : route.query.topic)))
const mood = computed(() => detailedFilters.value ? stringQuery(route.query.mood) : '')
const hasImages = computed(() => detailedFilters.value && route.query.images === '1')
const feed = computed(() => {
  const value = route.query.feed
  if (route.name === 'home' && (value === 'following' || value === 'subscribed')) return value
  return 'all'
})
const topicChoices = computed(() => feed.value === 'subscribed' ? subscriptions.value : tides.value.map(item => item.topic))
const sort = computed(() => {
  const value = route.query.sort
  return detailedFilters.value && (value === 'discussed' || value === 'liked') ? value : 'latest'
})
const submittedKeyword = computed(() => stringQuery(route.query.q).trim().slice(0, 100))
const page = computed(() => Math.min(100000, positiveId(stringQuery(route.query.page)) ?? 1))
const filtered = computed(() => !!((!topicPage.value && topic.value) || mood.value || hasImages.value || submittedKeyword.value || sort.value !== 'latest'))

function changeFilters(query: LocationQueryRaw) {
  void router.push({ path: route.path, query: { ...route.query, page: undefined, ...query } })
}

function clearFilters() {
  void router.push({ path: route.path, query: feed.value === 'all' ? {} : { feed: feed.value } })
}

async function goToPage(target: number) {
  await router.push({ query: { ...route.query, page: target > 1 ? String(target) : undefined } })
  results.value?.scrollIntoView({ block: 'start' })
}

async function loadRipples() {
  const version = ++requestVersion
  if (topicPage.value && !topic.value) {
    ripples.value = []
    loading.value = false
    return
  }
  loading.value = true
  failed.value = false
  try {
    const loaders = { all: listRipples, following: listFollowingRipples, subscribed: listSubscribedTopicRipples }
    const load = loaders[feed.value]
    const items = await load({
      topic_id: topic.value,
      keyword: submittedKeyword.value || undefined,
      emotion_code: mood.value || undefined,
      has_images: hasImages.value || undefined,
      sort: sort.value,
      limit: pageSize + 1,
      offset: (page.value - 1) * pageSize,
    })
    if (version !== requestVersion) return
    hasNext.value = items.length > pageSize
    ripples.value = items.slice(0, pageSize)
  } catch {
    if (version === requestVersion) failed.value = true
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

async function loadTopic() {
  const version = ++detailVersion
  const id = topic.value
  topicDetail.value = null
  topicError.value = ''
  changingSubscription.value = false
  topicLoading.value = false
  if (!topicPage.value) return
  if (!id) {
    topicError.value = '话题不存在'
    return
  }
  topicLoading.value = true
  try {
    const detail = await getTopic(id)
    if (version === detailVersion) topicDetail.value = detail
  } catch (error) {
    if (version !== detailVersion) return
    topicError.value = (error as { response?: { status?: number } }).response?.status === 404
      ? '话题不存在' : '话题加载失败'
  } finally {
    if (version === detailVersion) topicLoading.value = false
  }
}

async function toggleSubscription() {
  const detail = topicDetail.value
  if (!detail || changingSubscription.value) return
  const version = detailVersion
  changingSubscription.value = true
  try {
    const subscribe = !detail.is_subscribed
    await setTopicSubscription(detail.id, subscribe)
    if (version === detailVersion) detail.is_subscribed = subscribe
    if (feed.value === 'subscribed') {
      void loadSubscriptions()
      void loadRipples()
    }
  } catch { /* 请求失败时保留当前状态，由请求拦截器提示。 */ }
  finally {
    if (version === detailVersion) changingSubscription.value = false
  }
}

async function loadSubscriptions() {
  const version = ++subscriptionsVersion
  if (feed.value !== 'subscribed') return
  try {
    const items = await getSubscribedTopics()
    if (version === subscriptionsVersion) subscriptions.value = items
  } catch {
    if (version === subscriptionsVersion) subscriptions.value = []
  }
}

function updateLike(state: LikeOut) {
  const ripple = ripples.value.find((item) => item.id === state.ripple_id)
  if (ripple) {
    ripple.is_liked = state.is_liked
    ripple.like_count = state.like_count
  }
}

function updateCollection(state: CollectionOut) {
  const ripple = ripples.value.find((item) => item.id === state.ripple_id)
  if (ripple) ripple.is_collected = state.is_collected
}

watch(submittedKeyword, (value) => { keyword.value = value }, { immediate: true })
watch([feed, topicPage, topic, mood, hasImages, sort, submittedKeyword, page], loadRipples, { immediate: true })
watch([topicPage, topic], loadTopic, { immediate: true })
watch(feed, loadSubscriptions, { immediate: true })
onMounted(async () => {
  await Promise.allSettled([
    getHotTides().then((items) => { tides.value = items }),
    getMoodSummary().then((items) => { moods.value = items }),
  ])
  loadingPulse.value = false
})
onBeforeUnmount(() => {
  requestVersion++
  detailVersion++
  subscriptionsVersion++
})
</script>

<template>
  <div class="community">
    <section v-if="!detailedFilters" class="welcome">
      <img :src="heroImage" alt="" fetchpriority="high" class="welcome-image" />
      <div class="welcome-copy">
        <p class="welcome-eyebrow">微澜社区</p>
        <h1>让一个念头<br />泛起涟漪。</h1>
        <p class="welcome-description">记录片刻灵感，听见他人的回声。</p>
        <div class="welcome-actions">
          <router-link v-if="userStore.user?.role !== 'admin'" to="/compose" class="welcome-primary"><EditPen aria-hidden="true" />写微澜</router-link>
          <router-link to="/explore" class="welcome-secondary">探索社区<ArrowRight aria-hidden="true" /></router-link>
        </div>
      </div>
    </section>

    <div v-else-if="exploring" class="explore-heading">
      <div class="explore-icon"><Compass aria-hidden="true" /></div>
      <div><h1>探索微澜</h1><p>按话题和情绪挑选内容，或从讨论最多的微澜开始。</p></div>
      <router-link :to="{ name: 'tide' }" class="topic-back explore-topics">查看全部话题</router-link>
    </div>
    <section v-else class="explore-heading topic-heading" :aria-busy="topicLoading">
      <div class="explore-icon"><CollectionTag aria-hidden="true" /></div>
      <div v-if="topicDetail">
        <router-link :to="{ name: 'explore' }" class="topic-back">探索微澜</router-link>
        <h1># {{ topicDetail.name }}</h1>
        <p v-if="topicDetail.description">{{ topicDetail.description }}</p>
      </div>
      <div v-else>
        <h1>{{ topicError || '正在读取话题…' }}</h1>
        <router-link :to="{ name: 'explore' }" class="topic-back">返回探索</router-link>
        <button v-if="topicError === '话题加载失败'" class="reset-button" type="button" @click="loadTopic">重试</button>
      </div>
      <div v-if="topicDetail" class="topic-actions">
        <el-button type="primary" :plain="topicDetail.is_subscribed" :loading="changingSubscription"
          @click="toggleSubscription">{{ topicDetail.is_subscribed ? '取消订阅' : '订阅话题' }}</el-button>
        <router-link v-if="userStore.user?.role === 'user'"
          :to="{ name: 'compose', query: { topic: String(topicDetail.id) } }">发布到此话题</router-link>
        <router-link v-if="topicDetail.is_subscribed" :to="{ name: 'home', query: { feed: 'subscribed' } }">我的订阅</router-link>
      </div>
    </section>

    <div v-if="!topicPage || topicDetail" class="community-grid">
      <section ref="results" class="timeline" :aria-label="detailedFilters ? '微澜列表' : '时间线'">
        <div class="feed-heading">
          <h2>{{ topicPage ? '话题微澜' : exploring ? '浏览微澜' : '社区时间线' }}</h2>
          <div v-if="!detailedFilters" class="feed-switch" aria-label="时间线范围">
            <button type="button" :aria-pressed="feed === 'all'" @click="changeFilters({ feed: undefined, topic: undefined })">全部微澜</button>
            <button type="button" :aria-pressed="feed === 'following'" @click="changeFilters({ feed: 'following', topic: undefined })">关注的人</button>
            <button type="button" :aria-pressed="feed === 'subscribed'" @click="changeFilters({ feed: 'subscribed', topic: undefined })">订阅的话题</button>
          </div>
          <button v-else-if="filtered" class="reset-button" type="button" @click="clearFilters">清除筛选</button>
        </div>

        <div class="card feed-controls">
          <form class="feed-search" role="search" @submit.prevent="changeFilters({ q: keyword.trim() || undefined })">
            <Search aria-hidden="true" />
            <input v-model="keyword" maxlength="100" type="search" aria-label="搜索微澜内容" placeholder="搜索微澜内容" @search="!keyword && changeFilters({ q: undefined })" />
            <button type="submit">搜索</button>
          </form>

          <div v-if="detailedFilters" class="explore-filters">
            <label v-if="exploring">话题
              <select :value="topic ?? ''" @change="changeFilters({ topic: ($event.target as HTMLSelectElement).value || undefined })">
                <option value="">全部话题</option>
                <option v-if="topic && !tides.some(item => item.topic.id === topic)" :value="topic">话题 {{ topic }}</option>
                <option v-for="item in tides" :key="item.topic.id" :value="item.topic.id">{{ item.topic.name }}</option>
              </select>
            </label>
            <router-link v-if="exploring && topic && tides.some(item => item.topic.id === topic)"
              class="topic-back topic-open" :to="{ name: 'topic', params: { id: topic } }">进入话题</router-link>
            <label>情绪
              <select :value="mood" @change="changeFilters({ mood: ($event.target as HTMLSelectElement).value || undefined })">
                <option value="">全部情绪</option>
                <option v-if="mood && !moods.some(item => item.code === mood)" :value="mood">{{ mood }}</option>
                <option v-for="item in moods" :key="item.code" :value="item.code">{{ item.name }}</option>
              </select>
            </label>
            <label>排序
              <select :value="sort" @change="changeFilters({ sort: ($event.target as HTMLSelectElement).value })">
                <option value="latest">最新发布</option>
                <option value="discussed">讨论最多</option>
                <option value="liked">点赞最多</option>
              </select>
            </label>
            <label class="image-filter"><input type="checkbox" :checked="hasImages" @change="changeFilters({ images: hasImages ? undefined : '1' })" />仅看配图</label>
          </div>
          <div v-else-if="topicChoices.length" class="topic-chips" aria-label="按话题筛选">
            <button type="button" class="chip" :aria-pressed="!topic" @click="changeFilters({ topic: undefined })">全部话题</button>
            <button v-for="item in topicChoices" :key="item.id" type="button" class="chip" :aria-pressed="topic === item.id" @click="changeFilters({ topic: String(item.id) })"># {{ item.name }}</button>
            <router-link v-if="feed === 'subscribed' && topic && subscriptions.some(item => item.id === topic)"
              class="topic-back topic-open" :to="{ name: 'topic', params: { id: topic } }">进入话题</router-link>
          </div>
        </div>

        <div class="feed-body" :aria-busy="loading">
          <div v-if="loading" class="card feed-notice" role="status">正在读取微澜…</div>
          <div v-else-if="failed" class="card feed-notice"><p>加载失败，请重试。</p><button type="button" @click="loadRipples">重新加载</button></div>
          <template v-else>
            <RippleCard v-for="ripple in ripples" :key="ripple.id" :ripple="ripple" @like-updated="updateLike" @collection-updated="updateCollection" />
            <div v-if="!ripples.length" class="card feed-notice">
              <p>{{ filtered ? '没有符合筛选条件的微澜。' : feed === 'following' ? '关注的作者暂时没有公开微澜。' : feed === 'subscribed' ? '订阅的话题暂时没有公开微澜，去探索更多话题吧。' : '这里还没有公开的微澜。' }}</p>
              <button v-if="filtered" type="button" @click="clearFilters">清除筛选</button>
              <router-link v-else-if="!exploring" to="/explore">探索社区</router-link>
            </div>
            <nav v-if="page > 1 || hasNext" class="feed-pagination" aria-label="微澜分页">
              <button type="button" :disabled="page === 1" @click="goToPage(page - 1)"><ArrowLeft aria-hidden="true" />上一页</button>
              <span>第 {{ page }} 页</span>
              <button type="button" :disabled="!hasNext" @click="goToPage(page + 1)">下一页<ArrowRight aria-hidden="true" /></button>
            </nav>
          </template>
        </div>
      </section>
      <CommunityPulse :tides="tides" :moods="moods" :loading="loadingPulse" />
    </div>
  </div>
</template>

<style scoped>
.welcome { position: relative; border-radius: 22px; overflow: hidden; isolation: isolate; background: #153b36; color: #fff; margin-bottom: 30px; }
.welcome-image { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center 58%; z-index: -2; }
.welcome::before { content: ''; position: absolute; inset: 0; background: linear-gradient(90deg, #082725b5, #08272535 60%, transparent); z-index: -1; }
.welcome-copy { padding: 39px clamp(24px, 5.2vw, 72px); }
.welcome-eyebrow { color: #d1ebdc; font-size: 12px; letter-spacing: .24em; margin: 0 0 12px; }
.welcome h1 { font-family: 'Songti SC', 'Noto Serif CJK SC', SimSun, serif; font-size: clamp(39px, 5.6vw, 72px); line-height: 1.06; letter-spacing: -.045em; margin: 0; }
.welcome-description { color: #eff8f1; font-size: 15px; margin: 15px 0 23px; }
.welcome-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.welcome-actions a { display: inline-flex; align-items: center; gap: 7px; border-radius: 9px; text-decoration: none; padding: 10px 15px; font-size: 13px; font-weight: 600; }
.welcome-actions svg, .feed-search svg, .feed-pagination svg { width: 16px; height: 16px; flex: 0 0 16px; }
.welcome-primary { background: #f2f6e9; color: #143e37; }
.welcome-primary:hover { background: #fff; }
.welcome-secondary { color: #fff; border: 1px solid #dcebe3a3; background: #123a3480; }
.welcome-secondary:hover { background: #25574f; }
.community-grid { display: grid; grid-template-columns: minmax(0, 1fr) 294px; align-items: start; gap: 22px; }
.timeline { min-width: 0; scroll-margin-top: 130px; }
.feed-heading { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; min-height: 35px; margin-bottom: 12px; }
h2, h1 { margin: 0; }
.feed-heading h2 { font-size: 20px; }
.feed-switch { display: inline-flex; gap: 3px; padding: 3px; border: 1px solid var(--wl-border); border-radius: 9px; background: #eaf0eb; }
button, input, select { font: inherit; }
.feed-switch button, .chip, .reset-button { cursor: pointer; border: 0; background: transparent; border-radius: 7px; padding: 6px 10px; font-size: 13px; color: var(--wl-muted); }
.feed-switch button[aria-pressed="true"], .chip[aria-pressed="true"] { background: #e1efe6; color: #194e43; font-weight: 600; }
.feed-switch button[aria-pressed="true"] { background: white; }
.chip { background: #f3f6f3; }
.chip:hover, .reset-button:hover { background: #e9f1eb; }
.feed-controls { display: grid; gap: 12px; padding: 14px; }
.feed-search { display: flex; align-items: center; gap: 9px; padding-left: 11px; border: 1px solid var(--wl-border); border-radius: 9px; color: var(--wl-muted); overflow: hidden; }
.feed-search input { flex: 1; min-width: 0; border: 0; min-height: 38px; color: var(--wl-ink); }
.feed-search:focus-within { outline: 2px solid #579080; outline-offset: 1px; }
.feed-search input:focus { outline: none; }
.feed-search button { border: 0; background: #e9f2eb; color: var(--wl-primary); padding: 10px 14px; cursor: pointer; }
.topic-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.feed-notice { color: var(--wl-muted); padding: 30px 15px; text-align: center; }
.feed-notice p { margin: 0 0 8px; }
.feed-notice button, .feed-notice a, .feed-pagination button { border: 1px solid var(--wl-border); border-radius: 8px; background: white; color: var(--wl-primary); padding: 7px 11px; cursor: pointer; text-decoration: none; }
.feed-pagination { display: flex; align-items: center; justify-content: center; gap: 12px; margin: 18px 0 0; font-size: 13px; }
.feed-pagination button { display: inline-flex; align-items: center; gap: 3px; }
.feed-pagination button:disabled { cursor: default; color: #798880; background: #f2f5f2; }
.explore-heading { display: flex; align-items: center; gap: 15px; margin-bottom: 26px; padding: 23px; background: #e7f0e8; border: 1px solid #d7e5da; border-radius: 16px; }
.explore-heading h1 { font-size: clamp(25px, 3.8vw, 36px); }
.explore-heading p { margin: 4px 0 0; font-size: 14px; color: var(--wl-muted); }
.explore-icon { display: grid; place-items: center; width: 52px; height: 52px; flex: 0 0 52px; border-radius: 13px; background: #d3e8d9; color: #236358; }
.explore-icon svg { width: 27px; height: 27px; }
.topic-heading { flex-wrap: wrap; }
.topic-actions { margin-left: auto; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.topic-back, .topic-actions a { color: var(--wl-primary); font-size: 13px; text-underline-offset: 3px; }
.explore-topics { margin-left: auto; flex: 0 0 auto; }
.topic-open { align-self: end; padding: 7px; }
.explore-filters { display: flex; align-items: end; flex-wrap: wrap; gap: 10px; }
.explore-filters label { display: grid; gap: 5px; color: var(--wl-muted); font-size: 12px; }
.explore-filters select { max-width: 100%; padding: 7px 9px; border: 1px solid var(--wl-border); border-radius: 7px; background: #f7faf7; color: var(--wl-ink); }
.explore-filters .image-filter { display: flex; align-items: center; gap: 4px; min-height: 32px; cursor: pointer; }
.image-filter input { accent-color: var(--wl-primary); }
@media (max-width: 850px) {
  .community-grid { grid-template-columns: minmax(0, 1fr); gap: 24px; }
}
@media (max-width: 520px) {
  .explore-heading { flex-wrap: wrap; }
  .explore-topics { margin-left: 0; }
  .welcome { border-radius: 15px; margin-bottom: 20px; }
  .welcome-copy { padding-block: 28px; }
  .welcome-image { object-position: 56% center; }
  .welcome::before { background: linear-gradient(90deg, #082725d9, #08272547); }
}
</style>
