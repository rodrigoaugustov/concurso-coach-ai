/** @type {import('next').NextConfig} */
const nextConfig = {
  // Configuração para produção no Railway
  output: 'standalone',
  
  // Configurações de imagem para otimização
  images: {
    domains: ['localhost'],
    unoptimized: process.env.NODE_ENV === 'development'
  },
  
  // Configurações para desenvolvimento local ainda funcionarem
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
  },
  
  // Configurações para Railway
  experimental: {
    serverComponentsExternalPackages: []
  }
};

export default nextConfig;