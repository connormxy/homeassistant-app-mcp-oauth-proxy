import os
import json
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import StreamingResponse
import httpx
from urllib.parse import urlparse
import uuid

app = FastAPI(title="MCP OAuth Proxy")

def load_config():
    defaults = {
        "upstream_url": os.getenv("UPSTREAM_URL", "http://6560bdea-hass-n8n:5678/mcp-server/http"),
        "n8n_token": os.getenv("N8N_TOKEN", ""),
        "client_id": os.getenv("CLIENT_ID", "spark-client-id"),
        "client_secret": os.getenv("CLIENT_SECRET", "spark-client-secret"),
        "allowed_redirect_uris": [
            "https://spark.google.com/oauth/callback",
            "https://oauth.googleusercontent.com"
        ]
    }
    options_file = "/data/options.json"
    if os.path.exists(options_file):
        try:
            with open(options_file, "r") as f:
                user_opts = json.load(f)
                for k, v in user_opts.items():
                    if v is not None and v != "":
                        if k == "allowed_redirect_uris" and isinstance(v, str):
                            # Support comma-separated strings from the UI
                            defaults[k] = [u.strip() for u in v.split(",") if u.strip()]
                        else:
                            defaults[k] = v
        except Exception:
            pass
    return defaults

@app.get("/.well-known/oauth-authorization-server")
@app.get("/.well-known/oauth-protected-resource")
@app.get("/.well-known/oauth-protected-resource/{rest_of_path:path}")
def oauth_metadata(request: Request, rest_of_path: str = None):
    base = str(request.base_url).rstrip("/")
    if base.startswith("http://") and "localhost" not in base and "172." not in base:
        base = base.replace("http://", "https://")
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}/authorize",
        "token_endpoint": f"{base}/token",
        "registration_endpoint": f"{base}/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"]
    }

@app.get("/authorize")
def authorize(redirect_uri: str, state: str, client_id: str = None):
    cfg = load_config()
    allowed = cfg["allowed_redirect_uris"]
    # If allowed is configured, check it. If empty list, allow all.
    if allowed and not any(redirect_uri.startswith(uri) for uri in allowed):
        # Log or accept dynamically if needed, but now you can add it to the UI!
        raise HTTPException(status_code=403, detail=f"Forbidden redirect_uri: {redirect_uri}")
    return Response(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": f"{redirect_uri}?code=spark_auth_code&state={state}"}
    )

@app.post("/token")
def token():
    return {
        "access_token": "spark_mcp_access_token",
        "token_type": "Bearer",
        "expires_in": 3600
    }

@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register_client(request: Request):
    data = await request.json()
    redirect_uris = data.get("redirect_uris", [])
    client_id = f"dyn_{uuid.uuid4().hex[:12]}"
    client_secret = f"secret_{uuid.uuid4().hex[:24]}"
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
    if path in ["authorize", "token", "register"] or path.startswith(".well-known"):
        raise HTTPException(status_code=404, detail="OAuth endpoint match error")

    cfg = load_config()
    upstream_url = cfg["upstream_url"]
    token_val = cfg["n8n_token"]
    
    auth_header = token_val if token_val.startswith("Bearer ") else f"Bearer {token_val}"

    headers = dict(request.headers)
    headers["authorization"] = auth_header
    headers.pop("host", None)
    headers["x-forwarded-host"] = request.headers.get("host", "")
    headers["x-forwarded-proto"] = request.headers.get("x-forwarded-proto", "https")
    headers.pop("accept-encoding", None)
    headers.pop("content-encoding", None)
    headers.pop("connection", None) 

    body = await request.body()
    
    client = httpx.AsyncClient()
    req = client.build_request(
        method=request.method,
        url=upstream_url,
        headers=headers,
        content=body,
        timeout=86400.0
    )
    
    resp = await client.send(req, stream=True)
    
    resp_headers = dict(resp.headers)
    resp_headers.pop("content-encoding", None)
    resp_headers.pop("transfer-encoding", None)
    resp_headers.pop("content-length", None)
    
    resp_headers["x-accel-buffering"] = "no"
    resp_headers["cache-control"] = "no-cache"
    resp_headers["connection"] = "keep-alive"

    async def stream_wrapper():
        try:
            async for chunk in resp.aiter_bytes():
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(
        stream_wrapper(),
        status_code=resp.status_code,
        headers=resp_headers
    )
