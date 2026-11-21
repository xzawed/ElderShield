#!/usr/bin/env sh
# Build admin-web into backend/app/static/admin-spa (run from repo root or anywhere).
set -e
SCRIPT_DIR="$(CDPATH= cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd "$SCRIPT_DIR/../.." && pwd)"
ADMIN_WEB="$REPO_ROOT/admin-web"

if [ ! -f "$ADMIN_WEB/package.json" ]; then
  echo "build-admin-spa: missing $ADMIN_WEB/package.json (expected monorepo layout)" >&2
  exit 1
fi

cd "$ADMIN_WEB"
npm ci
npm run build
echo "build-admin-spa: wrote $REPO_ROOT/backend/app/static/admin-spa"