package com.example.currency;

import io.a2a.client.Client;
import io.a2a.client.ClientEvent;
import io.a2a.client.config.ClientConfig;
import io.a2a.client.http.A2ACardResolver;
import io.a2a.client.http.A2AHttpClient;
import io.a2a.client.http.JdkA2AHttpClient;
import io.a2a.client.transport.jsonrpc.JSONRPCTransport;
import io.a2a.client.transport.jsonrpc.JSONRPCTransportConfig;
import io.a2a.spec.AgentCard;
import io.a2a.spec.Message;
import io.a2a.spec.TextPart;
import java.util.List;
import java.util.UUID;
import java.util.function.BiConsumer;

/**
 * Direct A2A client for testing the Currency Agent over the A2A protocol.
 */
public class TestA2AClient {

    private static final String AGENT_URL =
            System.getenv().getOrDefault("AGENT_URL", "http://localhost:8081").replaceAll("/+$", "");
    private static final String ID_TOKEN = System.getenv("ID_TOKEN");

    private static A2AHttpClient createHttpClient() {
        A2AHttpClient delegate = new JdkA2AHttpClient();
        if (ID_TOKEN == null || ID_TOKEN.isBlank()) {
            return delegate;
        }
        return new A2AHttpClient() {
            @Override
            public GetBuilder createGet() {
                return delegate.createGet().addHeader("Authorization", "Bearer " + ID_TOKEN);
            }

            @Override
            public PostBuilder createPost() {
                return delegate.createPost().addHeader("Authorization", "Bearer " + ID_TOKEN);
            }

            @Override
            public DeleteBuilder createDelete() {
                return delegate.createDelete().addHeader("Authorization", "Bearer " + ID_TOKEN);
            }
        };
    }

    public static AgentCard getAgentCard() {
        System.out.println("🔄 Fetching the agent card at " + AGENT_URL);
        String agentCardUrl = AGENT_URL + "/.well-known/agent-card.json";
        AgentCard publicAgentCard =
                new A2ACardResolver(createHttpClient(), AGENT_URL, agentCardUrl).getAgentCard();
        System.out.println("✅ Successfully fetched the agent card");
        return publicAgentCard;
    }

    public static void sendMessage(AgentCard publicAgentCard, String textQuery) throws Exception {
        System.out.println("🔄 Initializing a non-streaming client");
        Client a2aClient = Client.builder(publicAgentCard)
                .withTransport(JSONRPCTransport.class, new JSONRPCTransportConfig(createHttpClient()))
                .clientConfig(new ClientConfig.Builder().setStreaming(false).build())
                .build();

        Message message = new Message.Builder()
                .messageId(UUID.randomUUID().toString())
                .role(Message.Role.USER)
                .parts(List.of(new TextPart(textQuery)))
                .build();

        System.out.println("Sending request: " + textQuery);
        System.out.println("Response:");

        BiConsumer<ClientEvent, AgentCard> consumer = (event, card) -> System.out.println(event);
        a2aClient.sendMessage(message, List.of(consumer), Throwable::printStackTrace, null);
    }

    public static void main(String[] args) {
        try {
            AgentCard publicAgentCard = getAgentCard();
            System.out.println("Agent Card: " + publicAgentCard);
            sendMessage(publicAgentCard, "how much is 100 USD in GBP?");
        } catch (Exception e) {
            e.printStackTrace();
            System.out.println("--- ❌ An error occurred: " + e.getMessage() + " ---");
            System.out.println("Ensure the agent server is running.");
        }
    }
}
