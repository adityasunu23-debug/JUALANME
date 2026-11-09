# dashboard/Dockerfile — Next.js 14 (app dir) multi-stage build
# Assumes standard package.json scripts: `next build` / `next start`.

# ---------- deps ----------
FROM node:20-alpine AS deps
WORKDIR /app
COPY dashboard/package.json dashboard/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# ---------- build ----------
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY dashboard/ .
# NEXT_PUBLIC_API_URL is inlined at build time (nginx proxies /api -> backend).
ENV NEXT_PUBLIC_API_URL=/api \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---------- runtime ----------
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 --ingroup nodejs nextjs

COPY --from=builder --chown=nextjs:nodejs /app/package.json ./package.json
COPY --from=builder --chown=nextjs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
RUN mkdir -p /app/public && chown -R nextjs:nodejs /app/public

USER nextjs
EXPOSE 3000

CMD ["npm", "run", "start"]
