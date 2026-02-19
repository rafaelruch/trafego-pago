/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    // http://backend:8000 é o hostname Docker interno (nome do serviço no docker-compose)
    // Avaliado no BUILD TIME e gravado no routes-manifest.json
    // Funciona tanto no local (docker-compose) quanto no EasyPanel
    return [
      {
        source: '/api/:path*',
        destination: 'http://backend:8000/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig
