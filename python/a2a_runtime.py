"""Top-level Agent Runtime A2A entrypoints for currency_agent and travel_agent.

Keeping this module outside the agent packages prevents Python from importing
`<agent_dir>/__init__.py` (and running Agent Registry lookups in `agent.py`)
during container startup—before a newly created Agent Identity has been granted
`roles/agentregistry.viewer`. Instead, `build_runner` imports `root_agent` lazily
on the first incoming A2A request.
"""

import os

from a2a.types import AgentSkill
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
import vertexai
from vertexai.agent_engines.templates.a2a import A2aAgent, create_agent_card

if region := os.getenv("REGION"):
    vertexai.init(location=region)


def _build_currency_runner() -> Runner:
    # gemini-3.8-flash is served via the global Vertex AI endpoint; Agent Engine
    # reserves GOOGLE_CLOUD_LOCATION in env_vars, so override it at runtime while
    # A2aAgent and AgentRegistry continue using REGION (e.g. europe-west1).
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    from currency_agent.agent import root_agent

    return Runner(
        app_name=root_agent.name,
        agent=root_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )


def _build_travel_runner() -> Runner:
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    from travel_agent.agent import root_agent

    return Runner(
        app_name=root_agent.name,
        agent=root_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )


def _make_a2a_agent(
    *,
    agent_name: str,
    description: str,
    skill: AgentSkill,
    runner_builder,
) -> A2aAgent:
    card = create_agent_card(
        agent_name=agent_name,
        description=description,
        skills=[skill],
    )
    return A2aAgent(
        agent_card=card,
        agent_executor_builder=lambda: A2aAgentExecutor(runner=runner_builder),
    )


currency_a2a_agent = _make_a2a_agent(
    agent_name="currency-agent",
    description="An agent that can help with currency conversions and exchange rates.",
    skill=AgentSkill(
        id="currency_conversion",
        name="Currency Conversion",
        description="Converts between currencies using live exchange rates via MCP.",
        tags=["currency", "exchange-rate", "finance"],
        examples=["How much is 500 USD in JPY?"],
    ),
    runner_builder=_build_currency_runner,
)

travel_a2a_agent = _make_a2a_agent(
    agent_name="travel-agent",
    description="A helpful travel assistant that delegates weather and currency questions.",
    skill=AgentSkill(
        id="travel_assistant",
        name="Travel Assistant",
        description="Helps plan trips with weather forecasts and currency conversions.",
        tags=["travel", "weather", "currency"],
        examples=[
            "I'm planning a trip to Tokyo. What is the weather like and how much is 500 USD in JPY?"
        ],
    ),
    runner_builder=_build_travel_runner,
)
