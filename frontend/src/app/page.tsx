'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import Layout from '@/components/Layout'
import MetricsCard from '@/components/MetricsCard'
import CampaignTable from '@/components/CampaignTable'
import { campaignsApi, reportsApi, aiApi } from '@/lib/api'
import { AdAccount, CampaignInsight, DATE_PRESET_LABELS, type DatePreset } from '@/lib/types'
import { Download, RefreshCw, Sparkles } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts'

export default function DashboardPage() {
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [datePreset, setDatePreset] = useState<DatePreset>('last_7d')
  const [downloading, setDownloading] = useState(false)
  const [suggesting, setSuggesting] = useState(false)

  const { data: accounts = [], isLoading: loadingAccounts } = useQuery<AdAccount[]>({
    queryKey: ['accounts'],
    queryFn: () => campaignsApi.getAccounts().then((r) => r.data),
  })

  useEffect(() => {
    if (accounts.length && !selectedAccount) setSelectedAccount(accounts[0].account_id)
  }, [accounts, selectedAccount])

  const { data: campaigns = [], isLoading: loadingInsights, refetch, isRefetching } = useQuery<CampaignInsight[]>({
    queryKey: ['dashboard-insights', selectedAccount, datePreset],
    queryFn: () => campaignsApi.getInsights(selectedAccount, datePreset).then((r) => r.data),
    enabled: !!selectedAccount,
  })

  const isLoading = loadingAccounts || (!!selectedAccount && loadingInsights)
  const hasData = !isLoading && campaigns.length > 0
  const isEmpty = !isLoading && selectedAccount && campaigns.length === 0

  // Métricas consolidadas da conta selecionada
  const totalSpend = campaigns.reduce((s, c) => s + c.spend, 0)
  const totalImpressions = campaigns.reduce((s, c) => s + c.impressions, 0)
  const totalClicks = campaigns.reduce((s, c) => s + c.clicks, 0)
  const totalConversions = campaigns.reduce((s, c) => s + c.conversions, 0)
  const avgRoas = campaigns.filter((c) => c.roas > 0).reduce((s, c, _, a) => s + c.roas / a.length, 0)
  const avgCpc = totalClicks > 0 ? totalSpend / totalClicks : 0

  // Top 10 por investimento para os gráficos
  const chartData = [...campaigns]
    .sort((a, b) => b.spend - a.spend)
    .slice(0, 10)
    .map((c) => ({
      name: c.campaign_name.length > 20 ? c.campaign_name.slice(0, 20) + '…' : c.campaign_name,
      investimento: c.spend,
      roas: c.roas,
    }))

  const router = useRouter()

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

  const handleDownloadPdf = async () => {
    setDownloading(true)
    try {
      const res = await reportsApi.downloadPdf(datePreset)
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `relatorio-${datePreset}-${new Date().toISOString().split('T')[0]}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('PDF gerado com sucesso!')
    } catch {
      toast.error('Erro ao gerar PDF')
    } finally {
      setDownloading(false)
    }
  }

  const selectedAccountName = accounts.find((a) => a.account_id === selectedAccount)?.name || selectedAccount

  return (
    <Layout>
      {/* Cabeçalho */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500">
            {selectedAccountName ? `Performance de ${selectedAccountName}` : 'Selecione uma conta'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {/* Seletor de conta */}
          <select
            value={selectedAccount}
            onChange={(e) => setSelectedAccount(e.target.value)}
            disabled={loadingAccounts}
            className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:ring-2 focus:ring-brand-500 outline-none max-w-xs"
          >
            {loadingAccounts && <option>Carregando contas...</option>}
            {accounts.map((acc) => (
              <option key={acc.account_id} value={acc.account_id}>
                {acc.name || acc.account_id}
              </option>
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

          <button onClick={() => refetch()} className="btn-secondary flex items-center gap-1.5 text-sm">
            <RefreshCw size={14} className={isRefetching ? 'animate-spin' : ''} />
            Atualizar
          </button>

          <button
            onClick={handleSuggestCampaigns}
            disabled={suggesting || !selectedAccount}
            className="btn-secondary flex items-center gap-1.5 text-sm"
          >
            <Sparkles size={14} />
            {suggesting ? 'Analisando...' : 'Sugerir Campanhas'}
          </button>

          <button onClick={handleDownloadPdf} disabled={downloading} className="btn-primary flex items-center gap-1.5 text-sm">
            <Download size={14} />
            {downloading ? 'Gerando...' : 'Exportar PDF'}
          </button>
        </div>
      </div>

      {/* Métricas */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
        <MetricsCard label="Investimento" value={`R$ ${totalSpend.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`} icon="💰" loading={isLoading} highlight="blue" />
        <MetricsCard label="Impressões" value={totalImpressions.toLocaleString('pt-BR')} icon="👁️" loading={isLoading} />
        <MetricsCard label="Cliques" value={totalClicks.toLocaleString('pt-BR')} icon="🖱️" loading={isLoading} />
        <MetricsCard label="Conversões" value={totalConversions} icon="🎯" loading={isLoading} highlight={totalConversions > 0 ? 'green' : 'none'} />
        <MetricsCard label="ROAS Médio" value={`${avgRoas.toFixed(2)}x`} icon="📈" loading={isLoading} highlight={avgRoas >= 2 ? 'green' : avgRoas > 0 && avgRoas < 1 ? 'red' : 'none'} />
        <MetricsCard label="CPC Médio" value={`R$ ${avgCpc.toFixed(2)}`} icon="💡" loading={isLoading} />
      </div>

      {/* Aviso sem dados */}
      {isEmpty && (
        <div className="card p-8 text-center mb-6">
          <p className="text-2xl mb-2">📭</p>
          <p className="font-semibold text-gray-700 mb-1">Nenhuma campanha encontrada para este período</p>
          <p className="text-sm text-gray-500">Tente selecionar "Últimos 30 dias", "Este mês" ou verifique se há campanhas ativas nesta conta.</p>
        </div>
      )}

      {/* Gráficos */}
      {hasData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          {/* Investimento por campanha */}
          <div className="card p-5">
            <h3 className="font-semibold text-gray-900 mb-4 text-sm">Investimento por Campanha (Top 10)</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} margin={{ left: 0, right: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 9 }} angle={-20} textAnchor="end" height={50} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `R$${v}`} />
                <Tooltip formatter={(v: number) => [`R$ ${v.toFixed(2)}`, 'Investimento']} />
                <Bar dataKey="investimento" fill="#1877F2" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* ROAS por campanha */}
          <div className="card p-5">
            <h3 className="font-semibold text-gray-900 mb-4 text-sm">ROAS por Campanha (Top 10)</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} margin={{ left: 0, right: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 9 }} angle={-20} textAnchor="end" height={50} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}x`} />
                <Tooltip formatter={(v: number) => [`${v.toFixed(2)}x`, 'ROAS']} />
                <Bar dataKey="roas" fill="#00B37A" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Tabela de campanhas */}
      {hasData && (
        <div className="mb-2">
          <h2 className="text-base font-semibold text-gray-900 mb-3">Campanhas</h2>
          <CampaignTable campaigns={campaigns} loading={isLoading} datePreset={datePreset} selectedAccount={selectedAccount} />
        </div>
      )}
    </Layout>
  )
}
