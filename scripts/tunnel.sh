#!/bin/bash
# starts the named cloudflare tunnel and restarts the identity and gateway services with the tunnel domain injected

set -e

CLOUDFLARED="${HOME}/.local/bin/cloudflared"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IDENTITY_DIR="${REPO_ROOT}/apps/api/services/identity"
GATEWAY_DIR="${REPO_ROOT}/apps/api/gateway"

TUNNEL_URL="https://qrew-dev.uk"
TUNNEL_HOST="qrew-dev.uk"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Tunnel URL: ${TUNNEL_URL}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$1" = "--restart" ]; then
  echo "Restarting identity service..."
  pkill -f "uvicorn.*identity" 2>/dev/null || true
  sleep 1
  cd "${IDENTITY_DIR}"
  RP_ID="${TUNNEL_HOST}" \
  RP_EXPECTED_ORIGIN="${TUNNEL_URL}" \
  BASE_URL="${TUNNEL_URL}" \
  CORS_ORIGINS='["http://localhost:5173","'"${TUNNEL_URL}"'"]' \
    uv run uvicorn com.qode.qrew.v1.identity.app:app \
      --reload --host 127.0.0.1 --port 8001 &
  IDENTITY_PID=$!

  echo "Restarting gateway..."
  pkill -f "uvicorn.*gateway" 2>/dev/null || true
  sleep 1
  cd "${GATEWAY_DIR}"
  CORS_ORIGINS='["http://localhost:5173","'"${TUNNEL_URL}"'"]' \
    uv run uvicorn com.qode.qrew.v1.gateway.app:app \
      --reload --host 127.0.0.1 --port 8000 &
  GATEWAY_PID=$!

  echo ""
  echo "Services restarted with tunnel config."
  echo ""
fi

echo "Open on your phone:"
echo ""
echo "  ${TUNNEL_URL}"
echo ""
echo "Press Ctrl+C to stop the tunnel."
echo ""

# stops the tunnel and any services it restarted
cleanup() {
  echo ""
  echo "Stopping tunnel..."
  kill "${CF_PID}" 2>/dev/null || true
  if [ -n "${IDENTITY_PID}" ]; then kill "${IDENTITY_PID}" 2>/dev/null || true; fi
  if [ -n "${GATEWAY_PID}" ]; then kill "${GATEWAY_PID}" 2>/dev/null || true; fi
  echo "Done."
}
trap cleanup EXIT INT TERM

"${CLOUDFLARED}" tunnel run qrew-dev &
CF_PID=$!

wait "${CF_PID}"
