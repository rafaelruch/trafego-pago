'use client'
import { useState, useRef, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Layout from '@/components/Layout'
import { aiApi, campaignsApi } from '@/lib/api'
import toast from 'react-hot-toast'
import { Send, Bot, User, Loader2, Sparkles } from 'lucide-react'
import { clsx } from 'clsx'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const QUICK_PROMPTS = [
  'Analise todas as minhas campanhas e crie sugestões de otimização',
  'Quais campanhas estão com ROAS abaixo de 1?',
  'Qual é minha campanha com melhor performance essa semana?',
  'Que campanhas devo pausar para economizar orçamento?',
  'Crie um resumo executivo das campanhas para enviar ao cliente',
]

export default function AIPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const qc = useQueryClient()

  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => campaignsApi.getAccounts().then((r) => r.data),
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text?: string) => {
    const msg = text || input.trim()
    if (!msg || streaming) return
    setInput('')

    const userMsg: Message = { role: 'user', content: msg, timestamp: new Date() }
    setMessages((prev) => [...prev, userMsg])
    setStreaming(true)

    const assistantMsg: Message = { role: 'assistant', content: '', timestamp: new Date() }
    setMessages((prev) => [...prev, assistantMsg])

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const token = localStorage.getItem('token')

      const response = await fetch(`${API_URL}/api/ai/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: msg }),
      })

      if (!response.ok) throw new Error('Erro na API')

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') break
            setMessages((prev) => {
              const next = [...prev]
              const last = next[next.length - 1]
              if (last.role === 'assistant') {
                last.content += data
              }
              return next
            })
          }
        }
      }

      // Atualiza contador de pendentes após possíveis sugestões
      qc.invalidateQueries({ queryKey: ['pending-count'] })
      qc.invalidateQueries({ queryKey: ['approvals'] })
    } catch (e) {
      setMessages((prev) => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last.role === 'assistant') {
          last.content = '❌ Erro ao conectar com a IA. Tente novamente.'
        }
        return next
      })
    } finally {
      setStreaming(false)
    }
  }

  const handleFullAnalysis = async () => {
    setAnalyzing(true)
    try {
      const res = await aiApi.analyze({ date_preset: 'last_7d' })
      const { analysis, suggestions_created } = res.data

      setMessages((prev) => [
        ...prev,
        { role: 'user', content: '🤖 Análise automática de todas as campanhas (últimos 7 dias)', timestamp: new Date() },
        { role: 'assistant', content: analysis, timestamp: new Date() },
      ])

      if (suggestions_created > 0) {
        toast.success(`${suggestions_created} sugestão(ões) criada(s)! Confira em Aprovações.`)
        qc.invalidateQueries({ queryKey: ['pending-count'] })
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Erro na análise')
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <Layout>
      <div className="h-[calc(100vh-8rem)] flex flex-col gap-4">
        {/* Cabeçalho */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Bot size={24} className="text-brand-500" /> Chat IA
            </h1>
            <p className="text-sm text-gray-500">Converse com Claude sobre suas campanhas</p>
          </div>
          <button
            onClick={handleFullAnalysis}
            disabled={analyzing}
            className="btn-primary flex items-center gap-2 text-sm"
          >
            <Sparkles size={16} />
            {analyzing ? 'Analisando...' : 'Análise Completa'}
          </button>
        </div>

        {/* Área de mensagens */}
        <div className="flex-1 card overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center gap-6">
              <div className="w-16 h-16 bg-brand-50 rounded-2xl flex items-center justify-center">
                <Bot size={32} className="text-brand-500" />
              </div>
              <div>
                <p className="font-semibold text-gray-900 text-lg">Olá! Sou seu especialista em tráfego pago</p>
                <p className="text-gray-500 text-sm mt-1">Faça uma pergunta ou escolha um dos prompts abaixo</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-2xl">
                {QUICK_PROMPTS.map((p) => (
                  <button
                    key={p}
                    onClick={() => sendMessage(p)}
                    disabled={streaming}
                    className="text-left text-sm bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl px-4 py-3 transition-colors text-gray-700"
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={clsx('flex gap-3', msg.role === 'user' ? 'justify-end' : 'justify-start')}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 bg-brand-500 rounded-full flex items-center justify-center shrink-0 mt-1">
                  <Bot size={16} className="text-white" />
                </div>
              )}
              <div
                className={clsx(
                  'max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap',
                  msg.role === 'user'
                    ? 'bg-brand-500 text-white rounded-br-sm'
                    : 'bg-gray-100 text-gray-900 rounded-bl-sm'
                )}
              >
                {msg.content || (
                  <span className="flex items-center gap-1 text-gray-400">
                    <Loader2 size={14} className="animate-spin" /> Pensando...
                  </span>
                )}
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center shrink-0 mt-1">
                  <User size={16} className="text-gray-600" />
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Pergunte sobre suas campanhas..."
            disabled={streaming}
            className="flex-1 border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-brand-500 bg-white disabled:opacity-50"
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || streaming}
            className="btn-primary px-5 rounded-xl"
          >
            {streaming ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </div>
      </div>
    </Layout>
  )
}
