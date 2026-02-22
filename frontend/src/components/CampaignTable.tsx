'use client'
import { useState } from 'react'
import { CampaignInsight } from '@/lib/types'
import { aiApi } from '@/lib/api'
import { clsx } from 'clsx'
import toast from 'react-hot-toast'
import { useRouter } from 'next/navigation'

interface CampaignTableProps {
  campaigns: CampaignInsight[]
  loading?: boolean
  onOptimize?: (campaign: CampaignInsight) => Promise<void>
  datePreset?: string
  selectedAccount?: string
}

function StatusBadge({ status }: { status: string }) {
  const isActive = status === 'ACTIVE'
  return (
    <span className={clsx('badge', isActive ? 'badge-green' : 'badge-yellow')}>
      {isActive ? '✅ Ativa' : '⏸️ Pausada'}
    </span>
  )
}

function RoasBadge({ roas }: { roas: number }) {
  const cls = roas >= 2 ? 'badge-green' : roas >= 1 ? 'badge-yellow' : 'badge-red'
  return <span className={clsx('badge', cls)}>{roas.toFixed(2)}x</span>
}

export default function CampaignTable({ campaigns, loading, onOptimize, datePreset = 'last_7d', selectedAccount }: CampaignTableProps) {
  const [analyzingId, setAnalyzingId] = useState<string | null>(null)
  const router = useRouter()

  const handleOptimize = async (campaign: CampaignInsight) => {
    if (onOptimize) {
      return onOptimize(campaign)
    }

    // Handler padrão: chama analyze com contexto da campanha
    setAnalyzingId(campaign.campaign_id)
    const toastId = toast.loading(`Analisando "${campaign.campaign_name}"...`)
    try {
      await aiApi.analyze({
        account_ids: [campaign.account_id || selectedAccount || ''],
        date_preset: datePreset,
        custom_prompt: `Analise especificamente a campanha "${campaign.campaign_name}" (ID: ${campaign.campaign_id}) com as métricas: impressões=${campaign.impressions}, cliques=${campaign.clicks}, gasto=R$${campaign.spend.toFixed(2)}, ROAS=${campaign.roas.toFixed(2)}x, CPC=R$${campaign.cpc.toFixed(2)}, conversões=${campaign.conversions}. Sugira otimizações concretas e específicas para esta campanha. Use as ferramentas disponíveis para criar as sugestões de ação.`,
      })
      toast.success('Análise concluída! Verifique as sugestões em Aprovações.', { id: toastId, duration: 5000 })
      router.push('/approvals')
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Erro ao analisar campanha', { id: toastId })
    } finally {
      setAnalyzingId(null)
    }
  }

  if (loading) {
    return (
      <div className="card overflow-hidden">
        <div className="animate-pulse">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex gap-4 p-4 border-b border-gray-100">
              <div className="h-4 bg-gray-200 rounded flex-1" />
              <div className="h-4 bg-gray-200 rounded w-20" />
              <div className="h-4 bg-gray-200 rounded w-24" />
              <div className="h-4 bg-gray-200 rounded w-16" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (!campaigns.length) {
    return (
      <div className="card p-10 text-center text-gray-400">
        <p className="text-3xl mb-2">📭</p>
        <p>Nenhuma campanha encontrada para o período selecionado.</p>
      </div>
    )
  }

  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-200">
            {['Campanha', 'Status', 'Impressões', 'Cliques', 'Investimento', 'CPM', 'CPC', 'CTR', 'Conv.', 'ROAS', 'Ações'].map((h) => (
              <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {campaigns.map((c) => (
            <tr key={c.campaign_id} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 max-w-[200px]">
                <p className="font-medium text-gray-900 truncate" title={c.campaign_name}>
                  {c.campaign_name}
                </p>
                {c.account_name && <p className="text-xs text-gray-400 truncate">{c.account_name}</p>}
              </td>
              <td className="px-4 py-3 whitespace-nowrap"><StatusBadge status={c.status} /></td>
              <td className="px-4 py-3 text-right font-mono text-gray-700">{c.impressions.toLocaleString('pt-BR')}</td>
              <td className="px-4 py-3 text-right font-mono text-gray-700">{c.clicks.toLocaleString('pt-BR')}</td>
              <td className="px-4 py-3 text-right font-mono font-medium text-gray-900">
                R$ {c.spend.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
              </td>
              <td className="px-4 py-3 text-right font-mono text-gray-700">R$ {c.cpm.toFixed(2)}</td>
              <td className="px-4 py-3 text-right font-mono text-gray-700">R$ {c.cpc.toFixed(2)}</td>
              <td className="px-4 py-3 text-right font-mono text-gray-700">{c.ctr.toFixed(2)}%</td>
              <td className="px-4 py-3 text-right font-mono text-gray-700">{c.conversions.toLocaleString('pt-BR')}</td>
              <td className="px-4 py-3"><RoasBadge roas={c.roas} /></td>
              <td className="px-4 py-3 whitespace-nowrap">
                <button
                  onClick={() => handleOptimize(c)}
                  disabled={analyzingId === c.campaign_id}
                  title="Pedir à IA análise e sugestões de otimização para esta campanha"
                  className={clsx(
                    'text-xs px-2.5 py-1.5 rounded-lg font-medium transition-all',
                    analyzingId === c.campaign_id
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200'
                  )}
                >
                  {analyzingId === c.campaign_id ? '⏳ Analisando...' : '🤖 Otimizar IA'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
