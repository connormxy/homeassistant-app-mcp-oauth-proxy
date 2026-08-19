ARG BUILD_ARCH=amd64
ARG BUILD_FROM=ghcr.io/home-assistant/${BUILD_ARCH}-base:latest

# 1. Pinned immutable upstream commit with pure-Go sqlite (amd64 + arm64)
FROM ghcr.io/obot-platform/mcp-oauth-proxy:main-32b8278 AS upstream

# 2. Official Home Assistant base image
FROM ${BUILD_FROM}

# Copy precompiled binary from upstream
COPY --from=upstream /app/oauth-proxy /usr/local/bin/oauth-proxy
COPY run.sh /

RUN chmod +x /usr/local/bin/oauth-proxy /run.sh

CMD [ "/run.sh" ]