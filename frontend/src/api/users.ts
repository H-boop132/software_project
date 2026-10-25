import request from './request'
import type { RippleOut, UserPage, UserProfile } from './types'

export function fetchUserProfile(id: number) {
  return request.get<unknown, UserProfile>(`/users/${id}`)
}

export function setUserFollow(id: number, following: boolean) {
  return following
    ? request.put<unknown, UserProfile>(`/users/${id}/follow`)
    : request.delete<unknown, UserProfile>(`/users/${id}/follow`)
}

export function fetchUserRelations(id: number, kind: 'following' | 'followers', params: { limit: number; offset: number }) {
  return request.get<unknown, UserPage>(`/users/${id}/${kind}`, { params })
}

export function fetchUserRipples(id: number, params: { limit: number; offset: number }) {
  return request.get<unknown, RippleOut[]>(`/users/${id}/ripples`, { params })
}
