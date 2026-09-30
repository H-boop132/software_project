<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getMoodSummary } from '@/api/ripples'
import type { MoodOut } from '@/api/types'

const moods = ref<MoodOut[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    moods.value = await getMoodSummary()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <h2 class="page-title">情绪气象</h2>
    <p class="sub">全站微澜的情绪色实时聚合 —— 此刻，这个社区集体在感受什么。</p>

    <div v-loading="loading" class="card">
      <div v-if="moods.length" class="mood-bar">
        <div
          v-for="m in moods"
          :key="m.code"
          class="mood-seg"
          :style="{ width: m.percent + '%', background: m.color }"
          :title="`${m.name} ${m.percent}%`"
        ></div>
      </div>

      <div v-if="moods.length" class="mood-list">
        <div v-for="m in moods" :key="m.code" class="mood-row">
          <span class="mood-dot" :style="{ background: m.color }"></span>
          <span class="mood-name">{{ m.name }}</span>
          <span class="mood-count">{{ m.count }} 朵</span>
          <span class="mood-percent">{{ m.percent }}%</span>
        </div>
      </div>

      <div v-if="!loading && moods.length === 0" class="empty-tip">
        暂无情绪数据，等一朵带情绪的微澜吧
      </div>
    </div>
  </div>
</template>

<style scoped>
.sub {
  color: #78909c;
  font-size: 13px;
  margin: -8px 0 16px;
}

.mood-bar {
  display: flex;
  height: 36px;
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: 20px;
}

.mood-seg {
  height: 100%;
  transition: width 0.4s;
}

.mood-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mood-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mood-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
}

.mood-name {
  font-weight: 600;
  width: 60px;
}

.mood-count {
  color: #78909c;
  font-size: 13px;
}

.mood-percent {
  margin-left: auto;
  font-weight: 700;
  color: #37474f;
}
</style>
