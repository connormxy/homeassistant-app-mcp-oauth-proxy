# MCP Server OAuth Proxy

A lightweight, high-performance FastAPI proxy designed for Home Assistant that bridges **OAuth 2.0 / 2.1 AI clients** (such as **Google Spark**, Claude, Cursor, ChatGPT) to any upstream **MCP (Model Context Protocol)** backend.

---

## 🎯 Purpose & Architecture

### The Problem
* Modern AI clients (like **Google Spark**) mandate full **OAuth 2.0 / 2.1** handshakes to connect to any MCP server and refuse connections without an active OAuth session.
* Most local or custom MCP servers (like **n8n**, **GitHub MCP**, **Playwright**, or **IFTTT**) do not implement downstream OAuth servers—they expect static API keys, raw SSE streaming, or upstream OAuth tokens.

### The Solution: Two-Way Decoupled Proxy
This proxy acts as a bidirectional authentication and protocol bridge:

```
┌─────────────────────────┐          ┌──────────────────────────┐          ┌──────────────────────────┐
│                         │  OAuth   │                          │  Custom  │   Target MCP Servers     │
│   Google Spark Client   │ 2.0/2.1  │   MCP Server OAuth Proxy │ Protocols│ ─ n8n (Static Bearer)    │
│ (Demands OAuth Login)   ├─────────►│  (Simulates OAuth 2.1)   ├─────────►│ ─ GitHub (SSE Bridge)    │
│                         │          │                          │          │ ─ IFTTT (OAuth Auto-Ref) │
│                         │          │                          │          │ ─ Playwright (CDP Bridge)│
└─────────────────────────┘          └──────────────────────────┘          └──────────────────────────┘
```

1. **Downstream (Facing Google Spark)**:
   * Serves complete RFC OAuth 2.1 & OIDC discovery metadata (`/.well-known/oauth-authorization-server`, `/.well-known/openid-configuration`).
   * Issues `401 Unauthorized` + `WWW-Authenticate` challenges to unauthenticated probes so Spark automatically opens its OAuth consent window.
   * Handles `/authorize` and `/token` seamlessly, granting standard Bearer tokens.
   * Handles browser CORS preflight (`OPTIONS` -> `204 No Content`) with `Access-Control-Allow-Origin: *`.

2. **Upstream (Facing Target Backends)**:
   * **Static Bearer Token**: Automatically attaches `Authorization: Bearer <upstream_token>` (e.g. n8n, GitHub).
   * **Upstream OAuth Auto-Refresh**: Uses `server_refresh_token` to maintain and inject live access tokens from 3rd-party providers (e.g. IFTTT, Azure, Google Workspace).
   * **Persistent SSE Session Bridge**: Automatically bridges Stateless HTTP JSON-RPC calls into persistent SSE streams (e.g. `@executeautomation/playwright-mcp-server` over `mcp-proxy`).
   * **Stateless HTTP to SSE Keepalive Bridge**: Keeps open SSE keepalive channels for stateless backends that reject GET requests with 405.

---

## ⚙️ Configuration Reference

In Home Assistant, navigate to **Settings > Add-ons > MCP Server OAuth Proxy > Configuration**.

### Server Options

