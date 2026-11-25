<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Bell, ChatDotRound, Star, User, Warning } from '@element-plus/icons-vue'
import {
  fetchNotifications, markAllNotificationsRead, markNotificationRead,
  type NotificationItem, type NotificationKind,
} from '@/api/notifications'
import { useNotificationStore } from '@/stores/notifications'

const router = useRouter()
const badge = useNotificationStore()
const items = ref<NotificationItem[]>([])
const filter = ref<NotificationKind | ''>('')
const unreadOnly = ref(false)
const nextBefore = ref<number | null>(null)
const loading = ref(false)
const failed = ref(false)
const marking = ref(false)
let loadVersion = 0

const descriptions = {
  echo: '回应了你的微澜',
  reply: '回复了你的回声',
  follow: '关注了你',
  moderation: '处理了你的内容',
  like: '点赞了你的微澜',
  collection: '收藏了你的微澜',
}

function destination(item: NotificationItem) {
  if (item.kind === 'moderation' || item.kind === 'like' || item.kind === 'collection') {
    return item.ripple_id !== null
      ? { name: 'ripple-detail', params: { id: item.ripple_id } }
      : { name: 'profile' }
  }
  if (item.ripple_id !== null && item.echo_id !== null) {
    return { name: 'ripple-detail', params: { id: item.ripple_id }, hash: `#echo-${item.echo_id}` }
  }
  return { name: 'user-profile', params: { id: item.actor_id } }
}

async function load(append = false) {
  const current = ++loadVersion
  const before = append ? nextBefore.value : null
  loading.value = true
  failed.value = false
  try {
    const page = await fetchNotifications({
      kind: filter.value || undefined,
      unread_only: unreadOnly.value,
      before: before ?? undefined,
    })
    if (current !== loadVersion) return
    items.value = append ? [...items.value, ...page.items] : page.items
    nextBefore.value = page.next_before
    badge.setUnread(page.unread_count)
  } catch {
    if (current === loadVersion) failed.value = true
  } finally {
    if (current === loadVersion) loading.value = false
  }
}

async function markAll() {
  marking.value = true
  try {
    const result = await markAllNotificationsRead()
    badge.setUnread(result.unread_count)
    await load()
  } catch { /* 保留现有列表，提示由拦截器展示 */ }
  finally { marking.value = false }
}

async function openMessage(event: MouseEvent, item: NotificationItem) {
  if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return
  event.preventDefault()
  if (!item.read_at) {
    try {
      const result = await markNotificationRead(item.id)
      badge.setUnread(result.unread_count)
    } catch { /* 消息已失效时仍可尝试打开原目标 */ }
  }
  await router.push(destination(item))
}

watch([filter, unreadOnly], () => {
  items.value = []
  nextBefore.value = null
  void load()
}, { immediate: true })
onBeforeUnmount(() => { loadVersion++ })
</script>

<template>
  <section class="inbox">
    <header class="card inbox-heading">
      <div class="inbox-icon"><Bell aria-hidden="true" /></div>
      <div><h1>消息中心</h1><p aria-live="polite">{{ badge.unread ? `${badge.unread} 条未读消息` : '所有消息均已读' }}</p></div>
      <el-button class="read-all" :disabled="!badge.unread || loading" :loading="marking" @click="markAll">全部标为已读</el-button>
    </header>
    <div class="card inbox-filters">
      <label>消息类型
        <select v-model="filter">
          <option value="">全部消息</option>
          <option value="echo">回应微澜</option>
          <option value="reply">回复回声</option>
          <option value="follow">新关注</option>
          <option value="like">点赞</option>
          <option value="collection">收藏</option>
          <option value="moderation">内容处理</option>
        </select>
      </label>
      <label><input v-model="unreadOnly" type="checkbox" /> 仅看未读</label>
      <el-button :disabled="loading" class="reload-button" @click="load()">刷新</el-button>
    </div>
    <ul v-if="items.length" class="card inbox-list" :aria-busy="loading">
      <li v-for="item in items" :key="item.id" :class="{ unread: !item.read_at }">
        <router-link :to="destination(item)" custom v-slot="{ href }">
          <a :href="href" class="inbox-item" @click="openMessage($event, item)">
            <span class="item-icon"><component :is="item.kind === 'follow' ? User : item.kind === 'moderation' ? Warning : item.kind === 'like' || item.kind === 'collection' ? Star : ChatDotRound" aria-hidden="true" /></span>
            <span class="item-copy">
              <span><strong>{{ item.actor_name }}</strong> {{ descriptions[item.kind] }}<span v-if="!item.read_at" class="unread-dot" title="未读">未读</span></span>
              <span v-if="item.note" class="preview note">{{ item.note }}</span>
              <span v-else-if="item.preview" class="preview">{{ item.preview }}</span>
              <time :datetime="item.created_at">{{ new Date(item.created_at).toLocaleString('zh-CN') }}</time>
            </span>
          </a>
        </router-link>
      </li>
    </ul>
    <p v-if="loading" class="card empty-tip" role="status">正在加载消息…</p>
    <div v-else-if="failed" class="card empty-tip"><p>消息加载失败。</p><el-button @click="load()">重试</el-button></div>
    <p v-else-if="!items.length" class="card empty-tip">{{ filter || unreadOnly ? '没有符合条件的消息' : '暂无消息。收到回声、回复、关注、点赞、收藏或内容处理结果后会在这里显示。' }}</p>
    <div v-if="nextBefore && !failed" class="load-more"><el-button :loading="loading" @click="load(true)">加载更早的消息</el-button></div>
  </section>
</template>

<style scoped>
.inbox-heading { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; padding: 23px; }
.inbox-heading h1 { margin: 0 0 5px; font-size: 25px; }
.inbox-heading p { margin: 0; color: var(--wl-muted); font-size: 14px; }
.inbox-icon, .item-icon { display: grid; place-items: center; width: 42px; height: 42px; flex: 0 0 42px; border-radius: 11px; background: #e5f1e9; color: var(--wl-primary); }
.inbox-icon svg, .item-icon svg { width: 21px; height: 21px; }
.read-all, .reload-button { margin-left: auto; }
.inbox-filters, .inbox-filters label { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; font-size: 14px; }
.inbox-filters select { font: inherit; border: 1px solid var(--wl-border); border-radius: 7px; padding: 6px; background: white; color: var(--wl-ink); }
.inbox-filters input { accent-color: var(--wl-primary); }
.inbox-list { list-style: none; padding: 0; overflow: hidden; }
.inbox-list li + li { border-top: 1px solid var(--wl-border); }
.inbox-list .unread { background: #f0f7f1; }
.inbox-item { display: flex; gap: 12px; text-decoration: none; color: inherit; padding: 15px; }
.inbox-item:hover { background: #eaf4ec; }
.inbox-item:focus-visible { outline-offset: -3px; }
.item-copy { display: grid; gap: 4px; min-width: 0; overflow-wrap: anywhere; }
.preview { white-space: pre-wrap; font-size: 14px; }
.note { color: #8a5a2b; background: #fdf6ec; border-radius: 7px; padding: 7px 9px; }
.item-copy time { color: var(--wl-muted); font-size: 12px; }
.unread-dot { display: inline-block; margin-left: 7px; border-radius: 8px; padding: 2px 6px; background: #dbece1; color: #265a4c; font-size: 11px; }
.load-more { text-align: center; }
</style>
