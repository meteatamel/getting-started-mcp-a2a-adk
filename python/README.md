# Productionizing MCP, A2A & ADK on Google Cloud (Python)

This guide walks through deploying the **Part 2 (`production` branch)** multi-agent system on Google Cloud with **Agent Runtime**, **Agent Registry**, **Agent Identity**, **Agent Gateway + Model Armor**, **Observability**, and **Evaluation**.

> [!NOTE]
> Local development works identically to Part 1: when `MCP_SERVER_NAME` and `CURRENCY_AGENT_NAME` are not set, both agents automatically fall back to `http://localhost:8080/mcp` and `http://localhost:8081`.

---

## 🚀 Prerequisites & Setup

```bash
git checkout production
cd python
uv sync
```

Set your environment variables:

```bash
export PROJECT_ID=<YOUR_GOOGLE_CLOUD_PROJECT_ID>
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export REGION=us-central1
gcloud config set project $PROJECT_ID
```

Enable the required Google Cloud APIs:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  agentregistry.googleapis.com \
  modelarmor.googleapis.com \
  networkservices.googleapis.com \
  networksecurity.googleapis.com \
  cloudtrace.googleapis.com
```

---

## 1. Deploy & Auto-Register the MCP Server on Cloud Run

**What this adds:** Locks down `currency-mcp-server` with `--no-allow-unauthenticated` (no public access) and automatically catalogs it in **Agent Registry** using `--functional-type=mcp-server` so downstream agents can discover it without hardcoded URLs.

```bash
gcloud beta run deploy currency-mcp-server \
  --source currency_mcp_server \
  --region $REGION \
  --no-allow-unauthenticated \
  --functional-type=mcp-server
```

Verify that the MCP server was automatically registered in Agent Registry (and note its resource name, e.g., `mcpServers/<SERVER_ID>`):

```bash
gcloud agent-registry mcp-servers list --location=$REGION
export MCP_SERVER_NAME="mcpServers/<SERVER_ID>"
```

---

## 2. Deploy `currency_agent` to Agent Runtime with Agent Identity & Observability

**What this adds:**
- **Agent Runtime**: Managed hosting for ADK agents with built-in scaling and automatic Agent Registry registration.
- **Agent Identity** (`.agent_engine_config.json` with `"identity_type": "AGENT_IDENTITY"`): Gives `currency_agent` its own unique, managed cryptographic principal instead of sharing a broad service account.
- **Agent Registry (`AgentRegistry.get_mcp_toolset`)**: Resolves `currency-mcp-server` dynamically and handles authentication automatically.
- **Observability (`--otel_to_cloud`)**: Exports OpenTelemetry traces to Cloud Trace and Agent Platform Observability.

Deploy `currency_agent`:

```bash
MCP_SERVER_NAME="$MCP_SERVER_NAME" \
AGENT_REGISTRY_LOCATION="$REGION" \
uv run adk deploy agent_engine \
  --project=$PROJECT_ID \
  --region=$REGION \
  --display_name="currency-agent" \
  --otel_to_cloud \
  --agent_engine_config_file=currency_agent/.agent_engine_config.json \
  currency_agent
```

Capture `currency_agent`'s Agent Engine ID and grant its **Agent Identity** least-privilege permissions (`roles/run.invoker` on `currency-mcp-server` and `roles/agentregistry.viewer`):

```bash
export CURRENCY_AGENT_ENGINE_ID=<CURRENCY_AGENT_ENGINE_ID>
export CURRENCY_AGENT_PRINCIPAL="principal://agents.global.proj-${PROJECT_NUMBER}.system.id.goog/resources/aiplatform/projects/${PROJECT_NUMBER}/locations/${REGION}/reasoningEngines/${CURRENCY_AGENT_ENGINE_ID}"
# Note: For projects inside a Google Cloud Organization, replace `proj-${PROJECT_NUMBER}` with `org-${ORG_ID}`.

gcloud run services add-iam-policy-binding currency-mcp-server \
  --region=$REGION \
  --member="$CURRENCY_AGENT_PRINCIPAL" \
  --role="roles/run.invoker"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="$CURRENCY_AGENT_PRINCIPAL" \
  --role="roles/agentregistry.viewer"
