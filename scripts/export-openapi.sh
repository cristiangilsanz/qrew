#!/usr/bin/env bash
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$REPO_ROOT/docs/openapi"
CONTRACTS_SRC="$REPO_ROOT/packages/contracts/src"

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

# Services that publish domain events (name maps to contracts.events.<name>)
declare -A SERVICE_EVENTS=(
  [identity]="identity"
  [catalog]="catalog"
  [entry]="entry"
  [payments]="payments"
  [sales]="sales"
  [ticketing]="ticketing"
)

echo "Exporting OpenAPI specs..."
echo ""

for svc in "${!SERVICES[@]}"; do
  IFS=':' read -r path module <<< "${SERVICES[$svc]}"
  svc_dir="$OUT_DIR/$svc"

  if [[ -n "${SERVICE_EVENTS[$svc]+x}" ]]; then
    mkdir -p "$svc_dir/events"
  else
    mkdir -p "$svc_dir"
  fi

  echo "[$svc] OpenAPI spec..."
  PYTHONPATH="$REPO_ROOT/$path/src" uv run --package "$svc" python -c "
import yaml
from $module import app

spec = app.openapi()
with open('$svc_dir/openapi.yaml', 'w') as f:
    yaml.dump(spec, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
"
  echo "  -> docs/openapi/$svc/openapi.yaml"
done

echo ""
echo "Exporting event schemas..."
echo ""

for svc in "${!SERVICE_EVENTS[@]}"; do
  events_module="${SERVICE_EVENTS[$svc]}"
  events_dir="$OUT_DIR/$svc/events"

  echo "[$svc] event schemas..."
  PYTHONPATH="$CONTRACTS_SRC" uv run --package contracts python -c "
import json, inspect
import contracts.events.$events_module as mod
from pydantic import BaseModel

for name, cls in inspect.getmembers(mod, inspect.isclass):
    if issubclass(cls, BaseModel) and cls is not BaseModel and name.endswith('Data'):
        event_name = name.removesuffix('Data')
        schema = cls.model_json_schema()
        schema['\$schema'] = 'https://json-schema.org/draft/2020-12/schema'
        schema['title'] = event_name
        out_path = '$events_dir/' + event_name + '.schema.json'
        with open(out_path, 'w') as f:
            json.dump(schema, f, indent=2)
        print(f'  -> docs/openapi/$svc/events/{event_name}.schema.json')
"
done

echo ""
echo "Done. All specs exported to docs/openapi/"
