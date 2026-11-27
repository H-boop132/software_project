<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getMyActivity, type AuthorActivity } from '@/api/activity'

const activity = ref<AuthorActivity | null>(null)
const loading = ref(true)
const failed = ref(false)
const selectedDate = ref('')
let requestVersion = 0
const selected = computed(() => activity.value?.days.find(day => day.date === selectedDate.value)
  ?? activity.value?.days[activity.value.days.length - 1])
const activeDays = computed(() => activity.value?.days.filter(day => day.count > 0).length ?? 0)
const monthCount = computed(() => activity.value?.days.reduce((sum, day) => sum + day.count, 0) ?? 0)
const maxCount = computed(() => Math.max(1, ...(activity.value?.days.map(day => day.count) ?? [])))
const chartTicks = computed(() => activity.value?.days.filter((_, index) => index === 0 || index === 14 || index === 29) ?? [])

async function load() {
  const version = ++requestVersion
  loading.value = true
  failed.value = false
  try {
    const result = await getMyActivity()
    if (version === requestVersion) activity.value = result
  } catch {
    if (version === requestVersion) failed.value = true
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

onMounted(load)
onBeforeUnmount(() => { requestVersion++ })
</script>

<template>
  <section class="activity-panel" aria-labelledby="activity-title" :aria-busy="loading">
    <header>
      <div><h2 id="activity-title">灵感轨迹</h2><p>统计当前公开的微澜，以及他人的回声和点赞。</p></div>
      <el-button text :disabled="loading" @click="load">刷新统计</el-button>
    </header>
    <p v-if="loading" class="activity-state" role="status">正在整理灵感记录…</p>
    <p v-else-if="failed" class="activity-state">统计加载失败，请点击刷新重试。</p>
    <template v-else-if="activity">
      <dl class="activity-totals">
        <div><dt>公开微澜</dt><dd>{{ activity.published_count }}</dd></div>
        <div><dt>收到回声</dt><dd>{{ activity.received_echoes }}</dd></div>
        <div><dt>收到点赞</dt><dd>{{ activity.received_likes }}</dd></div>
      </dl>
      <div class="chart-heading">
        <h3>近 30 天</h3>
        <span>{{ monthCount }} 条微澜 · {{ activeDays }} 天有记录</span>
      </div>
      <div class="activity-bars" role="group" aria-label="每天公开发布的微澜数">
        <button v-for="day in activity.days" :key="day.date" type="button"
          :class="{ 'is-selected': selected?.date === day.date }"
          :aria-label="day.date + '，' + day.count + ' 条微澜'"
          :aria-pressed="selected?.date === day.date"
          @focus="selectedDate = day.date" @click="selectedDate = day.date">
          <span :style="{ height: (day.count ? Math.max(6, day.count / maxCount * 100) : 3) + '%' }"></span>
        </button>
      </div>
      <div class="chart-dates" aria-hidden="true"><span v-for="day in chartTicks" :key="day.date">{{ day.date.slice(5) }}</span></div>
      <p v-if="selected" class="day-reading" role="status">{{ selected.date }} · {{ selected.count }} 条公开微澜</p>
      <router-link v-if="!activity.published_count" class="activity-start" to="/compose">写下第一条微澜</router-link>
    </template>
  </section>
</template>

<style scoped>
.activity-panel { padding: 20px; border: 1px solid var(--wl-border); background: white; border-radius: 12px; margin-bottom: 22px; }
header { display: flex; gap: 12px; align-items: start; justify-content: space-between; }
h2 { margin: 0; font-size: 19px; }
header p { color: var(--wl-muted); font-size: 12px; margin: 6px 0 0; }
.activity-totals { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 21px 0; }
.activity-totals div { display: flex; flex-direction: column-reverse; gap: 5px; }
.activity-totals dt { color: var(--wl-muted); font-size: 12px; }
.activity-totals dd { margin: 0; font-size: 27px; font-weight: 650; line-height: 1.1; font-variant-numeric: tabular-nums; }
.chart-heading { display: flex; gap: 10px; flex-wrap: wrap; justify-content: space-between; align-items: baseline; margin: 0 0 10px; }
.chart-heading h3 { margin: 0; font-size: 14px; }
.chart-heading span, .day-reading, .activity-state { color: var(--wl-muted); font-size: 12px; }
.activity-bars { display: flex; gap: 3px; height: 84px; padding-bottom: 1px; border-bottom: 1px solid var(--wl-border); }
.activity-bars button { flex: 1 1 0; min-width: 0; border: 0; background: transparent; padding: 0; display: flex; align-items: end; cursor: pointer; }
.activity-bars button span { display: block; width: 100%; background: #b3d1bf; border-radius: 2px 2px 0 0; transition: background-color .15s; }
.activity-bars button.is-selected span, .activity-bars button:hover span { background: #286855; }
.activity-bars button:focus-visible { outline: 2px solid #286855; outline-offset: 1px; }
.chart-dates { display: flex; justify-content: space-between; font-size: 11px; color: var(--wl-muted); padding-top: 5px; }
.day-reading { margin-bottom: 0; }
.activity-start { display: inline-block; margin-top: 12px; color: var(--wl-primary); font-size: 13px; }
@media (max-width: 420px) {
  .activity-panel { padding: 14px; }
  .activity-bars { gap: 2px; }
}
@media (prefers-reduced-motion: reduce) {
  .activity-bars button span { transition: none; }
}
</style>
