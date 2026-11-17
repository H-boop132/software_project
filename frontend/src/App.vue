<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Bell, Compass, House, TrendCharts, PartlyCloudy, Plus } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useNotificationStore } from '@/stores/notifications'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { isLoggedIn, user } = storeToRefs(userStore)
const notifications = useNotificationStore()
let notificationTimer: number | undefined

function refreshNotifications() {
  if (!document.hidden) void notifications.refresh()
}

// 裸页面（如登录页）：不显示顶栏与页脚
const bare = computed(() => route.meta.bare === true)
const wide = computed(() => route.name === 'home' || route.name === 'explore')

// 进入页面时恢复登录态（刷新后 user 信息需要重新拉取）
onMounted(() => {
  userStore.refreshMe()
  notificationTimer = window.setInterval(refreshNotifications, 30000)
  document.addEventListener('visibilitychange', refreshNotifications)
})
onBeforeUnmount(() => {
  window.clearInterval(notificationTimer)
  document.removeEventListener('visibilitychange', refreshNotifications)
})

function logout() {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-shell">
    <header v-if="!bare" class="topbar">
      <div class="topbar-inner">
        <router-link to="/" class="brand">
          <span class="brand-logo" aria-hidden="true"></span>
          <span class="brand-wordmark"><span class="brand-name">微澜</span><span class="brand-sub">MICRORIPPLE</span></span>
        </router-link>

        <nav class="nav">
          <router-link to="/" class="nav-link" exact-active-class="active"><House aria-hidden="true" />时间线</router-link>
          <router-link to="/explore" class="nav-link" active-class="active"><Compass aria-hidden="true" />探索</router-link>
          <router-link to="/tide" class="nav-link" active-class="active"><TrendCharts aria-hidden="true" />潮汐榜</router-link>
          <router-link to="/mood" class="nav-link" active-class="active"><PartlyCloudy aria-hidden="true" />情绪气象</router-link>
          <router-link
            v-if="isLoggedIn && user?.role === 'admin'"
            to="/admin"
            class="nav-link"
            active-class="active"
          >管理</router-link>
        </nav>

        <div class="actions">
          <router-link
            v-if="isLoggedIn && user?.role !== 'admin'"
            to="/compose"
            class="compose-btn"
          ><Plus aria-hidden="true" />发微澜</router-link>
          <template v-if="isLoggedIn && user">
            <router-link to="/notifications" class="notification-link" :aria-label="notifications.unread ? `消息，${notifications.unread} 条未读` : '消息'">
              <Bell aria-hidden="true" />
              <span v-if="notifications.unread" class="notification-badge" aria-hidden="true">{{ notifications.unread > 99 ? '99+' : notifications.unread }}</span>
            </router-link>
            <router-link to="/profile" class="user-chip" :title="user.nickname"><span class="user-initial" aria-hidden="true">{{ user.nickname.slice(0, 1) }}</span><span class="user-name">{{ user.nickname }}</span></router-link>
            <el-button link type="primary" @click="logout">退出</el-button>
          </template>
          <template v-else>
            <router-link to="/login" class="user-chip">登录</router-link>
          </template>
        </div>
      </div>
    </header>

    <main class="main" :class="{ 'main-wide': wide }">
      <router-view />
    </main>

    <footer v-if="!bare" class="footer">微澜 · 捕捉每一朵思想涟漪</footer>
  </div>
</template>

<style scoped>
.notification-link { position: relative; display: grid; place-items: center; width: 34px; height: 34px; flex: 0 0 34px; border-radius: 9px; color: var(--wl-primary); }
.notification-link:hover, .notification-link.router-link-active { background: #e8f2eb; }
.notification-link svg { width: 19px; height: 19px; }
.notification-badge { position: absolute; top: -3px; right: -6px; min-width: 16px; padding: 1px 4px; border-radius: 10px; color: white; background: #a94638; text-align: center; font-size: 10px; line-height: 14px; }
</style>
