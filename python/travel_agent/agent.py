import logging
import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH, RemoteA2aAgent
from google.adk.tools.agent_tool import AgentTool

try:
    from .subagents.weather_agent import weather_agent
except ImportError:
    from subagents.weather_agent import weather_agent

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

load_dotenv()

SYSTEM_INSTRUCTION = (
    "You are a helpful travel assistant. You help users plan trips, recommend places, "
    "and answer travel-related questions.\n\n"
    "- Whenever a user asks about currency exchange rates or money conversions, "
    "delegate the request to the 'currency_agent' tool.\n"
    "- Whenever a user asks about the weather, climate, or forecasts for a destination, "
    "delegate the request to the 'weather_agent' tool."
)

# In production, resolve the remote currency_agent dynamically from Google Cloud Agent Registry
# (no hardcoded URLs; Agent Registry also handles A2A authentication via Agent Identity).
# Locally, fall back to CURRENCY_AGENT_URL (default: http://localhost:8081).
CURRENCY_AGENT_NAME = os.getenv("CURRENCY_AGENT_NAME")

if CURRENCY_AGENT_NAME:
    from google.adk.integrations.agent_registry.agent_registry import AgentRegistry

    project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.getenv("AGENT_REGISTRY_LOCATION", os.getenv("GOOGLE_CLOUD_LOCATION", "global"))
    logger.info(
        "--- 📒 Resolving remote A2A agent '%s' from Agent Registry (%s/%s)... ---",
        CURRENCY_AGENT_NAME,
        project_id,
        location,
    )
    registry = AgentRegistry(project_id=project_id, location=location)
    currency_remote_agent = registry.get_remote_a2a_agent(agent_name=CURRENCY_AGENT_NAME)
else:
    currency_agent_url = os.getenv("CURRENCY_AGENT_URL", "http://localhost:8081").rstrip("/")
    logger.info(
        "--- 🔗 Connecting to Remote A2A Currency Agent at %s... ---",
        currency_agent_url,
    )
    currency_remote_agent = RemoteA2aAgent(
        name="currency_agent",
        agent_card=f"{currency_agent_url}{AGENT_CARD_WELL_KNOWN_PATH}",
        description="An agent that can help with currency conversions and exchange rates.",
    )

logger.info("--- 🤖 Creating ADK Travel Agent... ---")

root_agent = LlmAgent(
    model="gemini-3.8-flash",
    name="travel_agent",
    description="A travel assistant that can help plan trips, check weather forecasts via the local weather agent, and convert currencies via the remote currency agent.",
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        AgentTool(agent=currency_remote_agent),
        AgentTool(agent=weather_agent),
    ],
)

# Make the agent A2A-compatible
PORT = int(os.getenv("PORT", 8082))
AGENT_URL = os.getenv("AGENT_URL")

if AGENT_URL:
    parsed = urlparse(AGENT_URL)
    protocol = parsed.scheme or "https"
    host = parsed.hostname
    port = parsed.port or 443
else:
    protocol = "http"
    host = "localhost"
    port = PORT

a2a_app = to_a2a(root_agent, host=host, port=port, protocol=protocol)

if __name__ == "__main__":
    import uvicorn

    logger.info(f"🚀 Starting travel_agent A2A server on port {PORT}")
    uvicorn.run(a2a_app, host="0.0.0.0", port=PORT)
