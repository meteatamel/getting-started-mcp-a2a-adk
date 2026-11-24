#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-europe-west1}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Error: PROJECT_ID is not set. Run 'export PROJECT_ID=<your-project-id>' or 'gcloud config set project <your-project-id>'."
  exit 1
fi

echo "🚀 Deploying Java multi-agent system to Cloud Run (project: $PROJECT_ID, region: $REGION)"

echo ""
echo "=== 1/3 Deploying currency-mcp-server ==="
gcloud run deploy currency-mcp-server \
  --source currency_mcp_server \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --allow-unauthenticated

MCP_SERVER_URL="$(gcloud run services describe currency-mcp-server --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)')/mcp"
echo "✅ MCP_SERVER_URL=$MCP_SERVER_URL"

echo ""
echo "=== 2/3 Deploying currency-agent ==="
gcloud run deploy currency-agent \
  --source currency_agent \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --allow-unauthenticated \
  --update-env-vars "MCP_SERVER_URL=${MCP_SERVER_URL},GOOGLE_GENAI_USE_ENTERPRISE=true,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=global"

CURRENCY_AGENT_URL="$(gcloud run services describe currency-agent --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)')"
gcloud run services update currency-agent \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --update-env-vars "AGENT_URL=${CURRENCY_AGENT_URL}"
echo "✅ CURRENCY_AGENT_URL=$CURRENCY_AGENT_URL"

echo ""
echo "=== 3/3 Deploying travel-agent ==="
gcloud run deploy travel-agent \
  --source travel_agent \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --allow-unauthenticated \
  --update-env-vars "CURRENCY_AGENT_URL=${CURRENCY_AGENT_URL},GOOGLE_GENAI_USE_ENTERPRISE=true,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=global"

TRAVEL_AGENT_URL="$(gcloud run services describe travel-agent --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)')"
gcloud run services update travel-agent \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --update-env-vars "AGENT_URL=${TRAVEL_AGENT_URL}"
echo "✅ TRAVEL_AGENT_URL=$TRAVEL_AGENT_URL"

cat > .env.cloudrun <<EOF
export PROJECT_ID="${PROJECT_ID}"
export REGION="${REGION}"
export MCP_SERVER_URL="${MCP_SERVER_URL}"
export CURRENCY_AGENT_URL="${CURRENCY_AGENT_URL}"
export TRAVEL_AGENT_URL="${TRAVEL_AGENT_URL}"
EOF

echo ""
echo "🎉 All three services deployed! Load the URLs into your shell with:"
echo "   source .env.cloudrun"
