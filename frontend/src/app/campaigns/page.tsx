'use client'
import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import Layout from '@/components/Layout'
import CampaignTable from '@/components/CampaignTable'
import MetricsCard from '@/components/MetricsCard'
import { campaignsApi } from '@/lib/api'
import { AdAccount, CampaignInsight, DATE_PRESET_LABELS, type DatePreset } from '@/lib/types'

export default function CampaignsPage() {
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [datePreset, setDatePreset] = useState<DatePreset>('last_7d')

  const { data: accounts = [], isLoading: loadingAccounts } = useQuery<AdAccount[]>({
    queryKey: ['accounts'],
    queryFn: () => campaignsApi.getAccounts().then((r) => r.data),
  })

  useEffect(() => {
    if (accounts.length && !selectedAccount) setSelectedAccount(accounts[0].account_id)
  }, [accounts, selectedAccount])

  const { data: insights = [], isLoading: loadingInsights } = useQuery<CampaignInsight[]>({
    queryKey: ['insights', selectedAccount, datePreset],
    queryFn: () => campaignsApi.getInsights(selectedAccount, datePreset).then((r) => r.data),
    enabled: !!selectedAccount,
  })

  const totalSpend = insights.reduce((s, c) => s + c.spend, 0)
  const totalClicks = insights.reduce((s, c) => s + c.clicks, 0)
  const totalConversions = insights.reduce((s, c) => s + c.conversions, 0)
  const avgRoas = insights.filter((c) => c.roas > 0).reduce((s, c, _, a) => s + c.roas / a.length, 0)

  return (
    <Layout>
      {/* Cabeçalho */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Campanhas</h1>
          <p className="text-sm text-gray-500">Performance detalhada por conta e período</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Seletor de conta */}
          <select
            value={selectedAccount}
            onChange={(e) => setSelectedAccount(e.target.value)}
            disabled={loadingAccounts}
            className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:ring-2 focus:ring-brand-500 outline-none max-w-xs"
          >
            {accounts.map((acc) => (
              <option key={acc.account_id} value={acc.account_id}>{acc.name || acc.account_id}</option>
            ))}
          </select>
          {/* Seletor de período */}
          <select
            value={datePreset}
            onChange={(e) => setDatePreset(e.target.value as DatePreset)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:ring-2 focus:ring-brand-500 outline-none"
          >
            {Object.entries(DATE_PRESET_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Métricas da conta selecionada */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <MetricsCard label="Investimento" value={`R$ ${totalSpend.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`} icon="💰" loading={loadingInsights} />
        <MetricsCard label="Cliques" value={totalClicks} icon="🖱️" loading={loadingInsights} />
        <MetricsCard label="Conversões" value={totalConversions} icon="🎯" loading={loadingInsights} />
        <MetricsCard label="ROAS Médio" value={`${avgRoas.toFixed(2)}x`} icon="📈" loading={loadingInsights} highlight={avgRoas >= 2 ? 'green' : avgRoas > 0 && avgRoas < 1 ? 'red' : 'none'} />
      </div>

      {/* Tabela */}
      <CampaignTable campaigns={insights} loading={loadingInsights} />
    </Layout>
  )
}
