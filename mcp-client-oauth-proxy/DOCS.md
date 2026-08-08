# MCP Client OAuth Proxy

This Home Assistant add-on packages the standalone [obot-platform/mcp-oauth-proxy](https://github.com/obot-platform/mcp-oauth-proxy) project to act as a bridge.

## Purpose

The **MCP Client OAuth Proxy** is designed to proxy requests from an MCP client to an upstream, OAuth-protected MCP Server (like Google Workspace or Azure MCP servers). 

When a client makes a streamable HTTP request, it provides a bearer token. This proxy verifies the client via the OAuth 2.1 flow using the agreed-upon `client_id` and `client_secret`, and then forwards the request (with injected user context) to the `upstream_url`.

## Configuration Options

Because these options are injected at runtime into the container’s environment variables via Home Assistant's `bashio::config`, the Home Assistant Add-on UI is the *only* source of truth. Any changes to the UI configuration will be fully enforced on the next add-on restart.

*   **`upstream_url`**: The endpoint of the OAuth-protected, upstream MCP server you are proxying to.
*   **`bearer_token`**: The authorization token this container *expects to receive* from the connecting MCP client. 
*   **`client_id`**: The OAuth client ID.
*   **`client_secret`**: The OAuth client secret.
