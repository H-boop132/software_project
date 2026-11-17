<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowRight, TrendCharts } from '@element-plus/icons-vue'
import { getHotTides } from '@/api/ripples'
import type { TideOut } from '@/api/types'

const tides = ref<TideOut[]>([])
const loading = ref(true)
const failed = ref(false)
const leader = computed(() => tides.value[0])
const maxHeat = computed(() => Math.max(1, ...tides.value.map(item => item.heat)))
const maxActivity = computed(() => Math.max(1, ...tides.value.map(item => Math.max(item.recent_activity, item.previous_activity))))
const trendLabels: Record<string, string> = { '↑': '上升', '↓': '回落', '→': '平稳' }
const trendClasses: Record<string, string> = { '↑': 'rising', '↓': 'falling', '→': 'steady' }
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
    <section class="tide-hero" aria-labelledby="tide-title">
      <div class="tide-intro">
        <TrendCharts class="tide-icon" aria-hidden="true" />
        <h1 id="tide-title">话题潮汐榜</h1>
        <p>看见讨论的涨落，找到此刻值得加入的话题。</p>
      </div>
      <router-link v-if="!loading && !failed && leader" class="leader" :to="{ name: 'topic', params: { id: leader.topic.id } }">
        <span class="leader-label">当前热度第一</span>
        <strong>{{ leader.topic.name }}</strong>
        <span class="leader-score">{{ number.format(leader.heat) }} <small>热度</small></span>
        <ArrowRight class="leader-arrow" aria-hidden="true" />
      </router-link>
    </section>

    <section class="card tide-board" aria-labelledby="tide-list-title" :aria-busy="loading">
      <header class="board-heading">
        <div>
          <h2 id="tide-list-title">话题排行</h2>
          <p v-if="tides.length">{{ tides.length }} 个话题 · 按热度排序</p>
        </div>
        <div v-if="!loading && !failed && tides.length" class="tide-legend" aria-label="互动分图例">
          <span><i></i>近 24 小时</span>
          <span><i></i>前 24 小时</span>
        </div>
      </header>

      <div v-if="loading" class="empty-tip" role="status">正在读取话题热度…</div>
      <div v-else-if="failed" class="empty-tip">
        话题热度加载失败。 <el-button text @click="loadTides">重试</el-button>
      </div>
      <div v-else-if="!tides.length" class="empty-tip">暂无话题</div>
      <ol v-else class="tide-list">
        <li v-for="(item, index) in tides" :key="item.topic.id" class="tide-row" :class="{ 'tide-row-first': index === 0 }">
          <span class="tide-rank" :aria-label="'第 ' + (index + 1) + ' 名'">{{ String(index + 1).padStart(2, '0') }}</span>
          <div class="topic-info">
            <router-link class="topic-name" :to="{ name: 'topic', params: { id: item.topic.id } }">
              <span class="topic-hash" aria-hidden="true">#</span> {{ item.topic.name }} <ArrowRight aria-hidden="true" />
            </router-link>
            <p v-if="item.topic.description" class="topic-description">{{ item.topic.description }}</p>
            <span class="topic-counts">{{ number.format(item.ripple_count) }} 条微澜 · {{ number.format(item.echo_count) }} 条回声</span>
          </div>
          <div class="heat">
            <div class="heat-value">
              <strong>{{ number.format(item.heat) }}</strong>
              <span>热度</span>
              <span class="trend" :class="trendClasses[item.trend]">{{ item.trend }} {{ trendLabels[item.trend] }}</span>
            </div>
            <div class="heat-track" aria-hidden="true"><i :style="{ width: (item.heat / maxHeat * 100) + '%' }"></i></div>
          </div>
          <div class="activity">
            <div v-for="(score, period) in { recent: item.recent_activity, previous: item.previous_activity }" :key="period" class="activity-line" :class="period">
              <div class="activity-track" aria-hidden="true"><i :style="{ width: (score / maxActivity * 100) + '%' }"></i></div>
              <span :aria-label="(period === 'recent' ? '近 24 小时' : '前 24 小时') + '互动分 ' + score">{{ number.format(score) }}</span>
            </div>
          </div>
        </li>
      </ol>
      <details class="tide-method">
        <summary>热度如何计算？</summary>
        <p>微澜、回声和点赞分别贡献 10、5 和 2 分，贡献每 72 小时减半，再加上话题基础热度。趋势比较近 24 小时与前 24 小时的互动分。</p>
      </details>
    </section>
  </div>
</template>

