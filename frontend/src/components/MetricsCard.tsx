import { ReactNode } from 'react'
import { clsx } from 'clsx'

interface MetricsCardProps {
  label: string
  value: string | number
  icon?: string
  trend?: number       // % de variação (positivo = melhora, negativo = piora)
  prefix?: string
  suffix?: string
  loading?: boolean
  highlight?: 'green' | 'red' | 'blue' | 'none'
}

export default function MetricsCard({
  label, value, icon, trend, prefix = '', suffix = '', loading, highlight = 'none',
}: MetricsCardProps) {
  const highlightClass = {
    green: 'border-l-4 border-l-green-500',
    red: 'border-l-4 border-l-red-500',
    blue: 'border-l-4 border-l-brand-500',
    none: '',
  }[highlight]

  if (loading) {
    return (
      <div className={clsx('card p-5', highlightClass)}>
        <div className="animate-pulse space-y-3">
          <div className="h-3 bg-gray-200 rounded w-1/2" />
          <div className="h-7 bg-gray-200 rounded w-3/4" />
        </div>
      </div>
    )
  }

  return (
    <div className={clsx('card p-5', highlightClass)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">
            {prefix}{typeof value === 'number' ? value.toLocaleString('pt-BR') : value}{suffix}
          </p>
          {trend !== undefined && (
            <p className={clsx('text-xs mt-1 font-medium', trend >= 0 ? 'text-green-600' : 'text-red-600')}>
              {trend >= 0 ? '▲' : '▼'} {Math.abs(trend).toFixed(1)}% vs. período anterior
            </p>
          )}
        </div>
        {icon && <span className="text-2xl opacity-80">{icon}</span>}
      </div>
    </div>
  )
}
