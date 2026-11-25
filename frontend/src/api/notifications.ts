import request from './request'

export type NotificationKind = 'echo' | 'reply' | 'follow' | 'moderation' | 'like' | 'collection' | 'echo_like' | 'report' | 'appeal'

export interface NotificationItem {
  id: number
  kind: NotificationKind
  actor_id: number
  actor_name: string
  ripple_id: number | null
  echo_id: number | null
  preview: string | null
  /** 内容处理/举报/申诉说明 */
  note: string | null
  created_at: string
  read_at: string | null
}

export interface NotificationPage {
  items: NotificationItem[]
  next_before: number | null
  unread_count: number
}

export interface UnreadCount { unread_count: number }

export function fetchNotifications(params: { kind?: NotificationKind; unread_only?: boolean; before?: number }) {
  return request.get<unknown, NotificationPage>('/notifications', { params })
}

export function fetchUnreadCount() {
  return request.get<unknown, UnreadCount>('/notifications/unread-count', { silentError: true })
}

export function markNotificationRead(id: number) {
  return request.put<unknown, UnreadCount>(`/notifications/${id}/read`)
}

export function markAllNotificationsRead() {
  return request.put<unknown, UnreadCount>('/notifications/read-all')
}
