#!/usr/bin/env bash
set -e
cd services/identity  && ~/.local/bin/uv run pyright && cd - &&
cd services/catalog   && ~/.local/bin/uv run pyright && cd - &&
cd services/sales     && ~/.local/bin/uv run pyright && cd - &&
cd services/payments  && ~/.local/bin/uv run pyright && cd - &&
cd services/ticketing && ~/.local/bin/uv run pyright && cd - &&
cd services/entry     && ~/.local/bin/uv run pyright && cd - &&
cd services/audit     && ~/.local/bin/uv run pyright && cd - &&
cd gateway            && ~/.local/bin/uv run pyright
