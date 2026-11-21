# Railway rootDirectory=/backend: admin-web is outside Docker context.
# Run backend/scripts/build-admin-spa.sh before image build, or use repo-root Dockerfile (multi-stage).
# CI (.github/workflows/ci.yml) builds admin-web before pytest/deploy artifacts.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Production must set ADMIN_API_KEY / DEVICE_API_KEY (and Integrity vars as needed).
# Do not set ELDERSHIELD_ALLOW_INSECURE_DEFAULTS or ENROLL_SKIP_INTEGRITY in prod.
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
