# Dockerfile for ollama-pull-model
FROM alpine:3.19

# Install curl and bash (needed for sleep)
RUN apk add --no-cache curl bash

# Copy the pull script
COPY pull-model.sh /pull-model.sh
RUN chmod +x /pull-model.sh

# Set entrypoint to run the script
ENTRYPOINT ["/pull-model.sh"]
