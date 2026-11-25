import request from './request'
import type { RippleOut, UserOut, UserPage, UserProfile } from './types'

export interface UserUpdatePayload {
  nickname?: string
  bio?: string | null
  avatar_url?: string | null
  mood_tone?: string | null
}

export function fetchUserProfile(id: number) {
  return request.get<unknown, UserProfile>(`/users/${id}`)
}

export function updateMyProfile(data: UserUpdatePayload) {
  return request.put<unknown, UserOut>('/users/me', data)
}

/** 修改密码（校验原密码，新密码 ≥6 位） */
export function changeMyPassword(data: { old_password: string; new_password: string }) {
  return request.put<unknown, { ok: boolean }>('/users/me/password', data)
}

/** 注销账号（需密码确认，账号与内容一并删除） */
export function deleteMyAccount(data: { password: string }) {
  return request.post<unknown, { ok: boolean }>('/users/me/delete', data)
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
