import { Link, Outlet, useLocation } from 'react-router-dom'
import { langToggleHref, useI18n } from '../i18n/useI18n'

function NavItem({
  to,
  label,
  active,
}: {
  to: string
  label: string
  active: boolean
}) {
  return (
    <Link
      to={to}
      className={
        active
          ? 'flex items-center gap-2 rounded-lg px-3 py-2.5 bg-brand-600 text-white'
          : 'flex items-center gap-2 rounded-lg px-3 py-2.5 text-slate-300 hover:bg-white/5 hover:text-white'
      }
    >
      {label}
    </Link>
  )
}

function JinjaLink({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <a
      href={href}
      className={
        active
          ? 'flex items-center gap-2 rounded-lg px-3 py-2.5 bg-brand-600 text-white'
          : 'flex items-center gap-2 rounded-lg px-3 py-2.5 text-slate-300 hover:bg-white/5 hover:text-white'
      }
    >
      {label}
    </a>
  )
}

export default function AdminShell() {
  const { t, lang } = useI18n()
  const location = useLocation()
  const path = location.pathname

  const pageMeta = (() => {
    if (path.endsWith('/devices') || path === '/devices') {
      return { heading: t('devices.heading'), sub: t('devices.sub') }
    }
    return { heading: t('dashboard.heading'), sub: t('dashboard.sub') }
  })()

  return (
    <div className="min-h-screen lg:flex bg-slate-100">
      <aside className="lg:w-64 shrink-0 border-b lg:border-b-0 lg:border-r border-slate-200 bg-ink-950 text-slate-100">
        <div className="px-5 py-6">
          <p className="font-display text-xl tracking-tight text-white">ElderShield</p>
          <p className="mt-1 text-xs uppercase tracking-[0.18em] text-brand-100/80">{t('brand.sub')}</p>
        </div>
        <nav className="px-3 pb-6 space-y-1 text-sm">
          <NavItem to="/" label={t('nav.dashboard')} active={path === '/' || path === ''} />
          <NavItem
            to="/devices"
            label={t('nav.devices')}
            active={path === '/devices' || path.endsWith('/devices')}
          />
          <JinjaLink href="/admin/ui/restrictions" label={t('nav.restrictions')} active={false} />
          <JinjaLink href="/admin/ui/call-rules" label={t('nav.call_rules')} active={false} />
          <JinjaLink href="/admin/ui/dns-denylist" label={t('nav.dns')} active={false} />
          <JinjaLink href="/admin/ui/allowlist" label={t('nav.allowlist')} active={false} />
          <JinjaLink href="/admin/ui/audit" label={t('nav.audit')} active={false} />
          <a
            href="/admin/ui/logout"
            className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-slate-400 hover:bg-white/5 hover:text-white"
          >
            {t('nav.logout')}
          </a>
        </nav>
        <div className="px-5 pb-6 space-y-2">
          <div className="flex gap-2 text-xs">
            <a
              href={langToggleHref('ko')}
              className={`rounded-md px-2 py-1 ${lang === 'ko' ? 'bg-brand-600 text-white' : 'bg-white/5 text-slate-300 hover:text-white'}`}
            >
              {t('lang.ko')}
            </a>
            <a
              href={langToggleHref('en')}
              className={`rounded-md px-2 py-1 ${lang === 'en' ? 'bg-brand-600 text-white' : 'bg-white/5 text-slate-300 hover:text-white'}`}
            >
              {t('lang.en')}
            </a>
          </div>
        </div>
      </aside>
      <div className="flex-1 min-w-0">
        <header className="border-b border-slate-200 bg-white/90 backdrop-blur px-6 py-4 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold text-ink-950">{pageMeta.heading}</h1>
            <p className="text-sm text-ink-600">{pageMeta.sub}</p>
          </div>
          <span className="inline-flex items-center rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700 ring-1 ring-inset ring-brand-100">
            {t('header.live')}
          </span>
        </header>
        <main className="px-6 py-8 max-w-6xl">
          <Outlet />
        </main>
      </div>
    </div>
  )
}