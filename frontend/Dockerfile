# Imagem "final" do frontend — build de produção do Vite, servido
# por Nginx. Diferente do dia a dia de desenvolvimento (Vite dev server com
# HMR via `npm run dev`, ver README.md na raiz), este é o artefato estático
# otimizado, do jeito que rodaria atrás de qualquer servidor web de verdade.

FROM node:22-slim AS build
WORKDIR /app

# Copiado antes do resto do código de propósito: o cache de camadas do Docker
# só reinstala as dependências quando o lockfile muda, não a cada alteração
# de código.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# O Vite embute toda variável VITE_* no bundle em tempo de BUILD (não dá pra
# trocar depois, em runtime, como seria com uma variável de ambiente comum)
# — por isso precisa ser um build ARG, não uma ENV do container final.
ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