| Field | Type | Description |
| :--- | :--- | :--- |
| `client_name` | String | Identifier for connecting client (e.g. `"Google Spark"`). |
| `server_name` | String | Name of the upstream MCP service (e.g. `"n8n"`, `"GitHub"`, `"IFTTT"`, `"Playwright"`). |
| `server_url` | String | Full HTTP/SSE target URL (e.g. `http://6560bdea-hass-n8n:5678/mcp-server/http`). |
| `server_scheme` | String | Protocol for modular address (`"http"` or `"https"`). |
| `server_host` | String | Docker container name, LAN IP, or hostname (e.g. `"6560bdea-hass-n8n"` or `"192.168.86.61"`). |
| `server_port` | Int | Target service port (e.g. `5678`, `8082`, `9876`). |
| `server_path` | String | Target path route (e.g. `"/mcp-server/http"`, `"/sse"`). |
| `bearer_token` | String | Static token required by target server (if not using upstream OAuth refresh). |
| `client_id` | String | Client ID configured in Google Spark (e.g. `"spark-client-1"`). |
| `client_secret` | String | Client Secret configured in Google Spark. |
| `allowed_redirect_uris` | String | Permitted OAuth redirect URIs (e.g. `"https://oauth-redirect.googleusercontent.com"`). |
| `host` | String | Public subdomain routing traffic to this server (e.g. `"n8n-oauth.connormoseley.com"`). |
| `path_prefix` | String | Optional path prefix for single-domain routing (e.g. `"/n8n"`). |
| `server_authorize_url`| String | (Upstream OAuth) 3rd-party authorize URL (e.g. `"https://ifttt.com/oauth/authorize"`). |
| `server_token_url` | String | (Upstream OAuth) 3rd-party token exchange URL (e.g. `"https://ifttt.com/oauth/token"`). |
| `server_client_id` | String | (Upstream OAuth) Client ID registered with 3rd-party provider. |
| `server_client_secret`| String| (Upstream OAuth) Client Secret registered with 3rd-party provider. |
| `server_refresh_token`| String| (Upstream OAuth) Initial refresh token used to auto-renew access tokens. |

---

## 📋 Common Setup Examples

### 1. n8n Instance-Level MCP Server
```yaml
servers:
  - client_name: "Google Spark"
    server_name: "n8n"
    server_url: "http://6560bdea-hass-n8n:5678/mcp-server/http"
    bearer_token: "your-n8n-api-key"
    client_id: "spark-n8n"
    client_secret: "secret-n8n"
    allowed_redirect_uris: "https://oauth-redirect.googleusercontent.com"
    host: "n8n-oauth.yourdomain.com"
```

### 2. GitHub MCP Server (Container)
```yaml
servers:
  - client_name: "Google Spark"
    server_name: "GitHub"
    server_url: "http://192.168.86.250:8082/sse"
    bearer_token: "ghp_yourPersonalAccessToken"
    client_id: "spark-github"
    client_secret: "secret-github"
    allowed_redirect_uris: "https://oauth-redirect.googleusercontent.com"
    host: "github-oauth.yourdomain.com"
```

### 3. Playwright Browser Automation (via MCP Proxy)
```yaml
servers:
  - client_name: "Google Spark"
    server_name: "Playwright"
    server_url: "http://5fa18e75-mcp-proxy:9876/servers/playwright/sse"
    bearer_token: ""
    client_id: "spark-playwright"
    client_secret: "secret-playwright"
    allowed_redirect_uris: "https://oauth-redirect.googleusercontent.com"
    host: "playwright-oauth.yourdomain.com"
```

### 4. IFTTT (Upstream OAuth Auto-Refresh)
```yaml
servers:
  - client_name: "Google Spark"
    server_name: "IFTTT"
    server_url: "https://ifttt.com/mcp"
    client_id: "spark-ifttt"
    client_secret: "secret-ifttt"
    allowed_redirect_uris: "https://oauth-redirect.googleusercontent.com"
    host: "ifttt-oauth.yourdomain.com"
    server_authorize_url: "https://ifttt.com/oauth/authorize"
    server_token_url: "https://ifttt.com/oauth/token"
    server_client_id: "YOUR_IFTTT_DEVELOPER_CLIENT_ID"
    server_client_secret: "YOUR_IFTTT_DEVELOPER_CLIENT_SECRET"
    server_refresh_token: "YOUR_IFTTT_REFRESH_TOKEN"
```

---

## 🔗 Connecting from Google Spark

1. In **Google Spark** (or Google Workspace Gemini Extensions), click **Add Custom Tool / Server**.
2. **Server URL**: Enter your public proxy subdomain route (e.g. `https://n8n-oauth.yourdomain.com/mcp-server/http`).
3. **Authentication**: Choose **OAuth 2.0**.
4. Enter the matching **Client ID** and **Client Secret** configured in your add-on options.
5. Click **Connect**:
   * Google Spark will query the proxy's discovery endpoints and prompt for approval.
   * The proxy immediately fulfills the authorization code and token exchange.
   * Google Spark marks the server as **Connected** and locks the toggle **ON**.
