# Home Assistant MCP OAuth Proxies

This repository provides two Home Assistant OS local add-ons that facilitate OAuth authentication in opposite directions for the Model Context Protocol (MCP).

## 1. MCP Client OAuth Proxy
*(Located in `mcp-client-oauth-proxy/`)*

This add-on packages the open-source `obot-platform/mcp-oauth-proxy`. 
**Direction:** It allows a local MCP client to securely access external OAuth-protected MCP servers (e.g., Google Workspace, Azure). It handles the OAuth authorization flow and injects the resulting credentials and user identity into the streamable HTTP requests forwarded to the server.

## 2. MCP Server OAuth Proxy
*(Located in `mcp-server-oauth-proxy/`)*

This add-on runs a lightweight FastAPI application.
**Direction:** It allows external OAuth clients (e.g., Gemini Spark) to access your local MCP servers (e.g., n8n). It simulates an OAuth 2.1 server to accept connections from the external client, and then injects your personal access tokens (like an n8n API key) into the requests before forwarding them to your local MCP server.

## 3. Sigbit MCP Auth Proxy
*(Located in `sigbit-mcp-auth-proxy/`)*

This add-on packages the open-source `sigbit/mcp-auth-proxy`. 
**Direction:** It acts as a drop-in authentication gateway. It sits in front of any standard stdio, SSE, or HTTP MCP server and adds an authentication layer (OAuth, OIDC, or Password) before clients are allowed to connect.