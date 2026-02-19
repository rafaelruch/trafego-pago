'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { authApi, approvalsApi } from '@/lib/api'
import { BarChart3, Bot, CheckSquare, FileText, Settings, LogOut, Menu, X } from 'lucide-react'

const NAV = [
  { href: '/', label: 'Dashboard', icon: BarChart3 },
  { href: '/campaigns', label: 'Campanhas', icon: FileText },
  { href: '/approvals', label: 'Aprovações', icon: CheckSquare, badge: true },
  { href: '/ai', label: 'Chat IA', icon: Bot },
  { href: '/settings', label: 'Configurações', icon: Settings },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const { data: user, isError } = useQuery({
    queryKey: ['me'],
    queryFn: () => authApi.getMe().then((r) => r.data),
  })

  const { data: pendingData } = useQuery({
    queryKey: ['pending-count'],
    queryFn: () => approvalsApi.pendingCount().then((r) => r.data),
    refetchInterval: 30_000,
  })

  useEffect(() => {
    if (isError) router.push('/login')
  }, [isError, router])

  const handleLogout = () => {
    localStorage.removeItem('token')
    router.push('/login')
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-brand-700 text-white transform transition-transform duration-200
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 lg:static lg:flex lg:flex-col`}
      >
        {/* Logo */}
        <div className="p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-white/20 rounded-lg flex items-center justify-center">
              <span className="text-lg">📊</span>
            </div>
            <div>
              <p className="font-bold text-sm leading-tight">Gestor de Tráfego</p>
              <p className="text-xs text-white/60">Meta ADS + IA</p>
            </div>
          </div>
        </div>

        {/* Navegação */}
        <nav className="flex-1 p-4 space-y-1">
          {NAV.map(({ href, label, icon: Icon, badge }) => {
            const active = pathname === href || (href !== '/' && pathname.startsWith(href))
            const pendingCount = badge ? pendingData?.pending || 0 : 0
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                  ${active ? 'bg-white/20 text-white' : 'text-white/70 hover:bg-white/10 hover:text-white'}`}
              >
                <span className="flex items-center gap-3">
                  <Icon size={18} />
                  {label}
                </span>
                {badge && pendingCount > 0 && (
                  <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full font-bold">
                    {pendingCount}
                  </span>
                )}
              </Link>
            )
          })}
        </nav>

        {/* Usuário */}
        <div className="p-4 border-t border-white/10">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center text-sm font-bold">
              {user?.name?.[0]?.toUpperCase() || '?'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name || '...'}</p>
              <p className="text-xs text-white/60 truncate">{user?.email || ''}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-xs text-white/60 hover:text-white transition-colors w-full"
          >
            <LogOut size={14} />
            Sair
          </button>
        </div>
      </aside>

      {/* Overlay mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Conteúdo */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar mobile */}
        <header className="lg:hidden bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3">
          <button onClick={() => setSidebarOpen(true)}>
            <Menu size={22} className="text-gray-600" />
          </button>
          <span className="font-semibold text-gray-900">Gestor de Tráfego</span>
        </header>

        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
