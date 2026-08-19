import os
import json
import logging
import time
import asyncio
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from urllib.parse import urlparse
import uuid

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mcp_oauth_proxy")

app = FastAPI(title="MCP OAuth Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TOKEN_FILE = "/data/tokens.json"

def load_token_cache() -> dict:
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {TOKEN_FILE}: {e}")
    return {}

def save_token_cache():
    try:
        with open(TOKEN_FILE, "w") as f:
            json.dump(TOKEN_CACHE, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving {TOKEN_FILE}: {e}")

TOKEN_CACHE = load_token_cache()
UPSTREAM_SESSIONS: dict[str, dict] = {}

def build_effective_server_url(server: dict) -> str:
    """
    Constructs the target server URL either from modular fields
    (server_scheme, server_host, server_port, server_path) or from server_url.
    Guarantees clean formatting and slash normalization.
    """
    if not server:
        return ""
    
    server_host = (server.get("server_host") or "").strip()
    if server_host:
        scheme = (server.get("server_scheme") or "http").strip().lower()
        if "://" in scheme:
            scheme = scheme.split("://", 1)[0]

        # If user accidentally included scheme in server_host, extract and clean it
        if "://" in server_host:
            extracted_scheme, server_host = server_host.split("://", 1)
            if not server.get("server_scheme"):
                scheme = extracted_scheme.lower()

        # Extract port if present in host string
        port = server.get("server_port")
        if "/" in server_host:
            server_host = server_host.split("/", 1)[0]
        if ":" in server_host:
            host_part, port_part = server_host.split(":", 1)
            server_host = host_part
            if not port:
                try:
                    port = int(port_part)
                except ValueError:
                    pass

        path = (server.get("server_path") or "").strip()
        if path and not path.startswith("/"):
            path = "/" + path
        path = path.rstrip("/")

        port_str = f":{port}" if port else ""
        return f"{scheme}://{server_host}{port_str}{path}"

    return (server.get("server_url") or "").strip()

def load_config():
    options_file = "/data/options.json"
    if os.path.exists(options_file):
        try:
            with open(options_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {options_file}: {e}")
    return {}

def get_server_display_name(server: dict) -> str:
    """Returns a clean, human-readable label for logging and identification (e.g. 'Google Spark > n8n')."""
    if not server:
        return "Unknown"
    c_name = (server.get("client_name") or "").strip()
    s_name = (server.get("server_name") or "").strip()
    if c_name and s_name:
        return f"{c_name} > {s_name}"
    if s_name:
        return s_name
    if c_name:
        return c_name
    if server.get("client_id"):
        return server["client_id"].strip()
    return server.get("host") or build_effective_server_url(server) or "Server"

def clean_host(raw_host: str) -> str:
    """Strips scheme, port numbers, and slashes from a hostname for robust comparison."""
    if not raw_host:
        return ""
    host = raw_host.strip().lower()
    if "://" in host:
        host = host.split("://", 1)[1]
    if "/" in host:
        host = host.split("/", 1)[0]
    if ":" in host:
        host = host.split(":", 1)[0]
    return host

def get_server_for_request(request: Request, client_id: str = None, path: str = None) -> tuple[dict | None, str]:
    """
    Multi-factor server resolver:
    1. Host header match (e.g. host: 'n8n-oauth.connormoseley.com')
    2. Path prefix match (e.g. path_prefix: '/n8n')
    3. Client ID match from Authorization Bearer token or parameter
    4. Fallback to single server if only 1 configured
    Returns: (server_config, matched_path_prefix)
    """
    cfg = load_config()
    servers = cfg.get("servers", [])
    if not servers:
        return None, ""

    # Priority 1: Match by Host header (Cloudflare Tunnel / NPM / reverse proxy)
    raw_incoming_host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    incoming_host = clean_host(raw_incoming_host)
    if incoming_host:
        for s in servers:
            configured_host = clean_host(s.get("host", ""))
            if configured_host and configured_host == incoming_host:
                logger.info(f"[{get_server_display_name(s)}] Resolved server via Host '{incoming_host}' -> {build_effective_server_url(s)}")
                return s, ""

    # Priority 2: Match by Path Prefix
    if path:
        req_path = "/" + path.strip("/")
        # Sort configured prefixes by length descending so longer/more specific prefixes match first
        prefix_servers = [s for s in servers if s.get("path_prefix", "").strip()]
        prefix_servers.sort(key=lambda s: len(s.get("path_prefix", "").strip()), reverse=True)
        for s in prefix_servers:
            pfx = "/" + s.get("path_prefix", "").strip("/").lower()
            if req_path.lower() == pfx or req_path.lower().startswith(pfx + "/"):
                logger.info(f"[{get_server_display_name(s)}] Resolved server via Path Prefix '{pfx}' -> {build_effective_server_url(s)}")
                return s, pfx

    # Priority 3: Match by Client ID
    if client_id:
        for s in servers:
            if s.get("client_id") == client_id:
                logger.info(f"[{get_server_display_name(s)}] Resolved server via Client ID '{client_id}' -> {build_effective_server_url(s)}")
                return s, ""

    # Priority 4: Single server fallback
    if len(servers) == 1:
        logger.info(f"[{get_server_display_name(servers[0])}] Single server fallback -> {build_effective_server_url(servers[0])}")
        return servers[0], ""

    return None, ""

def get_server_by_client_id(client_id: str) -> dict | None:
    cfg = load_config()
    servers = cfg.get("servers", [])
    for s in servers:
        if s.get("client_id") == client_id:
            return s
    return None

async def get_or_refresh_upstream_token(server: dict, force_refresh: bool = False) -> str:
    """Returns a valid upstream bearer token, automatically refreshing if refresh_token is configured."""
    client_id = server.get("client_id", "")
    bearer_token = server.get("bearer_token", "")
    refresh_token = server.get("server_refresh_token", "")
    token_url = server.get("server_token_url", "")
    up_client_id = server.get("server_client_id", "")
    up_client_secret = server.get("server_client_secret", "")
    display_name = get_server_display_name(server)

    # If no OAuth refresh config, return bearer_token directly
    if not (refresh_token and token_url and up_client_id and up_client_secret):
        return bearer_token

    cached = TOKEN_CACHE.get(client_id, {})
    current_token = cached.get("access_token")
    expires_at = cached.get("expires_at", 0)
    cur_refresh = cached.get("refresh_token") or refresh_token

    # Use cached token if valid and not forcing refresh
    if current_token and time.time() < (expires_at - 60) and not force_refresh:
        return current_token

    # Refresh the token with upstream provider (e.g. IFTTT)
    logger.info(f"[{display_name}] Refreshing server OAuth token at {token_url}...")
    try:
        async with httpx.AsyncClient() as c:
            body = {
                "grant_type": "refresh_token",
                "refresh_token": cur_refresh,
                "client_id": up_client_id,
                "client_secret": up_client_secret,
            }
            res = await c.post(token_url, data=body, timeout=15.0)
            if res.status_code == 200:
                data = res.json()
                new_access = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                new_refresh = data.get("refresh_token", cur_refresh)
                TOKEN_CACHE[client_id] = {
                    "access_token": new_access,
                    "expires_at": time.time() + float(expires_in),
                    "refresh_token": new_refresh,
                }
                save_token_cache()
                logger.info(f"[{display_name}] Successfully refreshed server OAuth token (valid for {expires_in}s)")
                return new_access
            else:
                logger.error(f"[{display_name}] Failed to refresh server OAuth token: {res.status_code} - {res.text}")
                return current_token or bearer_token
    except Exception as e:
        logger.error(f"[{display_name}] Exception during server OAuth token refresh: {e}")
        return current_token or bearer_token

@app.get("/login")
@app.get("/link")
def login(request: Request, client_id: str = None):
    server, _ = get_server_for_request(request, client_id=client_id)
    if not server and client_id:
        server = get_server_by_client_id(client_id)
    if not server:
        raise HTTPException(status_code=400, detail="No matching server configuration found for login")
    
    auth_url = server.get("server_authorize_url") or "https://ifttt.com/oauth/authorize"
    up_client_id = server.get("server_client_id")
    if not up_client_id:
        raise HTTPException(status_code=400, detail="server_client_id is not configured for this server")
    
    proto = request.headers.get("x-forwarded-proto", "https")
    raw_host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    base = f"{proto}://{raw_host}".rstrip("/") if raw_host else str(request.base_url).rstrip("/")
    callback_uri = f"{base}/callback"
    
    target = f"{auth_url}?client_id={up_client_id}&redirect_uri={callback_uri}&response_type=code&scope=mcp"
    logger.info(f"[{get_server_display_name(server)}] Redirecting user to upstream OAuth: {target}")
    return Response(status_code=status.HTTP_302_FOUND, headers={"Location": target})

@app.get("/callback")
async def oauth_callback(request: Request, code: str = None, error: str = None, state: str = None):
    if error:
        return HTMLResponse(f"<h3 style='color:red;'>OAuth Error: {error}</h3>", status_code=400)
    if not code:
        return HTMLResponse("<h3 style='color:red;'>Missing authorization code</h3>", status_code=400)
    
    server, _ = get_server_for_request(request)
    if not server:
        cfg = load_config()
        servers = cfg.get("servers", [])
        for s in servers:
            if s.get("server_client_id"):
                server = s
                break
    
    if not server:
        return HTMLResponse("<h3 style='color:red;'>Error: No server configured with upstream OAuth credentials</h3>", status_code=400)
    
    display_name = get_server_display_name(server)
    token_url = server.get("server_token_url") or "https://ifttt.com/oauth/token"
    up_client_id = server.get("server_client_id")
    up_client_secret = server.get("server_client_secret")
    c_id = server.get("client_id", "default")
    
    proto = request.headers.get("x-forwarded-proto", "https")
    raw_host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    base = f"{proto}://{raw_host}".rstrip("/") if raw_host else str(request.base_url).rstrip("/")
    callback_uri = f"{base}/callback"
    
    logger.info(f"[{display_name}] Exchanging authorization code at {token_url}...")
    try:
        async with httpx.AsyncClient() as c:
            body = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": callback_uri,
                "client_id": up_client_id,
                "client_secret": up_client_secret,
            }
            res = await c.post(token_url, data=body, timeout=15.0)
            if res.status_code == 200:
                data = res.json()
                new_access = data.get("access_token")
                new_refresh = data.get("refresh_token")
                expires_in = data.get("expires_in", 3600)
                
                TOKEN_CACHE[c_id] = {
                    "access_token": new_access,
                    "expires_at": time.time() + float(expires_in),
                    "refresh_token": new_refresh,
                }
                save_token_cache()
                logger.info(f"[{display_name}] Successfully captured OAuth tokens! refresh_token='{new_refresh}'")
                
                server_name = server.get("server_name") or "Upstream Server"
                return HTMLResponse(
                    f"<html><body style='font-family:sans-serif;text-align:center;padding:40px;background:#1e1e2e;color:#cdd6f4;'>"
                    f"<h1 style='color:#a6e3a1;'>🎉 Successfully Connected to {server_name}!</h1>"
                    f"<p>Authentication tokens have been captured and saved permanently.</p>"
                    f"<p style='color:#89b4fa;'>Google Spark / your MCP client can now access {server_name} directly.</p>"
                    f"<p style='margin-top:20px;font-size:13px;color:#a6adc8;'>You may close this browser window.</p>"
                    f"</body></html>"
                )
            else:
                logger.error(f"[{display_name}] Failed to exchange code for token: {res.status_code} - {res.text}")
                return HTMLResponse(f"<h3 style='color:red;'>Token Exchange Failed ({res.status_code}): {res.text}</h3>", status_code=400)
    except Exception as e:
        logger.error(f"[{display_name}] Exception exchanging code: {e}")
        return HTMLResponse(f"<h3 style='color:red;'>Error during token exchange: {str(e)}</h3>", status_code=500)

@app.get("/.well-known/oauth-authorization-server")
@app.get("/.well-known/oauth-protected-resource")
@app.get("/.well-known/oauth-protected-resource/{rest_of_path:path}")
@app.get("/.well-known/openid-configuration")
def oauth_metadata(request: Request, rest_of_path: str = None):
    proto = request.headers.get("x-forwarded-proto", "https")
    raw_host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    if raw_host:
        base = f"{proto}://{raw_host}".rstrip("/")
    else:
        base = str(request.base_url).rstrip("/")
        if base.startswith("http://") and "localhost" not in base and "172." not in base:
            base = base.replace("http://", "https://")

    resource_uri = f"{base}/{rest_of_path.lstrip('/')}" if rest_of_path else base
    logger.info(f"Serving OAuth metadata for base: {base}, resource: {resource_uri}")
    return {
        "resource": resource_uri,
        "authorization_servers": [base],
        "issuer": base,
        "authorization_endpoint": f"{base}/authorize",
        "token_endpoint": f"{base}/token",
        "registration_endpoint": f"{base}/register",
        "revocation_endpoint": f"{base}/revoke",
        "introspection_endpoint": f"{base}/introspect",
        "userinfo_endpoint": f"{base}/userinfo",
        "jwks_uri": f"{base}/jwks.json",
        "scopes_supported": ["mcp", "read", "write", "offline_access"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic", "none"],
        "code_challenge_methods_supported": ["S256", "plain"]
    }

@app.get("/.well-known/jwks.json")
@app.get("/jwks.json")
def jwks(request: Request):
    return JSONResponse(
        content={"keys": []},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.get("/authorize")
@app.get("/oauth/authorize")
async def authorize(
    request: Request,
    redirect_uri: str = None,
    state: str = "",
    client_id: str = None,
    response_type: str = "code",
    scope: str = "",
    code_challenge: str = None,
    code_challenge_method: str = None,
    prompt: str = None
):
    params = dict(request.query_params)
    redirect_uri = redirect_uri or params.get("redirect_uri", "")
    state = state or params.get("state", "")
    client_id = client_id or params.get("client_id")
    
    logger.info(f"GET /authorize requested with params: {params}")
    server, _ = get_server_for_request(request, client_id=client_id)
    if not server and client_id:
        server = get_server_by_client_id(client_id)
    
    if not server:
        cfg = load_config()
        servers = cfg.get("servers", [])
        if len(servers) == 1:
            server = servers[0]
        else:
            logger.warning(f"Rejecting authorize: Unknown client_id '{client_id}' and no matching host")
            raise HTTPException(status_code=400, detail=f"Invalid client_id: {client_id}")

    display_name = get_server_display_name(server)
    allowed_raw = server.get("allowed_redirect_uris", "")
    if isinstance(allowed_raw, str):
        allowed = [u.strip() for u in allowed_raw.split(",") if u.strip()]
    else:
        allowed = allowed_raw or []
        
    if allowed and redirect_uri and not any(redirect_uri.startswith(uri) for uri in allowed):
        logger.warning(f"[{display_name}] Forbidden redirect_uri '{redirect_uri}'. Allowed: {allowed}")
        if not ("googleusercontent.com" in redirect_uri or "localhost" in redirect_uri):
            raise HTTPException(status_code=403, detail=f"Forbidden redirect_uri: {redirect_uri}")
    
    resolved_client = server.get("client_id") or client_id or "default"
    redirect_target = f"{redirect_uri}{'&' if '?' in redirect_uri else '?'}code={resolved_client}&state={state}"
    logger.info(f"[{display_name}] Redirecting user to: {redirect_target}")
    return Response(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": redirect_target}
    )

@app.post("/token")
@app.post("/oauth/token")
async def token(request: Request):
    code = ""
    grant_type = ""
    refresh_tok = ""
    c_id = ""
    
    # Check Authorization: Basic header (client_secret_basic)
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Basic "):
        try:
            import base64
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
            if ":" in decoded:
                c_id = decoded.split(":", 1)[0]
        except Exception:
            pass

    params = dict(request.query_params)
    code = params.get("code", "")
    grant_type = params.get("grant_type", "")
    refresh_tok = params.get("refresh_token", "")
    c_id = params.get("client_id") or c_id
    
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            code = body.get("code") or code
            grant_type = body.get("grant_type") or grant_type
            refresh_tok = body.get("refresh_token") or refresh_tok
            c_id = body.get("client_id") or c_id
        except Exception:
            pass
    else:
        try:
            form = await request.form()
            code = form.get("code") or code
            grant_type = form.get("grant_type") or grant_type
            refresh_tok = form.get("refresh_token") or refresh_tok
            c_id = form.get("client_id") or c_id
        except Exception:
            pass

    logger.info(f"POST /token with grant_type='{grant_type}', code='{code}', refresh_tok='{refresh_tok}', client_id='{c_id}'")
    server, _ = get_server_for_request(request, client_id=c_id or code or refresh_tok)
    client_id = (server.get("client_id") if server else None) or c_id or code or refresh_tok or "default"
    
    resp_data = {
        "access_token": client_id,
        "token_type": "Bearer",
        "expires_in": 86400,
        "refresh_token": client_id
    }
    logger.info(f"POST /token response: {resp_data}")
    return JSONResponse(
        content=resp_data,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.post("/revoke")
@app.post("/oauth/revoke")
async def revoke_token(request: Request):
    return JSONResponse(
        content={"status": "revoked"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.post("/introspect")
@app.post("/oauth/introspect")
async def introspect_token(request: Request):
    token_val = ""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            token_val = body.get("token", "")
        except Exception:
            pass
    else:
        try:
            form = await request.form()
            token_val = form.get("token", "")
        except Exception:
            pass
    server, _ = get_server_for_request(request, client_id=token_val)
    client_id = (server.get("client_id") if server else None) or token_val or "default"
    return JSONResponse(
        content={"active": True, "client_id": client_id, "scope": "mcp", "token_type": "Bearer"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.get("/userinfo")
@app.get("/oauth/userinfo")
@app.post("/userinfo")
@app.post("/oauth/userinfo")
async def userinfo(request: Request):
    auth = request.headers.get("authorization", "")
    sub = auth.replace("Bearer ", "").strip() if auth else "mcp_user"
    return JSONResponse(
        content={"sub": sub, "name": "MCP User", "preferred_username": "mcp_user"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.post("/register", status_code=status.HTTP_201_CREATED)
@app.post("/oauth/register", status_code=status.HTTP_201_CREATED)
async def register_client(request: Request):
    data = await request.json()
    redirect_uris = data.get("redirect_uris", [])
    client_id = f"dyn_{uuid.uuid4().hex[:12]}"
    client_secret = f"secret_{uuid.uuid4().hex[:24]}"
    logger.info(f"POST /register generated client_id='{client_id}' for uris={redirect_uris}")
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_name": data.get("client_name", "MCP Client"),
        "redirect_uris": redirect_uris,
        "grant_types": ["authorization_code"],
        "response_types": ["code"]
    }

@app.api_route("/{path:path}", methods=["GET", "POST", "HEAD", "OPTIONS", "PUT", "DELETE"])
async def proxy_mcp_catchall(path: str, request: Request):
    excluded_paths = [
        "authorize", "token", "register", "login", "link", "callback",
        "revoke", "introspect", "userinfo", "jwks.json",
        "oauth/authorize", "oauth/token", "oauth/register", "oauth/revoke", "oauth/introspect", "oauth/userinfo"
    ]
    if path in excluded_paths or path.startswith(".well-known"):
        raise HTTPException(status_code=404, detail="OAuth endpoint match error")

    auth_header = request.headers.get("authorization", "")
    token_str = ""
    if auth_header.startswith("Bearer "):
        token_str = auth_header[7:].strip()
    elif auth_header:
        token_str = auth_header.strip()

    client_id = token_str.replace("token_", "").strip() if token_str.startswith("token_") else token_str

    server, matched_prefix = get_server_for_request(request, client_id=client_id, path=path)
    if not server:
        logger.warning(f"Unauthorized proxy attempt: No matching server configuration for path='/{path}', token='{token_str}'")
        raise HTTPException(status_code=401, detail="Unauthorized: No matching MCP server configuration or valid token")

    display_name = get_server_display_name(server)
    effective_url = build_effective_server_url(server)
    
    # Calculate subpath to append cleanly
    clean_req_path = "/" + path.strip("/")
    if matched_prefix:
        subpath = clean_req_path[len(matched_prefix):].lstrip("/")
    else:
        parsed_eff = urlparse(effective_url)
        eff_path = parsed_eff.path.rstrip("/")
        # If effective_url already ends with the requested path, avoid doubling
        if eff_path and (clean_req_path == eff_path or clean_req_path == "/sse"):
            subpath = ""
        else:
            subpath = clean_req_path.lstrip("/")

    if subpath:
        target_url = effective_url.rstrip("/") + "/" + subpath
    else:
        target_url = effective_url

    # Preserve query string parameters (?foo=bar)
    if request.url.query:
        target_url += ("&" if "?" in target_url else "?") + str(request.url.query)

    logger.info(f"[{display_name}] Proxying {request.method} /{path} -> {target_url}")

    # Handle preflight OPTIONS requests immediately
    if request.method == "OPTIONS":
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD, PUT, DELETE",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Expose-Headers": "*",
                "Access-Control-Max-Age": "86400"
            }
        )

    # Handle HEAD requests immediately for MCP probing
    if request.method == "HEAD":
        return Response(
            status_code=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD, PUT, DELETE",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Expose-Headers": "*"
            }
        )

    # Downstream OAuth enforcement (facing Spark):
    # Every server with client_id configured requires Spark to authenticate via OAuth.
    # If no token is provided by Spark, challenge with 401 WWW-Authenticate.
    server_client_id = server.get("client_id", "").strip()
    is_authenticated = bool(token_str) or not bool(server_client_id)

    if not is_authenticated and request.method not in ["HEAD", "OPTIONS"]:
        proto = request.headers.get("x-forwarded-proto", "https")
        raw_host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        base = f"{proto}://{raw_host}".rstrip("/") if raw_host else str(request.base_url).rstrip("/")
        auth_uri = f"{base}/authorize"
        token_uri = f"{base}/token"
        logger.info(f"[{display_name}] Unauthenticated {request.method} /{path}. Responding with 401 WWW-Authenticate.")
        return Response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=json.dumps({"error": "unauthorized", "message": "Authentication required"}),
            media_type="application/json",
            headers={
                "WWW-Authenticate": f'Bearer realm="{base}", authorization_uri="{auth_uri}", token_uri="{token_uri}", as_uri="{base}", error="invalid_token", error_description="Authentication required"',
                "Link": f'<{base}/.well-known/oauth-protected-resource>; rel="oauth-protected-resource", <{base}/.well-known/oauth-authorization-server>; rel="oauth-authorization-server"',
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD, PUT, DELETE",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Expose-Headers": "*"
            }
        )

    token = await get_or_refresh_upstream_token(server)
    headers = dict(request.headers)
    if token:
        headers["authorization"] = token if token.startswith("Bearer ") else f"Bearer {token}"
    else:
        headers.pop("authorization", None)

    headers.pop("host", None)
    headers["x-forwarded-host"] = request.headers.get("host", "")
    headers["x-forwarded-proto"] = request.headers.get("x-forwarded-proto", "https")
    headers.pop("accept-encoding", None)
    headers.pop("content-encoding", None)
    headers.pop("connection", None) 

    body = await request.body()

    client = httpx.AsyncClient(follow_redirects=True)
    try:
        req = client.build_request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            timeout=86400.0
        )
        resp = await client.send(req, stream=True)

        # If client requested GET /sse (or Accept: text/event-stream) and upstream is a Stateless HTTP
        # server that rejects GET with 405 (like github-mcp-server), bridge an SSE keep-alive stream.
        if request.method == "GET" and resp.status_code == 405:
            logger.info(f"[{display_name}] Upstream returned 405 on GET /{path}. Bridging persistent SSE stream for client.")
            await resp.aclose()
            await client.aclose()

            async def sse_bridge_stream():
                clean_path = "/" + path.strip("/")
                yield f"event: endpoint\r\ndata: {clean_path}\r\n\r\n".encode("utf-8")
                try:
                    while True:
                        await asyncio.sleep(15)
                        yield b": keepalive\r\n\r\n"
                except (asyncio.CancelledError, GeneratorExit):
                    pass

            return StreamingResponse(
                sse_bridge_stream(),
                status_code=200,
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD",
                    "Access-Control-Allow-Headers": "*"
                }
            )

        # If client posted JSON-RPC directly to an SSE-only upstream (which returned 405 on POST),
        # bridge the Stateless HTTP POST into the persistent upstream SSE session.
        if request.method == "POST" and resp.status_code == 405 and "/sse" in target_url:
            await resp.aclose()

            session_key = f"{client_id or 'default'}:{target_url}"
            session = UPSTREAM_SESSIONS.get(session_key)

            if session and session.get("sse_resp") and session["sse_resp"].is_closed:
                session = None
                UPSTREAM_SESSIONS.pop(session_key, None)

            if not session:
                logger.info(f"[{display_name}] Opening new persistent upstream SSE session for {session_key}...")
                sse_headers = dict(headers)
                sse_headers.pop("content-length", None)
                sse_headers.pop("content-type", None)
                sse_headers["accept"] = "text/event-stream"

                sse_client = httpx.AsyncClient(follow_redirects=True)
                sse_req = sse_client.build_request("GET", target_url, headers=sse_headers, timeout=86400.0)
                sse_resp = await sse_client.send(sse_req, stream=True)

                messages_endpoint = None
                parsed_base = f"{urlparse(target_url).scheme}://{urlparse(target_url).netloc}"
                sse_line_iter = sse_resp.aiter_lines()

                try:
                    async for line in sse_line_iter:
                        if line.startswith("data:"):
                            raw_data = line[5:].strip()
                            if "/messages" in raw_data or "session_id" in raw_data:
                                messages_endpoint = raw_data
                                break
                except Exception as e:
                    logger.error(f"[{display_name}] Error discovering SSE messages endpoint: {e}")

                if messages_endpoint:
                    post_url = parsed_base + messages_endpoint if messages_endpoint.startswith("/") else messages_endpoint
                    session = {
                        "post_url": post_url,
                        "sse_resp": sse_resp,
                        "sse_client": sse_client,
                        "parsed_base": parsed_base,
                        "pending_requests": {},
                        "line_iter": sse_line_iter
                    }

                    # Dedicated background reader task for this SSE session
                    async def background_sse_reader(sess, dname, key):
                        try:
                            async for sline in sess["line_iter"]:
                                if sline.startswith("data:"):
                                    dstr = sline[5:].strip()
                                    if dstr:
                                        try:
                                            parsed_msg = json.loads(dstr)
                                            if isinstance(parsed_msg, dict) and "id" in parsed_msg and parsed_msg["id"] is not None:
                                                rid = str(parsed_msg["id"])
                                                fut = sess["pending_requests"].pop(rid, None)
                                                if fut and not fut.done():
                                                    fut.set_result(dstr)
                                        except Exception:
                                            # If not JSON, but has waiters, notify first waiter
                                            if sess["pending_requests"]:
                                                _, first_fut = sess["pending_requests"].popitem()
                                                if not first_fut.done():
                                                    first_fut.set_result(dstr)
                        except Exception as reader_err:
                            logger.error(f"[{dname}] SSE background reader error: {reader_err}")
                        finally:
                            UPSTREAM_SESSIONS.pop(key, None)

                    session["reader_task"] = asyncio.create_task(background_sse_reader(session, display_name, session_key))
                    UPSTREAM_SESSIONS[session_key] = session
                else:
                    await sse_resp.aclose()
                    await sse_client.aclose()

            if session:
                post_url = session["post_url"]
                logger.info(f"[{display_name}] Forwarding JSON-RPC message to persistent session at: {post_url}")
                
                # Check if this JSON-RPC payload expects a response (has an "id")
                req_id = None
                is_notification = False
                try:
                    parsed_body = json.loads(body.decode("utf-8"))
                    if isinstance(parsed_body, dict):
                        if "id" in parsed_body and parsed_body["id"] is not None:
                            req_id = str(parsed_body["id"])
                        else:
                            is_notification = True
                except Exception:
                    pass

                fut = None
                loop = asyncio.get_running_loop()
                if req_id is not None:
                    fut = loop.create_future()
                    session["pending_requests"][req_id] = fut

                post_headers = dict(headers)
                post_headers["content-type"] = "application/json"
                post_headers.pop("content-length", None)
                post_req = client.build_request("POST", post_url, headers=post_headers, content=body, timeout=30.0)
                post_res = await client.send(post_req)

                if post_res.status_code == 404:
                    logger.warning(f"[{display_name}] Upstream returned 404 for session URL {post_url}. Invalidating stale session.")
                    UPSTREAM_SESSIONS.pop(session_key, None)
                    if session.get("reader_task"):
                        session["reader_task"].cancel()
                    if session.get("sse_resp"):
                        await session["sse_resp"].aclose()
                    if session.get("sse_client"):
                        await session["sse_client"].aclose()

                cors_headers = {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS, HEAD",
                    "Access-Control-Allow-Headers": "*"
                }

                # If this was a notification (no "id" field), return immediately
                if is_notification:
                    return Response(content=json.dumps({"jsonrpc": "2.0", "result": {}}), media_type="application/json", status_code=200, headers=cors_headers)

                response_json = None
                if fut:
                    try:
                        response_json = await asyncio.wait_for(fut, timeout=30.0)
                    except asyncio.TimeoutError:
                        logger.warning(f"[{display_name}] Timed out waiting for JSON-RPC response for id='{req_id}'")
                        session["pending_requests"].pop(req_id, None)

                if response_json:
                    return Response(content=response_json, media_type="application/json", status_code=200, headers=cors_headers)
                elif post_res.text:
                    return Response(content=post_res.text, media_type="application/json", status_code=post_res.status_code, headers=cors_headers)
                else:
                    return Response(content=json.dumps({"jsonrpc": "2.0", "result": {}}), media_type="application/json", status_code=200, headers=cors_headers)
            else:
                await sse_resp.aclose()

        # If upstream returns 401 and server_refresh_token is configured, refresh and retry once
        if resp.status_code == 401 and server.get("server_refresh_token"):
            logger.warning(f"[{display_name}] Received 401 from upstream {target_url}. Attempting auto-refresh...")
            await resp.aclose()
            new_token = await get_or_refresh_upstream_token(server, force_refresh=True)
            if new_token:
                headers["authorization"] = new_token if new_token.startswith("Bearer ") else f"Bearer {new_token}"
                req = client.build_request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    content=body,
                    timeout=86400.0
                )
                resp = await client.send(req, stream=True)

    except httpx.ConnectError as e:
        logger.error(f"[{display_name}] Cannot connect to upstream {target_url}: {e}")
        await client.aclose()
        return JSONResponse(status_code=502, content={"error": f"Bad Gateway: Cannot connect to upstream {target_url}"})
    except Exception as e:
        logger.error(f"[{display_name}] Upstream error forwarding to {target_url}: {e}")
        await client.aclose()
        return JSONResponse(status_code=500, content={"error": f"Upstream error: {str(e)}"})

    resp_headers = dict(resp.headers)
    resp_headers.pop("content-encoding", None)
    resp_headers.pop("transfer-encoding", None)
    resp_headers.pop("content-length", None)

    resp_headers["access-control-allow-origin"] = "*"
    resp_headers["access-control-allow-methods"] = "GET, POST, OPTIONS, HEAD, PUT, DELETE"
    resp_headers["access-control-allow-headers"] = "*"
    resp_headers["access-control-expose-headers"] = "*"
    resp_headers["x-accel-buffering"] = "no"

    is_sse = "text/event-stream" in resp_headers.get("content-type", "").lower()

    if not is_sse:
        content = await resp.aread()
        await resp.aclose()
        await client.aclose()
        return Response(
            content=content,
            status_code=resp.status_code,
            headers=resp_headers
        )

    async def stream_wrapper():
        try:
            iter_chunks = resp.aiter_bytes().__aiter__()
            while True:
                try:
                    chunk = await asyncio.wait_for(iter_chunks.__anext__(), timeout=15.0)
                    yield chunk
                except asyncio.TimeoutError:
                    yield b": keepalive\r\n\r\n"
                except StopAsyncIteration:
                    break
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(
        stream_wrapper(),
        status_code=resp.status_code,
        headers=resp_headers
    )