# Productionizing MCP, A2A & ADK on Google Cloud (`production` branch)

[![Branch](https://img.shields.io/badge/Branch-production_(Part_2)-34A853.svg)](https://github.com/meteatamel/getting-started-mcp-a2a-adk/tree/production)
[![Codelab](https://img.shields.io/badge/Codelab-Part_2-4285F4.svg)](https://codelabs.developers.google.com/productionizing-mcp-a2a-adk)
[![Part 1](https://img.shields.io/badge/Part_1-main_(Getting_Started)-4285F4.svg)](https://github.com/meteatamel/getting-started-mcp-a2a-adk/tree/main)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-ADK-4285F4.svg)](https://adk.dev/)
[![Protocol](https://img.shields.io/badge/Protocol-A2A-34A853.svg)](https://a2a-protocol.org/)
[![Protocol](https://img.shields.io/badge/Protocol-MCP-EA4335.svg)](https://modelcontextprotocol.io/)

This **`production` branch** is **Part 2** of the `getting-started-mcp-a2a-adk` sample. It takes the exact 3-tier multi-agent system from Part 1 ([`main` branch](https://github.com/meteatamel/getting-started-mcp-a2a-adk/tree/main))—`travel_agent` → `currency_agent` (A2A) → `currency_mcp_server` (MCP)—and productionizes it on Google Cloud using the **Gemini Enterprise Agent Platform** (**Scale → Govern → Optimize**).

> 🎓 **Hands-on Codelab (Part 2):** Follow the step-by-step tutorial at **[Productionizing MCP, A2A & ADK on Google Cloud](https://codelabs.developers.google.com/productionizing-mcp-a2a-adk)**.

![Production Architecture Overview](images/architecture.png)

---

## 🔍 What Part 2 Adds Over Part 1

In Part 1 (`main`), all three services run as public `--allow-unauthenticated` Cloud Run containers wired together with hardcoded URLs, zero prompt guardrails, and no automated quality checks. Part 2 addresses each production gap one layer at a time:

| Capability | Problem in Part 1 (`main`) | What Part 2 (`production`) Adds |
| :--- | :--- | :--- |
| **Agent Runtime** | Agents run as DIY containers with manual scaling, sessions, and boilerplate | Hosts `currency_agent` and `travel_agent` (`gemini-3.8-flash`) on managed **Agent Runtime**, while keeping `currency_mcp_server` on **Cloud Run** (hybrid architecture) |
| **Agent Registry** | Hardcoded `MCP_SERVER_URL` and `CURRENCY_AGENT_URL` env vars break when URLs change and create shadow AI | Auto-registers the Cloud Run MCP server (`--functional-type=mcp-server`) and Agent Runtime agents; registers the `/mcp` interface and resolves tools & peers dynamically via ADK's `AgentRegistry` client |
| **Agent Identity** | Public `--allow-unauthenticated` endpoints or shared Compute Engine service accounts | Provisions a unique managed **Agent Identity** (`AGENT_IDENTITY`) per deployed agent, enforcing least-privilege resource-level IAM (`roles/run.invoker` on Cloud Run, resource-level `roles/aiplatform.user` on `currency-agent`, and `roles/agentregistry.viewer`) |
| **Agent Gateway & Model Armor** | No centralized outbound traffic governance, prompt-injection defense, or PII redaction | Places an **Agent Gateway** (`AGENT_TO_ANYWHERE` egress with default-deny IAP `AuthzPolicy`) and **Model Armor** (`CONTENT_AUTHZ`) in the outbound path to govern calls and block prompt injections and sensitive data leaks |
| **Observability** | Local console logs only; blind to multi-hop latency, tool failures, and token spend | Enables OpenTelemetry tracing (`GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true`) to inspect full distributed traces across `travel_agent` → `currency_agent` → `currency_mcp_server` in Cloud Trace & Agent Platform Observability |
| **Evaluation** | Manual one-off testing via `a2a-cli`; prompt or model changes can silently regress | Adds an automated ADK evaluation suite (`python/evals/`) that verifies tool-use trajectory (`weather_agent` + `currency_agent`) and response quality via `adk eval` and Agent Platform Evaluation |

---

## 🏗️ Production Architecture (Hybrid Cloud Run + Agent Runtime)

```
+-----------------------------------------------------------------------------------+
|                            Client (a2a-cli / App)                                 |
+------------------------------------------+----------------------------------------+
                                           | Authenticated A2A v1 (HTTPS)
                                           v
+-----------------------------------------------------------------------------------+
|  Agent Runtime: travel_agent  (Identity: AGENT_IDENTITY, OTel -> Cloud Trace)     |
|  - Resolves currency_agent dynamically from Agent Registry                        |
|                                                                                   |
|    +--> [Local AgentTool] weather_agent (in-process)                              |
|    +--> [Remote A2A] currency_agent (via Agent Registry + Egress Agent Gateway)   |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|       Agent Gateway (AGENT_TO_ANYWHERE Egress) + IAP + Model Armor                |
|  - Default-deny AuthzPolicy (IAP), Agent Registry catalog, prompt-injection & PII |
+------------------------------------------+----------------------------------------+
                                           | Authenticated A2A v1 (mTLS / Agent Identity)
                                           v
+-----------------------------------------------------------------------------------+
|  Agent Runtime: currency_agent  (Identity: AGENT_IDENTITY, OTel -> Cloud Trace)   |
|  - Resolves currency_mcp_server dynamically from Agent Registry                   |
+------------------------------------------+----------------------------------------+
                                           | Authenticated MCP (OIDC / Agent Identity)
                                           v
+-----------------------------------------------------------------------------------+
|  Cloud Run: currency_mcp_server  (--no-allow-unauthenticated,                     |
|                                   --functional-type=mcp-server -> Agent Registry) |
+-----------------------------------------------------------------------------------+
```

---

## 📂 What Changed on This Branch

Run `git diff main..production --stat` to see the exact delta from Part 1:

- **`python/deploy_a2a.py` & `python/a2a_runtime.py`**: Deploy, update, bind Agent Gateways (`--egress-gateway`), grant resource-level A2A IAM (`--grant-invoker`), and delete (`--delete`) native A2A ADK agents on Agent Runtime with `AGENT_IDENTITY` and OpenTelemetry enabled.
- **`python/currency_agent/agent.py` & `python/travel_agent/agent.py`**: Resolve MCP tools and remote A2A agents via `google.adk.integrations.agent_registry.agent_registry.AgentRegistry` when `MCP_SERVER_NAME` / `CURRENCY_AGENT_NAME` are set (keeping automatic fallback to `localhost` URLs for local development), using `gemini-3.8-flash`.
- **`policies/`**: Declarative YAML templates for `AgentGateway` (egress), IAP `AuthzExtension` / `AuthzPolicy` (`REQUEST_AUTHZ`), and Model Armor `AuthzExtension` / `AuthzPolicy` (`CONTENT_AUTHZ`).
- **`python/evals/`**: Automated ADK evaluation set (`travel_agent.evalset.json`) and rubric criteria config (`test_config.json`).

---

## 🚀 Getting Started

- **[Part 2 Codelab: Productionizing MCP, A2A & ADK on Google Cloud](https://codelabs.developers.google.com/productionizing-mcp-a2a-adk)** — Interactive step-by-step Google Codelab walkthrough.
- **[Python Productionizing Guide (`python/README.md`)](python/README.md)** — Full step-by-step commands for Cloud Run + Agent Runtime deployment, Agent Registry, Agent Identity, Agent Gateway + Model Armor, Observability, Evaluation, and Clean Up.
- **Part 1 (Getting Started)**: Switch to the [`main`](https://github.com/meteatamel/getting-started-mcp-a2a-adk/tree/main) branch.
