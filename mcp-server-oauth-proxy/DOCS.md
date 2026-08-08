# MCP Server OAuth Proxy

This Home Assistant add-on runs a lightweight FastAPI proxy. 

## Purpose

The **MCP Server OAuth Proxy** allows external OAuth 2.1 clients (like **Gemini Spark**) to securely connect to your local MCP servers (like **n8n** or custom containers) without exposing them directly.

It simulates a basic OAuth 2.1 authorization server, verifying the client's `client_id` and redirecting back with a one-time code. When proxying requests, it intercepts the call and injects a designated authorization header (e.g., your n8n Personal Access Token) before forwarding it to the target upstream URL.

## Configuration

You can configure your upstream MCP server in the Home Assistant add-on configuration tab.

*   **`upstream_url`**: The HTTP/SSE endpoint of your upstream MCP server.
*   **`n8n_token`**: The authentication token required by the upstream server.
*   **`client_id`**: The Client ID you provide to the external service (e.g., Gemini Spark).
*   **`client_secret`**: The Client Secret you provide to the external service.

## Catch-All Routing

This proxy is designed to act as a catch-all router. If you expose this proxy to the internet via Cloudflare Tunnels at `https://proxy.example.com`, whatever path the external client calls will be forwarded to the `upstream_url`. This allows the client to connect using its expected pathing (e.g., `/mcp-server/http`) without getting 404 errors.
