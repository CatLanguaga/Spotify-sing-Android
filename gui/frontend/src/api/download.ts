/**
 * Trigger a browser download via a temporary <a download> anchor.
 *
 * Unlike `window.location.href = url`, this does NOT navigate the page, so
 * many downloads can be triggered back-to-back without each one cancelling
 * the previous (the bug that broke "Descargar todo").
 */
export function triggerBrowserDownload(url: string): void {
  const a = document.createElement('a')
  a.href = url
  a.download = ''
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
