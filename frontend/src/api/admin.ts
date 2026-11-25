import request from './request'
import type { AppealOut, AppealPage, AppealStatus, ReportOut, ReportPage, ReportStatus, RippleOut, UserOut } from './types'

export interface AdminStats {
  users: number
  ripples: number
  echoes: number
  likes: number
  topics: number
  pending: number
  banned_users: number
  banned_ripples: number
  pending_reports: number
  pending_appeals: number
}

export type AdminUserStatus = 'active' | 'banned'
export type AdminRippleStatus = 'published' | 'banned' | 'pending' | 'deleted'

export interface ReviewLog {
  id: number
  ripple_id: number
  action: 'ban' | 'approve' | 'reject' | 'appeal_approve' | 'appeal_reject'
  reason: string | null
  reviewer_id: number
  reviewer_name: string
  author_id: number
  author_name: string
  content: string
  created_at: string
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

/** 用户列表：可按昵称/用户名搜索、按封禁状态筛选 */
export function listAdminUsers(params: { limit?: number; offset?: number; keyword?: string; status?: AdminUserStatus } = {}) {
  return request.get<unknown, UserOut[]>('/admin/users', { params })
}

/** 全部微澜（含封禁/待审核状态），可按状态筛选 */
export function listAdminRipples(params: { limit?: number; offset?: number; keyword?: string; status?: AdminRippleStatus } = {}) {
  return request.get<unknown, RippleOut[]>('/admin/ripples', { params })
}

/** 待审核队列 */
export function listPendingReviews(params: { limit?: number; offset?: number } = {}) {
  return request.get<unknown, RippleOut[]>('/admin/reviews', { params })
}

/** 审核记录（谁在何时对哪条内容做了什么处理） */
export function getReviewHistory(params: { limit?: number; offset?: number } = {}) {
  return request.get<unknown, ReviewLog[]>('/admin/reviews/history', { params })
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

/** 举报队列（默认待处理） */
export function listAdminReports(params: { limit?: number; offset?: number; status?: ReportStatus } = {}) {
  return request.get<unknown, ReportPage>('/admin/reports', { params })
}

export function handleAdminReport(id: number, data: { action: 'uphold' | 'dismiss'; note?: string | null }) {
  return request.post<unknown, ReportOut>(`/admin/reports/${id}/handle`, data)
}

/** 申诉队列（默认待处理） */
export function listAdminAppeals(params: { limit?: number; offset?: number; status?: AppealStatus } = {}) {
  return request.get<unknown, AppealPage>('/admin/appeals', { params })
}

export function handleAdminAppeal(id: number, data: { action: 'approve' | 'reject'; note?: string | null }) {
  return request.post<unknown, AppealOut>(`/admin/appeals/${id}/handle`, data)
}