```

---

## 3. Deploy `travel_agent` with Dynamic A2A Discovery

**What this adds:** `travel_agent` looks up `currency_agent` dynamically from **Agent Registry** via `registry.get_remote_a2a_agent(...)`, runs under its own separate **Agent Identity**, and exports distributed traces linked across both agents.

Look up `currency_agent`'s Agent Registry resource name:

```bash
gcloud agent-registry agents list --location=$REGION
export CURRENCY_AGENT_NAME="agents/<AGENT_ID>"
```

Deploy `travel_agent`:

```bash
CURRENCY_AGENT_NAME="$CURRENCY_AGENT_NAME" \
AGENT_REGISTRY_LOCATION="$REGION" \
uv run adk deploy agent_engine \
  --project=$PROJECT_ID \
  --region=$REGION \
  --display_name="travel-agent" \
  --otel_to_cloud \
  --agent_engine_config_file=travel_agent/.agent_engine_config.json \
  travel_agent
```

Grant `travel_agent`'s **Agent Identity** permission to query Agent Registry and invoke `currency_agent`:

```bash
export TRAVEL_AGENT_ENGINE_ID=<TRAVEL_AGENT_ENGINE_ID>
export TRAVEL_AGENT_PRINCIPAL="principal://agents.global.proj-${PROJECT_NUMBER}.system.id.goog/resources/aiplatform/projects/${PROJECT_NUMBER}/locations/${REGION}/reasoningEngines/${TRAVEL_AGENT_ENGINE_ID}"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="$TRAVEL_AGENT_PRINCIPAL" \
  --role="roles/agentregistry.viewer"
```

---

## 4. Govern Traffic with Agent Gateway & Model Armor

**What this adds:**
- **Agent Gateway**: Central policy enforcement point for both **Client-to-Agent (ingress)** and **Agent-to-Anywhere (egress)** traffic. Egress gateways default to **deny-all** until an explicit `AuthzPolicy` allows approved traffic.
- **Model Armor**: Inspects and sanitizes prompts and tool responses in flight to block prompt injections, jailbreaks, and PII leakage.

Import the gateway YAML templates from [`policies/`](../policies/):

```bash
# 1. Client-to-Agent (ingress) gateway
gcloud network-services agent-gateways import travel-agent-ingress-gateway \
  --source=../policies/agent-gateway-ingress.yaml \
  --location=$REGION

# 2. Agent-to-Anywhere (egress) gateway wired to Agent Registry
envsubst < ../policies/agent-gateway-egress.yaml > /tmp/agent-gateway-egress.yaml
gcloud network-services agent-gateways import travel-agent-egress-gateway \
  --source=/tmp/agent-gateway-egress.yaml \
  --location=$REGION
```

Create a **Model Armor** template (with prompt-injection & jailbreak detection) and attach it to your gateway in the Google Cloud Console (**Gemini Enterprise Agent Platform → Governance → Agent Gateway**) or via `gcloud model-armor templates create`.

---

## 5. Observability & Evaluation

### Observability
**What this adds:** Because both agents were deployed with `--otel_to_cloud`, every request generates an end-to-end OpenTelemetry trace in **Cloud Trace** and **Agent Platform Observability**—showing `travel_agent` LLM calls, in-process `weather_agent` execution, remote A2A delegation to `currency_agent`, and the MCP tool call to `currency_mcp_server`.

### Automated Evaluation (`adk eval`)
**What this adds:** Prevents silent regressions when you change prompts, models, or tools by verifying both **tool trajectory** (did `travel_agent` call `weather_agent` and `currency_agent`?) and **response quality**.

With the three services running locally (`currency_mcp_server`, `currency_agent`, `travel_agent`), run the evaluation suite in [`evals/`](evals/):

```bash
uv run adk eval \
  travel_agent \
  evals/travel_agent.evalset.json \
  --config_file_path=evals/test_config.json \
  --print_detailed_results
```

You can also run offline, online, and simulated evaluations directly on your deployed Agent Runtime instance in the **Agent Platform Evaluation** console using trajectory metrics (`trajectory_any_order_match`, `trajectory_precision`, `trajectory_recall`).
