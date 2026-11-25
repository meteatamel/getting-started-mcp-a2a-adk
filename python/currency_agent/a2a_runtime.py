"""Agent Runtime A2A entrypoint for currency_agent."""

import os

from a2a.types import AgentSkill
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from vertexai.agent_engines.templates.a2a import A2aAgent, create_agent_card


def build_runner() -> Runner:
    from currency_agent.agent import root_agent

    return Runner(
        app_name=root_agent.name,
        agent=root_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )


agent_card = create_agent_card(
    agent_name="currency-agent",
    description="An agent that can help with currency conversions and exchange rates.",
    skills=[
        AgentSkill(
            id="currency_conversion",
            name="Currency Conversion",
            description="Converts between currencies using live exchange rates via MCP.",
            tags=["currency", "exchange-rate", "finance"],
            examples=["How much is 500 USD in JPY?"],
        )
    ],
)
a2a_agent = A2aAgent(
    agent_card=agent_card,
    agent_executor_builder=lambda: A2aAgentExecutor(runner=build_runner),
)
if region := os.getenv("REGION"):
    a2a_agent._tmpl_attrs["location"] = region
