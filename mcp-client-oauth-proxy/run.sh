#!/usr/bin/with-contenv bashio

LOG_LEVEL=$(bashio::config 'log_level' 'info')
OAUTH_CLIENT_ID=$(bashio::config 'oauth_client_id')
OAUTH_CLIENT_SECRET=$(bashio::config 'oauth_client_secret')
OAUTH_AUTHORIZE_URL=$(bashio::config 'oauth_authorize_url')
SCOPES_SUPPORTED=$(bashio::config 'scopes_supported')
MCP_SERVER_URL=$(bashio::config 'mcp_server_url')
ENCRYPTION_KEY=$(bashio::config 'encryption_key')

export OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID}"
export OAUTH_CLIENT_SECRET="${OAUTH_CLIENT_SECRET}"
export OAUTH_AUTHORIZE_URL="${OAUTH_AUTHORIZE_URL}"
export SCOPES_SUPPORTED="${SCOPES_SUPPORTED}"
export MCP_SERVER_URL="${MCP_SERVER_URL}"
export ENCRYPTION_KEY="${ENCRYPTION_KEY}"
export HOST="0.0.0.0"
export PORT=8090

mkdir -p /data
export DATABASE_DSN="/data/oauth_proxy.db"

bashio::log.info "Starting MCP Client OAuth Proxy on 0.0.0.0:8090 with log_level=${LOG_LEVEL}..."

if [ "$LOG_LEVEL" = "debug" ] || [ "$LOG_LEVEL" = "trace" ]; then
    bashio::log.info "Verbose logging enabled for oauth-proxy binary."
    export ROOT_CMD_VERBOSE="true"
fi

exec /usr/local/bin/oauth-proxy