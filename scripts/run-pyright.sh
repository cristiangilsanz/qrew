#!/usr/bin/env bash
set -e
cd apps/api/services/identity  && ~/.local/bin/uv run pyright && cd - &&
cd apps/api/services/catalog   && ~/.local/bin/uv run pyright && cd - &&
cd apps/api/services/sales     && ~/.local/bin/uv run pyright && cd - &&
cd apps/api/services/payments  && ~/.local/bin/uv run pyright && cd - &&
cd apps/api/services/ticketing && ~/.local/bin/uv run pyright && cd - &&
cd apps/api/services/entry     && ~/.local/bin/uv run pyright && cd - &&
cd apps/api/services/audit     && ~/.local/bin/uv run pyright && cd - &&
cd apps/api/gateway            && ~/.local/bin/uv run pyright
