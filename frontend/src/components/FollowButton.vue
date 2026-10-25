<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { UserProfile } from '@/api/types'
import { setUserFollow } from '@/api/users'
import { useUserStore } from '@/stores/user'

const props = defineProps<{ profile: UserProfile }>()
const emit = defineEmits<{ updated: [profile: UserProfile] }>()
const store = useUserStore()
const router = useRouter()
const pending = ref(false)

async function toggle() {
  if (pending.value) return
  if (!store.isLoggedIn) {
    ElMessage.info('请先登录再关注')
    await router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    return
  }
  pending.value = true
  try {
    emit('updated', await setUserFollow(props.profile.id, !props.profile.is_following))
  } catch {
    // 全局拦截器提示错误；原状态保持可重试。
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <el-button
    v-if="profile.id !== store.user?.id"
    :type="profile.is_following ? 'default' : 'primary'"
    :loading="pending"
    :aria-pressed="profile.is_following"
    :aria-label="profile.is_following ? '取消关注' : '关注用户'"
    @click="toggle"
  >{{ profile.is_following ? (profile.follows_you ? '互相关注' : '已关注') : '关注' }}</el-button>
</template>
