import request from './request'
import type { LikeOut } from './types'

export function setRippleLike(rippleId: number, liked: boolean) {
  const url = `/interactions/ripples/${rippleId}/like`
  return liked
    ? request.put<unknown, LikeOut>(url)
    : request.delete<unknown, LikeOut>(url)
}
