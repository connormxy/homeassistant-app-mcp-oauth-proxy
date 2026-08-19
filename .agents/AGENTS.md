# Architecture Guide for AI Agents & Robots (Antigravity Reference)

## 📌 Mission Statement
This codebase (`mcp-server-oauth-proxy`) is a high-reliability, protocol-adapting OAuth 2.1 gateway designed to allow strict OAuth AI clients (specifically **Google Spark**) to communicate with any MCP (Model Context Protocol) backend, regardless of the backend's native authentication or transport capabilities.

---

## 🏛️ Core Architecture Principles

### 1. Two-Tier Decoupling (Downstream vs. Upstream)
Always maintain a strict mental and code separation between:
* **Downstream (Client ➔ Proxy)**:
  * Google Spark **only** talks OAuth 2.0 / 2.1.
  * If a server has `client_id` configured, any request from Spark that lacks a valid Bearer token **MUST receive a `401 Unauthorized` + `WWW-Authenticate` challenge**.
  * **CRITICAL RULE**: NEVER bypass the 401 challenge on unauthenticated downstream requests just because an upstream `bearer_token` is present. The 401 challenge is the exact signal that tells Google Spark's client to open its OAuth popup and save the connection!
* **Upstream (Proxy ➔ MCP Server)**:
  * Downstream authentication is completely decoupled from upstream authentication.
  * The proxy swaps Spark's incoming client Bearer token with whatever upstream requires:
    - **Static Bearer**: Injects `Authorization: Bearer <bearer_token>` (e.g. n8n, GitHub).
    - **Upstream OAuth**: Uses `server_refresh_token` + `server_token_url` to automatically maintain and inject live upstream access tokens (e.g. IFTTT, Azure).
    - **Persistent SSE Bridge**: Maintains background reading tasks to bridge Stateless HTTP JSON-RPC calls into persistent SSE streams (e.g. Playwright via `mcp-proxy`).

---

## 🔑 Key Mechanisms & Endpoints in `proxy.py`

### 1. OAuth 2.1 / OIDC Discovery
* `/.well-known/oauth-authorization-server` (RFC 8414)
* `/.well-known/oauth-protected-resource` & subpaths
* `/.well-known/openid-configuration` (OIDC)
* `/.well-known/jwks.json` & `/jwks.json` (returns `{"keys": []}`)

### 2. Authorization Handshake (`/authorize` & `/oauth/authorize`)
* Accepts standard OAuth 2.1 parameters (`redirect_uri`, `state`, `client_id`, `response_type`, `scope`, `code_challenge`, `code_challenge_method`, `prompt`).
* **Rule**: All parameters must have default values (`= None` or `= ""`) in the FastAPI signature to prevent `422 Unprocessable Entity` crashes when clients omit non-essential fields.
* Redirects user back to `redirect_uri` with `code=<resolved_client_id>&state=<state>`.

### 3. Token Exchange (`/token` & `/oauth/token`)
* Supports `application/x-www-form-urlencoded`, `application/json`, URL query parameters, and `Authorization: Basic <base64>` header credentials (`client_secret_basic`).
* Returns:
  ```json
  {
    "access_token": "<client_id>",
    "token_type": "Bearer",
    "expires_in": 86400,
    "refresh_token": "<client_id>"
  }
  ```

### 4. CORS & Preflight (`OPTIONS` & `HEAD`)
* **`OPTIONS` requests**: Handled immediately with `204 No Content` and full wildcard CORS headers (`Access-Control-Allow-Origin: *`, `Access-Control-Expose-Headers: *`, `Access-Control-Max-Age: 86400`).
* **`HEAD` requests**: Handled immediately with `200 OK` for fast MCP endpoint liveness probing.
* **Non-SSE responses**: Read in full (`await resp.aread()`) and returned as finite closed HTTP responses with exact headers to prevent client-side chunked stream hangs.

### 5. Persistent Upstream SSE Bridge (`mcp-proxy` & Playwright)
* When a stateless client issues `POST` JSON-RPC messages to an SSE-only upstream (which returns `405 Method Not Allowed` on POST):
  1. Proxy opens a long-lived upstream SSE connection (`GET <target_url>`).
  2. Discovers the dynamic messages endpoint (e.g. `/messages?session_id=...`).
  3. Spawns an asynchronous background reader task `background_sse_reader` listening to the SSE stream.
  4. Associates JSON-RPC request `id`s with `asyncio.Future` promises.
  5. Forwards the `POST` payload to the discovered messages endpoint and waits for the matching response `id` from the SSE reader.

---

## 🚦 Server Matching Order in `get_server_for_request`
1. **Subdomain / Host Header** (`host: "n8n-oauth.domain.com"`).
2. **URL Path Prefix** (`path_prefix: "/n8n"`).
3. **Bearer Token / Client ID** matching `server.client_id`.
4. **Single-server fallback** (if only 1 server is configured).

---

## 🛡️ Future Robot Checklist Before Making Edits
- [ ] Did you preserve `is_authenticated = bool(token_str) or not bool(server_client_id)`? (Do NOT remove the 401 challenge!)
- [ ] Are all query parameters in OAuth endpoints defaulted so FastAPI never throws 422?
- [ ] Are non-SSE JSON responses returned as buffered `Response(content=...)` rather than `StreamingResponse`?
- [ ] Does `config.yaml` version match the release tag you intend to deploy?
