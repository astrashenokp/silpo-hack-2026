# Next.js frontend. Build from the repository root:
#   docker build -f deploy/web.Dockerfile --build-arg API_BASE_URL=http://api:8000 -t smart-basket-web .
# API_BASE_URL is baked into the /api rewrites at build time; `next start` ignores a runtime value.
FROM node:24-bookworm-slim AS build
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /repo/apps/web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
# apps/web/tsconfig.json maps @fixtures/* to ../../fixtures/* for the demo views.
COPY fixtures /repo/fixtures
COPY apps/web ./
ARG API_BASE_URL=http://api:8000
ENV API_BASE_URL=${API_BASE_URL}
RUN npm run build

FROM node:24-bookworm-slim
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1
WORKDIR /repo/apps/web
COPY --from=build /repo/apps/web ./
EXPOSE 3000
CMD ["npm", "run", "start", "--", "--port", "3000"]
