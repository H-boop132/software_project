import request from './request'

export type SupportKind = 'reports' | 'appeals'
export type SupportStatus = 'pending' | 'uphold' | 'dismissed' | 'approved' | 'rejected'
export interface SupportItem {
  id: number
  ripple_id: number
  ripple_preview: string | null
  can_open: boolean
  reason_code?: string
  detail?: string | null
  reason?: string
  status: SupportStatus
  handle_note: string | null
  created_at: string
  handled_at: string | null
}

export interface SupportPage {
  items: SupportItem[]
  total: number
  limit: number
  offset: number
}

export function getMySupport(kind: SupportKind, params: { status?: string; limit: number; offset: number }) {
  return request.get<unknown, SupportPage>(`/users/me/${kind}`, { params })
}
