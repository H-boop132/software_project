import axios from 'axios'
import { ElMessage } from 'element-plus'

declare module 'axios' {
  interface AxiosRequestConfig {
    silentError?: boolean
  }
}

// 统一请求实例：走 Vite 代理 /api → http://127.0.0.1:8000
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 10000,
})

const FIELD_LABELS: Record<string, string> = {
  username: '用户名',
  nickname: '昵称',
  password: '密码',
  old_password: '原密码',
  new_password: '新密码',
  bio: '签名',
  avatar_url: '头像',
  mood_tone: '情绪色调',
  content: '内容',
  images: '配图',
  reason: '理由',
  note: '备注',
  keyword: '关键词',
  url: '图片地址',
  ripple_id: '微澜',
  parent_id: '父回声',
}

function fieldLabel(loc: unknown): string {
  if (!Array.isArray(loc)) return ''
  const parts = loc.filter((part) => part !== 'body' && part !== 'query' && part !== 'path')
  const last = String(parts[parts.length - 1] ?? '')
  return FIELD_LABELS[last] || last || '参数'
}

/** 把 FastAPI 的 422 detail（字符串或校验错误数组）转成一句可读中文，避免提示框空白 */
function formatDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail.trim()
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === 'string') return item
        const label = fieldLabel(item?.loc)
        const type = String(item?.type || '')
        const ctx = item?.ctx || {}
        const msg = String(item?.msg || '').replace(/^Value error, /, '')
        if (type === 'missing') return `请填写${label}`
        if (type === 'string_too_short') return `${label}至少 ${ctx.min_length} 个字符`
        if (type === 'string_too_long') return `${label}最多 ${ctx.max_length} 个字符`
        if (/^(int|float|bool)_parsing$/.test(type) || type === 'string_type') return `${label}格式不正确`
        if (type === 'value_error') return msg || `${label}填写有误`
        if (type === 'greater_than_equal') return `${label}不能小于 ${ctx.ge}`
        if (type === 'less_than_equal') return `${label}不能大于 ${ctx.le}`
        return msg ? `${label}：${msg}` : `${label}填写有误`
      })
      .filter(Boolean)
    return parts.join('；')
  }
  if (detail && typeof detail === 'object') {
    const message = (detail as { msg?: unknown; message?: unknown }).msg ?? (detail as { message?: unknown }).message
    if (typeof message === 'string') return message
  }
  return ''
}

// 请求拦截：自动携带 JWT
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('weilan_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：统一错误提示；401 时清除本地 token 并回登录页
request.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const detail = err.response?.data?.detail
    if (err.response?.status === 401) {
      localStorage.removeItem('weilan_token')
      // 登录接口自身的 401（密码错误）不跳转，其余均视为会话失效
      const reqUrl: string = err.config?.url || ''
      if (!reqUrl.includes('/auth/login')) {
        window.location.href = '/login'
      }
    }
    if (!err.config?.silentError) {
      const message = formatDetail(detail) || err.message || '网络错误'
      ElMessage.error(message)
    }
    return Promise.reject(err)
  },
)

export default request
