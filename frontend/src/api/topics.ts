import request from './request'
import type { TopicOut } from './types'

export interface TopicDetail extends TopicOut {
  is_subscribed: boolean
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
