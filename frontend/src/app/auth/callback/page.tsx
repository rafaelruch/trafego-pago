'use client'
import { Suspense, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

function CallbackHandler() {
  const router = useRouter()
  const params = useSearchParams()

  useEffect(() => {
    const token = params.get('token')
    const code = params.get('code')
    const state = params.get('state')

    if (token) {
      // Fluxo completo: backend processou o code e devolveu o JWT
      localStorage.setItem('token', token)
      router.replace('/')
    } else if (code) {
      // Meta redirecionou para o frontend com o code OAuth
      // Repassa para o backend via proxy Next.js (/api → http://backend:8000/api)
      const qs = state ? `code=${code}&state=${state}` : `code=${code}`
      window.location.replace(`/api/auth/callback?${qs}`)
    } else {
      router.replace('/login?error=auth_failed')
    }
  }, [params, router])

  return null
}

export default function AuthCallback() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-600">Conectando ao Meta ADS...</p>
      </div>
      <Suspense fallback={null}>
        <CallbackHandler />
      </Suspense>
    </div>
  )
}
