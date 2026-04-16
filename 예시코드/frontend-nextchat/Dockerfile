# frontend-nextchat/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# 의존성 파일을 먼저 복사하여 레이어 캐시를 활용한다.
COPY package.json package-lock.json ./
RUN npm ci

# 소스 코드를 복사하고 빌드한다.
COPY . .
RUN npm run build

# ─── 실행 단계 ───
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# 빌드 결과물만 복사한다.
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
