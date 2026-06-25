#!/usr/bin/env bash
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$REPO_ROOT/docs/openapi"

declare -A SERVICES=(
  [identity]="services/identity:com.qode.qrew.v1.identity.app"
  [catalog]="services/catalog:com.qode.qrew.v1.catalog.app"
  [entry]="services/entry:com.qode.qrew.v1.entry.app"
  [payments]="services/payments:com.qode.qrew.v1.payments.app"
  [sales]="services/sales:com.qode.qrew.v1.sales.app"
  [ticketing]="services/ticketing:com.qode.qrew.v1.ticketing.app"
  [audit]="services/audit:com.qode.qrew.v1.audit.app"
  [gateway]="gateway:com.qode.qrew.v1.gateway.app"
)

for svc in "${!SERVICES[@]}"; do
  IFS=':' read -r path module <<< "${SERVICES[$svc]}"
  echo "Exporting $svc..."
  PYTHONPATH="$REPO_ROOT/$path/src" uv run --package "$svc" python -c "
import json
from $module import app
with open('$OUT_DIR/$svc.json', 'w') as f:
    json.dump(app.openapi(), f, indent=2)
"
  echo "  -> docs/openapi/$svc.json"
done

echo ""
echo "Done. All OpenAPI specs exported to docs/openapi/"
