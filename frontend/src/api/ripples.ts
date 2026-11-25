import request from './request'
import type { AppealOut, EchoDeleteOut, EchoLikeOut, EchoOut, EchoPayload, EmotionOut, MoodOut, MyRippleOut, MyRippleStatus, ReportOut, ReportReason, RippleDetail, RippleOut, TideOut } from './types'

export interface RipplePayload {
  content: string
  topic_id?: number | null
  emotion_code?: string | null
  images?: string[]
}

export interface RippleListParams {
  topic_id?: number
  keyword?: string
  start?: string
  end?: string
  limit?: number
  offset?: number
  emotion_code?: string
  has_images?: boolean
  sort?: 'latest' | 'discussed' | 'liked'
}

export function listRipples(params: RippleListParams = {}) {
  return request.get<unknown, RippleOut[]>('/ripples', { params })
}

export function listFollowingRipples(params: RippleListParams = {}) {
  return request.get<unknown, RippleOut[]>('/ripples/following', { params })
}

export function listSubscribedTopicRipples(params: RippleListParams = {}) {
  return request.get<unknown, RippleOut[]>('/ripples/subscribed-topics', { params })
}

export function createRipple(data: RipplePayload) {
  return request.post<unknown, RippleOut>('/ripples', data)
}

export function fetchMyRipples(params: { limit?: number; offset?: number; keyword?: string; status?: MyRippleStatus } = {}) {
  return request.get<unknown, MyRippleOut[]>('/ripples/mine', { params })
}

export function updateRipple(id: number, data: RipplePayload & { expected_status?: 'published' | 'banned' }) {
  return request.put<unknown, RippleOut>(`/ripples/${id}`, data)
}

export function deleteMyRipple(id: number) {
  return request.delete<unknown, void>(`/ripples/${id}`)
}

export function getRippleDetail(id: number) {
  return request.get<unknown, RippleDetail>(`/ripples/${id}`)
}

/** 举报公开微澜 */
export function reportRipple(id: number, data: { reason_code: ReportReason; detail?: string | null }) {
  return request.post<unknown, ReportOut>(`/ripples/${id}/report`, data)
}

/** 被下架微澜的作者申诉 */
export function appealRipple(id: number, data: { reason: string }) {
  return request.post<unknown, AppealOut>(`/ripples/${id}/appeal`, data)
}

export function createEcho(rippleId: number, data: EchoPayload) {
  return request.post<unknown, EchoOut>(`/ripples/${rippleId}/echoes`, data)
}

export function deleteEcho(echoId: number) {
  return request.delete<unknown, EchoDeleteOut>(`/echoes/${echoId}`)
}

export function setEchoLike(echoId: number, liked: boolean) {
  return liked
    ? request.put<unknown, EchoLikeOut>(`/echoes/${echoId}/like`)
    : request.delete<unknown, EchoLikeOut>(`/echoes/${echoId}/like`)
}

export function getHotTides() {
  return request.get<unknown, TideOut[]>('/tides/hot')
}

export function getMoodSummary() {
  return request.get<unknown, MoodOut[]>('/moods/summary')
}

/** 全部可选情绪色调（资料编辑下拉用） */
export function getMoodTones() {
  return request.get<unknown, EmotionOut[]>('/moods/tones')
}
