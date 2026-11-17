<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowRight, PartlyCloudy } from '@element-plus/icons-vue'
import { getMoodSummary } from '@/api/ripples'
import type { MoodOut } from '@/api/types'

const moods = ref<MoodOut[]>([])
const loading = ref(true)
const failed = ref(false)
const total = computed(() => moods.value.reduce((sum, item) => sum + item.count, 0))
const number = new Intl.NumberFormat('zh-CN')

const palette: Record<string, string> = {
  joy: '#d1954d',
  anger: '#c66d60',
  sorrow: '#6589b2',
  fear: '#8b76ae',
  think: '#4d8d73',
  calm: '#6f8e91',
}

const readings = computed(() => moods.value.map(item => ({ ...item, tone: palette[item.code] || item.color })))
const leaders = computed(() => readings.value.filter(item => item.count === readings.value[0]?.count))
const ring = computed(() => {
  let end = 0
  return readings.value.map((item, index) => {
    const start = end
    end = index === readings.value.length - 1 ? 100 : start + item.count / total.value * 100
    return item.tone + ' ' + start + '% ' + end + '%'
  }).join(', ')
})

async function loadMoods() {
  loading.value = true
  failed.value = false
  try {
    moods.value = await getMoodSummary()
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadMoods)
</script>

<template>
  <div class="mood-page">
    <header class="mood-hero">
      <PartlyCloudy class="hero-icon" aria-hidden="true" />
      <h1>情绪气象</h1>
      <p>从带有情绪标签的公开微澜里，感受社区的情绪分布。</p>
    </header>

    <section v-if="loading || failed || !total" class="card mood-state" :aria-busy="loading">
      <p v-if="loading" role="status">正在汇总情绪…</p>
      <p v-else-if="failed">情绪数据加载失败。 <el-button text @click="loadMoods">重试</el-button></p>
      <p v-else>暂无带情绪标签的公开微澜。</p>
    </section>

    <div v-else class="mood-grid">
      <section class="card outlook" aria-labelledby="outlook-title">
        <h2 id="outlook-title">社区情绪分布</h2>
        <div class="mood-chart">
          <div class="chart-ring" :style="{ background: 'conic-gradient(' + ring + ')' }" aria-hidden="true"></div>
          <div class="chart-center">
            <strong>{{ number.format(total) }}</strong>
            <span>条带情绪的微澜</span>
          </div>
        </div>
        <p class="mood-leading">
          {{ leaders.length > 1 ? '并列最多' : '出现最多' }}
          <strong>{{ leaders.map(item => item.name).join('、') }}</strong>
        </p>
      </section>
      <section class="card breakdown" aria-labelledby="breakdown-title">
        <h2 id="breakdown-title">情绪明细</h2>
        <p>点击一种情绪，浏览相应的微澜。</p>
        <ul class="mood-list">
          <li v-for="item in readings" :key="item.code">
            <router-link :to="{ name: 'explore', query: { mood: item.code } }" class="mood-row">
              <span class="mood-name"><i :style="{ backgroundColor: item.tone }"></i>{{ item.name }}</span>
              <span class="mood-count">{{ number.format(item.count) }} 条</span>
              <strong class="mood-percent">{{ item.percent }}%</strong>
              <ArrowRight class="mood-arrow" aria-hidden="true" />
              <span class="mood-track" aria-hidden="true"><i :style="{ width: item.percent + '%', backgroundColor: item.tone }"></i></span>
            </router-link>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<style scoped>
.mood-page { display: grid; gap: 24px; }
.mood-hero { isolation: isolate; position: relative; overflow: hidden; padding: clamp(24px, 5vw, 46px); border-radius: 24px; border: 1px solid #dae8dd; background: linear-gradient(115deg, #edf6ed, #dcece5); }
.mood-hero::before { content: ''; position: absolute; inset: 0; z-index: -1; opacity: .82; background: radial-gradient(ellipse at 84% 13%, #fff4cf 0 4%, transparent 30%), repeating-radial-gradient(ellipse 220px 100px at 84% 33%, #fff8e162 0 1px, transparent 2px 23px); pointer-events: none; }
.hero-icon { width: 30px; height: 30px; padding: 9px; box-sizing: content-box; border-radius: 13px; border: 1px solid #c9dfd2; background: #ffffff8c; color: #347061; }
.mood-hero h1 { font-family: 'Songti SC', 'Noto Serif CJK SC', SimSun, serif; font-size: clamp(32px, 5.5vw, 60px); margin: 13px 0 8px; line-height: 1.12; letter-spacing: -.035em; }
.mood-hero p { color: #44645b; font-size: 14px; line-height: 1.65; margin: 0; }
.mood-grid { display: grid; grid-template-columns: minmax(0, .85fr) minmax(0, 1.15fr); gap: 18px; align-items: start; }
.mood-grid .card, .mood-state { border-radius: 20px; margin: 0; padding: clamp(16px, 3vw, 29px); }
.mood-grid h2 { font-size: 21px; margin: 0; }
.outlook { text-align: center; background: linear-gradient(155deg, #ffffff, #f7faf7); }
.mood-chart { isolation: isolate; position: relative; display: grid; place-items: center; width: min(100%, 255px); aspect-ratio: 1; margin: 22px auto 19px; border: 1px solid #e0eae2; border-radius: 50%; }
.chart-ring { position: absolute; inset: 10px; z-index: -1; border-radius: 50%; }
.chart-center { width: 72%; aspect-ratio: 1; display: grid; align-content: center; justify-items: center; gap: 8px; background: #fff; border: 1px solid #e8efe9; border-radius: 50%; }
.chart-center strong { font: 650 clamp(27px, 5vw, 43px)/1 system-ui, sans-serif; font-variant-numeric: tabular-nums; color: var(--wl-ink); }
.chart-center span, .mood-leading, .breakdown > p { color: var(--wl-muted); font-size: 13px; }
.mood-leading { margin: 0; }
.mood-leading strong { font-size: 15px; color: var(--wl-ink); margin-left: 5px; }
.breakdown > p { margin: 5px 0 16px; }
.mood-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 5px; }
.mood-row { display: grid; grid-template-columns: minmax(55px, 1fr) auto minmax(48px, auto) 16px; align-items: center; gap: 7px 12px; padding: 10px 9px; border-radius: 9px; color: var(--wl-ink); text-decoration: none; }
.mood-row:hover, .mood-row:focus-visible { background: #eff5f0; }
.mood-name { display: inline-flex; align-items: center; gap: 8px; font-weight: 650; }
.mood-name i { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.mood-count { color: var(--wl-muted); font-size: 13px; }
.mood-percent { text-align: right; font-variant-numeric: tabular-nums; }
.mood-arrow { width: 14px; height: 14px; color: var(--wl-primary); }
.mood-track { grid-column: 1 / -1; height: 6px; background: #ebf0ec; border-radius: 6px; overflow: hidden; }
.mood-track i { height: 100%; display: block; border-radius: inherit; }
.mood-state { text-align: center; color: var(--wl-muted); }
@media (max-width: 680px) {
  .mood-grid { grid-template-columns: 1fr; }
}
</style>
