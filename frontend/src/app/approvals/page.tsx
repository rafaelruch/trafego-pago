'use client'
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Layout from '@/components/Layout'
import ApprovalCard from '@/components/ApprovalCard'
import { approvalsApi } from '@/lib/api'
import { Approval } from '@/lib/types'
import { clsx } from 'clsx'
import toast from 'react-hot-toast'

const TABS = [
  { key: 'pending', label: 'Pendentes', icon: '⏳' },
  { key: 'executed', label: 'Executados', icon: '✅' },
  { key: 'rejected', label: 'Rejeitados', icon: '✕' },
]

export default function ApprovalsPage() {
  const [tab, setTab] = useState('pending')
  const [bulkIds, setBulkIds] = useState<Set<number>>(new Set())
  const [bulkLoading, setBulkLoading] = useState(false)
  const qc = useQueryClient()

  const { data: approvals = [], isLoading, refetch } = useQuery<Approval[]>({
    queryKey: ['approvals', tab],
    queryFn: () => approvalsApi.list(tab).then((r) => r.data),
  })

  const onDecision = () => {
    qc.invalidateQueries({ queryKey: ['approvals'] })
    qc.invalidateQueries({ queryKey: ['pending-count'] })
  }

  const toggleBulk = (id: number) => {
    setBulkIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleBulkApprove = async () => {
    if (!bulkIds.size) return
    setBulkLoading(true)
    try {
      await approvalsApi.bulkApprove([...bulkIds])
      toast.success(`${bulkIds.size} ações aprovadas e executadas!`)
      setBulkIds(new Set())
      onDecision()
    } catch {
      toast.error('Erro ao aprovar em massa')
    } finally {
      setBulkLoading(false)
    }
  }

  const pendingApprovals = approvals.filter((a) => a.status === 'pending')

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Aprovações de IA</h1>
        <p className="text-sm text-gray-500">
          Revise e aprove as sugestões de otimização geradas pela inteligência artificial
        </p>
      </div>

      {/* Abas */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl mb-6 w-fit">
        {TABS.map(({ key, label, icon }) => (
          <button
            key={key}
            onClick={() => { setTab(key); setBulkIds(new Set()) }}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5',
              tab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            )}
          >
            {icon} {label}
          </button>
        ))}
      </div>

      {/* Ação em massa (apenas pendentes) */}
      {tab === 'pending' && pendingApprovals.length > 0 && (
        <div className="flex items-center justify-between bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-6">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              className="w-4 h-4 accent-brand-500"
              checked={bulkIds.size === pendingApprovals.length}
              onChange={(e) => {
                if (e.target.checked) setBulkIds(new Set(pendingApprovals.map((a) => a.id)))
                else setBulkIds(new Set())
              }}
            />
            <span className="text-sm text-gray-700">
              {bulkIds.size > 0
                ? `${bulkIds.size} sugestão(ões) selecionada(s)`
                : `${pendingApprovals.length} sugestão(ões) aguardando aprovação`}
            </span>
          </div>
          {bulkIds.size > 0 && (
            <button
              onClick={handleBulkApprove}
              disabled={bulkLoading}
              className="btn-primary text-sm"
            >
              {bulkLoading ? 'Executando...' : `✅ Aprovar ${bulkIds.size} selecionadas`}
            </button>
          )}
        </div>
      )}

      {/* Lista */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card p-5 animate-pulse space-y-3">
              <div className="h-4 bg-gray-200 rounded w-3/4" />
              <div className="h-3 bg-gray-200 rounded w-full" />
              <div className="h-3 bg-gray-200 rounded w-5/6" />
            </div>
          ))}
        </div>
      ) : approvals.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-4xl mb-3">🎉</p>
          <p className="font-medium text-gray-600">Nenhuma sugestão {tab === 'pending' ? 'pendente' : tab === 'executed' ? 'executada' : 'rejeitada'}</p>
          {tab === 'pending' && (
            <p className="text-sm mt-2">Vá ao Chat IA e peça uma análise das suas campanhas!</p>
          )}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {approvals.map((approval) => (
            <div key={approval.id} className="relative">
              {tab === 'pending' && (
                <input
                  type="checkbox"
                  className="absolute top-4 right-4 w-4 h-4 z-10 accent-brand-500"
                  checked={bulkIds.has(approval.id)}
                  onChange={() => toggleBulk(approval.id)}
                />
              )}
              <ApprovalCard approval={approval} onDecision={onDecision} />
            </div>
          ))}
        </div>
      )}
    </Layout>
  )
}
