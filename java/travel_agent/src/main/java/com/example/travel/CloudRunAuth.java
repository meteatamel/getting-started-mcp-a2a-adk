package com.example.travel;

import com.google.auth.oauth2.GoogleCredentials;
import com.google.auth.oauth2.IdTokenCredentials;
import com.google.auth.oauth2.IdTokenProvider;
import io.a2a.client.http.A2AHttpClient;
import io.a2a.client.http.JdkA2AHttpClient;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.net.URI;

/**
 * Wraps {@link JdkA2AHttpClient} to attach Google-signed OIDC ID tokens for Cloud Run A2A calls.
 */
public final class CloudRunAuth {

    public static A2AHttpClient createA2AHttpClient(String agentUrl) {
        A2AHttpClient delegate = new JdkA2AHttpClient();
        if (!agentUrl.startsWith("https://")) {
            return delegate;
        }
        URI uri = URI.create(agentUrl);
        String audience = uri.getScheme() + "://" + uri.getAuthority();
        IdTokenCredentials credentials = createIdTokenCredentials(audience);

        return new A2AHttpClient() {
            @Override
            public GetBuilder createGet() {
                return delegate.createGet().addHeader("Authorization", "Bearer " + fetchToken(credentials));
            }

            @Override
            public PostBuilder createPost() {
                return delegate.createPost().addHeader("Authorization", "Bearer " + fetchToken(credentials));
            }

            @Override
            public DeleteBuilder createDelete() {
                return delegate.createDelete().addHeader("Authorization", "Bearer " + fetchToken(credentials));
            }
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
