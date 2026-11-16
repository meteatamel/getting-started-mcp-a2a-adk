package com.example.travel;

import com.example.travel.subagents.WeatherAgent;
import com.google.adk.a2a.agent.RemoteA2AAgent;
import com.google.adk.agents.BaseAgent;
import com.google.adk.agents.LlmAgent;
import com.google.adk.agents.RunConfig;
import com.google.adk.events.Event;
import com.google.adk.runner.InMemoryRunner;
import com.google.adk.sessions.Session;
import com.google.adk.tools.AgentTool;
import com.google.adk.web.AdkWebServer;
import com.google.genai.types.Content;
import com.google.genai.types.Part;
import io.a2a.client.Client;
import io.a2a.client.config.ClientConfig;
import io.a2a.client.http.A2ACardResolver;
import io.a2a.client.http.A2AHttpClient;
import io.a2a.client.http.JdkA2AHttpClient;
import io.a2a.client.transport.jsonrpc.JSONRPCTransport;
import io.a2a.client.transport.jsonrpc.JSONRPCTransportConfig;
import io.a2a.spec.AgentCard;
import io.reactivex.rxjava3.core.Flowable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Orchestrating Travel Agent serving the ADK Web UI, delegating weather queries to the local
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
        // Uncomment to enable Cloud Run IAM authentication (and comment out the line above):
        // A2AHttpClient httpClient = CloudRunAuth.createA2AHttpClient(currencyAgentUrl);

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

    public static void main(String[] args) {
        if (args.length > 0) {
            String query = String.join(" ", args);
            logger.info("Running CLI query against travel_agent: {}", query);
            RunConfig runConfig = RunConfig.builder().build();
            InMemoryRunner runner = new InMemoryRunner(ROOT_AGENT);
            Session session = runner.sessionService()
                    .createSession(runner.appName(), "user123")
                    .blockingGet();
            Content userMsg = Content.fromParts(Part.fromText(query));
            Flowable<Event> events = runner.runAsync(session.userId(), session.id(), userMsg, runConfig);
            events.blockingForEach(event -> {
                if (event.finalResponse()) {
                    System.out.println(event.stringifyContent());
                }
            });
            return;
        }

        String port = System.getenv().getOrDefault("PORT", "8082");
        System.setProperty("server.port", port);
        System.setProperty("server.address", "0.0.0.0");
        logger.info("🚀 Starting travel_agent Web UI on port {}", port);
        AdkWebServer.start(ROOT_AGENT);
    }

    private TravelAgent() {
    }
}
