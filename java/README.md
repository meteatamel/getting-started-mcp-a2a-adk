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
  - **`travel_agent`**: Built with [ADK Java (`google-adk`, `google-adk-a2a`, `google-adk-dev`)](https://github.com/google/adk-java), using `RemoteA2AAgent`, `AgentTool`, and `AdkWebServer`.

---

## 🚀 Getting Started

### Prerequisites

- Java 17+
- Apache Maven 3.9+
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

Start the travel agent locally in terminal 3 (starts the ADK Web UI on port 8082):

```bash
mvn -f travel_agent/pom.xml compile exec:java
```

### 🧪 Testing

Test the MCP server:

```bash
mvn -f currency_mcp_server/pom.xml compile exec:java -Dexec.mainClass="com.example.mcp.TestServer"
```

Test the currency agent (over A2A protocol):

```bash
mvn -f currency_agent/pom.xml compile exec:java -Dexec.mainClass="com.example.currency.TestA2AClient"
```

Test the travel agent (Interactive ADK Web UI):

Open your browser at `http://localhost:8082` and chat with `travel_agent`:
> *"I'm planning a trip to London. What is the weather like and how much is 200 EUR in GBP?"*

This runs end-to-end:
1. Queries travel and currency conversion (delegated via A2A to `currency_agent` -> `currency_mcp_server`).
2. Queries weather forecasts (delegated to local `WeatherAgent` in `com.example.travel.subagents`).

You can also test queries directly from the command line:

```bash
mvn -f travel_agent/pom.xml compile exec:java \
  -Dexec.args="What is the weather in London and how much is 100 USD in EUR?"
```

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

### 🧪 Testing

Test the MCP server:

```bash
MCP_SERVER_URL="$MCP_SERVER_URL" mvn -f currency_mcp_server/pom.xml compile exec:java \
  -Dexec.mainClass="com.example.mcp.TestServer"
```

Test the currency agent (over A2A protocol):

```bash
AGENT_URL="$CURRENCY_AGENT_URL" mvn -f currency_agent/pom.xml compile exec:java \
  -Dexec.mainClass="com.example.currency.TestA2AClient"
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

Both agents include a `CloudRunAuth` helper class (`IdTokenCredentials`) that automatically attaches and refreshes Google-signed OIDC ID tokens for `https://` Cloud Run targets while leaving `http://localhost` development unchanged:

1. In `currency_agent/src/main/java/com/example/currency/CurrencyAgent.java`, swap the `McpToolset` line:
   ```java
   // McpToolset mcpToolset = new McpToolset(streamableParams);
   // Uncomment to enable Cloud Run IAM authentication (and comment out the line above):
   McpToolset mcpToolset = CloudRunAuth.createMcpToolset(streamableParams);
   ```
2. In `travel_agent/src/main/java/com/example/travel/TravelAgent.java`, swap the `A2AHttpClient` line:
   ```java
   // A2AHttpClient httpClient = new JdkA2AHttpClient();
   // Uncomment to enable Cloud Run IAM authentication (and comment out the line above):
   A2AHttpClient httpClient = CloudRunAuth.createA2AHttpClient(currencyAgentUrl);
   ```

### 3. Lock Down Services & Grant Hop-by-Hop `roles/run.invoker`

> [!NOTE]
> `TravelAgent` resolves `currency-agent`'s Agent Card at startup, so always grant `travel-agent-sa` the `roles/run.invoker` role on `currency-agent` before deploying `travel-agent` (as ordered below).

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
MCP_SERVER_URL="$MCP_SERVER_URL" mvn -f currency_mcp_server/pom.xml compile exec:java \
  -Dexec.mainClass="com.example.mcp.TestServer"
AGENT_URL="$CURRENCY_AGENT_URL" mvn -f currency_agent/pom.xml compile exec:java \
  -Dexec.mainClass="com.example.currency.TestA2AClient"
```

Now pass an identity token (`ID_TOKEN`) to authenticate your CLI requests and proxy the Web UI:

```bash
# Test MCP server with an identity token
ID_TOKEN=$(gcloud auth print-identity-token) \
  MCP_SERVER_URL="$MCP_SERVER_URL" \
  mvn -f currency_mcp_server/pom.xml compile exec:java \
  -Dexec.mainClass="com.example.mcp.TestServer"

# Test Currency Agent over A2A with an identity token
ID_TOKEN=$(gcloud auth print-identity-token) \
  AGENT_URL="$CURRENCY_AGENT_URL" \
  mvn -f currency_agent/pom.xml compile exec:java \
  -Dexec.mainClass="com.example.currency.TestA2AClient"

# Access the authenticated Travel Agent Web UI locally on http://localhost:8080
gcloud run services proxy travel-agent --region $REGION --port 8080
```
