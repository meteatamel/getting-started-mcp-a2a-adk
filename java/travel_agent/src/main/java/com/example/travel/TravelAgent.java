package com.example.travel;

import com.example.travel.subagents.WeatherAgent;
import com.google.adk.a2a.agent.RemoteA2AAgent;
import com.google.adk.agents.BaseAgent;
import com.google.adk.agents.LlmAgent;
import com.google.adk.tools.AgentTool;
import io.a2a.client.Client;
import io.a2a.client.config.ClientConfig;
import io.a2a.client.http.A2ACardResolver;
import io.a2a.client.http.A2AHttpClient;
import io.a2a.client.http.JdkA2AHttpClient;
import io.a2a.client.transport.jsonrpc.JSONRPCTransport;
import io.a2a.client.transport.jsonrpc.JSONRPCTransportConfig;
import io.a2a.spec.AgentCard;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Orchestrating Travel Agent exposed over A2A, delegating weather queries to the local
 * {@link WeatherAgent} and currency queries to the remote A2A Currency Agent.
 */
public final class TravelAgent {

    private static final Logger logger = LoggerFactory.getLogger(TravelAgent.class);

    private static final String SYSTEM_INSTRUCTION = """
            You are a helpful travel assistant. You help users plan trips, recommend places, and answer travel-related questions.

            - Whenever a user asks about currency exchange rates or money conversions, delegate the request to the 'currency_agent' tool.
            - Whenever a user asks about the weather, climate, or forecasts for a destination, delegate the request to the 'weather_agent' tool.
            """;

    public static final BaseAgent ROOT_AGENT = createRootAgent();

    private static BaseAgent createRootAgent() {
        String currencyAgentUrl = System.getenv()
                .getOrDefault("CURRENCY_AGENT_URL", "http://localhost:8081")
                .replaceAll("/+$", "");

        logger.info("--- 🔗 Connecting to Remote A2A Currency Agent at {}... ---", currencyAgentUrl);

        String agentCardUrl = currencyAgentUrl + "/.well-known/agent-card.json";
        A2AHttpClient httpClient = new JdkA2AHttpClient();

        AgentCard publicAgentCard =
                new A2ACardResolver(httpClient, currencyAgentUrl, agentCardUrl).getAgentCard();

        Client a2aClient = Client.builder(publicAgentCard)
                .withTransport(JSONRPCTransport.class, new JSONRPCTransportConfig(httpClient))
                .clientConfig(
                        new ClientConfig.Builder()
                                .setStreaming(publicAgentCard.capabilities().streaming())
                                .build())
                .build();

        BaseAgent currencyRemoteAgent = RemoteA2AAgent.builder()
                .name("currency_agent")
                .description("An agent that can help with currency conversions and exchange rates.")
                .a2aClient(a2aClient)
                .agentCard(publicAgentCard)
                .build();

        logger.info("--- 🤖 Creating ADK Travel Agent... ---");

        return LlmAgent.builder()
                .model("gemini-3.8-flash")
                .name("travel_agent")
                .description("A travel assistant that can help plan trips, check weather forecasts via the local weather agent, and convert currencies via the remote currency agent.")
                .instruction(SYSTEM_INSTRUCTION)
                .tools(
                        AgentTool.create(currencyRemoteAgent),
                        AgentTool.create(WeatherAgent.WEATHER_AGENT))
                .build();
    }

    private TravelAgent() {
    }
}
