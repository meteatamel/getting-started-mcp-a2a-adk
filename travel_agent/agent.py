import logging
import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH

try:
    from travel_agent.subagents.weather_agent import weather_agent
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

CURRENCY_AGENT_URL = os.getenv("CURRENCY_AGENT_URL", "http://localhost:8081").rstrip("/")

logger.info(
    "--- 🔗 Connecting to Remote A2A Currency Agent at %s... ---",
    CURRENCY_AGENT_URL,
)

currency_remote_agent = RemoteA2aAgent(
    name="currency_agent",
    agent_card=f"{CURRENCY_AGENT_URL}{AGENT_CARD_WELL_KNOWN_PATH}",
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

if __name__ == "__main__":
    import uvicorn
    from google.adk.cli.fast_api import get_fast_api_app

    PORT = int(os.getenv("PORT", 8082))
    logger.info(f"🚀 Starting travel_agent Web UI on port {PORT}")
    app = get_fast_api_app(web=True, allow_origins=["*"], agents_dir=os.path.dirname(__file__) or ".")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
