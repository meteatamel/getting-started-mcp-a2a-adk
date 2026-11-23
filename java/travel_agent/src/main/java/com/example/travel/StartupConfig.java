package com.example.travel;

import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import io.quarkus.runtime.StartupEvent;
import io.vertx.core.json.jackson.DatabindCodec;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.enterprise.event.Observes;

/**
 * Registers Jackson modules on startup for Vert.x JSON serialization.
 */
@ApplicationScoped
public class StartupConfig {

    void onStart(@Observes StartupEvent ev) {
        DatabindCodec.mapper().registerModule(new JavaTimeModule());
    }
}
