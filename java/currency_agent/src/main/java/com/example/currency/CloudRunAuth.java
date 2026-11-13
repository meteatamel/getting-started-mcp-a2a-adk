package com.example.currency;

import com.google.adk.JsonBaseModel;
import com.google.adk.tools.mcp.DefaultMcpTransportBuilder;
import com.google.adk.tools.mcp.McpSessionManager;
import com.google.adk.tools.mcp.McpToolset;
import com.google.adk.tools.mcp.McpTransportBuilder;
import com.google.adk.tools.mcp.StreamableHttpServerParameters;
import com.google.auth.oauth2.GoogleCredentials;
import com.google.auth.oauth2.IdTokenCredentials;
import com.google.auth.oauth2.IdTokenProvider;
import io.modelcontextprotocol.client.transport.HttpClientStreamableHttpTransport;
import io.modelcontextprotocol.client.transport.customizer.McpAsyncHttpClientRequestCustomizer;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.net.URI;

/**
 * Attaches Google-signed OIDC ID tokens to outgoing Cloud Run MCP HTTP requests.
 */
public final class CloudRunAuth {

    public static McpToolset createMcpToolset(StreamableHttpServerParameters streamableParams) {
        return new McpToolset(
                new McpSessionManager(streamableParams, mcpTransportBuilder(streamableParams.url())),
                JsonBaseModel.getMapper());
    }

    public static McpTransportBuilder mcpTransportBuilder(String mcpServerUrl) {
        if (!mcpServerUrl.startsWith("https://")) {
            return new DefaultMcpTransportBuilder();
        }
        URI uri = URI.create(mcpServerUrl);
        String baseUri = uri.getScheme() + "://" + uri.getAuthority();
        String endpoint = (uri.getRawPath() == null || uri.getRawPath().isEmpty()) ? "/mcp" : uri.getRawPath();
        IdTokenCredentials idTokenCredentials = createIdTokenCredentials(baseUri);

        return params -> {
            if (params instanceof StreamableHttpServerParameters streamableParams) {
                return HttpClientStreamableHttpTransport.builder(baseUri)
                        .endpoint(endpoint)
                        .connectTimeout(streamableParams.timeout())
                        .asyncHttpRequestCustomizer(McpAsyncHttpClientRequestCustomizer.fromSync(
                                (builder, method, requestUri, body, context) ->
                                        builder.header("Authorization", "Bearer " + fetchToken(idTokenCredentials))))
                        .build();
            }
            return new DefaultMcpTransportBuilder().build(params);
        };
    }

    private static IdTokenCredentials createIdTokenCredentials(String audience) {
        try {
            GoogleCredentials adc = GoogleCredentials.getApplicationDefault();
            if (!(adc instanceof IdTokenProvider idTokenProvider)) {
                throw new IllegalStateException("Default credentials do not support OIDC ID tokens: " + adc.getClass());
            }
            return IdTokenCredentials.newBuilder()
                    .setIdTokenProvider(idTokenProvider)
                    .setTargetAudience(audience)
                    .build();
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to initialize Google ID token credentials", e);
        }
    }

    private static synchronized String fetchToken(IdTokenCredentials credentials) {
        try {
            credentials.refreshIfExpired();
            return credentials.getAccessToken().getTokenValue();
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to refresh Google ID token", e);
        }
    }

    private CloudRunAuth() {
    }
}
