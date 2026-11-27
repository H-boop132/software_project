<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ChatDotRound } from '@element-plus/icons-vue'
import type { CollectionOut, LikeOut, RippleOut } from '@/api/types'
import ImageViewer from '@/components/ImageViewer.vue'
import LikeButton from '@/components/LikeButton.vue'
import CollectionButton from '@/components/CollectionButton.vue'
import { restoreOriginalImage, thumbnailUrl } from '@/utils/images'

defineProps<{ ripple: RippleOut }>()
const emit = defineEmits<{
  'like-updated': [state: LikeOut]
  'collection-updated': [state: CollectionOut]
}>()

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

let galleryObserver: ResizeObserver | undefined
onMounted(() => {
  updateArrows()
  if (galleryEl.value) {
    galleryObserver = new ResizeObserver(updateArrows)
    galleryObserver.observe(galleryEl.value)
  }
})
onBeforeUnmount(() => galleryObserver?.disconnect())
</script>

<template>
  <div class="card ripple-card">
    <div class="rc-head">
      <router-link :to="`/users/${ripple.user.id}`" class="rc-avatar" :aria-label="ripple.user.nickname">
        <img v-if="ripple.user.avatar_url" :src="ripple.user.avatar_url" alt="" class="rc-avatar-img" />
        <template v-else>{{ ripple.user.nickname.slice(0, 1) }}</template>
      </router-link>
      <div class="rc-author">
        <router-link :to="`/users/${ripple.user.id}`" class="rc-nickname">{{ ripple.user.nickname }}</router-link>
        <time class="rc-time" :datetime="ripple.created_at">{{ formatTime(ripple.created_at) }}</time>
      </div>
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

    <div v-if="ripple.images?.length" class="rc-gallery" :class="{ 'rc-gallery-single': ripple.images.length === 1 }">
      <button
        v-if="ripple.images.length > 1"
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
        <button
          v-for="(url, i) in ripple.images"
          :key="url + i"
          type="button"
          class="rc-image-button"
          :aria-label="`查看第 ${i + 1} 张配图`"
          @click="openViewer(ripple.images, i)"
        ><img :src="thumbnailUrl(url)" class="rc-img" alt="" loading="lazy" @load="updateArrows" @error="restoreOriginalImage($event, url)" /></button>
      </div>
      <button
        v-if="ripple.images.length > 1"
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
      <router-link v-if="ripple.topic" :to="{ name: 'topic', params: { id: ripple.topic.id } }" class="rc-topic"># {{ ripple.topic.name }}</router-link>
      <router-link :to="`/ripples/${ripple.id}`" class="rc-stat" :aria-label="`查看回声，共 ${ripple.echo_count} 条`"><ChatDotRound aria-hidden="true" />{{ ripple.echo_count }}</router-link>
      <router-link v-if="ripple.echo_count > 1" :to="{ name: 'ripple-detail', params: { id: ripple.id }, query: { view: 'tree' } }" class="rc-tree-entry">查看回声树</router-link>
      <LikeButton :ripple="ripple" @updated="emit('like-updated', $event)" />
      <CollectionButton :ripple="ripple" @updated="emit('collection-updated', $event)" />
    </div>
  </div>
</template>

<style scoped>
.rc-tree-entry { color: var(--wl-primary); font-size: 12px; text-underline-offset: 3px; padding: 4px; white-space: nowrap; }
.ripple-card {
  padding: 17px 18px 13px;
  border-radius: 15px;
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

.rc-avatar { width: 36px; height: 36px; flex: 0 0 36px; border-radius: 50%; display: grid; place-items: center; background: #e7f1e8; color: var(--wl-primary); font-size: 14px; font-weight: 600; text-decoration: none; overflow: hidden; }
.rc-avatar-img { width: 100%; height: 100%; object-fit: cover; }
.rc-author { display: grid; gap: 2px; min-width: 0; }

.rc-nickname {
  font-weight: 600;
  color: #37474f;
  text-decoration: none;
}

.rc-time {
  font-size: 12px;
  color: var(--wl-muted);
}

.rc-emotion {
  font-size: 12px;
  margin-left: auto;
  white-space: nowrap;
  padding: 4px 7px;
  border: 1px solid var(--wl-border);
  border-radius: 99px;
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
  min-width: 0;
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 2px 0;
  scrollbar-width: none;
}

.rc-image-button { max-width: 100%; flex-shrink: 0; border: 0; padding: 0; border-radius: 8px; display: block; background: #eef4ef; cursor: zoom-in; overflow: hidden; }
.rc-gallery-single .rc-image-button { max-width: min(100%, 420px); }

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
  display: block;
  max-width: 100%;
  height: clamp(120px, 27vw, 184px);
  width: auto;
  object-fit: contain;
  border-radius: 8px;
  cursor: zoom-in;
  flex-shrink: 0;
}

.rc-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 9px;
  padding-top: 9px;
  border-top: 1px solid var(--wl-border);
  font-size: 13px;
  color: #78909c;
}

.rc-topic {
  color: var(--wl-primary);
  margin-right: auto;
  background: #edf4ee;
  padding: 4px 8px;
  border-radius: 6px;
  text-decoration: none;
}
.rc-stat { display: inline-flex; align-items: center; gap: 4px; color: var(--wl-muted); text-decoration: none; padding: 4px; }
.rc-stat svg { width: 15px; height: 15px; }
.rc-topic:hover, .rc-stat:hover, .rc-nickname:hover { text-decoration: underline; }
</style>
