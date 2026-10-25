<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { fetchUserRelations } from '@/api/users'
import type { UserProfile } from '@/api/types'
import FollowButton from '@/components/FollowButton.vue'
import { useUserStore } from '@/stores/user'

const props = defineProps<{ userId: number; kind: 'following' | 'followers' }>()
const emit = defineEmits<{ changed: [] }>()
const store = useUserStore()
const items = ref<UserProfile[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const failed = ref(false)
let version = 0

async function load(target = page.value) {
  const current = ++version
  loading.value = true
  failed.value = false
  try {
    const result = await fetchUserRelations(props.userId, props.kind, { limit: 10, offset: (target - 1) * 10 })
    if (current !== version) return
    const last = Math.max(1, Math.ceil(result.total / 10))
    if (target > last) { await load(last); return }
    page.value = target
    items.value = result.items
    total.value = result.total
  } catch {
    if (current === version) failed.value = true
  } finally {
    if (current === version) loading.value = false
  }
}

function updated(profile: UserProfile) {
  const item = items.value.find((user) => user.id === profile.id)
  if (item) Object.assign(item, profile)
  if (props.kind === 'following' && props.userId === store.user?.id && !profile.is_following) void load()
  emit('changed')
}

watch(() => [props.userId, props.kind], () => { void load(1) }, { immediate: true })
onBeforeUnmount(() => { version++ })
</script>

<template>
  <div v-loading="loading" class="relations">
    <div v-if="failed" class="empty-tip"><el-button @click="load()">加载失败，点击重试</el-button></div>
    <template v-else>
      <p class="relation-total">共 {{ total }} 人</p>
      <div v-for="item in items" :key="item.id" class="card relation-row">
        <router-link :to="`/users/${item.id}`" class="relation-user">
          <strong>{{ item.nickname }}</strong><span>@{{ item.username }}</span>
          <small>{{ item.bio || '这个人还没有写签名' }}</small>
        </router-link>
        <FollowButton :profile="item" @updated="updated" />
      </div>
      <div v-if="!loading && !total" class="empty-tip">{{ kind === 'following' ? '暂时还没有关注任何人' : '暂时还没有粉丝' }}</div>
      <el-pagination v-if="total > 10" :current-page="page" :page-size="10" :total="total" :disabled="loading" layout="prev, pager, next" @current-change="load" />
    </template>
  </div>
</template>

<style scoped>
.relations { min-height: 140px; }
.relation-total { color: #78909c; font-size: 13px; }
.relation-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.relation-user { display: grid; gap: 5px; color: var(--wl-primary); text-decoration: none; min-width: 0; }
.relation-user span, .relation-user small { color: #78909c; overflow-wrap: anywhere; }
</style>
