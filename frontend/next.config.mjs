/** Log da URL em tempo de build para auditoria */
console.log('NEXT_PUBLIC_API_URL at build time:', process.env.NEXT_PUBLIC_API_URL);

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    domains: ['localhost'],
    unoptimized: process.env.NODE_ENV === 'development'
  },
  /**
   * Força a URL da API a vir do ambiente do Railway.
   * Sem fallback para localhost para evitar builds com URL errada.
   */
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL
  }
};

export default nextConfig;
