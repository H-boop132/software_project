<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { setRippleLike } from '@/api/interactions'
import type { LikeOut, RippleOut } from '@/api/types'
import { useUserStore } from '@/stores/user'

const props = defineProps<{ ripple: RippleOut }>()
const emit = defineEmits<{ updated: [state: LikeOut] }>()
const pending = ref(false)
const router = useRouter()
const userStore = useUserStore()

async function toggleLike() {
  if (pending.value || props.ripple.status !== 'published') return
  if (!userStore.isLoggedIn) {
    ElMessage.info('请先登录再点赞')
    await router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  pending.value = true
  try {
    const state = await setRippleLike(props.ripple.id, !props.ripple.is_liked)
    emit('updated', state)
  } catch {
    // 请求拦截器负责提示；保留服务端确认前的原状态，允许重试。
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <button
    type="button"
    class="like-button"
    :class="{ liked: ripple.is_liked }"
    :disabled="pending || ripple.status !== 'published'"
    :aria-pressed="ripple.is_liked"
    :aria-busy="pending"
    :aria-label="`${ripple.is_liked ? '取消点赞' : '点赞'}，${ripple.like_count} 个赞`"
    @click.stop="toggleLike"
  >
    <span aria-hidden="true">{{ ripple.is_liked ? '♥' : '♡' }}</span>
    {{ pending ? '处理中…' : ripple.is_liked ? '已点赞' : '点赞' }}
    <span class="like-count">{{ ripple.like_count }}</span>
  </button>
</template>

<style scoped>
.like-button {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 3px 7px;
  background: transparent;
  color: #607d8b;
  font: inherit;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.like-button:hover:not(:disabled), .like-button.liked {
  background: #fff0f3;
  color: #c33859;
}
.like-button:focus-visible {
  outline: 2px solid var(--wl-primary);
  outline-offset: 2px;
}
.like-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.like-count {
  min-width: 1ch;
  font-variant-numeric: tabular-nums;
}
</style>
