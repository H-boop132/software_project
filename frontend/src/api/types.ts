/** 后端 API 数据类型定义（与 backend/app/schemas 对应） */

export interface UserOut {
  id: number
  username: string
  nickname: string
  avatar_url: string | null
  bio: string | null
  mood_tone: string | null
  hide_following: boolean
  hide_followers: boolean
  hide_likes: boolean
  hide_collections: boolean
  role: string
  ban_status: string
  ban_until: string | null
  ban_reason: string | null
  created_at: string
}

export interface UserBrief {
  id: number
  nickname: string
  avatar_url: string | null
  bio: string | null
  mood_tone: string | null
}

export interface EmotionOut {
  code: string
  name: string
  color: string
}

export interface UserProfile {
  id: number
  username: string
  nickname: string
  avatar_url: string | null
  bio: string | null
  mood_tone: string | null
  created_at: string
  follower_count: number
  following_count: number
  is_following: boolean
  follows_you: boolean
  hide_following: boolean
  hide_followers: boolean
  hide_likes: boolean
  hide_collections: boolean
}

export interface UserPage {
  items: UserProfile[]
  total: number
  limit: number
  offset: number
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
  user: UserBrief
  status: string
  images: string[]
  created_at: string
  like_count: number
  is_liked: boolean
  is_collected: boolean
  echo_count: number
}

export type MyRippleStatus = 'published' | 'banned' | 'pending'

export interface MyRippleOut extends RippleOut {
  latest_review: { action: 'ban' | 'approve' | 'reject' | 'appeal_approve' | 'appeal_reject'; reason: string | null; created_at: string } | null
  latest_appeal: AppealBrief | null
}

export type ReportReason = 'spam' | 'abuse' | 'misinformation' | 'illegal' | 'other'
export type ReportStatus = 'pending' | 'uphold' | 'dismissed'
export type AppealStatus = 'pending' | 'approved' | 'rejected'

export interface AppealBrief {
  id: number
  status: AppealStatus
  reason: string
  handle_note: string | null
  created_at: string
  handled_at: string | null
}

export interface ReportOut {
  id: number
  ripple_id: number
  reporter_id: number
  reporter_name: string
  reason_code: ReportReason
  detail: string | null
  status: ReportStatus
  handle_note: string | null
  created_at: string
  handled_at: string | null
  ripple_content: string
  ripple_status: string
  author_id: number
  author_name: string
}

export interface AppealOut {
  id: number
  ripple_id: number
  user_id: number
  user_name: string
  reason: string
  status: AppealStatus
  handle_note: string | null
  created_at: string
  handled_at: string | null
  ripple_content: string
  ripple_status: string
  author_id: number
  author_name: string
}

export interface ReportPage {
  items: ReportOut[]
  total: number
  limit: number
  offset: number
}

export interface AppealPage {
  items: AppealOut[]
  total: number
  limit: number
  offset: number
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

export interface CollectionPage {
  items: RippleOut[]
  total: number
  limit: number
  offset: number
}

export interface LikePage {
  items: RippleOut[]
  total: number
  limit: number
  offset: number
}

export interface EchoLikeOut {
  echo_id: number
  is_liked: boolean
  like_count: number
}

export interface EchoOut {
  id: number
  content: string
  emotion: EmotionOut | null
  user: UserBrief
  parent_echo_id: number | null
  reply_to_user: UserBrief | null
  like_count: number
  is_liked: boolean
  created_at: string
  children: EchoOut[]
}

export interface EchoPayload {
  content: string
  parent_echo_id?: number | null
  emotion_code?: string | null
}

export interface EchoDeleteOut {
  ripple_id: number
  echo_count: number
}

export interface RippleDetail {
  ripple: RippleOut
  echoes: EchoOut[]
  report_status: ReportStatus | null
  latest_appeal: AppealBrief | null
}

export interface TideOut {
  topic: TopicOut
  heat: number
  ripple_count: number
  echo_count: number
  trend: string
  recent_activity: number
  previous_activity: number
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
