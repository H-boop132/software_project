<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps<{
  /** 可预览的图片 URL 列表（多图时支持左右切换） */
  urls: string[]
  /** 初始展示第几张（从 0 开始） */
  index: number
}>()

const emit = defineEmits<{ (e: 'close'): void }>()

const current = ref(props.index)
watch(
  () => props.index,
  (v) => (current.value = v),
)

const url = computed(() => props.urls[current.value] || '')

function prev() {
  if (current.value > 0) current.value -= 1
}

function next() {
  if (current.value < props.urls.length - 1) current.value += 1
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
  else if (e.key === 'ArrowLeft') prev()
  else if (e.key === 'ArrowRight') next()
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <!-- 全屏遮罩：居中放大展示原图，保持图片原始比例不变形、不裁切 -->
  <Teleport to="body">
    <div class="iv-mask" @click.self="emit('close')">
      <button class="iv-close" type="button" @click="emit('close')" aria-label="关闭">✕</button>

      <button
        v-if="urls.length > 1"
        type="button"
        class="iv-nav iv-prev"
        :disabled="current === 0"
        @click.stop="prev"
        aria-label="上一张"
      >
        ‹
      </button>

      <img :src="url" class="iv-img" alt="图片预览" @click.stop />

      <button
        v-if="urls.length > 1"
        type="button"
        class="iv-nav iv-next"
        :disabled="current === urls.length - 1"
        @click.stop="next"
        aria-label="下一张"
      >
        ›
      </button>

      <div v-if="urls.length > 1" class="iv-counter">{{ current + 1 }} / {{ urls.length }}</div>
    </div>
  </Teleport>
</template>

<style scoped>
.iv-mask {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(10, 16, 20, 0.88);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: zoom-out;
}

.iv-img {
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5);
  cursor: default;
  user-select: none;
}

.iv-close {
  position: absolute;
  top: 20px;
  right: 28px;
  width: 44px;
  height: 44px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  transition: background 0.2s;
}

.iv-close:hover {
  background: rgba(255, 255, 255, 0.28);
}

.iv-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 52px;
  height: 52px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  font-size: 30px;
  line-height: 1;
  cursor: pointer;
  transition: background 0.2s;
}

.iv-nav:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.28);
}

.iv-nav:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.iv-prev {
  left: 28px;
}

.iv-next {
  right: 28px;
}

.iv-counter {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  color: #fff;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.14);
  padding: 6px 14px;
  border-radius: 20px;
}
</style>
