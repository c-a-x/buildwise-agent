FROM node:22-alpine AS build

WORKDIR /app
ARG VITE_API_BASE_URL=/api/v1
ARG NPM_REGISTRY=https://registry.npmmirror.com
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
COPY package*.json ./
RUN npm ci --registry="${NPM_REGISTRY}" --fetch-retries=5 --fetch-retry-factor=2 --fetch-retry-mintimeout=1000 --fetch-retry-maxtimeout=120000 --fetch-timeout=120000 --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
