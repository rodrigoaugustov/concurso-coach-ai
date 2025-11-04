# Usa a imagem oficial do Node.js
FROM node:20-alpine AS base

# Define o diretório de trabalho
WORKDIR /app

# Instalar dependências apenas se package.json mudou
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# --- Build ---
FROM base AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Build da aplicação para produção
RUN npm run build

# --- Runner ---
FROM base AS runner
WORKDIR /app

# Criar usuário não-root para segurança
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copiar arquivos necessários do builder
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Mudar para usuário não-root
USER nextjs

# Expor porta (Railway usará a variável PORT)
EXPOSE 3000

# Definir variável de ambiente
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Comando para iniciar o servidor - Railway definirá PORT automaticamente
CMD ["node", "server.js"]