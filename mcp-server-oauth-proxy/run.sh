#!/usr/bin/with-contenv bashio

bashio::log.info "Starting MCP Server OAuth Proxy on port 8090..."
cd /app
exec uvicorn proxy:app --host 0.0.0.0 --port 8090