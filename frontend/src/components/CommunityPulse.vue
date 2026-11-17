<script setup lang="ts">
import { ArrowRight, PartlyCloudy, TrendCharts } from '@element-plus/icons-vue'
import type { MoodOut, TideOut } from '@/api/types'

defineProps<{ tides: TideOut[]; moods: MoodOut[]; loading: boolean }>()
</script>

<template>
  <aside class="pulse" aria-label="社区动态">
    <section class="card pulse-panel">
      <div class="pulse-header">
        <div class="pulse-title"><TrendCharts aria-hidden="true" /><h2>话题潮汐</h2></div>
        <router-link to="/tide" aria-label="查看完整潮汐榜"><ArrowRight aria-hidden="true" /></router-link>
      </div>
      <ol v-if="tides.length" class="pulse-topics">
        <li v-for="(item, index) in tides.slice(0, 5)" :key="item.topic.id">
          <router-link :to="{ name: 'topic', params: { id: item.topic.id } }">
            <span class="topic-rank">{{ String(index + 1).padStart(2, '0') }}</span>
            <span>{{ item.topic.name }}</span>
            <span class="topic-score" :aria-label="`热度 ${item.heat}`">{{ item.heat }}</span>
          </router-link>
        </li>
      </ol>
      <p v-else class="pulse-message">{{ loading ? '正在读取话题…' : '暂无话题数据' }}</p>
    </section>

    <section class="card pulse-panel">
      <div class="pulse-header">
        <div class="pulse-title mood-title"><PartlyCloudy aria-hidden="true" /><h2>情绪气象</h2></div>
        <router-link to="/mood" aria-label="查看完整情绪分布"><ArrowRight aria-hidden="true" /></router-link>
      </div>
      <ul v-if="moods.length" class="pulse-moods">
        <li v-for="item in moods.slice(0, 4)" :key="item.code">
          <router-link :to="{ name: 'explore', query: { mood: item.code } }">
            <span class="mood-label"><i :style="{ background: item.color }"></i>{{ item.name }}</span>
            <span>{{ item.percent }}%</span>
            <span class="mood-track" aria-hidden="true"><i :style="{ width: item.percent + '%', background: item.color }"></i></span>
          </router-link>
        </li>
      </ul>
      <p v-else class="pulse-message">{{ loading ? '正在读取情绪…' : '暂无情绪数据' }}</p>
    </section>
  </aside>
</template>

<style scoped>
.pulse { display: grid; gap: 16px; align-content: start; }
.pulse-panel { padding: 20px; margin: 0; }
.pulse-header, .pulse-title { display: flex; align-items: center; gap: 9px; }
.pulse-header { justify-content: space-between; }
.pulse-header a { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 9px; background: #f1f6f3; color: var(--wl-primary); }
.pulse-header a:hover { background: #dcece4; }
.pulse-header svg { width: 16px; height: 16px; }
.pulse-title { color: var(--wl-primary); }
.mood-title { color: #a16b37; }
h2 { margin: 0; font-size: 16px; color: var(--wl-ink); }
ol, ul { list-style: none; padding: 0; margin: 11px 0 0; }
.pulse-topics a, .pulse-moods a { text-decoration: none; color: var(--wl-ink); }
.pulse-topics a { display: grid; grid-template-columns: 25px 1fr auto; gap: 8px; align-items: center; padding: 10px 0; font-size: 13px; }
.pulse-topics li + li { border-top: 1px solid var(--wl-border); }
.pulse a:hover { color: var(--wl-primary); }
.topic-rank, .topic-score { font-size: 12px; color: var(--wl-muted); font-variant-numeric: tabular-nums; }
.topic-rank { color: #966332; }
.pulse-moods a { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 6px; padding: 6px 0 8px; font-size: 12px; }
.mood-label { display: inline-flex; align-items: center; gap: 7px; }
.mood-label i { width: 8px; height: 8px; border-radius: 50%; }
.mood-track { grid-column: span 2; height: 4px; border-radius: 5px; background: #eef2ef; overflow: hidden; }
.mood-track i { display: block; height: 100%; border-radius: inherit; }
.pulse-message { margin-bottom: 0; font-size: 13px; color: var(--wl-muted); }
</style>
