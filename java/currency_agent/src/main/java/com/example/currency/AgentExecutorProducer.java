package com.example.currency;

import com.google.adk.a2a.executor.AgentExecutor.Builder;
import com.google.adk.a2a.executor.AgentExecutorConfig;
import com.google.adk.artifacts.InMemoryArtifactService;
import com.google.adk.sessions.InMemorySessionService;
import io.a2a.server.agentexecution.AgentExecutor;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.inject.Produces;

/**
 * Produces the ADK {@link AgentExecutor} that bridges A2A JSON-RPC requests to {@link CurrencyAgent}.
 */
@ApplicationScoped
public class AgentExecutorProducer {

    @Produces
    public AgentExecutor agentExecutor() {
        return new Builder()
                .agent(CurrencyAgent.ROOT_AGENT)
                .appName("currency_agent")
                .sessionService(new InMemorySessionService())
                .artifactService(new InMemoryArtifactService())
                .agentExecutorConfig(AgentExecutorConfig.builder().build())
                .build();
    }
}
