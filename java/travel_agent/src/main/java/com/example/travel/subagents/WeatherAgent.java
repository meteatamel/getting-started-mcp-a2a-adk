package com.example.travel.subagents;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.adk.agents.BaseAgent;
import com.google.adk.agents.LlmAgent;
import com.google.adk.tools.Annotations.Schema;
import com.google.adk.tools.FunctionTool;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Local specialist ADK agent that provides current weather reports and forecasts for travel destinations.
 */
public final class WeatherAgent {

    private static final Logger logger = LoggerFactory.getLogger(WeatherAgent.class);
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    private static final HttpClient HTTP_CLIENT = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(8))
            .build();

    private static final String SYSTEM_INSTRUCTION = """
            You are a specialized assistant for providing weather forecasts and conditions for travel destinations.
            Your sole purpose is to use the 'get_weather' tool to fetch weather information.
            Provide clear, concise summaries of current weather conditions, temperatures, and forecasts to help travelers pack and plan.
            """;

    @Schema(
            name = "get_weather",
            description = "Gets the current weather and forecast for a given location or city.")
    public static Map<String, Object> getWeather(
            @Schema(
                    name = "location",
                    description = "The city or location name (e.g., 'London', 'Tokyo', 'Paris').")
            String location) {
        String loc = (location == null || location.isBlank()) ? "London" : location;
        logger.info("--- 🌤️ Tool: get_weather called for {} ---", loc);
        try {
            String encodedLoc = URLEncoder.encode(loc, StandardCharsets.UTF_8);
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create("https://wttr.in/" + encodedLoc + "?format=j1"))
                    .header("User-Agent", "curl/7.68.0")
                    .timeout(Duration.ofSeconds(8))
                    .GET()
                    .build();

            HttpResponse<String> response = HTTP_CLIENT.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new RuntimeException("HTTP status " + response.statusCode());
            }

            JsonNode data = OBJECT_MAPPER.readTree(response.body());
            JsonNode current = data.path("current_condition").get(0);
            String desc = current.path("weatherDesc").path(0).path("value").asText("Unknown");
            String tempC = current.path("temp_C").asText("N/A");
            String tempF = current.path("temp_F").asText("N/A");
            String humidity = current.path("humidity").asText("N/A");
            String windSpeedKmph = current.path("windspeedKmph").asText("N/A");

            Map<String, Object> result = Map.of(
                    "location", loc,
                    "condition", desc,
                    "temperature_celsius", tempC + "°C",
                    "temperature_fahrenheit", tempF + "°F",
                    "humidity", humidity + "%",
                    "wind_speed_kmph", windSpeedKmph + " km/h");

            logger.info("✅ Weather data fetched: {}", result);
            return result;
        } catch (Exception e) {
            logger.warn("⚠️ Weather lookup via API failed: {}. Returning simulated estimate.", e.getMessage());
            return Map.of(
                    "location", loc,
                    "condition", "Partly Cloudy",
                    "temperature_celsius", "20°C",
                    "temperature_fahrenheit", "68°F",
                    "humidity", "55%",
                    "wind_speed_kmph", "10 km/h",
                    "note", "Live data unavailable (" + e.getMessage() + "); showing estimated conditions.");
        }
    }

    public static final BaseAgent WEATHER_AGENT = LlmAgent.builder()
            .model("gemini-3.8-flash")
            .name("weather_agent")
            .description("A local specialist agent that provides current weather reports and forecasts for travel destinations.")
            .instruction(SYSTEM_INSTRUCTION)
            .tools(FunctionTool.create(WeatherAgent.class, "getWeather"))
            .build();

    private WeatherAgent() {
    }
}
