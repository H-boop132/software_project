import request from './request'

export interface UploadOut {
  url: string
}

/** 上传微澜配图，返回可访问的 URL（/uploads/...） */
export function uploadImage(file: File) {
  const form = new FormData()
  form.append('file', file)
  return request.post<unknown, UploadOut>('/upload', form)
}

/** 撤销上传：图片未被引用时才真正删除文件（移除图片/放弃草稿时调用） */
export function cleanupUpload(url: string) {
  return request.post<unknown, { deleted: boolean }>('/upload/cleanup', { url }, { silentError: true })
}
