<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { fetchMyLikes } from '@/api/interactions'
import { fetchUserLikes } from '@/api/users'
import type { LikeOut, RippleOut } from '@/api/types'
import RippleCard from '@/components/RippleCard.vue'

const props = withDefaults(defineProps<{ userId?: number; own?: boolean }>(), { own: true })
const emit = defineEmits<{ 'like-updated': [state: LikeOut] }>()
const items = ref<RippleOut[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 5
const loading = ref(false)
const failed = ref(false)
let requestVersion = 0

async function loadLikes(targetPage = page.value) {
  const version = ++requestVersion
  loading.value = true
  failed.value = false
  try {
    const result = props.userId
      ? await fetchUserLikes(props.userId, { limit: pageSize, offset: (targetPage - 1) * pageSize })
      : await fetchMyLikes({ limit: pageSize, offset: (targetPage - 1) * pageSize })
    if (version !== requestVersion) return
    const lastPage = Math.max(1, Math.ceil(result.total / pageSize))
    // 取消最后一条喜欢后，自动回到仍有内容的有效页。
    if (targetPage > lastPage) {
      await loadLikes(lastPage)
      return
    }
    page.value = targetPage
    total.value = result.total
    items.value = result.items
  } catch {
    if (version === requestVersion) failed.value = true
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

function updateLike(state: LikeOut) {
  const ripple = items.value.find((item) => item.id === state.ripple_id)
  if (ripple) {
    ripple.is_liked = state.is_liked
    ripple.like_count = state.like_count
  }
  emit('like-updated', state)
  // 只有自己的喜欢列表会因取消点赞而减少；看别人的列表时，自己的点赞操作不改变对方的列表。
  if (props.own && !state.is_liked) void loadLikes()
}

onMounted(() => { void loadLikes() })
onBeforeUnmount(() => { requestVersion++ })
</script>

<template>
  <section :aria-label="props.own ? '我的喜欢' : 'TA 的喜欢'">
    <div class="likes-toolbar">
      <span v-if="!failed" aria-live="polite">共 {{ total }} 条喜欢</span>
      <span v-else>喜欢加载失败，请重试</span>
      <el-button :disabled="loading" @click="loadLikes()">刷新喜欢</el-button>
    </div>
    <div v-loading="loading" class="likes-list" :aria-busy="loading">
      <div v-if="failed" class="empty-tip">
        <el-button type="primary" :disabled="loading" @click="loadLikes()">重新加载</el-button>
      </div>
      <template v-else>
        <RippleCard
          v-for="ripple in items"
          :key="ripple.id"
          :ripple="ripple"
          @like-updated="updateLike"
        />
        <div v-if="!loading && total === 0" class="empty-tip">
          <p>{{ props.own ? '还没有喜欢的微澜，去时间线点亮爱心吧。' : 'TA 还没有喜欢的微澜。' }}</p>
          <router-link v-if="props.own" to="/">浏览时间线</router-link>
        </div>
      </template>
    </div>
    <nav v-if="!failed && total > pageSize" aria-label="喜欢分页" class="likes-pagination">
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :total="total"
        :disabled="loading"
        layout="prev, pager, next"
        @current-change="loadLikes"
      />
    </nav>
  </section>
</template>

<style scoped>
.likes-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin: 8px 0 16px;
  color: #607d8b;
  font-size: 14px;
}
.likes-list {
  min-height: 120px;
}
.likes-pagination {
  display: flex;
  justify-content: center;
  margin: 20px 0;
}
</style>
