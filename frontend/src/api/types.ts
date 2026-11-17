/** 后端 API 数据类型定义（与 backend/app/schemas 对应） */

export interface UserOut {
  id: number
  username: string
  nickname: string
  avatar_url: string | null
  bio: string | null
  mood_tone: string | null
  role: string
  ban_status: string
  ban_until: string | null
  ban_reason: string | null
  created_at: string
}

export interface EmotionOut {
  code: string
  name: string
  color: string
}

export interface TopicOut {
  id: number
  name: string
  slug: string
  description: string | null
}

export interface RippleOut {
  id: number
  content: string
  emotion: EmotionOut | null
  topic: TopicOut | null
  user: UserOut
  status: string
  images: string[]
  created_at: string
  like_count: number
  is_liked: boolean
  is_collected: boolean
  echo_count: number
}

export interface LikeOut {
  ripple_id: number
  is_liked: boolean
  like_count: number
}

export interface CollectionOut {
  ripple_id: number
  is_collected: boolean
}

export interface EchoOut {
  id: number
  content: string
  emotion: EmotionOut | null
  user: UserOut
  parent_echo_id: number | null
  created_at: string
  children: EchoOut[]
}

export interface RippleDetail {
  ripple: RippleOut
  echoes: EchoOut[]
}

export interface TideOut {
  topic: TopicOut
  heat: number
  ripple_count: number
  echo_count: number
  trend: string
}

export interface MoodOut {
  code: string
  name: string
  color: string
  count: number
  percent: number
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserOut
}
