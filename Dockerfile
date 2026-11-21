# Monorepo root build context: admin SPA + backend (use when Railway rootDirectory is repo root).
FROM node:20-alpine AS admin-build

WORKDIR /src/admin-web

COPY admin-web/package.json admin-web/package-lock.json ./
RUN npm ci

COPY admin-web/ ./
RUN npm run build

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=admin-build /src/backend/app/static/admin-spa ./app/static/admin-spa

EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]