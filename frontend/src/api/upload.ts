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
