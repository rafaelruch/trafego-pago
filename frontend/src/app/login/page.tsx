'use client'
import { metaLoginUrl } from '@/lib/api'

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-700 to-brand-500 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-10 w-full max-w-md text-center">
        {/* Logo */}
        <div className="w-16 h-16 bg-brand-500 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <span className="text-3xl">📊</span>
        </div>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">Gestor de Tráfego</h1>
        <p className="text-gray-500 mb-8 text-sm">
          Conecte-se ao Meta ADS e gerencie todas as suas campanhas com inteligência artificial
        </p>

        {/* Benefícios */}
        <div className="space-y-3 mb-8 text-left">
          {[
            ['📈', 'Relatórios unificados de todos os BMs'],
            ['🤖', 'Análise e otimização com IA (Claude)'],
            ['✅', 'Aprovação humana antes de qualquer mudança'],
            ['🔗', 'Integração com N8N para automações'],
            ['📄', 'Exportação de relatórios em PDF'],
          ].map(([icon, text]) => (
            <div key={text} className="flex items-center gap-3 text-sm text-gray-600">
              <span className="text-lg">{icon}</span>
              <span>{text}</span>
            </div>
          ))}
        </div>

        <a
          href={metaLoginUrl}
          className="block w-full bg-brand-500 hover:bg-brand-600 text-white font-semibold py-3 px-6 rounded-xl transition-colors"
        >
          <span className="flex items-center justify-center gap-2">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
            </svg>
            Continuar com o Meta
          </span>
        </a>

        <p className="mt-4 text-xs text-gray-400">
          Será solicitado acesso às suas contas de anúncio e Business Managers
        </p>
      </div>
    </div>
  )
}
