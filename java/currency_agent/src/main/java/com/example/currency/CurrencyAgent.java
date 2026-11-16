package com.example.currency;

import com.google.adk.agents.BaseAgent;
import com.google.adk.agents.LlmAgent;
import com.google.adk.tools.mcp.McpToolset;
import com.google.adk.tools.mcp.StreamableHttpServerParameters;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Specialized ADK Currency Agent connected to the Currency MCP Server.
 */
public final class CurrencyAgent {

    private static final Logger logger = LoggerFactory.getLogger(CurrencyAgent.class);

    private static final String SYSTEM_INSTRUCTION = """
            You are a specialized assistant for currency conversions.
            Your sole purpose is to use the 'get_exchange_rate' tool to answer questions about currency exchange rates.
            If the user asks about anything other than currency conversion or exchange rates, politely state that you cannot help with that topic and can only assist with currency-related queries.
            Do not attempt to answer unrelated questions or use tools for other purposes.
            """;

    public static final BaseAgent ROOT_AGENT = createAgent();

    private static BaseAgent createAgent() {
        String mcpServerUrl = System.getenv().getOrDefault("MCP_SERVER_URL", "http://localhost:8080/mcp");
        if (!mcpServerUrl.endsWith("/mcp")) {
            mcpServerUrl = mcpServerUrl.replaceAll("/+$", "") + "/mcp";
        }

        logger.info("--- 🔧 Loading MCP tools from MCP Server at {}... ---", mcpServerUrl);
        logger.info("--- 🤖 Creating ADK Currency Agent... ---");

        StreamableHttpServerParameters streamableParams = StreamableHttpServerParameters.builder()
                .url(mcpServerUrl)
                .build();

        McpToolset mcpToolset = new McpToolset(streamableParams);
        // Uncomment to enable Cloud Run IAM authentication (and comment out the line above):
        // McpToolset mcpToolset = CloudRunAuth.createMcpToolset(streamableParams);

        return LlmAgent.builder()
                .model("gemini-3.8-flash")
                .name("currency_agent")
                .description("An agent that can help with currency conversions")
                .instruction(SYSTEM_INSTRUCTION)
                .tools(mcpToolset)
                .build();
    }

    private CurrencyAgent() {
    }
}
