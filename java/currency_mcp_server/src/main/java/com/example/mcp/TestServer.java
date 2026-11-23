package com.example.mcp;

import io.modelcontextprotocol.client.McpClient;
import io.modelcontextprotocol.client.McpSyncClient;
import io.modelcontextprotocol.client.transport.HttpClientStreamableHttpTransport;
import io.modelcontextprotocol.spec.McpSchema.CallToolRequest;
import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import io.modelcontextprotocol.spec.McpSchema.ListToolsResult;
import io.modelcontextprotocol.spec.McpSchema.TextContent;
import io.modelcontextprotocol.spec.McpSchema.Tool;
import java.net.URI;
import java.util.Map;

/**
 * Direct MCP client for testing the Currency MCP Server over Streamable HTTP.
 */
public class TestServer {

    public static void main(String[] args) {
        String mcpUrl = System.getenv().getOrDefault("MCP_SERVER_URL", "http://localhost:8080/mcp");
        System.out.println("Connecting to MCP server at: " + mcpUrl);

        URI uri = URI.create(mcpUrl);
        String baseUri = uri.getScheme() + "://" + uri.getAuthority();
        String endpoint = (uri.getRawPath() == null || uri.getRawPath().isEmpty()) ? "/mcp" : uri.getRawPath();

        HttpClientStreamableHttpTransport transport = HttpClientStreamableHttpTransport.builder(baseUri)
                .endpoint(endpoint)
                .build();

        try (McpSyncClient client = McpClient.sync(transport).build()) {
            client.initialize();

            ListToolsResult toolsResult = client.listTools();
            for (Tool tool : toolsResult.tools()) {
                System.out.println("--- 🛠️  Tool found: " + tool.name() + " ---");
            }

            System.out.println("--- 🪛  Calling get_exchange_rate tool for USD to EUR ---");
            CallToolResult result = client.callTool(
                    new CallToolRequest("get_exchange_rate", Map.of("currency_from", "USD", "currency_to", "EUR")));

            if (result.content() != null && !result.content().isEmpty()
                    && result.content().get(0) instanceof TextContent textContent) {
                System.out.println("--- ✅  Success: " + textContent.text() + " ---");
            } else {
                System.out.println("--- ✅  Success: " + result + " ---");
            }
        }
    }
}
