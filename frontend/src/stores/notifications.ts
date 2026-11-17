import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { fetchUnreadCount } from '@/api/notifications'
import { useUserStore } from '@/stores/user'

export const useNotificationStore = defineStore('notifications', () => {
  const user = useUserStore()
  const unread = ref(0)
  let version = 0

  function setUnread(count: number) {
    version++
    unread.value = count
  }

  async function refresh() {
    if (!user.token) return
    const current = ++version
    try {
      const { unread_count } = await fetchUnreadCount()
      if (current === version) unread.value = unread_count
    } catch { /* 下次轮询重试 */ }
  }

  watch(() => user.token, () => {
    setUnread(0)
    void refresh()
  }, { immediate: true })

  return { unread, setUnread, refresh }
})
