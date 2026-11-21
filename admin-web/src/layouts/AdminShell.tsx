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
    if (path.startsWith('/incidents/')) {
      return { heading: t('incident.heading'), sub: t('incident.sub') }
    }
    if (path.startsWith('/devices/') && path !== '/devices') {
      return { heading: t('device.heading'), sub: t('device.sub') }
    }
    if (path === '/devices' || path.endsWith('/devices')) {
      return { heading: t('devices.heading'), sub: t('devices.sub') }
    }
    if (path === '/audit' || path.endsWith('/audit')) {
      return { heading: t('audit.heading'), sub: t('audit.sub') }
    }
    if (path === '/dns-logs' || path.endsWith('/dns-logs')) {
      return { heading: t('dns_logs.heading'), sub: t('dns_logs.sub') }
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
            active={path === '/devices' || path.startsWith('/devices/')}
          />
          <NavItem to="/audit" label={t('nav.audit')} active={path === '/audit'} />
          <NavItem to="/dns-logs" label={t('nav.dns_logs')} active={path === '/dns-logs'} />
          <JinjaLink href="/admin/ui/restrictions" label={t('nav.restrictions')} active={false} />
          <JinjaLink href="/admin/ui/call-rules" label={t('nav.call_rules')} active={false} />
          <JinjaLink href="/admin/ui/dns-denylist" label={t('nav.dns')} active={false} />
          <JinjaLink href="/admin/ui/allowlist" label={t('nav.allowlist')} active={false} />
          <a
            href="/admin/ui/logout"
            className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-slate-400 hover:bg-white/5 hover:text-white"
          >
            {t('nav.logout')}
          </a>
        </nav>
        <div className="px-5 pb-6 space-y-2">
          <a
            href={langToggleHref(lang === 'ko' ? 'en' : 'ko')}
            className="text-xs text-slate-400 hover:text-white"
          >
            {lang === 'ko' ? t('lang.en') : t('lang.ko')}
          </a>
        </div>
      </aside>
      <main className="flex-1 min-w-0">
        <header className="border-b border-slate-200 bg-white/80 backdrop-blur px-6 py-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h1 className="font-display text-2xl text-ink-950 tracking-tight">{pageMeta.heading}</h1>
              <p className="mt-1 text-sm text-ink-600">{pageMeta.sub}</p>
            </div>
            <span className="hidden sm:inline-flex items-center rounded-full bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200 px-2.5 py-1 text-xs font-semibold">
              {t('header.live')}
            </span>
          </div>
        </header>
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
