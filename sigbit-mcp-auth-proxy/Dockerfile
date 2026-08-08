ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

RUN apk add --no-cache curl tzdata nodejs npm python3

# Download binary based on architecture. Use -f to fail on 404s.
RUN if [ "$(uname -m)" = "x86_64" ]; then \
        curl -sfL -o /usr/local/bin/mcp-auth-proxy https://github.com/sigbit/mcp-auth-proxy/releases/download/v2.10.2/mcp-auth-proxy-linux-amd64; \
    elif [ "$(uname -m)" = "aarch64" ]; then \
        curl -sfL -o /usr/local/bin/mcp-auth-proxy https://github.com/sigbit/mcp-auth-proxy/releases/download/v2.10.2/mcp-auth-proxy-linux-arm64; \
    fi && \
    chmod +x /usr/local/bin/mcp-auth-proxy

COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD [ "/run.sh" ]