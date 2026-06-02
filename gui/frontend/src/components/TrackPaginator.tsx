import { useState } from 'react'
import { usePreferences } from '../preferences'

interface TrackPaginatorProps {
  currentPage: number
  totalPages: number
  total: number
  loading: boolean
  onPageChange: (page: number) => void
}

const PAGE_SIZE = 50

function pageNumbers(current: number, total: number): (number | '...')[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)

  if (current <= 4) {
    const pages: (number | '...')[] = []
    for (let i = 1; i <= Math.min(5, total - 1); i++) pages.push(i)
    pages.push('...')
    pages.push(total)
    return pages
  }

  if (current >= total - 3) {
    const pages: (number | '...')[] = [1, '...']
    for (let i = Math.max(2, total - 4); i <= total; i++) pages.push(i)
    return pages
  }

  return [1, '...', current - 1, current, current + 1, '...', total]
}

export function TrackPaginator({ currentPage, totalPages, total, loading, onPageChange }: TrackPaginatorProps) {
  const { t } = usePreferences()
  const from = (currentPage - 1) * PAGE_SIZE + 1
  const to = Math.min(currentPage * PAGE_SIZE, total)
  const pages = pageNumbers(currentPage, totalPages)
  const [jump, setJump] = useState('')

  const goToJump = () => {
    if (!/^\d+$/.test(jump)) return
    const target = Math.min(totalPages, Math.max(1, Number(jump)))
    onPageChange(target)
    setJump('')
  }

  return (
    <nav className="track-paginator" aria-label={t('pgNavAria')}>
      <div className="paginator-info">
        {loading
          ? <span className="paginator-loading"><span className="spinner" /> {t('pgLoading')(currentPage)}</span>
          : <span>{t('pgPageOf')(currentPage, totalPages, from, to, total)}</span>
        }
      </div>
      <div className="paginator-controls">
        <button
          type="button"
          className="paginator-btn"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1 || loading}
          aria-label={t('pgPrevAria')}
        >
          {t('pgPrev')}
        </button>

        <div className="paginator-pages">
          {pages.map((p, i) =>
            p === '...'
              ? <span key={`ellipsis-${i}`} className="paginator-ellipsis">…</span>
              : <button
                  key={p}
                  type="button"
                  className={`paginator-page ${p === currentPage ? 'active' : ''}`}
                  onClick={() => onPageChange(p as number)}
                  disabled={loading}
                  aria-current={p === currentPage ? 'page' : undefined}
                >
                  {p}
                </button>
          )}
        </div>

        <button
          type="button"
          className="paginator-btn"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages || loading}
          aria-label={t('pgNextAria')}
        >
          {t('pgNext')}
        </button>

        <div className="paginator-jump">
          <input
            type="number"
            min={1}
            max={totalPages}
            value={jump}
            placeholder={t('pgJumpPlaceholder')}
            disabled={loading}
            onChange={e => setJump(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') goToJump() }}
            aria-label={t('pgGoAria')}
          />
          <button
            type="button"
            className="paginator-page"
            onClick={goToJump}
            disabled={loading || !jump}
          >
            {t('pgGo')}
          </button>
        </div>
      </div>
    </nav>
  )
}
