import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { login as apiLogin, register as apiRegister, fetchMe } from '@/api/auth'
import type { UserOut } from '@/api/types'

const TOKEN_KEY = 'weilan_token'

export const useUserStore = defineStore('user', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<UserOut | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  async function login(username: string, password: string) {
    const res = await apiLogin(username, password)
    token.value = res.access_token
    user.value = res.user
    localStorage.setItem(TOKEN_KEY, res.access_token)
  }

  async function register(username: string, nickname: string, password: string) {
    const res = await apiRegister(username, nickname, password)
    token.value = res.access_token
    user.value = res.user
    localStorage.setItem(TOKEN_KEY, res.access_token)
  }

  async function refreshMe() {
    if (!token.value) return
    try {
      user.value = await fetchMe()
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
  }

  return { token, user, isLoggedIn, login, register, refreshMe, logout }
})
