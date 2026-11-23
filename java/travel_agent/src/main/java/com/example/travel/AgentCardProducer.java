package com.example.travel;

import io.a2a.server.PublicAgentCard;
import io.a2a.spec.AgentCard;
import io.a2a.util.Utils;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;

/**
 * Produces the public {@link AgentCard} for the Travel A2A server.
 */
@ApplicationScoped
public class AgentCardProducer {

    @Produces
    @PublicAgentCard
    public AgentCard agentCard() {
        String port = System.getenv().getOrDefault("PORT", "8082");
        String agentUrl = System.getenv("AGENT_URL");
        if (agentUrl == null || agentUrl.isBlank()) {
            agentUrl = "http://localhost:" + port;
        }

        String cardJson = """
                {
                  "name": "travel_agent",
                  "description": "A travel assistant that can help plan trips, check weather forecasts via the local weather agent, and convert currencies via the remote currency agent.",
                  "url": "%s",
                  "version": "1.0.0",
                  "preferredTransport": "JSONRPC",
                  "capabilities": {
                    "streaming": false
                  },
                  "defaultInputModes": ["text/plain"],
                  "defaultOutputModes": ["text/plain"],
                  "skills": [
                    {
                      "id": "travel_planning",
                      "name": "Travel Planning Assistant",
                      "description": "Helps plan trips, checks weather forecasts via the local weather agent, and converts currencies via the remote A2A currency agent",
                      "tags": ["travel", "weather", "currency"]
                    }
                  ]
                }
                """.formatted(agentUrl);

        try {
            return Utils.OBJECT_MAPPER.readValue(cardJson, AgentCard.class);
        } catch (Exception e) {
            throw new RuntimeException("Failed to create AgentCard", e);
        }
    }
}
