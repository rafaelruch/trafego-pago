import axios from 'axios'

// Todas as chamadas usam URL relativa — o Next.js faz proxy para o backend via rewrites
export const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Injeta token JWT automaticamente
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Redireciona para login se token expirou
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// URL relativa — o Next.js faz proxy para o backend
export const metaLoginUrl = '/api/auth/meta'

// Funções helpers
export const authApi = {
  getMe: () => api.get('/auth/me'),
  listApiKeys: () => api.get('/auth/api-keys'),
  createApiKey: (name: string) => api.post(`/auth/api-keys?name=${encodeURIComponent(name)}`),
  revokeApiKey: (id: number) => api.delete(`/auth/api-keys/${id}`),
}

export const campaignsApi = {
  getBusinessManagers: () => api.get('/campaigns/business-managers'),
  getAccounts: (businessId?: string) =>
    api.get('/campaigns/accounts', { params: businessId ? { business_id: businessId } : {} }),
  getCampaigns: (accountId: string) => api.get(`/campaigns/${accountId}`),
  getInsights: (accountId: string, datePreset = 'last_7d', campaignId?: string) =>
    api.get(`/campaigns/${accountId}/insights`, {
      params: { date_preset: datePreset, ...(campaignId ? { campaign_id: campaignId } : {}) },
    }),
}

export const aiApi = {
  analyze: (data: { account_ids?: string[]; date_preset?: string; custom_prompt?: string }) =>
    api.post('/ai/analyze', data),
  chat: (message: string, account_ids?: string[]) => ({
    url: '/api/ai/chat',
    body: { message, account_ids },
  }),
}

export const approvalsApi = {
  list: (status?: string) => api.get('/approvals/', { params: status ? { status } : {} }),
  pendingCount: () => api.get('/approvals/pending/count'),
  approve: (id: number, notes?: string) => api.post(`/approvals/${id}/approve`, { notes }),
  reject: (id: number, notes?: string) => api.post(`/approvals/${id}/reject`, { notes }),
  bulkApprove: (ids: number[]) => api.post('/approvals/bulk/approve', ids),
}

export const reportsApi = {
  getSummary: (datePreset = 'last_7d', accountIds?: string[]) =>
    api.get('/reports/summary', { params: { date_preset: datePreset, account_ids: accountIds } }),
  downloadPdf: (datePreset = 'last_7d') =>
    api.get('/reports/pdf', { params: { date_preset: datePreset }, responseType: 'blob' }),
}
