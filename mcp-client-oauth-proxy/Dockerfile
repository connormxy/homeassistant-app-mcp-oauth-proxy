ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# 1. Copy ONLY the compiled executable from the official upstream image
COPY --from=ghcr.io/obot-platform/mcp-oauth-proxy:latest /app/oauth-proxy /usr/local/bin/oauth-proxy

# 2. Copy the startup script
COPY run.sh /

# 3. Single chained RUN step to set permissions and clean temporary files
RUN chmod +x /usr/local/bin/oauth-proxy /run.sh \
    && rm -rf /tmp/* /var/cache/apk/*

CMD [ "/run.sh" ]