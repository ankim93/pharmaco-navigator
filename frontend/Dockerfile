# Stage 1 - Compiler:Compiles the React/Vite/Tailwind application into static production assets.
FROM node:22-alpine AS compiler

WORKDIR /build

# Copy package manifests first to maximise Docker layer caching.
COPY package.json package-lock.json ./

# Clean, reproducible install from the lock file (no package-lock mutations).
RUN npm ci

# Copy the rest of the source tree and build the production bundle.
# Vite outputs compiled assets to /build/dist by default.
COPY . .

RUN npm run build

# Stage 2 - Production Server: Minimal Nginx Alpine image that serves only the compiled static assets.
FROM nginx:alpine AS runner

# Nginx listens on port 80 inside the container; map host port as needed via docker-compose.

# Copy the compiled distribution assets from the compiler stage.
COPY --from=compiler /build/dist /usr/share/nginx/html

EXPOSE 80

# Run Nginx in the foreground so the container stays alive.
CMD ["nginx", "-g", "daemon off;"]
