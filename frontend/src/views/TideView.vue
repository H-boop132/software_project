<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'
import { getHotTides } from '@/api/ripples'
import type { TideOut } from '@/api/types'

const tides = ref<TideOut[]>([])
const loading = ref(true)
const failed = ref(false)
const selectedId = ref<number>()
const selected = computed(() => tides.value.find(item => item.topic.id === selectedId.value) ?? tides.value[0])
const maxHeat = computed(() => Math.max(1, ...tides.value.map(item => item.heat)))
const activity = computed(() => selected.value ? [
  { label: '近 24 小时', score: selected.value.recent_activity },
  { label: '前 24 小时', score: selected.value.previous_activity },
] : [])
const maxActivity = computed(() => Math.max(1, ...activity.value.map(item => item.score)))
const trendLabels: Record<string, string> = { '↑': '上升', '↓': '回落', '→': '平稳' }
const number = new Intl.NumberFormat('zh-CN')

async function loadTides() {
  loading.value = true
  failed.value = false
  try {
    tides.value = await getHotTides()
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadTides)
</script>

<template>
  <div class="tide-page">
    <header class="page-heading">
      <div>
        <h1>话题潮汐榜</h1>
        <p>按热度排序，比较话题在过去两个 24 小时的互动。</p>
      </div>
      <details class="tide-method">
        <summary>热度如何计算</summary>
        <p>微澜、回声和点赞分别贡献 10、5 和 2 分，贡献每 72 小时减半，再加上话题基础热度。</p>
      </details>
    </header>

    <p v-if="loading" class="page-state" role="status">正在读取话题热度…</p>
    <p v-else-if="failed" class="page-state">话题热度加载失败。 <button type="button" @click="loadTides">重试</button></p>
    <p v-else-if="!selected" class="page-state">暂无话题</p>
    <div v-else class="tide-layout">
      <section aria-label="话题排名">
        <div class="list-head" aria-hidden="true"><span>排名</span><span>话题</span><span>热度</span><span></span></div>
        <ol class="tide-list">
          <li v-for="(item, index) in tides" :key="item.topic.id" class="tide-row"
            :class="{ 'is-selected': selected.topic.id === item.topic.id }">
            <button type="button" class="topic-select" :aria-pressed="selected.topic.id === item.topic.id"
              :aria-label="'第 ' + (index + 1) + ' 名，' + item.topic.name + '，热度 ' + item.heat + '，查看互动概况'"
              @click="selectedId = item.topic.id">
              <span class="rank">{{ index + 1 }}</span>
              <span class="topic-copy">
                <strong>{{ item.topic.name }}</strong>
                <span v-if="item.topic.description">{{ item.topic.description }}</span>
              </span>
              <span class="heat">
                <strong>{{ number.format(item.heat) }}</strong>
                <span class="heat-track" aria-hidden="true"><i :style="{ '--value': item.heat / maxHeat }"></i></span>
              </span>
            </button>
            <router-link class="topic-go" :to="{ name: 'topic', params: { id: item.topic.id } }" :aria-label="'进入话题 ' + item.topic.name">
              <ArrowRight aria-hidden="true" />
            </router-link>
          </li>
        </ol>
      </section>

      <aside class="topic-detail" aria-label="所选话题互动概况">
        <header>
          <p>话题概况</p>
          <h2 :key="selected.topic.id">{{ selected.topic.name }}</h2>
          <span class="trend" :data-trend="selected.trend">{{ selected.trend }} {{ trendLabels[selected.trend] }}</span>
        </header>
        <dl class="topic-totals">
          <div><dt>微澜</dt><dd>{{ number.format(selected.ripple_count) }}</dd></div>
          <div><dt>回声</dt><dd>{{ number.format(selected.echo_count) }}</dd></div>
        </dl>
        <h3>互动分</h3>
        <div class="activity" v-for="(item, index) in activity" :key="item.label">
          <div><span>{{ item.label }}</span><strong>{{ number.format(item.score) }}</strong></div>
          <div class="activity-track" aria-hidden="true">
            <i :class="{ previous: index === 1 }" :style="{ transform: 'scaleX(' + item.score / maxActivity + ')' }"></i>
          </div>
        </div>
        <router-link class="detail-link" :to="{ name: 'topic', params: { id: selected.topic.id } }">进入话题 <ArrowRight aria-hidden="true" /></router-link>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.tide-page { --rule: #d5e0d9; --accent: #236358; padding-top: 8px; }
.page-heading { display: flex; justify-content: space-between; align-items: end; gap: 14px 30px; flex-wrap: wrap; padding: 10px 0 21px; border-bottom: 2px solid var(--wl-ink); }
.page-heading h1 { margin: 0; font-size: clamp(29px, 4vw, 44px); line-height: 1.2; letter-spacing: -.035em; }
.page-heading p { margin: 8px 0 0; color: var(--wl-muted); font-size: 14px; line-height: 1.6; }
.tide-method { position: relative; font-size: 13px; color: var(--accent); }
.tide-method summary { cursor: pointer; }
.tide-method p { position: absolute; right: 0; z-index: 2; width: min(280px, 80vw); margin-top: 9px; padding: 12px; background: #fff; border: 1px solid var(--rule); font-size: 13px; }
.tide-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(215px, 29%); gap: clamp(20px, 3.2vw, 40px); align-items: start; padding-top: 22px; }
.list-head, .tide-row { display: grid; grid-template-columns: minmax(0, 1fr) 40px; }
.list-head { grid-template-columns: 48px minmax(0, 1fr) minmax(65px, 23%) 40px; padding: 0 0 9px; font-size: 12px; color: var(--wl-muted); }
.list-head span:first-child { padding-left: 10px; }
.list-head span:nth-child(3) { text-align: right; padding-right: 9px; }
.tide-list { margin: 0; padding: 0; list-style: none; border-bottom: 1px solid var(--rule); }
.tide-row { border-top: 1px solid var(--rule); position: relative; transition: background-color .18s ease; }
.tide-row:hover { background: #f9fbf9; }
.tide-row.is-selected { background: #e8f0ea; }
.tide-row.is-selected::before { content: ''; position: absolute; inset: 9px auto 9px 0; width: 3px; background: var(--accent); }
.topic-select { display: grid; grid-template-columns: 48px minmax(0, 1fr) minmax(65px, 24%); align-items: center; min-height: 64px; padding: 9px 9px 9px 0; border: 0; background: transparent; color: inherit; text-align: left; cursor: pointer; font: inherit; }
.rank { padding-left: 12px; color: var(--wl-muted); font: 500 19px/1.2 system-ui, sans-serif; font-variant-numeric: tabular-nums; }
.is-selected .rank { color: var(--accent); font-weight: 700; }
.topic-copy, .heat { display: grid; gap: 5px; min-width: 0; }
.topic-copy { padding-right: 8px; }
.topic-copy strong { font-size: 16px; overflow-wrap: anywhere; }
.topic-copy span { font-size: 12px; color: var(--wl-muted); overflow-wrap: anywhere; }
.heat { text-align: right; font-variant-numeric: tabular-nums; }
.heat strong { font-size: 14px; }
.heat-track, .activity-track { height: 4px; background: #dce7df; overflow: hidden; }
.heat-track i, .activity-track i { display: block; height: 100%; background: #377764; transform-origin: left; }
.heat-track i { transform: scaleX(var(--value)); animation: heat-in .48s cubic-bezier(.2,.75,.3,1) both; }
@keyframes heat-in { from { transform: scaleX(0); } }
.topic-go { display: grid; place-items: center; color: var(--accent); }
.topic-go svg, .detail-link svg { width: 15px; height: 15px; transition: transform .18s ease; }
.topic-go:hover svg, .detail-link:hover svg { transform: translateX(3px); }
.topic-detail { padding: 3px 0 5px clamp(16px, 2.4vw, 26px); border-left: 1px solid var(--rule); }
.topic-detail header > p { margin: 0 0 8px; font-size: 12px; color: var(--wl-muted); }
.topic-detail h2 { margin: 0 0 6px; font-size: clamp(21px, 3vw, 28px); line-height: 1.3; overflow-wrap: anywhere; animation: name-in .19s ease-out both; }
@keyframes name-in { from { opacity: .55; transform: translateY(3px); } }
.trend { color: var(--wl-muted); font-size: 13px; }
.trend[data-trend='↑'] { color: #216852; }
.trend[data-trend='↓'] { color: #9b5039; }
.topic-totals { display: grid; grid-template-columns: 1fr 1fr; margin: 16px 0; padding: 12px 0; border-block: 1px solid var(--rule); }
.topic-totals div { display: flex; flex-direction: column-reverse; gap: 4px; }
.topic-totals dt, .activity { color: var(--wl-muted); font-size: 12px; }
.topic-totals dd { margin: 0; font-size: 21px; line-height: 1.2; font-weight: 650; font-variant-numeric: tabular-nums; }
.topic-detail h3 { margin: 0 0 10px; font-size: 14px; }
.activity { display: grid; gap: 5px; margin: 0 0 10px; }
.activity > div:first-child { display: flex; justify-content: space-between; gap: 10px; }
.activity strong { color: var(--wl-ink); font-variant-numeric: tabular-nums; }
.activity-track i { transition: transform .32s cubic-bezier(.2,.75,.3,1); }
.activity-track i.previous { background: #829f91; }
.detail-link { display: inline-flex; align-items: center; gap: 6px; margin-top: 12px; font-size: 13px; font-weight: 650; color: var(--accent); text-underline-offset: 4px; }
.page-state { padding-block: 26px; color: var(--wl-muted); }
.page-state button { font: inherit; cursor: pointer; }
:is(.topic-select, .topic-go, .detail-link, summary):focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
@media (max-width: 650px) {
  .tide-layout { grid-template-columns: minmax(0, 1fr); }
  .topic-detail { padding: 14px 0 0; border: 0; border-top: 2px solid var(--wl-ink); }
  .tide-method p { right: auto; left: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .tide-page :is(.tide-row, .topic-detail h2, .heat-track i, .activity-track i, svg) { animation: none; transition: none; }
}
</style>
