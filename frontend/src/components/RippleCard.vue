<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { RippleOut } from '@/api/types'
import ImageViewer from '@/components/ImageViewer.vue'

defineProps<{ ripple: RippleOut }>()

function formatTime(iso: string): string {
  const d = new Date(iso)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

/* ---------- 图片放大预览（居中显示，关闭后恢复正常操作） ---------- */
const viewer = reactive({
  visible: false,
  urls: [] as string[],
  index: 0,
})

function openViewer(urls: string[], index: number) {
  viewer.urls = urls
  viewer.index = index
  viewer.visible = true
}

/* ---------- 多图横滑：一行放不下时出现左右滑动按钮 ---------- */
const galleryEl = ref<HTMLElement | null>(null)
const canLeft = ref(false)
const canRight = ref(false)

function updateArrows() {
  const el = galleryEl.value
  if (!el) return
  canLeft.value = el.scrollLeft > 1
  canRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 1
}

function scrollBy(dir: number) {
  const el = galleryEl.value
  if (!el) return
  el.scrollBy({ left: dir * el.clientWidth * 0.8, behavior: 'smooth' })
}

onMounted(updateArrows)
</script>

<template>
  <div class="card ripple-card">
    <div class="rc-head">
      <span class="rc-nickname">{{ ripple.user.nickname }}</span>
      <span class="rc-time">{{ formatTime(ripple.created_at) }}</span>
      <span
        v-if="ripple.emotion"
        class="rc-emotion"
        :style="{ color: ripple.emotion.color }"
      >
        ● {{ ripple.emotion.name }}
      </span>
    </div>

    <router-link :to="`/ripples/${ripple.id}`" class="rc-content">
      {{ ripple.content }}
    </router-link>

    <div v-if="ripple.images?.length" class="rc-gallery">
      <button
        type="button"
        class="rc-arrow"
        :disabled="!canLeft"
        @click="scrollBy(-1)"
        aria-label="向左滑动"
      >
        ‹
      </button>
      <div
        ref="galleryEl"
        class="rc-images"
        @scroll.passive="updateArrows"
      >
        <img
          v-for="(url, i) in ripple.images"
          :key="i"
          :src="url"
          class="rc-img"
          alt="配图"
          @click="openViewer(ripple.images, i)"
          @load="updateArrows"
        />
      </div>
      <button
        type="button"
        class="rc-arrow"
        :disabled="!canRight"
        @click="scrollBy(1)"
        aria-label="向右滑动"
      >
        ›
      </button>
    </div>

    <ImageViewer
      v-if="viewer.visible"
      :urls="viewer.urls"
      :index="viewer.index"
      @close="viewer.visible = false"
    />

    <div class="rc-foot">
      <span v-if="ripple.topic" class="rc-topic"># {{ ripple.topic.name }}</span>
      <span class="rc-stat">💬 {{ ripple.echo_count }}</span>
      <span class="rc-stat">❤ {{ ripple.like_count }}</span>
    </div>
  </div>
</template>

<style scoped>
.ripple-card {
  transition: box-shadow 0.2s;
}

.ripple-card:hover {
  box-shadow: 0 4px 16px rgba(31, 122, 140, 0.1);
}

.rc-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.rc-nickname {
  font-weight: 600;
  color: #37474f;
}

.rc-time {
  font-size: 12px;
  color: #90a4ae;
}

.rc-emotion {
  font-size: 12px;
  margin-left: auto;
}

.rc-content {
  display: block;
  font-size: 15px;
  line-height: 1.7;
  color: #263238;
  text-decoration: none;
  margin-bottom: 10px;
}

.rc-content:hover {
  color: var(--wl-primary);
}

.rc-gallery {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.rc-images {
  flex: 1;
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 2px 0;
  scrollbar-width: none;
}

.rc-images::-webkit-scrollbar {
  display: none;
}

.rc-arrow {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border: 1px solid var(--wl-border);
  border-radius: 50%;
  background: #fff;
  color: #546e7a;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  transition: all 0.2s;
}

.rc-arrow:hover:not(:disabled) {
  background: var(--wl-primary);
  color: #fff;
}

.rc-arrow:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.rc-img {
  /* 多图：高度固定（与单图高度一致），宽度按原图比例自动，不变形不裁切 */
  height: 184px;
  width: auto;
  border-radius: 8px;
  cursor: zoom-in;
  flex-shrink: 0;
}

.rc-foot {
  display: flex;
  gap: 14px;
  font-size: 13px;
  color: #78909c;
}

.rc-topic {
  color: var(--wl-primary);
  margin-right: auto;
}
</style>
