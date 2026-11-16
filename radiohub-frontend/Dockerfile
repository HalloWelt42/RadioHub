# Oberfläche von RadioHub. Gebaut aus dem Wurzelordner des Repos (docker-compose.yml, compose.pi.yml: context .), damit
# version.json, die einzige Quelle der Fassung, beim Bauen bereitliegt (vite.config.js liest ../version.json).
FROM node:20-slim AS builder

WORKDIR /bau/radiohub-frontend

# Install curl for font downloads
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Abhängigkeiten genau nach package-lock.json (npm install ohne Sperrdatei löst jedes Mal neu auf und scheiterte)
COPY radiohub-frontend/package.json radiohub-frontend/package-lock.json ./
RUN npm ci

# Quellen und Fassung
COPY version.json /bau/
COPY radiohub-frontend/ ./

# Download fonts locally (no external CDN at runtime)
RUN chmod +x download-fonts.sh && ./download-fonts.sh

# Build
RUN npm run build

# Auslieferung ohne root: nginx-unprivileged läuft als Nutzer nginx (101) und lauscht auf 8080
FROM nginxinc/nginx-unprivileged:1.28-alpine

COPY radiohub-frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Built files
COPY --from=builder /bau/radiohub-frontend/dist /usr/share/nginx/html

# Nur im Netz der Container (vor der Oberfläche steht der Vorschaltdienst)
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
