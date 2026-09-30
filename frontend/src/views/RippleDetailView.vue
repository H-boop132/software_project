<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getRippleDetail } from '@/api/ripples'
import type { EchoOut, RippleDetail } from '@/api/types'
import ImageViewer from '@/components/ImageViewer.vue'

const route = useRoute()
const detail = ref<RippleDetail | null>(null)
const loading = ref(false)

/* ---------- 图片放大预览 ---------- */
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

function formatTime(iso: string): string {
  const d = new Date(iso)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

onMounted(async () => {
  loading.value = true
  try {
    detail.value = await getRippleDetail(Number(route.params.id))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-loading="loading">
    <template v-if="detail">
      <div class="card">
        <div class="rc-head">
          <span class="rc-nickname">{{ detail.ripple.user.nickname }}</span>
          <span class="rc-time">{{ formatTime(detail.ripple.created_at) }}</span>
          <span
            v-if="detail.ripple.emotion"
            class="rc-emotion"
            :style="{ color: detail.ripple.emotion.color }"
          >
            ● {{ detail.ripple.emotion.name }}
          </span>
        </div>
        <p class="rc-content">{{ detail.ripple.content }}</p>
        <div v-if="detail.ripple.images?.length" class="rd-images">
          <img
            v-for="(url, i) in detail.ripple.images"
            :key="i"
            :src="url"
            class="rd-img"
            alt="配图"
            @click="openViewer(detail.ripple.images, i)"
          />
        </div>
        <div class="rc-foot">
          <span v-if="detail.ripple.topic" class="rc-topic"># {{ detail.ripple.topic.name }}</span>
          <span>💬 {{ detail.ripple.echo_count }} · ❤ {{ detail.ripple.like_count }}</span>
        </div>
      </div>

      <ImageViewer
        v-if="viewer.visible"
        :urls="viewer.urls"
        :index="viewer.index"
        @close="viewer.visible = false"
      />

      <h3 class="echo-title">回声 · 涟漪树</h3>
      <div v-if="detail.echoes.length === 0" class="empty-tip">
        还没有回声，等待第一个共鸣者。
      </div>

      <!-- 递归渲染涟漪树 -->
      <EchoNode v-for="e in detail.echoes" :key="e.id" :echo="e" :depth="0" />
    </template>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import type { PropType } from 'vue'
import type { EchoOut } from '@/api/types'

const EchoNode = defineComponent({
  name: 'EchoNode',
  props: {
    echo: { type: Object as PropType<EchoOut>, required: true },
    depth: { type: Number, default: 0 },
  },
  template: `
    <div class="echo-node" :style="{ marginLeft: depth + 'em' }">
      <div class="echo-body">
        <span class="echo-user">{{ echo.user.nickname }}</span>
        <span class="echo-text">{{ echo.content }}</span>
        <span v-if="echo.emotion" class="echo-emotion" :style="{ color: echo.emotion.color }">
          ● {{ echo.emotion.name }}
        </span>
      </div>
      <EchoNode v-for="c in echo.children" :key="c.id" :echo="c" :depth="depth + 1" />
    </div>
  `,
})

export default {
  components: { EchoNode },
}
</script>

<style scoped>
.rc-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.rc-nickname {
  font-weight: 600;
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
  font-size: 16px;
  line-height: 1.8;
  margin: 0 0 12px;
}

.rd-images {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.rd-img {
  max-width: 100%;
  max-height: 320px;
  border-radius: 10px;
  /* contain：按原始比例完整显示，不裁切不变形 */
  object-fit: contain;
  background: #f2f6f8;
  cursor: zoom-in;
}

.rc-foot {
  font-size: 13px;
  color: #78909c;
  display: flex;
  gap: 14px;
}

.rc-topic {
  color: var(--wl-primary);
}

.echo-title {
  margin: 20px 0 12px;
  font-size: 16px;
}

.echo-node {
  border-left: 2px solid var(--wl-border);
  padding: 6px 0 6px 12px;
  margin-bottom: 4px;
}

.echo-body {
  background: #fff;
  border: 1px solid var(--wl-border);
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.echo-user {
  font-size: 13px;
  font-weight: 600;
  color: var(--wl-primary);
  white-space: nowrap;
}

.echo-text {
  font-size: 14px;
  flex: 1;
}

.echo-emotion {
  font-size: 12px;
  white-space: nowrap;
}
</style>
