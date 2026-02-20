'use client'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Layout from '@/components/Layout'
import MetricsCard from '@/components/MetricsCard'
import CampaignTable from '@/components/CampaignTable'
import { reportsApi } from '@/lib/api'
import { DATE_PRESET_LABELS, type DatePreset } from '@/lib/types'
import { Download, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, Legend,
} from 'recharts'

export default function DashboardPage() {
  const [datePreset, setDatePreset] = useState<DatePreset>('last_7d')
  const [downloading, setDownloading] = useState(false)

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['dashboard', datePreset],
    queryFn: () => reportsApi.getSummary(datePreset).then((r) => r.data),
  })

  const summary = data?.summary
  const campaigns: any[] = data?.campaigns || []
  const hasData = !isLoading && campaigns.length > 0
  const isEmpty = !isLoading && data && campaigns.length === 0

  // Top 10 por investimento para o gráfico
  const chartData = [...campaigns]
    .sort((a, b) => b.spend - a.spend)
    .slice(0, 10)
    .map((c) => ({
      name: c.campaign_name.length > 20 ? c.campaign_name.slice(0, 20) + '…' : c.campaign_name,
      investimento: c.spend,
      roas: c.roas,
      conversoes: c.conversions,
    }))

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

  return (
    <Layout>
      {/* Cabeçalho */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500">Visão consolidada de todas as campanhas</p>
        </div>
        <div className="flex items-center gap-3">
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

          <button onClick={handleDownloadPdf} disabled={downloading} className="btn-primary flex items-center gap-1.5 text-sm">
            <Download size={14} />
            {downloading ? 'Gerando...' : 'Exportar PDF'}
          </button>
        </div>
      </div>

      {/* Métricas de resumo */}
      <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4 mb-6">
        <MetricsCard label="Investimento Total" value={`R$ ${(summary?.total_spend || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`} icon="💰" loading={isLoading} highlight="blue" />
        <MetricsCard label="Impressões" value={summary?.total_impressions || 0} icon="👁️" loading={isLoading} />
        <MetricsCard label="Cliques" value={summary?.total_clicks || 0} icon="🖱️" loading={isLoading} />
        <MetricsCard label="Conversões" value={summary?.total_conversions || 0} icon="🎯" loading={isLoading} highlight={summary?.total_conversions > 0 ? 'green' : 'none'} />
        <MetricsCard label="ROAS Médio" value={`${(summary?.average_roas || 0).toFixed(2)}x`} icon="📈" loading={isLoading} highlight={summary?.average_roas >= 2 ? 'green' : summary?.average_roas > 0 && summary.average_roas < 1 ? 'red' : 'none'} />
        <MetricsCard label="CPC Médio" value={`R$ ${(summary?.average_cpc || 0).toFixed(2)}`} icon="💡" loading={isLoading} />
      </div>

      {/* Aviso sem dados */}
      {isEmpty && (
        <div className="card p-8 text-center mb-6">
          <p className="text-2xl mb-2">📭</p>
          <p className="font-semibold text-gray-700 mb-1">Nenhuma campanha encontrada para este período</p>
          <p className="text-sm text-gray-500">Tente selecionar "Últimos 30 dias", "Este mês" ou verifique se há campanhas ativas na sua conta Meta Ads.</p>
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
          <h2 className="text-base font-semibold text-gray-900 mb-3">Todas as Campanhas</h2>
          <CampaignTable campaigns={campaigns} loading={isLoading} />
        </div>
      )}
    </Layout>
  )
}
