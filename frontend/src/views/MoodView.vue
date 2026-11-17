<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'
import { getMoodSummary } from '@/api/ripples'
import type { MoodOut } from '@/api/types'

const moods = ref<MoodOut[]>([])
const loading = ref(true)
const failed = ref(false)
const selectedCode = ref<string>()
const hoveredCode = ref<string>()
const focusedCode = ref<string>()
const number = new Intl.NumberFormat('zh-CN')
const ticks = [0, 25, 50, 75, 100]
const palette: Record<string, string> = {
  think: '#266651',
  calm: '#466f73',
  joy: '#a15c21',
  anger: '#a14b40',
  fear: '#705989',
  sorrow: '#476a96',
}

const readings = computed(() => moods.value.filter(item => item.count > 0).map(item => ({
  ...item, tone: palette[item.code] ?? '#536c60',
})))
const total = computed(() => readings.value.reduce((sum, item) => sum + item.count, 0))
const selected = computed(() => readings.value.find(item => item.code === selectedCode.value) ?? readings.value[0])
const current = computed(() => readings.value.find(item => item.code === (hoveredCode.value ?? focusedCode.value)) ?? selected.value)

function preview(event: PointerEvent, code: string) {
  if (event.pointerType === 'mouse') hoveredCode.value = code
}

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
    <header class="page-heading">
      <div>
        <h1>情绪气象</h1>
        <p>带有情绪标签的公开微澜，按情绪统计。</p>
      </div>
      <div v-if="!loading && !failed && total" class="sample">
        <strong>{{ number.format(total) }}</strong>
        <span>条微澜参与统计</span>
      </div>
    </header>

    <p v-if="loading" class="page-state" role="status">正在汇总情绪…</p>
    <p v-else-if="failed" class="page-state">情绪数据加载失败。 <button type="button" @click="loadMoods">重试</button></p>
    <p v-else-if="!current" class="page-state">暂无带情绪标签的公开微澜。</p>
    <template v-else>
      <section class="mood-chart" aria-labelledby="distribution-title">
        <h2 id="distribution-title">情绪占比</h2>
        <div class="scale" aria-hidden="true"><span v-for="tick in ticks" :key="tick">{{ tick }}%</span></div>
        <div class="distribution" role="group" aria-label="选择情绪查看占比详情" @pointerleave="hoveredCode = undefined">
          <button v-for="item in readings" :key="item.code" type="button" class="segment"
            :class="{ 'is-current': item.code === current.code }"
            :style="{ '--tone': item.tone, '--size': item.count }"
            :aria-pressed="item.code === selected?.code" :aria-label="item.name + '，' + item.percent + '%'"
            @pointerenter="preview($event, item.code)" @focus="focusedCode = item.code" @blur="focusedCode = undefined"
            @click="selectedCode = item.code">
            <span v-if="item.percent >= 12">{{ item.name }}</span>
          </button>
        </div>
      </section>

      <div class="mood-layout">
        <section class="mood-table" aria-label="情绪明细">
          <div class="table-head" aria-hidden="true"><span>情绪</span><span>微澜数</span><span>占比</span></div>
          <ul class="mood-list" @pointerleave="hoveredCode = undefined">
            <li v-for="item in readings" :key="item.code" class="mood-row">
              <button type="button" class="mood-item" :class="{ 'is-current': item.code === current.code }"
                :style="{ '--tone': item.tone }" :aria-pressed="item.code === selected?.code"
                :aria-label="item.name + '，' + item.count + ' 条微澜，占比 ' + item.percent + '%'"
                @pointerenter="preview($event, item.code)" @focus="focusedCode = item.code" @blur="focusedCode = undefined"
                @click="selectedCode = item.code">
                <span class="mood-name"><i aria-hidden="true"></i>{{ item.name }}</span>
                <span>{{ number.format(item.count) }}</span>
                <strong>{{ item.percent }}%</strong>
              </button>
            </li>
          </ul>
        </section>

        <aside class="mood-detail" :style="{ '--tone': current.tone }" aria-label="当前情绪详情">
          <div class="detail-name"><i aria-hidden="true"></i><h2>{{ current.name }}</h2></div>
          <div :key="current.code" class="detail-value">
            <strong>{{ current.percent }}<small>%</small></strong>
            <span>{{ number.format(current.count) }} / {{ number.format(total) }} 条微澜</span>
          </div>
          <router-link :to="{ name: 'explore', query: { mood: current.code } }">浏览「{{ current.name }}」微澜 <ArrowRight aria-hidden="true" /></router-link>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.mood-page { --rule: #d5e0d9; --accent: #236358; padding-top: 8px; }
.page-heading { display: flex; justify-content: space-between; align-items: end; flex-wrap: wrap; gap: 14px 24px; padding: 10px 0 21px; border-bottom: 2px solid var(--wl-ink); }
.page-heading h1 { margin: 0; font-size: clamp(29px, 4vw, 44px); line-height: 1.2; letter-spacing: -.035em; }
.page-heading p { margin: 8px 0 0; color: var(--wl-muted); font-size: 14px; line-height: 1.6; }
.sample { display: flex; gap: 8px; align-items: baseline; color: var(--wl-muted); font-size: 13px; }
.sample strong { color: var(--wl-ink); font-size: 25px; line-height: 1; font-variant-numeric: tabular-nums; }
.mood-chart { padding: 22px 0 26px; border-bottom: 1px solid var(--rule); }
.mood-chart h2 { margin: 0 0 15px; font-size: 17px; }
.scale { position: relative; display: flex; justify-content: space-between; padding-bottom: 9px; font-size: 11px; color: var(--wl-muted); font-variant-numeric: tabular-nums; }
.scale span { position: absolute; transform: translateX(-50%); top: 0; }
.scale span:nth-child(2) { left: 25%; }
.scale span:nth-child(3) { left: 50%; }
.scale span:nth-child(4) { left: 75%; }
.scale span:first-child { left: 0; transform: none; }
.scale span:last-child { right: 0; transform: none; }
.scale::after { content: ''; height: 12px; }
.distribution { display: flex; isolation: isolate; min-height: 67px; animation: band-in .54s cubic-bezier(.2,.75,.3,1) both; }
@keyframes band-in { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
.segment { position: relative; display: grid; place-items: center; flex: var(--size) 0 0; min-width: 0; padding: 0; border: 0; background: var(--tone); color: #fff; font: inherit; font-size: clamp(11px, 1.4vw, 14px); line-height: 1.1; font-weight: 650; white-space: nowrap; cursor: pointer; transition: filter .18s ease; }
.segment + .segment { box-shadow: inset 1px 0 #f3f6f3; }
.segment span { max-width: 100%; overflow: hidden; text-overflow: ellipsis; }
.distribution:has(.segment:is(:hover, :focus-visible)) .segment:not(.is-current) { filter: saturate(.5); }
.segment.is-current::after { content: ''; height: 3px; background: #fff; position: absolute; inset: auto max(2px, 8%) 6px; }
.mood-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(210px, 29%); gap: clamp(20px, 3.2vw, 40px); align-items: start; margin-top: 22px; }
.table-head, .mood-item { display: grid; grid-template-columns: minmax(80px, 1fr) minmax(48px, 20%) minmax(60px, 24%); align-items: center; text-align: right; padding-inline: 12px; }
.table-head { padding-block: 0 9px; color: var(--wl-muted); font-size: 12px; }
.table-head span:first-child { text-align: left; }
.mood-list { list-style: none; padding: 0; margin: 0; border-bottom: 1px solid var(--rule); }
.mood-row { border-top: 1px solid var(--rule); }
.mood-item { width: 100%; min-height: 45px; border: 0; background: transparent; color: var(--wl-ink); cursor: pointer; font: inherit; font-size: 14px; font-variant-numeric: tabular-nums; transition: background-color .18s ease; }
.mood-item.is-current { background: #e8f0ea; box-shadow: inset 3px 0 var(--tone); }
.mood-name, .detail-name { display: flex; align-items: center; text-align: left; gap: 8px; }
.mood-name i, .detail-name i { display: block; flex: 0 0 9px; width: 9px; height: 9px; background: var(--tone); }
.mood-detail { padding: 3px 0 5px clamp(16px, 2.4vw, 26px); border-left: 1px solid var(--rule); }
.detail-name h2 { margin: 0; font-size: 19px; }
.detail-name i { transition: background-color .18s ease; }
.detail-value { display: grid; gap: 7px; margin: 12px 0 20px; animation: value-in .18s ease-out both; }
@keyframes value-in { from { opacity: .55; transform: translateY(3px); } }
.detail-value strong { color: var(--tone); font-size: clamp(32px, 5vw, 48px); line-height: 1; font-weight: 650; letter-spacing: -.04em; font-variant-numeric: tabular-nums; }
.detail-value small { font-size: .52em; margin-left: 3px; }
.detail-value span { color: var(--wl-muted); font-size: 13px; }
.mood-detail a { display: inline-flex; gap: 6px; align-items: center; color: var(--accent); font-size: 13px; font-weight: 650; text-underline-offset: 4px; }
.mood-detail a svg { width: 15px; height: 15px; transition: transform .18s ease; }
.mood-detail a:hover svg { transform: translateX(3px); }
.page-state { padding-block: 26px; color: var(--wl-muted); }
.page-state button { font: inherit; cursor: pointer; }
:is(.mood-item, a):focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
.segment:focus-visible { z-index: 1; outline: 2px solid #fff; outline-offset: -4px; }
@media (max-width: 630px) {
  .mood-layout { grid-template-columns: minmax(0, 1fr); }
  .mood-detail { grid-row: 1; padding: 0 0 14px; border: 0; border-bottom: 1px solid var(--rule); }
  .detail-value { margin-bottom: 12px; }
}
@media (prefers-reduced-motion: reduce) {
  .mood-page :is(.distribution, .segment, .mood-item, .detail-name i, .detail-value, svg) { animation: none; transition: none; }
}
</style>
