# Build stage
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
RUN mvn package -DskipTests -B

# Run stage
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /app/target/quarkus-app/ /app/quarkus-app/

EXPOSE 8080

CMD ["java", "-jar", "/app/quarkus-app/quarkus-run.jar"]
