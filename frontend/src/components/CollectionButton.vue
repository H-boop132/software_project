<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { setRippleCollection } from '@/api/interactions'
import type { CollectionOut, RippleOut } from '@/api/types'
import { useUserStore } from '@/stores/user'

const props = defineProps<{ ripple: RippleOut }>()
const emit = defineEmits<{ updated: [state: CollectionOut] }>()
const pending = ref(false)
const router = useRouter()
const userStore = useUserStore()

async function toggleCollection() {
  if (pending.value || props.ripple.status !== 'published') return
  if (!userStore.isLoggedIn) {
    ElMessage.info('请先登录再收藏')
    await router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  pending.value = true
  try {
    const state = await setRippleCollection(props.ripple.id, !props.ripple.is_collected)
    emit('updated', state)
  } catch {
    // 请求拦截器统一提示；失败时保留原状态，可再次点击重试。
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <button
    type="button"
    class="collection-button"
    :class="{ collected: ripple.is_collected }"
    :disabled="pending || ripple.status !== 'published'"
    :aria-pressed="ripple.is_collected"
    :aria-busy="pending"
    :aria-label="ripple.is_collected ? '取消收藏' : '收藏'"
    @click.stop="toggleCollection"
  >
    <span aria-hidden="true">{{ ripple.is_collected ? '★' : '☆' }}</span>
    {{ pending ? '处理中…' : ripple.is_collected ? '已收藏' : '收藏' }}
  </button>
</template>

<style scoped>
.collection-button {
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
.collection-button:hover:not(:disabled), .collection-button.collected {
  background: #fff6df;
  color: #8a5a00;
}
.collection-button:focus-visible {
  outline: 2px solid var(--wl-primary);
  outline-offset: 2px;
}
.collection-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
