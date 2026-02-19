'use client'
import { useState } from 'react'
import { Approval, ACTION_TYPE_LABELS, ACTION_TYPE_ICONS } from '@/lib/types'
import { approvalsApi } from '@/lib/api'
import { clsx } from 'clsx'
import toast from 'react-hot-toast'

interface ApprovalCardProps {
  approval: Approval
  onDecision: () => void
}

export default function ApprovalCard({ approval, onDecision }: ApprovalCardProps) {
  const [loading, setLoading] = useState<'approve' | 'reject' | null>(null)

  const payload = (() => {
    try { return JSON.parse(approval.payload) }
    catch { return {} }
  })()

  const handleApprove = async () => {
    setLoading('approve')
    try {
      await approvalsApi.approve(approval.id)
      toast.success('Ação aprovada e executada!')
      onDecision()
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Erro ao aprovar')
    } finally {
      setLoading(null)
    }
  }

  const handleReject = async () => {
    setLoading('reject')
    try {
      await approvalsApi.reject(approval.id)
      toast.success('Sugestão rejeitada')
      onDecision()
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Erro ao rejeitar')
    } finally {
      setLoading(null)
    }
  }

  const statusConfig: Record<string, { label: string; cls: string }> = {
    pending: { label: 'Aguardando', cls: 'badge-yellow' },
    approved: { label: 'Aprovado', cls: 'badge-blue' },
    executed: { label: 'Executado', cls: 'badge-green' },
    rejected: { label: 'Rejeitado', cls: 'badge-gray' },
    failed: { label: 'Falhou', cls: 'badge-red' },
  }

  const status = statusConfig[approval.status] || { label: approval.status, cls: 'badge-gray' }
  const icon = ACTION_TYPE_ICONS[approval.action_type] || '⚙️'
  const actionLabel = ACTION_TYPE_LABELS[approval.action_type] || approval.action_type

  return (
    <div className={clsx('card p-5', approval.status === 'pending' && 'border-l-4 border-l-yellow-400')}>
      {/* Cabeçalho */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">{icon}</span>
          <div>
            <p className="font-semibold text-gray-900 text-sm">{actionLabel}</p>
            {approval.campaign_name && (
              <p className="text-xs text-gray-500 truncate max-w-xs">{approval.campaign_name}</p>
            )}
          </div>
        </div>
        <span className={clsx('badge shrink-0', status.cls)}>{status.label}</span>
      </div>

      {/* Detalhes do payload */}
      {Object.keys(payload).length > 0 && (
        <div className="bg-gray-50 rounded-lg p-3 mb-3 text-xs text-gray-600 font-mono space-y-1">
          {payload.new_budget && (
            <p>💰 Novo orçamento: <strong>R$ {Number(payload.new_budget).toFixed(2)}/dia</strong></p>
          )}
          {payload.current_budget && (
            <p>📋 Orçamento atual: R$ {Number(payload.current_budget).toFixed(2)}/dia</p>
          )}
          {payload.new_bid && (
            <p>🎯 Novo lance: <strong>R$ {Number(payload.new_bid).toFixed(2)}</strong></p>
          )}
          {payload.campaign_id && (
            <p className="text-gray-400">ID: {payload.campaign_id}</p>
          )}
        </div>
      )}

      {/* Justificativa da IA */}
      <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 mb-4">
        <p className="text-xs font-semibold text-blue-700 mb-1">💡 Justificativa da IA</p>
        <p className="text-xs text-blue-800 leading-relaxed">{approval.ai_reasoning}</p>
      </div>

      {/* Resultado de execução */}
      {approval.execution_result && (
        <div className={clsx(
          'rounded-lg p-3 mb-4 text-xs',
          approval.status === 'executed' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        )}>
          {approval.execution_result}
        </div>
      )}

      {/* Data */}
      <p className="text-xs text-gray-400 mb-4">
        Criado em {new Date(approval.created_at).toLocaleString('pt-BR')}
      </p>

      {/* Botões (apenas para pendentes) */}
      {approval.status === 'pending' && (
        <div className="flex gap-2">
          <button
            onClick={handleApprove}
            disabled={loading !== null}
            className="flex-1 btn-primary text-sm py-2"
          >
            {loading === 'approve' ? '⏳ Executando...' : '✅ Aprovar e Executar'}
          </button>
          <button
            onClick={handleReject}
            disabled={loading !== null}
            className="btn-secondary text-sm py-2 px-4"
          >
            {loading === 'reject' ? '...' : '✕ Rejeitar'}
          </button>
        </div>
      )}
    </div>
  )
}
