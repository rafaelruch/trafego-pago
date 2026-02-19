'use client'
import { CampaignInsight } from '@/lib/types'
import { clsx } from 'clsx'

interface CampaignTableProps {
  campaigns: CampaignInsight[]
  loading?: boolean
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

export default function CampaignTable({ campaigns, loading }: CampaignTableProps) {
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
            {['Campanha', 'Status', 'Impressões', 'Cliques', 'Investimento', 'CPM', 'CPC', 'CTR', 'Conv.', 'ROAS'].map((h) => (
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
