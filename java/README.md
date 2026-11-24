# Getting Started with MCP & A2A with ADK (Java)

[![Java](https://img.shields.io/badge/Java-17+-orange.svg)](https://openjdk.org/)
[![Framework](https://img.shields.io/badge/Framework-ADK_Java-4285F4.svg)](https://github.com/google/adk-java)
[![Protocol](https://img.shields.io/badge/Protocol-A2A_Java-34A853.svg)](https://github.com/a2aproject/a2a-java)
[![Protocol](https://img.shields.io/badge/Protocol-MCP_Java-EA4335.svg)](https://github.com/modelcontextprotocol/java-sdk)

This directory contains the **Java** implementation of the MCP + A2A + ADK multi-agent system. See the [top-level README](../README.md) for the architecture overview and the [deployed codelab](https://codelabs.developers.google.com/getting-started-mcp-a2a-adk).

---

## 📦 Dependency Management (Maven Multi-Module Reactor)

Project modules are organized as a unified **Maven Reactor**:
- Root `pom.xml` orchestrates the three modules (`currency_mcp_server`, `currency_agent`, `travel_agent`).
- Running `mvn compile` at the `java/` root builds all three services at once.
- Each service directory (`currency_mcp_server/`, `currency_agent/`, `travel_agent/`) has its own self-contained `pom.xml` and `Dockerfile` for independent Cloud Run builds:
  - **`currency_mcp_server`**: Built with the official [MCP Java SDK (`io.modelcontextprotocol.sdk:mcp`)](https://github.com/modelcontextprotocol/java-sdk) and embedded Jetty (`HttpServletStreamableServerTransportProvider`) exposing `/mcp`.
  - **`currency_agent`**: Built with [ADK Java (`google-adk`, `google-adk-a2a`)](https://github.com/google/adk-java) and the [A2A Java SDK (`a2a-java-sdk-reference-jsonrpc`)](https://github.com/a2aproject/a2a-java) on Quarkus.
  - **`travel_agent`**: Built with [ADK Java (`google-adk`, `google-adk-a2a`)](https://github.com/google/adk-java) and the [A2A Java SDK (`a2a-java-sdk-reference-jsonrpc`)](https://github.com/a2aproject/a2a-java) on Quarkus, using `RemoteA2AAgent` and `AgentTool`.

---

## 🚀 Getting Started

### Prerequisites

- Java 17+
- Apache Maven 3.9+
- [a2a-cli](https://github.com/a2aproject/a2a-cli) (for testing the A2A agents):
  ```bash
  curl -fsSL https://raw.githubusercontent.com/a2aproject/a2a-cli/main/install.sh | A2A_INSTALL_DIR="$HOME/.local/bin" bash
  export PATH="$HOME/.local/bin:$PATH"
  ```
- Google Cloud SDK (`gcloud`) if deploying to Cloud Run.

### Installation

1. Clone the repository and navigate to the `java` folder:
   ```bash
   git clone https://github.com/meteatamel/getting-started-mcp-a2a-adk.git
   cd getting-started-mcp-a2a-adk/java
   ```

2. Compile all modules across the project:
   ```bash
   mvn compile
   ```

3. Configure Environment Variables:
   Export the environment variables in your terminal (or save them to `.env` and run `set -a && source .env && set +a`):

   **Option A: Google AI Studio**
   ```sh
   export GOOGLE_API_KEY=<your_api_key_here>
   export GOOGLE_GENAI_USE_ENTERPRISE=FALSE
   ```

   **Option B: Gemini Enterprise (Google Cloud)**
   ```sh
   export GOOGLE_GENAI_USE_ENTERPRISE=TRUE
   export GOOGLE_CLOUD_PROJECT=<your_gcp_project_id>
   export GOOGLE_CLOUD_LOCATION=global
   ```

---

## 💻 Local Execution

You can run all three services concurrently in separate terminal windows from the `java/` directory. Make sure to run them in the order of MCP server first, then currency agent, then travel agent.

### Step 1: Start Currency MCP Server

Start the MCP server locally in terminal 1 (runs on port 8080):

```bash
mvn -f currency_mcp_server/pom.xml compile exec:java
```

### Step 2: Start Currency Agent

Start the A2A currency agent locally in terminal 2 (runs on port 8081):

```bash
mvn -f currency_agent/pom.xml quarkus:dev
```

### Step 3: Start Travel Agent

Start the A2A travel agent locally in terminal 3 (runs on port 8082):

```bash
mvn -f travel_agent/pom.xml quarkus:dev
```

### 🧪 Testing

Test the MCP server:

```bash
mvn -f currency_mcp_server/pom.xml compile exec:java -Dexec.mainClass="com.example.mcp.TestServer"
```

Test the currency agent over A2A with `a2a-cli` (or `mvn -f currency_agent/pom.xml compile exec:java -Dexec.mainClass="com.example.currency.TestA2AClient"`):

```bash
a2a card get http://localhost:8081
a2a send -a http://localhost:8081 "How much is 100 USD in GBP?"
```

Test the travel agent over A2A with `a2a-cli`:

```bash
# Inspect the Travel Agent's Agent Card
a2a card get http://localhost:8082

# Send an end-to-end travel query
a2a send -a http://localhost:8082 \
  "I'm planning a trip to London. What is the weather like and how much is 200 EUR in GBP?"
```

This runs end-to-end:
1. Sends an A2A request to `travel_agent` (`:8082`).
2. Queries weather forecasts (delegated to local `WeatherAgent` in `com.example.travel.subagents`).
3. Queries currency conversion (delegated via A2A to `currency_agent` `:8081` -> `currency_mcp_server` `:8080`).

---

## ☁️ Cloud Run Deployment

All three components include multi-stage Dockerfiles and can be deployed directly from source to Cloud Run. You can use `gcloud` to automatically capture service URLs and wire them into the next steps without manual copy-pasting.

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
> For simplicity in this getting-started sample, all services are deployed with `--allow-unauthenticated`, making them publicly accessible. **Do not use this configuration in production**—always lock down service-to-service traffic with IAM authentication, Agent Identity, and/or Agent Gateway.

### Quick Deploy (`deploy.sh`)

Run the included [`deploy.sh`](deploy.sh) script to deploy all three services in order (`currency-mcp-server` → `currency-agent` + `AGENT_URL` update → `travel-agent` + `AGENT_URL` update) and save the resulting URLs to `.env.cloudrun`:

```bash
./deploy.sh
source .env.cloudrun
```

*(You can also inspect `deploy.sh` or run the three steps manually below.)*

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

Deploy `travel-agent` connected to `CURRENCY_AGENT_URL`, then set its `AGENT_URL` so its Agent Card advertises its public Cloud Run URL:

```bash
# 1. Deploy Travel Agent connected to Currency Agent
gcloud run deploy travel-agent \
  --source travel_agent \
  --region $REGION \
  --allow-unauthenticated \
  --update-env-vars CURRENCY_AGENT_URL="$CURRENCY_AGENT_URL",GOOGLE_GENAI_USE_ENTERPRISE="true",GOOGLE_CLOUD_PROJECT="$PROJECT_ID",GOOGLE_CLOUD_LOCATION="global"

# 2. Capture its assigned Cloud Run URL
TRAVEL_AGENT_URL=$(gcloud run services describe travel-agent --region $REGION --format='value(status.url)')
echo "Travel Agent URL: $TRAVEL_AGENT_URL"

# 3. Update AGENT_URL so the agent advertises its public HTTPS endpoint in its Agent Card
gcloud run services update travel-agent \
  --region $REGION \
  --update-env-vars AGENT_URL="$TRAVEL_AGENT_URL"
```

### 🧪 Testing

Test the MCP server:

```bash
MCP_SERVER_URL="$MCP_SERVER_URL" mvn -f currency_mcp_server/pom.xml compile exec:java \
  -Dexec.mainClass="com.example.mcp.TestServer"
```

Test the currency agent over A2A:

```bash
a2a card get "$CURRENCY_AGENT_URL"
a2a send -a "$CURRENCY_AGENT_URL" "How much is 100 USD in GBP?"
```

Test the travel agent over A2A:

```bash
a2a card get "$TRAVEL_AGENT_URL"
a2a send -a "$TRAVEL_AGENT_URL" \
  "I'm planning a trip to Tokyo. What is the weather like and how much is 500 USD in JPY?"
```

This tests the complete end-to-end multi-agent system running in Cloud Run:
1. Remote A2A invocation via `a2a-cli` to `travel-agent` on Cloud Run.
2. In-process execution of the local `weather_agent` tool in Cloud Run.
3. Remote A2A invocation across Cloud Run to `currency-agent`.
4. Remote MCP invocation across Cloud Run to `currency-mcp-server`.
