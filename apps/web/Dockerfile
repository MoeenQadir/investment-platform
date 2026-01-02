FROM node:18-alpine AS base

# Install pnpm
RUN npm install -g pnpm

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml* package-lock.json* ./

# Install dependencies
# Use npm if pnpm-lock.yaml doesn't exist, otherwise use pnpm
RUN if [ -f pnpm-lock.yaml ]; then \
      pnpm install --frozen-lockfile; \
    else \
      npm install; \
    fi

# Copy application files
COPY . .

# Development stage
FROM base AS development
EXPOSE 3000
# Default to pnpm if available, fallback to npm
CMD ["sh", "-c", "if [ -f pnpm-lock.yaml ]; then pnpm run dev; else npm run dev; fi"]

# Production build stage
FROM base AS build
RUN if [ -f pnpm-lock.yaml ]; then pnpm run build; else npm run build; fi

# Production runtime stage (using Next.js standalone output)
FROM node:18-alpine AS production

WORKDIR /app

ENV NODE_ENV=production

# Copy standalone build from build stage
# Next.js standalone output includes all necessary files
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]

