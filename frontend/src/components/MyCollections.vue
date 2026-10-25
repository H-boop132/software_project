<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { fetchMyCollections } from '@/api/interactions'
import type { CollectionOut, LikeOut, RippleOut } from '@/api/types'
import RippleCard from '@/components/RippleCard.vue'

const emit = defineEmits<{ 'like-updated': [state: LikeOut] }>()
const items = ref<RippleOut[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 5
const loading = ref(false)
const failed = ref(false)
let requestVersion = 0

async function loadCollections(targetPage = page.value) {
  const version = ++requestVersion
  loading.value = true
  failed.value = false
  try {
    const result = await fetchMyCollections({ limit: pageSize, offset: (targetPage - 1) * pageSize })
    if (version !== requestVersion) return
    const lastPage = Math.max(1, Math.ceil(result.total / pageSize))
    // 最后一页最后一项被取消，或其他页面改变收藏时，自动回到有效页。
    if (targetPage > lastPage) {
      await loadCollections(lastPage)
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
}

function updateCollection(state: CollectionOut) {
  if (!state.is_collected) void loadCollections()
}

onMounted(() => { void loadCollections() })
onBeforeUnmount(() => { requestVersion++ })
</script>

<template>
  <section aria-label="我的收藏">
    <div class="collections-toolbar">
      <span v-if="!failed" aria-live="polite">共 {{ total }} 条收藏</span>
      <span v-else>收藏加载失败，请重试</span>
      <el-button :disabled="loading" @click="loadCollections()">刷新收藏</el-button>
    </div>
    <div v-loading="loading" class="collections-list" :aria-busy="loading">
      <div v-if="failed" class="empty-tip">
        <el-button type="primary" :disabled="loading" @click="loadCollections()">重新加载</el-button>
      </div>
      <template v-else>
        <RippleCard
          v-for="ripple in items"
          :key="ripple.id"
          :ripple="ripple"
          @like-updated="updateLike"
          @collection-updated="updateCollection"
        />
        <div v-if="!loading && total === 0" class="empty-tip">
          <p>还没有收藏，去时间线收藏喜欢的微澜吧。</p>
          <router-link to="/">浏览时间线</router-link>
        </div>
      </template>
    </div>
    <nav v-if="!failed && total > pageSize" aria-label="收藏分页" class="collections-pagination">
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :total="total"
        :disabled="loading"
        layout="prev, pager, next"
        @current-change="loadCollections"
      />
    </nav>
  </section>
</template>

<style scoped>
.collections-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin: 8px 0 16px;
  color: #607d8b;
  font-size: 14px;
}
.collections-list {
  min-height: 120px;
}
.collections-pagination {
  display: flex;
  justify-content: center;
  margin: 20px 0;
}
</style>
