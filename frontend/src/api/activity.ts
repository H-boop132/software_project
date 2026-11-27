import request from './request'

export interface AuthorActivity {
  start_date: string
  end_date: string
  published_count: number
  received_echoes: number
  received_likes: number
  days: { date: string; count: number }[]
}

export function getMyActivity() {
  return request.get<unknown, AuthorActivity>('/users/me/activity')
}
