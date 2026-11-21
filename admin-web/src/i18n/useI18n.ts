import { useCallback, useMemo, useState } from 'react'
import en from './en.json'
import ko from './ko.json'

export type Lang = 'ko' | 'en'

const LANG_COOKIE = 'es_admin_lang'

const catalogs: Record<Lang, Record<string, string>> = { ko, en }

function readLangFromCookie(): Lang {
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${LANG_COOKIE}=([^;]+)`))
  const value = match?.[1]?.trim()
  return value === 'en' ? 'en' : 'ko'
}

export function useI18n() {
  const [lang, setLangState] = useState<Lang>(readLangFromCookie)

  const t = useCallback(
    (key: string): string => {
      return catalogs[lang][key] ?? catalogs.ko[key] ?? key
    },
    [lang],
  )

  const setLang = useCallback((next: Lang) => {
    setLangState(next)
  }, [])

  return useMemo(() => ({ lang, t, setLang }), [lang, t, setLang])
}

export function langToggleHref(set: Lang): string {
  const next = window.location.pathname + window.location.search
  return `/admin/ui/lang?set=${set}&next=${encodeURIComponent(next)}`
}