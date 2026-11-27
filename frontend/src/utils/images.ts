export function thumbnailUrl(url: string) {
  const name = url.match(/^\/uploads\/([A-Za-z0-9_-]{1,128}\.(?:jpe?g|png|webp))$/i)?.[1]
  return name ? `/api/v1/upload/thumbnail/${encodeURIComponent(name)}` : url
}

export function restoreOriginalImage(event: Event, original: string) {
  const image = event.target as HTMLImageElement
  const originalUrl = new URL(original, window.location.origin).href
  if (image.src !== originalUrl) image.src = originalUrl
}
