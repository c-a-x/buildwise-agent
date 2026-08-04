FROM node:20-alpine AS build

WORKDIR /app
ARG VITE_API_BASE_URL=/api/v1
ARG NPM_REGISTRY=https://registry.npmmirror.com
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
COPY package*.json ./
COPY .npm-cache-slim /root/.npm
COPY .docker-native /tmp/docker-native
RUN if test -d /root/.npm/_cacache; then \
        npm ci --offline --no-audit --no-fund || \
        npm ci --registry="${NPM_REGISTRY}" --fetch-retries=5 --fetch-retry-factor=2 --fetch-retry-mintimeout=1000 --fetch-retry-maxtimeout=120000 --fetch-timeout=120000 --no-audit --no-fund; \
    else \
        npm ci --registry="${NPM_REGISTRY}" --fetch-retries=5 --fetch-retry-factor=2 --fetch-retry-mintimeout=1000 --fetch-retry-maxtimeout=120000 --fetch-timeout=120000; \
    fi \
    && if find /tmp/docker-native -maxdepth 1 -type f -name '*.tgz' | grep -q .; then \
        npm install --no-save --package-lock=false --ignore-scripts --no-audit --no-fund /tmp/docker-native/*.tgz; \
    else \
        npm install --no-save --package-lock=false --ignore-scripts --no-audit --no-fund --registry="${NPM_REGISTRY}" \
            lightningcss-linux-x64-musl@1.33.0 \
            @rolldown/binding-linux-x64-musl@1.2.1 \
            @oxfmt/binding-linux-x64-musl@0.59.0; \
    fi \
    && rm -rf /root/.npm /tmp/docker-native
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
