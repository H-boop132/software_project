import request from './request'
import type { TopicOut } from './types'

export interface TopicDetail extends TopicOut {
  is_subscribed: boolean
}

/** 全部话题（发布页下拉、话题筛选等；无需登录） */
export function listTopics() {
  return request.get<unknown, TopicOut[]>('/topics')
}

export function getTopic(id: number) {
  return request.get<unknown, TopicDetail>(`/topics/${id}`, { silentError: true })
}

export function getSubscribedTopics() {
  return request.get<unknown, TopicOut[]>('/topics/subscribed')
}

export function setTopicSubscription(id: number, subscribe: boolean) {
  const path = `/topics/${id}/subscription`
  return subscribe ? request.put(path) : request.delete(path)
}
