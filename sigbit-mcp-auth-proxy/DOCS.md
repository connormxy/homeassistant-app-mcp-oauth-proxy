# Sigbit MCP Auth Proxy

This add-on packages the open-source `sigbit/mcp-auth-proxy` project, offering a lightweight drop-in OAuth 2.1/OIDC gateway for any MCP server.

## Purpose

It allows you to put an authentication layer (OAuth, OIDC, or plain password) in front of any MCP server with zero code changes. It supports stdio, SSE, and HTTP transports. 

For stdio connections, you provide the backend command (like `npx -y @modelcontextprotocol/server-filesystem ./`), and the proxy converts the traffic to HTTP at `/mcp`. 
Alternatively, if your MCP server already operates via HTTP/SSE (like n8n), you can provide its internal HTTP URL instead of a command.

## Configuration Options

- **`external_url`**: Your externally accessible URL (e.g., `https://your-domain.com`).
- **`password`**: Plain text password for basic authentication.
- **`google_client_id`**: Your Google OAuth Client ID.
- **`google_client_secret`**: Your Google OAuth Client Secret.
- **`google_allowed_users`**: Comma-separated list of allowed Google user emails.
- **`proxy_bearer_token`**: A bearer token (like a Personal Access Token) to add to the `Authorization` header when proxying requests to an HTTP upstream server.
- **`backend_command`**: The CLI command to start your MCP server using stdio (e.g., `npx @modelcontextprotocol/server-everything`), or the target HTTP URL if proxying directly to a local HTTP server (e.g. `http://localhost:5678/mcp-server/http`).