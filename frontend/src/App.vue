<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { isLoggedIn, user } = storeToRefs(userStore)

// 裸页面（如登录页）：不显示顶栏与页脚
const bare = computed(() => route.meta.bare === true)

// 进入页面时恢复登录态（刷新后 user 信息需要重新拉取）
onMounted(() => {
  userStore.refreshMe()
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
          <span class="brand-logo">🌊</span>
          <span class="brand-name">微澜</span>
          <span class="brand-sub">Microripple</span>
        </router-link>

        <nav class="nav">
          <router-link to="/" class="nav-link" exact-active-class="active">时间线</router-link>
          <router-link to="/tide" class="nav-link" active-class="active">潮汐榜</router-link>
          <router-link to="/mood" class="nav-link" active-class="active">情绪气象</router-link>
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
          >+ 发微澜</router-link>
          <template v-if="isLoggedIn && user">
            <router-link to="/profile" class="user-chip">{{ user.nickname }}</router-link>
            <el-button link type="primary" @click="logout">退出</el-button>
          </template>
          <template v-else>
            <router-link to="/login" class="user-chip">登录</router-link>
          </template>
        </div>
      </div>
    </header>

    <main class="main">
      <router-view />
    </main>

    <footer v-if="!bare" class="footer">微澜 · 捕捉每一朵思想涟漪</footer>
  </div>
</template>
