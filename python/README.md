# Getting Started with MCP & A2A with ADK (Python)

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-ADK-4285F4.svg)](https://github.com/google/adk-python)
[![Protocol](https://img.shields.io/badge/Protocol-A2A-34A853.svg)](https://github.com/a2aproject/a2a-python)
[![Protocol](https://img.shields.io/badge/Protocol-MCP-EA4335.svg)](https://modelcontextprotocol.io/)

This directory contains the **Python** implementation of the MCP + A2A + ADK multi-agent system. See the [top-level README](../README.md) for the architecture overview and the [deployed codelab](https://codelabs.developers.google.com/getting-started-mcp-a2a-adk).

---

## 📦 Dependency Management (`uv` Workspace)

Project dependencies are organized as a unified **`uv` Workspace**:
- Root `pyproject.toml` orchestrates workspace members (`currency_mcp_server`, `currency_agent`, `travel_agent`).
- Running `uv sync` at the `python/` root automatically resolves and installs all packages for local development into a single `.venv`.
- Each service directory has its own self-contained `pyproject.toml` and `Dockerfile` for independent Cloud Run builds.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation):
  ```bash
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Google Cloud SDK (`gcloud`) if deploying to Cloud Run.

### Installation

1. Clone the repository and navigate to the `python` folder:
   ```bash
   git clone https://github.com/meteatamel/getting-started-mcp-a2a-adk.git
   cd getting-started-mcp-a2a-adk/python
   ```

2. Install all dependencies across the workspace:
   ```bash
   uv sync
   ```

3. Configure Environment Variables:
   Create a `.env` file in the `python/` directory (or copy `.env.example` to `.env`).

   **Option A: Google AI Studio**
   ```sh
   GOOGLE_API_KEY=<your_api_key_here>
   GOOGLE_GENAI_USE_ENTERPRISE=FALSE
   ```

   **Option B: Gemini Enterprise (Google Cloud)**
   ```sh
   GOOGLE_GENAI_USE_ENTERPRISE=TRUE
   GOOGLE_CLOUD_PROJECT=<your_gcp_project_id>
   GOOGLE_CLOUD_LOCATION=global
   ```

---

## 💻 Local Execution

You can run all three services concurrently in separate terminal windows from the `python/` directory. Make sure to run them in the order of MCP server first, then currency agent, then travel agent.

### Step 1: Start Currency MCP Server

Start MCP server locally in terminal 1:

```bash
uv run python currency_mcp_server/server.py
```

### Step 2: Start Currency Agent

Start agent locally in terminal 2:

```bash
uv run python currency_agent/agent.py
```

### Step 3: Start Travel Agent

Start travel agent locally in terminal 3 (starts the ADK Web UI on port 8082):

```bash
uv run python travel_agent/agent.py
```

*(Alternatively, you can run `uv run adk web travel_agent` to launch it on port 8000).*

### 🧪 Testing

Test the MCP server:

```bash
uv run python currency_mcp_server/test_server.py
```

Test the currency agent (over A2A protocol):

```bash
uv run python currency_agent/test_a2aclient.py
```

Test the travel agent (Interactive ADK Web UI):

Open your browser at `http://localhost:8082` (or `http://localhost:8000` if using `adk web`) and chat with `travel_agent`:
> *"I'm planning a trip to London. What is the weather like and how much is 200 EUR in GBP?"*

This runs end-to-end:
1. Queries travel and currency conversion (delegated via A2A to `currency_agent` -> `currency_mcp_server`).
2. Queries weather forecasts (delegated to local `weather_agent` in `travel_agent/subagents/`).

You can also test queries directly from the command line:

```bash
uv run adk run travel_agent "What is the weather in London and how much is 100 USD in EUR?"
```

---

## ☁️ Cloud Run Deployment

All three components include optimized Dockerfiles and can be deployed directly from source to Cloud Run. You can use `gcloud` to automatically capture service URLs and wire them into the next steps without manual copy-pasting.

First, set some environment variables for your Google Cloud project and Cloud Run region:

```bash
export PROJECT_ID=<YOUR_GOOGLE_CLOUD_PROJECT_ID>
export REGION=europe-west1
```

Enable the required Google Cloud APIs for Cloud Run, Cloud Build, Artifact Registry, and Vertex AI:

```bash
gcloud services enable run.googleapis.com \
                       cloudbuild.googleapis.com \
                       artifactregistry.googleapis.com \
                       aiplatform.googleapis.com
```

> [!WARNING]
> For simplicity in this initial deployment, services are deployed with `--allow-unauthenticated`. See the optional **[Securing Cloud Run Services (IAM Authentication)](#-optional-securing-cloud-run-services-iam-authentication)** section at the end of this guide to lock down all three services with dedicated service accounts and OIDC ID tokens.

### Step 1: Deploy Currency MCP Server

```bash
# Deploy MCP server
gcloud run deploy currency-mcp-server \
  --source currency_mcp_server \
  --region $REGION \
  --allow-unauthenticated

# Capture the deployed MCP server URL
MCP_SERVER_URL=$(gcloud run services describe currency-mcp-server --region $REGION --format='value(status.url)')/mcp
echo "MCP Server URL: $MCP_SERVER_URL"
```

### Step 2: Deploy Currency Agent

Since `currency-agent`'s public URL is only generated upon its first deployment, deploy the service first, capture its URL, and then set `AGENT_URL` via a fast configuration update:

```bash
# 1. Deploy Currency Agent with the MCP Server URL
gcloud run deploy currency-agent \
  --source currency_agent \
  --region $REGION \
  --allow-unauthenticated \
  --update-env-vars MCP_SERVER_URL="$MCP_SERVER_URL",GOOGLE_GENAI_USE_ENTERPRISE="true",GOOGLE_CLOUD_PROJECT="$PROJECT_ID",GOOGLE_CLOUD_LOCATION="global"

# 2. Capture its assigned Cloud Run URL
CURRENCY_AGENT_URL=$(gcloud run services describe currency-agent --region $REGION --format='value(status.url)')
echo "Currency Agent URL: $CURRENCY_AGENT_URL"

# 3. Update AGENT_URL so the agent advertises its public HTTPS endpoint in its Agent Card
gcloud run services update currency-agent \
  --region $REGION \
  --update-env-vars AGENT_URL="$CURRENCY_AGENT_URL"
```

### Step 3: Deploy Travel Agent

Deploy `travel-agent` connected to `CURRENCY_AGENT_URL`:

```bash
# 1. Deploy Travel Agent (with ADK Web UI) connected to Currency Agent
gcloud run deploy travel-agent \
  --source travel_agent \
  --region $REGION \
  --allow-unauthenticated \
  --update-env-vars CURRENCY_AGENT_URL="$CURRENCY_AGENT_URL",GOOGLE_GENAI_USE_ENTERPRISE="true",GOOGLE_CLOUD_PROJECT="$PROJECT_ID",GOOGLE_CLOUD_LOCATION="global"

# 2. Capture its assigned Cloud Run URL
TRAVEL_AGENT_URL=$(gcloud run services describe travel-agent --region $REGION --format='value(status.url)')
echo "Travel Agent URL: $TRAVEL_AGENT_URL"
```

> [!TIP]
> You can also deploy `travel_agent` using ADK's `adk deploy cloud_run` with the `--with_ui` flag:
> ```bash
> uv run adk deploy cloud_run travel_agent \
>   --project $PROJECT_ID \
>   --region $REGION \
>   --with_ui \
>   --env CURRENCY_AGENT_URL="$CURRENCY_AGENT_URL"
> ```

### 🧪 Testing

Test the MCP server:

```bash
MCP_SERVER_URL="$MCP_SERVER_URL" uv run python currency_mcp_server/test_server.py
```

Test the currency agent (over A2A protocol):

```bash
AGENT_URL="$CURRENCY_AGENT_URL" uv run python currency_agent/test_a2aclient.py
```

Test the travel agent (Directly in Cloud Run via Web UI):

Simply open `$TRAVEL_AGENT_URL` in your browser! The ADK Web UI is served directly from Cloud Run:
> *"I'm planning a trip to Tokyo. What is the weather like and how much is 500 USD in JPY?"*

This tests the complete end-to-end multi-agent system running in Cloud Run:
1. The **ADK Web UI** loaded from `travel-agent` on Cloud Run.
2. In-process execution of the local `weather_agent` tool in Cloud Run.
3. Remote A2A invocation across Cloud Run to `currency-agent`.
4. Remote MCP invocation across Cloud Run to `currency-mcp-server`.

---

## 🔒 (Optional) Securing Cloud Run Services (IAM Authentication)

To lock down all three Cloud Run services so they require IAM authentication (`roles/run.invoker`) and run with least-privilege service accounts:

### 1. Create Least-Privilege Service Accounts

```bash
gcloud iam service-accounts create currency-mcp-sa --display-name="Currency MCP Server SA"
gcloud iam service-accounts create currency-agent-sa --display-name="Currency Agent SA"
gcloud iam service-accounts create travel-agent-sa --display-name="Travel Agent SA"

# Grant Vertex AI access only to the two LLM agents
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:currency-agent-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:travel-agent-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### 2. Uncomment OIDC Authentication in Both Agents

Both agents include an `auth.py` helper (`GoogleIdTokenAuth`) that automatically attaches and refreshes Google-signed OIDC ID tokens for `https://` Cloud Run targets while leaving `http://localhost` development unchanged:

1. In `currency_agent/agent.py`, uncomment `httpx_client_factory`:
   ```python
   McpToolset(
       connection_params=StreamableHTTPConnectionParams(
           url=mcp_server_url,
           # Uncomment to enable Cloud Run IAM authentication:
           httpx_client_factory=get_mcp_http_client_factory(mcp_server_url),
       )
   )
   ```
2. In `travel_agent/agent.py`, uncomment `httpx_client`:
   ```python
   currency_remote_agent = RemoteA2aAgent(
       name="currency_agent",
       agent_card=f"{CURRENCY_AGENT_URL}{AGENT_CARD_WELL_KNOWN_PATH}",
       description="An agent that can help with currency conversions and exchange rates.",
       # Uncomment to enable Cloud Run IAM authentication:
       httpx_client=get_a2a_http_client(CURRENCY_AGENT_URL),
   )
   ```

### 3. Lock Down Services & Grant Hop-by-Hop `roles/run.invoker`

```bash
# 1. Lock down currency-mcp-server & grant currency-agent-sa invoker access
gcloud run services update currency-mcp-server \
  --region $REGION \
  --service-account="currency-mcp-sa@$PROJECT_ID.iam.gserviceaccount.com"

gcloud run services remove-iam-policy-binding currency-mcp-server \
  --region $REGION \
  --member="allUsers" \
  --role="roles/run.invoker"

gcloud run services add-iam-policy-binding currency-mcp-server \
  --region $REGION \
  --member="serviceAccount:currency-agent-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# 2. Redeploy currency-agent with auth enabled & grant travel-agent-sa invoker access
gcloud run deploy currency-agent \
  --source currency_agent \
  --region $REGION \
  --no-allow-unauthenticated \
  --service-account="currency-agent-sa@$PROJECT_ID.iam.gserviceaccount.com"

gcloud run services add-iam-policy-binding currency-agent \
  --region $REGION \
  --member="serviceAccount:travel-agent-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# 3. Redeploy travel-agent with auth enabled
gcloud run deploy travel-agent \
  --source travel_agent \
  --region $REGION \
  --no-allow-unauthenticated \
  --service-account="travel-agent-sa@$PROJECT_ID.iam.gserviceaccount.com"

# 4. Grant your user account invoker access for testing
USER_EMAIL=$(gcloud config get-value account)
for SERVICE in currency-mcp-server currency-agent travel-agent; do
  gcloud run services add-iam-policy-binding $SERVICE \
    --region $REGION \
    --member="user:$USER_EMAIL" \
    --role="roles/run.invoker"
done
```

### 4. Test Authenticated Services

Verify that unauthenticated requests are now blocked (`403 Forbidden`):

```bash
MCP_SERVER_URL="$MCP_SERVER_URL" uv run python currency_mcp_server/test_server.py
AGENT_URL="$CURRENCY_AGENT_URL" uv run python currency_agent/test_a2aclient.py
```

Now pass an identity token (`ID_TOKEN`) to authenticate your CLI requests and proxy the Web UI:

```bash
# Test MCP server with an identity token
ID_TOKEN=$(gcloud auth print-identity-token) \
  MCP_SERVER_URL="$MCP_SERVER_URL" \
  uv run python currency_mcp_server/test_server.py

# Test Currency Agent over A2A with an identity token
ID_TOKEN=$(gcloud auth print-identity-token) \
  AGENT_URL="$CURRENCY_AGENT_URL" \
  uv run python currency_agent/test_a2aclient.py

# Access the authenticated Travel Agent Web UI locally on http://localhost:8080
gcloud run services proxy travel-agent --region $REGION --port 8080
```
