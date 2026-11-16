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

# Production
FROM nginx:alpine

# Config mit CORS
COPY radiohub-frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Built files
COPY --from=builder /bau/radiohub-frontend/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
