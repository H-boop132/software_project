import request from './request'
import type { MoodOut, RippleDetail, RippleOut, TideOut } from './types'

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
}

export function listRipples(params: RippleListParams = {}) {
  return request.get<unknown, RippleOut[]>('/ripples', { params })
}

export function createRipple(data: RipplePayload) {
  return request.post<unknown, RippleOut>('/ripples', data)
}

export function fetchMyRipples(params: { limit?: number; offset?: number } = {}) {
  return request.get<unknown, RippleOut[]>('/ripples/mine', { params })
}

/** 修改被封禁的微澜并重新提交审核 */
export function updateRipple(id: number, data: RipplePayload) {
  return request.put<unknown, RippleOut>(`/ripples/${id}`, data)
}

export function getRippleDetail(id: number) {
  return request.get<unknown, RippleDetail>(`/ripples/${id}`)
}

export function getHotTides() {
  return request.get<unknown, TideOut[]>('/tides/hot')
}

export function getMoodSummary() {
  return request.get<unknown, MoodOut[]>('/moods/summary')
}
