export interface User {
  id: number
  name: string
  email?: string
  has_meta_token: boolean
  meta_token_expires_at?: string
}

export interface CampaignInsight {
  campaign_id: string
  campaign_name: string
  status: 'ACTIVE' | 'PAUSED' | 'DELETED' | 'ARCHIVED' | string
  objective?: string
  impressions: number
  clicks: number
  spend: number
  reach: number
  cpm: number
  cpc: number
  ctr: number
  conversions: number
  cost_per_conversion: number
  roas: number
  frequency: number
  date_start?: string
  date_stop?: string
  account_id?: string
  account_name?: string
}

export interface AdAccount {
  account_id: string
  name: string
  currency: string
  status: number
  business_id?: string
}

export interface BusinessManager {
  id: string
  name: string
}

export interface Approval {
  id: number
  action_type: string
  payload: string
  account_id?: string
  campaign_id?: string
  campaign_name?: string
  adset_id?: string
  ai_reasoning: string
  status: 'pending' | 'approved' | 'rejected' | 'executed' | 'failed'
  created_at: string
  decided_at?: string
  executed_at?: string
  execution_result?: string
}

export interface ReportSummary {
  period: string
  total_spend: number
  total_impressions: number
  total_clicks: number
  total_conversions: number
  average_cpc: number
  average_roas: number
  average_ctr: number
  campaigns: CampaignInsight[]
  generated_at: string
}

export interface ApiKey {
  id: number
  name: string
  key_preview: string
  is_active: boolean
  created_at: string
  last_used_at?: string
}

export type DatePreset = 'last_7d' | 'last_30d' | 'this_month' | 'last_month'

export const DATE_PRESET_LABELS: Record<DatePreset, string> = {
  last_7d: 'Últimos 7 dias',
  last_30d: 'Últimos 30 dias',
  this_month: 'Este mês',
  last_month: 'Mês passado',
}

export const ACTION_TYPE_LABELS: Record<string, string> = {
  pause_campaign: 'Pausar Campanha',
  enable_campaign: 'Ativar Campanha',
  adjust_budget: 'Ajustar Orçamento',
  adjust_bid: 'Ajustar Lance',
  create_campaign: 'Criar Nova Campanha',
}

export const ACTION_TYPE_ICONS: Record<string, string> = {
  pause_campaign: '⏸️',
  enable_campaign: '▶️',
  adjust_budget: '💰',
  adjust_bid: '🎯',
  create_campaign: '🚀',
}
