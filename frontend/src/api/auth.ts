import request from './request'
import type { TokenResponse, UserOut } from './types'

export function login(username: string, password: string) {
  return request.post<unknown, TokenResponse>('/auth/login', { username, password })
}

export function register(username: string, nickname: string, password: string) {
  return request.post<unknown, TokenResponse>('/auth/register', { username, nickname, password })
}

export function fetchMe() {
  return request.get<unknown, UserOut>('/users/me')
}
