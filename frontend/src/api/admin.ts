import request from './request'
import type { RippleOut, UserOut } from './types'

export interface AdminStats {
  users: number
  ripples: number
  echoes: number
  likes: number
  topics: number
}

export interface BanUserPayload {
  duration_days?: number | null
  reason?: string | null
}

export interface ReviewActionPayload {
  reason?: string | null
}

export function getAdminStats() {
  return request.get<unknown, AdminStats>('/admin/stats')
}

export function listAdminUsers(params: { limit?: number; offset?: number } = {}) {
  return request.get<unknown, UserOut[]>('/admin/users', { params })
}

/** 全部微澜（含封禁/待审核状态） */
export function listAdminRipples(params: { limit?: number; offset?: number } = {}) {
  return request.get<unknown, RippleOut[]>('/admin/ripples', { params })
}

/** 待审核队列 */
export function listPendingReviews(params: { limit?: number; offset?: number } = {}) {
  return request.get<unknown, RippleOut[]>('/admin/reviews', { params })
}

/** 封禁微澜（下架为仅作者可见） */
export function banRipple(id: number, data: ReviewActionPayload = {}) {
  return request.post<unknown, RippleOut>(`/admin/ripples/${id}/ban`, data)
}

/** 审核通过 */
export function approveRipple(id: number) {
  return request.post<unknown, RippleOut>(`/admin/ripples/${id}/approve`)
}

/** 审核驳回 */
export function rejectRipple(id: number, data: ReviewActionPayload = {}) {
  return request.post<unknown, RippleOut>(`/admin/ripples/${id}/reject`, data)
}

/** 封禁用户（duration_days 不填=永久） */
export function banUser(id: number, data: BanUserPayload) {
  return request.post<unknown, UserOut>(`/admin/users/${id}/ban`, data)
}

/** 解封用户 */
export function unbanUser(id: number) {
  return request.post<unknown, UserOut>(`/admin/users/${id}/unban`)
}

export function deleteRipple(id: number) {
  return request.delete<unknown, { ok: boolean }>(`/admin/ripples/${id}`)
}
