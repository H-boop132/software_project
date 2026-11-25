<script setup lang="ts">
import { computed, ref } from 'vue'
import { Star, StarFilled } from '@element-plus/icons-vue'
import type { EchoOut } from '@/api/types'
import { setEchoLike } from '@/api/ripples'
import { MAX_ECHO_DEPTH } from '@/constants/limits'
import { useUserStore } from '@/stores/user'

// depth 从 1 起算：第一条回声为第 1 层，与后端校验口径一致
const props = withDefaults(defineProps<{ echo: EchoOut; depth?: number; interactive: boolean }>(), { depth: 1 })
const emit = defineEmits<{ reply: [echo: EchoOut]; remove: [echo: EchoOut] }>()
const store = useUserStore()
const collapsed = ref(false)
const liking = ref(false)
const canDelete = computed(() => props.echo.user.id === store.user?.id || store.user?.role === 'admin')

async function toggleLike() {
  if (!props.interactive || liking.value) return
  liking.value = true
  try {
    const result = await setEchoLike(props.echo.id, !props.echo.is_liked)
    props.echo.is_liked = result.is_liked
    props.echo.like_count = result.like_count
  } catch { /* 全局提示 */ }
  finally { liking.value = false }
}
</script>

<template>
  <li class="echo-node">
    <article :id="`echo-${echo.id}`" tabindex="-1" class="echo-body">
      <div class="echo-meta">
        <router-link :to="`/users/${echo.user.id}`">{{ echo.user.nickname }}</router-link>
        <time>{{ new Date(echo.created_at).toLocaleString('zh-CN') }}</time>
        <span v-if="echo.emotion" :style="{ color: echo.emotion.color }">● {{ echo.emotion.name }}</span>
      </div>
      <p v-if="echo.reply_to_user" class="reply-target">
        回复 <router-link :to="`/users/${echo.reply_to_user.id}`">@{{ echo.reply_to_user.nickname }}</router-link>
      </p>
      <p>{{ echo.content }}</p>
      <div class="echo-actions">
        <el-button link type="primary" :disabled="!interactive || depth >= MAX_ECHO_DEPTH" :aria-label="`回复 ${echo.user.nickname}`" @click="emit('reply', echo)">回复</el-button>
        <el-button link :type="echo.is_liked ? 'primary' : 'info'" :disabled="!interactive || liking"
          :aria-label="`${echo.is_liked ? '取消点赞' : '点赞'}这条回声，当前 ${echo.like_count} 个赞`" @click="toggleLike">
          <el-icon><StarFilled v-if="echo.is_liked" /><Star v-else /></el-icon>
          <span class="like-label">{{ echo.like_count ? echo.like_count : '点赞' }}</span>
        </el-button>
        <el-button v-if="canDelete" link type="danger" :disabled="!interactive" :aria-label="`删除回声 ${echo.id}`" @click="emit('remove', echo)">删除</el-button>
        <el-button v-if="echo.children.length" link @click="collapsed = !collapsed" :aria-expanded="!collapsed">{{ collapsed ? '展开回复' : '收起回复' }}（{{ echo.children.length }}）</el-button>
      </div>
    </article>
    <ul v-if="echo.children.length && !collapsed" class="echo-children">
      <EchoNode v-for="child in echo.children" :key="child.id" :echo="child" :depth="depth + 1" :interactive="interactive" @reply="emit('reply', $event)" @remove="emit('remove', $event)" />
    </ul>
  </li>
</template>

<style scoped>
.echo-node { list-style: none; position: relative; margin: 12px 0; }
.echo-body { border: 1px solid var(--wl-border); background: white; border-radius: 10px; padding: 12px 14px; }
.echo-body { scroll-margin-top: 120px; }
.echo-body:target { border-color: #4a8777; box-shadow: 0 0 0 3px #dbeee2; }
.echo-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; font-size: 12px; }
.echo-meta a { color: var(--wl-primary); text-decoration: none; font-weight: 600; }
.echo-meta time { color: #90a4ae; }
.echo-body p { font-size: 14px; line-height: 1.7; white-space: pre-wrap; overflow-wrap: anywhere; margin: 8px 0; }
.reply-target { font-size: 12.5px; color: var(--wl-muted); margin: 0 0 -2px; }
.reply-target a { color: var(--wl-primary); text-decoration: none; }
.like-label { margin-left: 4px; }
.echo-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.echo-children { margin: 10px 0 0 10px; padding-left: 16px; border-left: 2px solid #b8dce3; }
.echo-children > .echo-node::before { content: ''; position: absolute; left: -16px; top: 22px; width: 15px; border-top: 2px solid #b8dce3; }
@media (max-width: 600px) { .echo-children { margin-left: 3px; padding-left: 9px; } .echo-children > .echo-node::before { left: -9px; width: 8px; } }
</style>
