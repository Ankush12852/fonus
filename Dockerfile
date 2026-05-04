# ============================================================
# FONUS Frontend — Dockerfile
#
# This builds the Next.js frontend into a container.
# It uses a multi-stage build to keep the final image small:
#   Stage 1 (builder): Install dependencies and build Next.js
#   Stage 2 (runner):  Only copy the built output — no dev tools
# ============================================================

# ── Stage 1: Builder ─────────────────────────────────────────
FROM node:20-alpine AS builder

# Set working directory inside the container
WORKDIR /app

# Copy package files first (Docker cache optimization)
COPY package.json package-lock.json ./

# Install all dependencies (including devDependencies for the build)
RUN npm ci --frozen-lockfile

# Copy the rest of the Next.js source code
COPY . .

# Build the Next.js production bundle
# This creates the .next/ folder with optimized output
RUN npm run build


# ── Stage 2: Runner ──────────────────────────────────────────
# This is the final, lean image that actually runs in production.
# It only has the built output — no source code, no dev tools.
FROM node:20-alpine AS runner

WORKDIR /app

# Create a non-root user for security
# Running as root inside Docker is a security risk.
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy only the built output from the builder stage
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Switch to the non-root user
USER nextjs

# Tell Docker this container uses port 3000
EXPOSE 3000

# Set the hostname so Next.js listens on all interfaces
ENV HOSTNAME="0.0.0.0"
ENV PORT=3000

# Start the Next.js server
CMD ["node", "server.js"]
