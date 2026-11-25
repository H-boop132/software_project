import { ElMessage } from 'element-plus'

/** 全站轻提示统一时长：1 秒，短于 Element Plus 默认 3 秒，避免遮挡页面。 */
const TOAST_DURATION = 1000

type ToastKind = 'success' | 'warning' | 'info' | 'error'

function show(kind: ToastKind, message: string) {
  ElMessage({ type: kind, message, duration: TOAST_DURATION, grouping: true })
}

export const toast = {
  success: (message: string) => show('success', message),
  warning: (message: string) => show('warning', message),
  info: (message: string) => show('info', message),
  error: (message: string) => show('error', message),
}
