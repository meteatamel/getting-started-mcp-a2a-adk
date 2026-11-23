import logging
import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

load_dotenv()

SYSTEM_INSTRUCTION = (
    "You are a specialized assistant for currency conversions. "
    "Your sole purpose is to use the 'get_exchange_rate' tool to answer questions about currency exchange rates. "
    "If the user asks about anything other than currency conversion or exchange rates, "
    "politely state that you cannot help with that topic and can only assist with currency-related queries. "
    "Do not attempt to answer unrelated questions or use tools for other purposes."
)

# In production, resolve the MCP server dynamically from Google Cloud Agent Registry
# (no hardcoded URLs; Agent Registry also handles authentication via Agent Identity).
# Locally, fall back to MCP_SERVER_URL (default: http://localhost:8080/mcp).
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME")

if MCP_SERVER_NAME:
    from google.adk.integrations.agent_registry.agent_registry import AgentRegistry

    project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.getenv("AGENT_REGISTRY_LOCATION", os.getenv("GOOGLE_CLOUD_LOCATION", "global"))
    logger.info(
        "--- 📒 Resolving MCP server '%s' from Agent Registry (%s/%s)... ---",
        MCP_SERVER_NAME,
        project_id,
        location,
    )
    registry = AgentRegistry(project_id=project_id, location=location)
    mcp_toolset = registry.get_mcp_toolset(mcp_server_name=MCP_SERVER_NAME)
else:
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp")
    if not mcp_server_url.endswith("/mcp"):
        mcp_server_url = f"{mcp_server_url.rstrip('/')}/mcp"
    logger.info("--- 🔧 Loading MCP tools from MCP Server at %s... ---", mcp_server_url)
    mcp_toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=mcp_server_url,
        )
    )

logger.info("--- 🤖 Creating ADK Currency Agent... ---")

root_agent = LlmAgent(
    model="gemini-3.8-flash",
    name="currency_agent",
    description="An agent that can help with currency conversions",
    instruction=SYSTEM_INSTRUCTION,
    tools=[mcp_toolset],
)

# Make the agent A2A-compatible
PORT = int(os.getenv("PORT", 8081))
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

    logger.info(f"🚀 Starting currency_agent on port {PORT}")
    uvicorn.run(a2a_app, host="0.0.0.0", port=PORT)
