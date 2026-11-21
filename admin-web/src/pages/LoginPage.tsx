import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import { langToggleHref, useI18n } from '../i18n/useI18n'

export default function LoginPage() {
  const { t, lang } = useI18n()
  const navigate = useNavigate()
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const result = await login(apiKey.trim())
      if (result.ok) {
        navigate('/', { replace: true })
        return
      }
      setError(
        result.error === 'invalid'
          ? t('login.error_invalid')
          : result.error === 'rate'
            ? t('login.error_rate')
            : t('login.error_generic'),
      )
    } catch {
      setError(t('login.error_generic'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen grid place-items-center px-4 py-12 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-brand-50 via-slate-100 to-slate-200">
      <div className="absolute top-4 right-4 flex gap-2 text-xs">
        <a
          href={langToggleHref('ko')}
          className={`rounded-md px-2 py-1 ${lang === 'ko' ? 'bg-brand-600 text-white' : 'bg-white/80 text-ink-800 ring-1 ring-slate-200'}`}
        >
          {t('lang.ko')}
        </a>
        <a
          href={langToggleHref('en')}
          className={`rounded-md px-2 py-1 ${lang === 'en' ? 'bg-brand-600 text-white' : 'bg-white/80 text-ink-800 ring-1 ring-slate-200'}`}
        >
          {t('lang.en')}
        </a>
      </div>
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <p className="font-display text-3xl text-brand-700 tracking-tight">ElderShield</p>
          <p className="mt-2 text-sm text-ink-600">{t('brand.sub')}</p>
        </div>
        <form
          onSubmit={onSubmit}
          className="rounded-2xl bg-white shadow-panel ring-1 ring-slate-200/80 p-8 space-y-5"
        >
          <div>
            <h2 className="text-lg font-semibold text-ink-950">{t('login.title')}</h2>
            <p className="mt-1 text-sm text-ink-600">{t('login.sub')}</p>
          </div>
          <div>
            <label htmlFor="apiKey" className="block text-sm font-medium text-ink-800 mb-1.5">
              {t('login.api_key')}
            </label>
            <input
              id="apiKey"
              type="password"
              autoComplete="current-password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm text-ink-950 placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/25"
              required
            />
          </div>
          {error ? (
            <p className="text-sm text-red-700 bg-red-50 border border-red-100 rounded-lg px-3 py-2" role="alert">
              {error}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60 transition-colors"
          >
            {t('login.submit')}
          </button>
        </form>
      </div>
    </div>
  )
}