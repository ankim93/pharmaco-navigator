# Stage 1: Compiler — build the Vite production bundle
FROM node:22-alpine AS compiler

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

COPY . .
RUN npm run build


# Stage 2: Server — serve static assets from nginx on port 3000
FROM nginx:alpine AS server

# Remap nginx from port 80 to port 3000 to match compose/k8s conventions
RUN sed -i 's/listen\s*80;/listen 3000;/g' /etc/nginx/conf.d/default.conf && \
    sed -i 's/listen\s*\[::\]:80;/listen [::]:3000;/g' /etc/nginx/conf.d/default.conf

COPY --from=compiler /app/dist /usr/share/nginx/html

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
