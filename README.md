# Home Assistant MCP OAuth Proxies

A repository of Home Assistant OS local add-ons providing enterprise-grade OAuth 2.0 / 2.1 bridging, authentication, and protocol adaptation for the Model Context Protocol (MCP).

---

## 📦 Included Add-ons

### 1. MCP Server OAuth Proxy (`mcp-server-oauth-proxy/`)
* **Direction**: Downstream OAuth Server ➔ Upstream MCP Backends.
* **Use Case**: Allows strict OAuth 2.0 / 2.1 AI clients (such as **Google Spark**, Claude, Cursor, ChatGPT) to connect to internal MCP servers (like **n8n**, **GitHub**, **Playwright**, **IFTTT**, or custom Docker containers).
* **Key Features**:
  * **OAuth 2.1 & OIDC Discovery**: RFC 8414 (`/.well-known/oauth-authorization-server`) and OpenID discovery (`/.well-known/openid-configuration`) with complete `/authorize`, `/token`, `/register`, `/revoke`, `/introspect`, and `/jwks.json` suites.
  * **Static Bearer Token Injection**: Automatically attaches upstream API keys / Bearer tokens for backends that don't speak OAuth (e.g. n8n, GitHub).
  * **Upstream OAuth Auto-Refresh**: Automatically maintains and renews 3rd-party OAuth access tokens (e.g. IFTTT, Google Workspace, Azure) via background token caching and refresh flows.
  * **Persistent SSE Session Bridge**: Automatically bridges Stateless HTTP JSON-RPC calls into persistent SSE streams (e.g. `@executeautomation/playwright-mcp-server` over `mcp-proxy`) with asynchronous background readers.
  * **Multi-Factor Routing**: Routes incoming requests by Host Header / Subdomain (`host`), URL Path Prefix (`path_prefix`), or Client ID.
  * **Full CORS & Zero-Latency Preflight**: Intercepts browser `OPTIONS` with `204 No Content` and broadcasts complete CORS headers for web-based AI clients.

---

### 2. MCP Client OAuth Proxy (`mcp-client-oauth-proxy/`)
* **Direction**: Local MCP Client ➔ Upstream OAuth-Protected Services.
* **Use Case**: Packages `obot-platform/mcp-oauth-proxy`. Allows local MCP clients (like Home Assistant AI agents or local IDEs) to securely call external OAuth-protected MCP servers (e.g. Google Workspace, Azure, Salesforce).

---

## 🛠️ Repository Structure

```
homeassistant-app-mcp-oauth-proxy/
├── mcp-server-oauth-proxy/        # FastAPI Dynamic OAuth 2.1 Server & Protocol Bridge
│   ├── config.yaml                # Add-on manifest & schema
│   ├── proxy.py                   # Proxy core, OAuth engine, & session bridge
│   ├── DOCS.md                    # In-depth setup & backend configuration guide
│   └── translations/              # Home Assistant UI schema labels
├── mcp-client-oauth-proxy/        # Obot Platform MCP Client Proxy
├── .agents/                       # Developer & Agent architecture guidelines
└── README.md                      # Repository overview
```