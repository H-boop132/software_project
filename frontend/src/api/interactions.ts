import request from './request'
import type { CollectionOut, CollectionPage, LikeOut } from './types'

export function setRippleLike(rippleId: number, liked: boolean) {
  const url = `/interactions/ripples/${rippleId}/like`
  return liked
    ? request.put<unknown, LikeOut>(url)
    : request.delete<unknown, LikeOut>(url)
}

export function setRippleCollection(rippleId: number, collected: boolean) {
  const url = `/interactions/ripples/${rippleId}/collection`
  return collected
    ? request.put<unknown, CollectionOut>(url)
    : request.delete<unknown, CollectionOut>(url)
}

export function fetchMyCollections(params: { limit?: number; offset?: number } = {}) {
  return request.get<unknown, CollectionPage>('/interactions/collections', { params })
}
