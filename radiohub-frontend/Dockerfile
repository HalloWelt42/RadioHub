FROM node:20-slim AS builder

WORKDIR /app

# Install curl for font downloads
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Dependencies
COPY package.json ./
RUN npm install

# Source
COPY . .

# Download fonts locally (no external CDN at runtime)
RUN chmod +x download-fonts.sh && ./download-fonts.sh

# Build
RUN npm run build

# Production
FROM nginx:alpine

# Config mit CORS
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Built files
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
