#!/usr/bin/with-contenv bashio

EXTERNAL_URL=$(bashio::config 'external_url')
PASSWORD=$(bashio::config 'password')
GOOGLE_CLIENT_ID=$(bashio::config 'google_client_id')
GOOGLE_CLIENT_SECRET=$(bashio::config 'google_client_secret')
GOOGLE_ALLOWED_USERS=$(bashio::config 'google_allowed_users')
PROXY_BEARER_TOKEN=$(bashio::config 'proxy_bearer_token')
BACKEND_COMMAND=$(bashio::config 'backend_command')

# Build the command array
CMD=( "/usr/local/bin/mcp-auth-proxy" )

if bashio::config.has_value 'external_url'; then
    CMD+=( "--external-url" "${EXTERNAL_URL}" )
fi

if bashio::config.has_value 'password'; then
    CMD+=( "--password" "${PASSWORD}" )
fi

if bashio::config.has_value 'google_client_id'; then
    CMD+=( "--google-client-id" "${GOOGLE_CLIENT_ID}" )
fi

if bashio::config.has_value 'google_client_secret'; then
    CMD+=( "--google-client-secret" "${GOOGLE_CLIENT_SECRET}" )
fi

if bashio::config.has_value 'google_allowed_users'; then
    CMD+=( "--google-allowed-users" "${GOOGLE_ALLOWED_USERS}" )
fi

if bashio::config.has_value 'proxy_bearer_token'; then
    CMD+=( "--proxy-bearer-token" "${PROXY_BEARER_TOKEN}" )
fi

bashio::log.info "Starting Sigbit MCP Auth Proxy..."

if bashio::config.has_value 'backend_command'; then
    # Do not use eval with CMD[*] to avoid space splitting in passwords
    exec "${CMD[@]}" -- $BACKEND_COMMAND
else
    exec "${CMD[@]}"
fi