<style scoped>
.tide-page { display: grid; gap: 24px; }
.tide-hero { isolation: isolate; position: relative; overflow: hidden; display: flex; align-items: end; justify-content: space-between; gap: 24px; padding: clamp(24px, 5vw, 50px); border-radius: 24px; color: #f2fbf5; background: radial-gradient(ellipse at top right, #348479 0%, transparent 64%), linear-gradient(125deg, #102f2d, #194b45); }
.tide-hero::before { content: ''; position: absolute; z-index: -1; inset: 0; opacity: .65; background: repeating-radial-gradient(ellipse 390px 145px at 81% 128%, transparent 0 23px, #afedc73c 24px 25px, transparent 26px 40px); pointer-events: none; }
.tide-icon { width: 30px; height: 30px; padding: 9px; box-sizing: content-box; border: 1px solid #d1f9df55; border-radius: 13px; background: #e0ffee1a; color: #c0efd2; }
.tide-intro h1 { font-family: 'Songti SC', 'Noto Serif CJK SC', SimSun, serif; font-size: clamp(32px, 5.5vw, 60px); margin: 13px 0 8px; line-height: 1.12; letter-spacing: -.035em; }
.tide-intro p { margin: 0; color: #d6eee2; font-size: 14px; line-height: 1.65; }
.leader { position: relative; align-self: stretch; display: grid; align-content: center; gap: 7px; min-width: min(245px, 100%); padding: 18px 42px 18px 20px; border: 1px solid #cbf8da55; border-radius: 15px; background: #122f2c9c; color: #f5faf5; text-decoration: none; }
.leader:hover { background: #173932; }
.leader-label, .leader-score small { color: #bde3cb; font-size: 12px; }
.leader strong { font-size: clamp(16px, 2.4vw, 22px); overflow-wrap: anywhere; }
.leader-score { color: #f6dda7; font: 650 27px/1 system-ui, sans-serif; font-variant-numeric: tabular-nums; }
.leader-arrow { position: absolute; top: 18px; right: 15px; width: 16px; color: #d5f4df; }
.tide-board { padding: clamp(15px, 3vw, 28px); margin: 0; border-radius: 20px; }
.board-heading { display: flex; align-items: end; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 17px; }
.board-heading h2 { margin: 0; font-size: 21px; }
.board-heading p { margin: 5px 0 0; font-size: 13px; color: var(--wl-muted); }
.tide-legend { display: flex; gap: 13px; flex-wrap: wrap; color: var(--wl-muted); font-size: 12px; }
.tide-legend span { display: inline-flex; align-items: center; gap: 5px; }
.tide-legend i { width: 11px; height: 6px; border-radius: 6px; background: #358173; }
.tide-legend span + span i { background: #a0bab0; }
.tide-list { padding: 0; margin: 0; list-style: none; }
.tide-row { display: grid; grid-template-columns: 42px minmax(130px, 1.4fr) minmax(130px, 1fr) minmax(95px, .76fr); align-items: center; gap: clamp(8px, 2vw, 22px); padding: 15px 12px; border-top: 1px solid var(--wl-border); }
.tide-row-first { background: #f4f8f4; border-radius: 12px; border-top-color: transparent; }
.tide-rank { color: #526f64; font: 650 21px/1 system-ui, sans-serif; font-variant-numeric: tabular-nums; }
.tide-row-first .tide-rank { color: #936020; }
.topic-name { display: inline-flex; gap: 5px; align-items: center; color: var(--wl-ink); font-size: 16px; font-weight: 700; overflow-wrap: anywhere; text-decoration: none; }
.topic-name:hover { text-decoration: underline; text-underline-offset: 4px; }
.topic-name svg { width: 14px; height: 14px; flex: 0 0 14px; color: var(--wl-primary); }
.topic-hash { color: #398173; }
.topic-description { margin: 4px 0 3px; font-size: 13px; color: var(--wl-muted); overflow-wrap: anywhere; }
.topic-counts, .heat-value, .activity { color: var(--wl-muted); font-size: 12px; }
.heat-value { display: flex; flex-wrap: wrap; gap: 4px; align-items: baseline; margin-bottom: 7px; font-variant-numeric: tabular-nums; }
.heat-value strong { color: var(--wl-ink); font-size: 19px; line-height: 1; }
.trend { padding: 2px 6px; border-radius: 6px; white-space: nowrap; }
.trend.rising { background: #e3f1e9; color: #255949; }
.trend.falling { background: #e9ebf7; color: #475682; }
.trend.steady { background: #edf0eb; color: #4f655e; }
.heat-track, .activity-track { height: 6px; background: #e8efeb; border-radius: 6px; overflow: hidden; }
.heat-track i, .activity-track i { display: block; height: 100%; border-radius: inherit; background: #358173; }
.heat-track i { background: linear-gradient(90deg, #255f55, #6ea990); }
.activity { display: grid; gap: 7px; font-variant-numeric: tabular-nums; }
.activity-line { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 6px; }
.activity-line.previous i { background: #a0bab0; }
.tide-method { margin-top: 15px; padding: 13px 12px 0; border-top: 1px solid var(--wl-border); color: var(--wl-muted); font-size: 13px; }
.tide-method summary { cursor: pointer; color: var(--wl-primary); width: fit-content; }
.tide-method p { margin: 8px 0 0; line-height: 1.65; }
@media (max-width: 670px) {
  .tide-row { grid-template-columns: 26px minmax(0, 1.2fr) minmax(0, 1fr); gap: 10px; padding-inline: 7px; }
  .topic-info { grid-column: 2 / -1; }
  .heat { grid-column: 2; }
  .activity { grid-column: 3; }
}
@media (max-width: 470px) {
  .tide-hero { display: grid; }
  .leader { min-width: 0; }
}
</style>
