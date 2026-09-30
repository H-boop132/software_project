import axios from 'axios'
import { ElMessage } from 'element-plus'

// 统一请求实例：走 Vite 代理 /api → http://127.0.0.1:8000
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 10000,
})

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
    ElMessage.error(detail || err.message || '网络错误')
    return Promise.reject(err)
  },
)

export default request
