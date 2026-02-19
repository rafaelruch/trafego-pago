/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    // BACKEND_URL é lida em runtime pelo servidor Next.js (não é baked no build)
    // Dentro do Docker: http://backend:8000
    // Desenvolvimento local sem Docker: http://localhost:8000
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
