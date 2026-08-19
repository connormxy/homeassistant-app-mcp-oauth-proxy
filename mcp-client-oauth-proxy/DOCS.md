# MCP Client OAuth Proxy

This Home Assistant add-on packages the upstream [obot-platform/mcp-oauth-proxy](https://github.com/obot-platform/mcp-oauth-proxy) project as an official Home Assistant Add-on.

---

## 🎯 Purpose & Architecture

The **MCP Client OAuth Proxy** is an OAuth 2.1 proxy server designed to add authentication and authorization to Model Context Protocol (MCP) servers.

It sits between MCP clients (e.g. VS Code, Antigravity IDE, Cursor, Claude Desktop) and upstream MCP servers that require OAuth token exchange, dynamically managing authorization flows, token storage, and session validation.

```
+------------+       +-------------------------+       +-------------------+
| MCP Client | ----> | MCP Client OAuth Proxy  | ----> | Upstream Server   |
| (IDE / UI) |       | (Home Assistant :8098)  |       | (Google / IFTTT)  |
+------------+       +-------------------------+       +-------------------+
                                  |
                                  v
                       +-----------------------+
                       | OAuth Provider        |
                       | (accounts.google.com) |
                       +-----------------------+
```

---

## ⚙️ Configuration Options

Configure these in the Home Assistant Add-on **Configuration** tab:

| Option | Required | Description | Example |
| :--- | :---: | :--- | :--- |
| `oauth_client_id` | ✅ | OAuth Client ID from provider | `TANL26zrttBBoUN2Z5ILX5Da...` |
| `oauth_client_secret` | ✅ | OAuth Client Secret from provider | `jJRiJ9AjR4AbfOXWTRH5DR...` |
| `oauth_authorize_url` | ✅ | Provider Base Auth URL | `https://ifttt.com` or `https://accounts.google.com` |
| `scopes_supported` | ✅ | Comma-separated OAuth scopes | `mcp` or `openid,profile,email` |
| `mcp_server_url` | ✅ | Upstream MCP server URL to proxy | `https://ifttt.com/mcp` |
| `encryption_key` | ✅ | Base64 32-byte AES encryption key | Generated with PowerShell / OpenSSL |

---

## 🔑 Generating the Encryption Key

The proxy requires a 32-byte (256-bit) AES key for local token encryption. Generate one using:

### In PowerShell:
```powershell
& "D:\AntigravityServer\Generate-OAuth-Credentials.ps1"
```

### In Bash / OpenSSL:
```bash
openssl rand -base64 32
```

---

## 🌐 Common Provider Base URLs & Redirect URIs

When registering apps with upstream providers, set the **Redirect / Callback URI** to:
`http://<YOUR_HA_IP_OR_HOSTNAME>:8098/callback` (or `http://127.0.0.1:8098/callback`)

| Provider | `oauth_authorize_url` | Scope |
| :--- | :--- | :--- |
| **IFTTT** | `https://ifttt.com` | `mcp` |
| **Google** | `https://accounts.google.com` | `openid,profile,email` |
| **GitHub** | `https://github.com/login/oauth/authorize` | `repo,read:user` |
| **Microsoft** | `https://login.microsoftonline.com/common/oauth2/v2.0/authorize` | `User.Read` |

---

## 📚 Upstream Documentation
For advanced details, database storage options, and API routes, refer directly to the [official obot-platform/mcp-oauth-proxy repository](https://github.com/obot-platform/mcp-oauth-proxy).
