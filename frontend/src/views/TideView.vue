<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getHotTides } from '@/api/ripples'
import type { TideOut } from '@/api/types'

const tides = ref<TideOut[]>([])
const loading = ref(false)
const maxHeat = ref(1)

onMounted(async () => {
  loading.value = true
  try {
    tides.value = await getHotTides()
    maxHeat.value = Math.max(...tides.value.map((t) => t.heat), 1)
  } finally {
    loading.value = false
  }
})

function trendColor(trend: string): string {
  if (trend === '↑') return '#e2543f'
  if (trend === '↓') return '#5c7cfa'
  return '#90a4ae'
}
</script>

<template>
  <div>
    <h2 class="page-title">话题潮汐榜</h2>
    <p class="sub">热度 = 基础热度 + 微澜×10 + 回声×5 + 点赞×2，随讨论实时涨落。</p>

    <div v-loading="loading">
      <div v-for="t in tides" :key="t.topic.id" class="card tide-item">
        <div class="tide-head">
          <span class="tide-rank">{{ tides.indexOf(t) + 1 }}</span>
          <span class="tide-name"># {{ t.topic.name }}</span>
          <span class="tide-trend" :style="{ color: trendColor(t.trend) }">
            {{ t.trend }} {{ t.heat }}
          </span>
        </div>
        <div class="tide-bar">
          <div class="tide-fill" :style="{ width: (t.heat / maxHeat) * 100 + '%' }"></div>
        </div>
        <div class="tide-meta">
          微澜 {{ t.ripple_count }} · 回声 {{ t.echo_count }}
          <span class="tide-desc">{{ t.topic.description }}</span>
        </div>
      </div>

      <div v-if="!loading && tides.length === 0" class="empty-tip">暂无话题</div>
    </div>
  </div>
</template>

<style scoped>
.sub {
  color: #78909c;
  font-size: 13px;
  margin: -8px 0 16px;
}

.tide-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.tide-rank {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--wl-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
}

.tide-name {
  font-weight: 600;
  font-size: 15px;
}

.tide-trend {
  margin-left: auto;
  font-weight: 700;
  font-size: 16px;
}

.tide-bar {
  height: 8px;
  background: #eef3f5;
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: 8px;
}

.tide-fill {
  height: 100%;
  background: linear-gradient(90deg, #1f7a8c, #4fb3c4);
  border-radius: 999px;
  transition: width 0.4s;
}

.tide-meta {
  font-size: 12px;
  color: #90a4ae;
}

.tide-desc {
  margin-left: 12px;
}
</style>
