<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import RippleCard from '@/components/RippleCard.vue'
import { listRipples, getHotTides } from '@/api/ripples'
import type { CollectionOut, LikeOut, RippleOut, TopicOut } from '@/api/types'

const ripples = ref<RippleOut[]>([])
const topics = ref<TopicOut[]>([])
const activeTopic = ref<number | null>(null)
const keyword = ref('')
const loading = ref(false)

function updateLike(state: LikeOut) {
  const ripple = ripples.value.find((r) => r.id === state.ripple_id)
  if (ripple) {
    ripple.is_liked = state.is_liked
    ripple.like_count = state.like_count
  }
}

async function loadRipples() {
  loading.value = true
  try {
    ripples.value = await listRipples({
      ...(activeTopic.value ? { topic_id: activeTopic.value } : {}),
      ...(keyword.value.trim() ? { keyword: keyword.value.trim() } : {}),
    })
  } finally {
    loading.value = false
  }
}

function updateCollection(state: CollectionOut) {
  const ripple = ripples.value.find((r) => r.id === state.ripple_id)
  if (ripple) ripple.is_collected = state.is_collected
}

function search() {
  loadRipples()
}

function pickTopic(id: number | null) {
  activeTopic.value = id
  loadRipples()
}

onMounted(async () => {
  loadRipples()
  try {
    const tides = await getHotTides()
    topics.value = tides.map((t) => t.topic)
  } catch {
    /* 话题加载失败不影响时间线 */
  }
})
</script>

<template>
  <div>
    <section class="hero">
      <h1>今天，你的心里泛起了什么涟漪？</h1>
      <p>记录 ≤200 字的一闪之念，等待共鸣的回声。</p>
      <router-link to="/compose" class="hero-btn">写下第一朵微澜 →</router-link>
    </section>

    <div class="search-bar">
      <el-input
        v-model="keyword"
        placeholder="搜索微澜内容关键词…"
        clearable
        @keyup.enter="search"
        @clear="search"
      >
        <template #append>
          <el-button @click="search">搜索</el-button>
        </template>
      </el-input>
    </div>

    <div v-if="topics.length" class="topic-chips">
      <button
        class="chip"
        :class="{ on: activeTopic === null }"
        @click="pickTopic(null)"
      >
        全部
      </button>
      <button
        v-for="t in topics"
        :key="t.id"
        class="chip"
        :class="{ on: activeTopic === t.id }"
        @click="pickTopic(t.id)"
      >
        # {{ t.name }}
      </button>
    </div>

    <div v-loading="loading">
      <RippleCard
        v-for="r in ripples"
        :key="r.id"
        :ripple="r"
        @like-updated="updateLike"
        @collection-updated="updateCollection"
      />
      <div v-if="!loading && ripples.length === 0" class="empty-tip">
        还没有微澜，来掀开第一朵吧 🌊
      </div>
    </div>
  </div>
</template>

<style scoped>
.hero {
  background: linear-gradient(135deg, #1f7a8c, #2ba0b8);
  color: #fff;
  border-radius: 16px;
  padding: 36px 28px;
  margin-bottom: 20px;
}

.hero h1 {
  margin: 0 0 8px;
  font-size: 24px;
}

.hero p {
  margin: 0 0 18px;
  opacity: 0.9;
}

.hero-btn {
  display: inline-block;
  background: #fff;
  color: var(--wl-primary);
  font-weight: 600;
  padding: 8px 20px;
  border-radius: 999px;
  text-decoration: none;
  font-size: 14px;
}

.search-bar {
  margin-bottom: 16px;
}

.topic-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.chip {
  border: 1px solid var(--wl-border);
  background: #fff;
  border-radius: 999px;
  padding: 5px 14px;
  font-size: 13px;
  color: #546e7a;
  cursor: pointer;
}

.chip.on {
  background: var(--wl-primary);
  border-color: var(--wl-primary);
  color: #fff;
}
</style>
