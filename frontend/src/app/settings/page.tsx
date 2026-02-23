'use client'
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Layout from '@/components/Layout'
import { authApi, settingsApi } from '@/lib/api'
import { ApiKey } from '@/lib/types'
import toast from 'react-hot-toast'
import { Key, Plus, Trash2, Copy, Eye, EyeOff, Bot, Save } from 'lucide-react'

export default function SettingsPage() {
  const [newKeyName, setNewKeyName] = useState('')
  const [creating, setCreating] = useState(false)
  const [newKey, setNewKey] = useState<{ key: string; name: string } | null>(null)
  const [geminiKey, setGeminiKey] = useState('')
  const [showGeminiKey, setShowGeminiKey] = useState(false)
  const [selectedModel, setSelectedModel] = useState('')
  const [savingAI, setSavingAI] = useState(false)
  const qc = useQueryClient()

  const { data: apiKeys = [], isLoading } = useQuery<ApiKey[]>({
    queryKey: ['api-keys'],
    queryFn: () => authApi.listApiKeys().then((r) => r.data),
  })

  const { data: aiSettings } = useQuery({
    queryKey: ['ai-settings'],
    queryFn: () => settingsApi.getAISettings().then((r) => r.data),
    onSuccess: (data: any) => {
      if (!selectedModel) setSelectedModel(data.ai_model || 'gemini-2.0-flash')
    },
  })

  const handleCreate = async () => {
    if (!newKeyName.trim()) return
    setCreating(true)
    try {
      const res = await authApi.createApiKey(newKeyName.trim())
      setNewKey({ key: res.data.key, name: res.data.name })
      setNewKeyName('')
      qc.invalidateQueries({ queryKey: ['api-keys'] })
      toast.success('API Key criada!')
    } catch {
      toast.error('Erro ao criar API Key')
    } finally {
      setCreating(false)
    }
  }

  const handleRevoke = async (id: number, name: string) => {
    if (!confirm(`Revogar a API Key "${name}"? Isso vai quebrar integrações que a usam.`)) return
    try {
      await authApi.revokeApiKey(id)
      qc.invalidateQueries({ queryKey: ['api-keys'] })
      toast.success('API Key revogada')
    } catch {
      toast.error('Erro ao revogar')
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Copiado!')
  }

  const handleSaveAI = async () => {
    setSavingAI(true)
    try {
      const payload: { gemini_api_key?: string; ai_model?: string } = {}
      if (geminiKey.trim()) payload.gemini_api_key = geminiKey.trim()
      if (selectedModel) payload.ai_model = selectedModel
      await settingsApi.updateAISettings(payload)
      qc.invalidateQueries({ queryKey: ['ai-settings'] })
      setGeminiKey('')
      toast.success('Configurações de IA salvas!')
    } catch {
      toast.error('Erro ao salvar configurações')
    } finally {
      setSavingAI(false)
    }
  }

  return (
    <Layout>
      <div className="max-w-2xl">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Configurações</h1>
        <p className="text-sm text-gray-500 mb-8">Gerencie integrações e API Keys</p>

        {/* Seção IA */}
        <div className="card p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Bot size={20} className="text-brand-500" />
            <h2 className="font-semibold text-gray-900">Configurações de IA</h2>
          </div>
          <p className="text-sm text-gray-500 mb-6">
            Configure sua chave do Google Gemini e o modelo de IA a usar nas análises.
            Se não configurar, o sistema usa a chave padrão da plataforma.
          </p>

          {/* Status da chave atual */}
          {aiSettings && (
            <div className={`rounded-xl px-4 py-3 mb-5 text-sm flex items-center gap-2 ${
              aiSettings.has_custom_key
                ? 'bg-green-50 text-green-800 border border-green-200'
                : 'bg-gray-50 text-gray-600 border border-gray-200'
            }`}>
              <span>{aiSettings.has_custom_key ? '✅ Usando sua chave Gemini personalizada' : '🔧 Usando chave padrão da plataforma'}</span>
            </div>
          )}

          {/* Chave Gemini */}
          <div className="mb-5">
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Chave da API Gemini
              <span className="text-gray-400 font-normal ml-1">(opcional — substitui a chave padrão)</span>
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <input
                  type={showGeminiKey ? 'text' : 'password'}
                  placeholder={aiSettings?.has_custom_key ? '••••••••••••••• (chave salva)' : 'AIzaSy...'}
                  value={geminiKey}
                  onChange={(e) => setGeminiKey(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-500 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowGeminiKey(!showGeminiKey)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showGeminiKey ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
            {aiSettings?.has_custom_key && (
              <button
                onClick={async () => {
                  await settingsApi.updateAISettings({ gemini_api_key: '' })
                  qc.invalidateQueries({ queryKey: ['ai-settings'] })
                  toast.success('Chave removida — usando chave padrão')
                }}
                className="text-xs text-red-500 mt-1.5 hover:underline"
              >
                Remover chave personalizada
              </button>
            )}
          </div>

          {/* Modelo */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Modelo de IA</label>
            <select
              value={selectedModel || aiSettings?.ai_model || 'gemini-2.0-flash'}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-500 bg-white"
            >
              {(aiSettings?.available_models || []).map((m: { id: string; label: string }) => (
                <option key={m.id} value={m.id}>{m.label}</option>
              ))}
            </select>
          </div>

          <button
            onClick={handleSaveAI}
            disabled={savingAI || (!geminiKey.trim() && !selectedModel)}
            className="btn-primary flex items-center gap-2 text-sm"
          >
            <Save size={15} />
            {savingAI ? 'Salvando...' : 'Salvar configurações de IA'}
          </button>
        </div>

        {/* Seção API Keys */}
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Key size={20} className="text-brand-500" />
            <h2 className="font-semibold text-gray-900">API Keys para N8N</h2>
          </div>
          <p className="text-sm text-gray-500 mb-6">
            Use essas chaves para autenticar no N8N e outras integrações.
            Envie o header <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">X-API-Key: sua_chave</code> nas requisições.
          </p>

          {/* Endpoints N8N */}
          <div className="bg-gray-50 rounded-xl p-4 mb-6 space-y-2">
            <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Endpoints disponíveis</p>
            {[
              ['GET', '/api/reports/n8n/campaigns', 'Dados JSON das campanhas'],
              ['GET', '/api/reports/n8n/summary', 'Resumo de métricas'],
              ['GET', '/api/reports/n8n/pdf', 'PDF do relatório'],
            ].map(([method, path, desc]) => (
              <div key={path} className="flex items-start gap-2">
                <span className="text-xs font-mono bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">{method}</span>
                <div>
                  <code className="text-xs text-gray-800">{path}</code>
                  <p className="text-xs text-gray-500">{desc}</p>
                </div>
              </div>
            ))}
            <p className="text-xs text-gray-500 mt-2">
              Parâmetros: <code className="bg-gray-200 px-1 rounded">date_preset</code> (last_7d, last_30d, this_month, last_month)
            </p>
          </div>

          {/* Nova key sendo exibida */}
          {newKey && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 mb-4">
              <p className="text-sm font-semibold text-yellow-800 mb-2">
                ⚠️ Copie agora — esta chave não será exibida novamente
              </p>
              <p className="text-xs text-gray-600 mb-1">{newKey.name}</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-xs bg-white border border-yellow-200 rounded-lg px-3 py-2 break-all">
                  {newKey.key}
                </code>
                <button onClick={() => copyToClipboard(newKey.key)} className="btn-secondary px-3 py-2">
                  <Copy size={14} />
                </button>
              </div>
              <button onClick={() => setNewKey(null)} className="text-xs text-yellow-700 mt-2 underline">
                Ok, já copiei
              </button>
            </div>
          )}

          {/* Criar nova key */}
          <div className="flex gap-2 mb-6">
            <input
              type="text"
              placeholder="Nome da integração (ex: N8N Produção)"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-500"
            />
            <button
              onClick={handleCreate}
              disabled={!newKeyName.trim() || creating}
              className="btn-primary flex items-center gap-1.5 text-sm"
            >
              <Plus size={16} />
              {creating ? 'Criando...' : 'Criar'}
            </button>
          </div>

          {/* Lista de keys */}
          {isLoading ? (
            <div className="space-y-3 animate-pulse">
              {[...Array(2)].map((_, i) => <div key={i} className="h-12 bg-gray-100 rounded-lg" />)}
            </div>
          ) : apiKeys.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">Nenhuma API Key criada ainda</p>
          ) : (
            <div className="space-y-2">
              {apiKeys.map((k) => (
                <div key={k.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{k.name}</p>
                    <p className="text-xs text-gray-400 font-mono">{k.key_preview}</p>
                    {k.last_used_at && (
                      <p className="text-xs text-gray-400">
                        Último uso: {new Date(k.last_used_at).toLocaleString('pt-BR')}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => handleRevoke(k.id, k.name)}
                    className="text-red-500 hover:text-red-700 transition-colors p-1.5"
                    title="Revogar"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}
