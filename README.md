# Productionizing MCP, A2A & ADK on Google Cloud (`production` branch)

[![Branch](https://img.shields.io/badge/Branch-production_(Part_2)-34A853.svg)](https://github.com/meteatamel/getting-started-mcp-a2a-adk/tree/production)
[![Part 1](https://img.shields.io/badge/Part_1-main_(Getting_Started)-4285F4.svg)](https://github.com/meteatamel/getting-started-mcp-a2a-adk/tree/main)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-ADK-4285F4.svg)](https://adk.dev/)
[![Protocol](https://img.shields.io/badge/Protocol-A2A-34A853.svg)](https://a2a-protocol.org/)
[![Protocol](https://img.shields.io/badge/Protocol-MCP-EA4335.svg)](https://modelcontextprotocol.io/)

This **`production` branch** is **Part 2** of the `getting-started-mcp-a2a-adk` sample. It takes the exact 3-tier multi-agent system from Part 1 ([`main` branch](https://github.com/meteatamel/getting-started-mcp-a2a-adk/tree/main))—`travel_agent` → `currency_agent` (A2A) → `currency_mcp_server` (MCP)—and productionizes it on Google Cloud using the **Gemini Enterprise Agent Platform** (**Scale → Govern → Optimize**).

![Production Architecture Overview](images/architecture.png)

---

## 🔍 What Part 2 Adds Over Part 1

In Part 1 (`main`), all three services run as public `--allow-unauthenticated` Cloud Run containers wired together with hardcoded URLs, zero prompt guardrails, and no automated quality checks. Part 2 addresses each production gap one layer at a time:

| Capability | Problem in Part 1 (`main`) | What Part 2 (`production`) Adds |
| :--- | :--- | :--- |
| **Agent Runtime** | Agents run as DIY containers with manual scaling, sessions, and boilerplate | Hosts `currency_agent` and `travel_agent` on managed **Agent Runtime**, while keeping `currency_mcp_server` on **Cloud Run** (hybrid architecture) |
| **Agent Registry** | Hardcoded `MCP_SERVER_URL` and `CURRENCY_AGENT_URL` env vars break when URLs change and create shadow AI | Auto-registers the Cloud Run MCP server (`--functional-type=mcp-server`) and Agent Runtime agents; agents resolve tools & peers dynamically via ADK's `AgentRegistry` client |
| **Agent Identity** | Public `--allow-unauthenticated` endpoints or shared Compute Engine service accounts | Provisions a unique managed **Agent Identity** (`AGENT_IDENTITY`) per deployed agent, enforcing least-privilege hop-by-hop IAM (`roles/run.invoker`, `roles/agentregistry.viewer`) and per-agent audit logs |
| **Agent Gateway & Model Armor** | No centralized traffic governance, prompt-injection defense, or PII redaction | Places **Agent Gateway** (`CLIENT_TO_AGENT` ingress & `AGENT_TO_ANYWHERE` egress with default-deny `AuthzPolicy`) and **Model Armor** in front to block prompt injections and sensitive data leaks |
| **Observability** | Local console logs only; blind to multi-hop latency, tool failures, and token spend | Enables OpenTelemetry tracing (`--otel_to_cloud`) to inspect full distributed traces across `travel_agent` → `currency_agent` → `currency_mcp_server` in Cloud Trace & Agent Platform Observability |
| **Evaluation** | Manual one-off testing via `a2a-cli`; prompt or model changes can silently regress | Adds an automated ADK evaluation suite (`python/evals/`) that verifies tool-use trajectory (`weather_agent` + `currency_agent`) and response quality via `adk eval` and Agent Platform Evaluation |

---

## 🏗️ Production Architecture (Hybrid Cloud Run + Agent Runtime)

```
+-----------------------------------------------------------------------------------+
|                            Client (a2a-cli / App)                                 |
+------------------------------------------+----------------------------------------+
                                           | Authenticated A2A (HTTPS)
                                           v
+-----------------------------------------------------------------------------------+
|             Agent Gateway (CLIENT_TO_AGENT Ingress) + Model Armor                 |
|  - Prompt injection & jailbreak defense, PII/SDP sanitization, ingress authz      |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|  Agent Runtime: travel_agent  (Identity: AGENT_IDENTITY, OTel -> Cloud Trace)     |
|  - Resolves currency_agent dynamically from Agent Registry                        |
|                                                                                   |
|    +--> [Local AgentTool] weather_agent (in-process)                              |
|    +--> [Remote A2A] currency_agent (via Agent Registry + Agent Gateway Egress)   |
+------------------------------------------+----------------------------------------+
                                           | Authenticated A2A (via Agent Gateway)
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

- **`python/currency_agent/agent.py` & `python/travel_agent/agent.py`**: Resolve MCP tools and remote A2A agents via `google.adk.integrations.agent_registry.agent_registry.AgentRegistry` when `MCP_SERVER_NAME` / `CURRENCY_AGENT_NAME` are set (keeping automatic fallback to `localhost` URLs for local development).
- **`python/currency_agent/.agent_engine_config.json` & `python/travel_agent/.agent_engine_config.json`**: Enable managed `AGENT_IDENTITY` on Agent Runtime.
- **`policies/`**: Declarative YAML templates for `AgentGateway` (ingress & egress) and `AuthzPolicy`.
- **`python/evals/`**: Automated ADK evaluation set (`travel_agent.evalset.json`) and criteria config (`test_config.json`).

---

## 🚀 Getting Started

- **[Python Productionizing Guide (`python/README.md`)](python/README.md)** — Full step-by-step commands for local dev, Cloud Run + Agent Runtime deployment, Agent Registry, Agent Identity, Agent Gateway + Model Armor, Observability, and Evaluation.
- **Part 1 (Getting Started)**: Switch to the [`main`](https://github.com/meteatamel/getting-started-mcp-a2a-adk/tree/main) branch.
