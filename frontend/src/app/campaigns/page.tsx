'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import Layout from '@/components/Layout'
import CampaignTable from '@/components/CampaignTable'
import MetricsCard from '@/components/MetricsCard'
import { campaignsApi, aiApi } from '@/lib/api'
import { AdAccount, CampaignInsight, DATE_PRESET_LABELS, type DatePreset } from '@/lib/types'
import { Sparkles } from 'lucide-react'
import toast from 'react-hot-toast'

export default function CampaignsPage() {
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [datePreset, setDatePreset] = useState<DatePreset>('last_7d')
  const [suggesting, setSuggesting] = useState(false)
  const router = useRouter()

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

  const handleSuggestCampaigns = async () => {
    if (!selectedAccount) return
    setSuggesting(true)
    const toastId = toast.loading('Analisando oportunidades e gerando sugestões de novas campanhas...')
    try {
      await aiApi.analyze({
        account_ids: [selectedAccount],
        date_preset: datePreset,
        custom_prompt: `Com base nos dados das campanhas desta conta, identifique oportunidades não exploradas e sugira 2 a 3 novas campanhas estratégicas. Para cada sugestão, use a ferramenta suggest_new_campaign com nome, objetivo, orçamento diário, público-alvo e estratégia completa. Considere: objetivos ausentes, nichos não atendidos, diversificação de criativos, e oportunidades sazonais.`,
      })
      toast.success('Sugestões criadas! Verifique em Aprovações.', { id: toastId, duration: 5000 })
      router.push('/approvals')
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Erro ao gerar sugestões', { id: toastId })
    } finally {
      setSuggesting(false)
    }
  }

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
        <div className="flex flex-wrap items-center gap-3">
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
          <button
            onClick={handleSuggestCampaigns}
            disabled={suggesting || !selectedAccount}
            className="btn-secondary flex items-center gap-1.5 text-sm"
          >
            <Sparkles size={14} />
            {suggesting ? 'Analisando...' : 'Sugerir Campanhas'}
          </button>
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
      <CampaignTable campaigns={insights} loading={loadingInsights} datePreset={datePreset} selectedAccount={selectedAccount} />
    </Layout>
  )
}
