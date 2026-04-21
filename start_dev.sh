#!/bin/bash
# Arranca Cloudflare Tunnel, captura la URL, actualiza .env, luego levanta uvicorn.
# Uso: bash start_dev.sh

set -e

LOG=/tmp/cf_tunnel.log

# Limpiar log anterior
> "$LOG"

echo "🌐 Iniciando Cloudflare Tunnel..."
cloudflared tunnel --url http://localhost:8000 > "$LOG" 2>&1 &
CF_PID=$!

# Esperar hasta que cloudflared imprima la URL (máx 30s)
URL=""
for i in $(seq 1 30); do
    URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG" | head -1)
    if [ -n "$URL" ]; then
        break
    fi
    sleep 1
done

if [ -z "$URL" ]; then
    echo "❌ Timeout esperando URL de Cloudflare. Ver log: $LOG"
    kill "$CF_PID" 2>/dev/null
    exit 1
fi

echo "✅ Tunnel activo: $URL"

# Actualizar WEBHOOK_BASE_URL en .env
if grep -q "^WEBHOOK_BASE_URL=" .env; then
    sed -i "s|^WEBHOOK_BASE_URL=.*|WEBHOOK_BASE_URL=$URL|" .env
else
    echo "WEBHOOK_BASE_URL=$URL" >> .env
fi

echo "✅ .env actualizado"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Slack App > Interactivity > Request URL:"
echo "  $URL/slack/interactive"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Iniciar uvicorn (foreground — Ctrl+C para parar todo)
trap "kill $CF_PID 2>/dev/null; echo '🛑 Tunnel cerrado'" EXIT
echo "🚀 Iniciando webhook server en :8000..."
uvicorn api.slack_webhook:app --reload --port 8000
