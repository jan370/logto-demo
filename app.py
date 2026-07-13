import os
import urllib.parse

import requests
from flask import Flask, jsonify, redirect, request


LOGTO_ISSUER = os.environ["LOGTO_ISSUER"].rstrip("/")
CLIENT_ID = os.environ["LOGTO_CLIENT_ID"]
CLIENT_SECRET = os.environ["LOGTO_CLIENT_SECRET"]

DISCOVERY_URL = f"{LOGTO_ISSUER}/.well-known/openid-configuration"
TOKEN_URL = f"{LOGTO_ISSUER}/token"

app = Flask(__name__)


def load_oidc_metadata():
    try:
        response = requests.get(DISCOVERY_URL, timeout=15)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return {}


def parse_response(response):
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text}


def post_token_action(endpoint_name, fallback_path, token):
    metadata = load_oidc_metadata()
    endpoint = metadata.get(endpoint_name) or f"{LOGTO_ISSUER}{fallback_path}"
    response = requests.post(
        endpoint,
        data={"token": token, "token_type_hint": "access_token"},
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=15,
    )
    return response, endpoint


HTML = """<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Logto OIDC Flow Demo</title>
  <style>
    :root {
      --bg: #f4f7fb;
      --card: #ffffff;
      --ink: #182437;
      --muted: #52627a;
      --accent: #0b6bcb;
      --accent-2: #0f8b8d;
      --border: #d8e2ef;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: "Segoe UI", "Trebuchet MS", sans-serif;
      background:
        radial-gradient(circle at 10% -20%, #dff0ff 0%, transparent 55%),
        radial-gradient(circle at 95% 0%, #dff7f4 0%, transparent 45%),
        var(--bg);
    }
    .wrap { max-width: 980px; margin: 0 auto; padding: 24px; }
    .hero {
      color: #fff;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      border-radius: 16px;
      padding: 20px;
      box-shadow: 0 14px 28px rgba(15, 30, 58, 0.16);
    }
    .hero h1 { margin: 0 0 8px; font-size: 1.5rem; }
    .hero p { margin: 0; opacity: 0.95; }
    .card {
      margin-top: 16px;
      padding: 16px;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      box-shadow: 0 8px 22px rgba(15, 30, 58, 0.08);
    }
    .step-title { margin: 0 0 8px; font-size: 1.05rem; }
    .muted { color: var(--muted); }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
    button {
      padding: 10px 14px;
      color: var(--ink);
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 10px;
      cursor: pointer;
      font-weight: 600;
    }
    button.primary {
      color: #fff;
      background: linear-gradient(180deg, #0b6bcb, #095baa);
      border-color: #09539e;
    }
    button.warn {
      color: #fff;
      background: linear-gradient(180deg, #c72a2a, #a62323);
      border-color: #942020;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
    pre {
      max-height: 260px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      padding: 12px;
      color: #cde3ff;
      background: #0f1724;
      border: 1px solid #22324d;
      border-radius: 10px;
    }
    .pill {
      display: inline-block;
      padding: 4px 10px;
      color: var(--muted);
      background: #f8fbff;
      border: 1px solid var(--border);
      border-radius: 999px;
      font-size: 12px;
    }
    @media (max-width: 700px) {
      .wrap { padding: 14px; }
      .hero h1 { font-size: 1.2rem; }
    }
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <h1>OIDC Schritt-fuer-Schritt Demo</h1>
      <p>1) Authorization Code, 2) Token Exchange, 3) Introspection und <code>sub</code> anzeigen.</p>
    </section>

    <section class="card">
      <span class="pill">Konfiguration</span>
      <p class="muted">Issuer: <code>__ISSUER__</code><br>Client ID: <code>__CLIENT_ID__</code></p>
      <div class="actions">
        <button class="primary" id="login">Login bei Logto starten</button>
        <button class="warn" id="logout">Logout</button>
      </div>
    </section>

    <section class="card">
      <h2 class="step-title">Schritt 1: Authorization Code</h2>
      <p class="muted">Nach dem Login wird der einmalige Code hier angezeigt.</p>
      <pre id="auth-code">(noch kein Code)</pre>
      <div class="actions">
        <button class="primary" id="exchange" disabled>Weiter: Code gegen Token tauschen</button>
      </div>
    </section>

    <section class="card">
      <h2 class="step-title">Schritt 2: Access Token</h2>
      <p class="muted">Der Token Exchange erfolgt serverseitig, damit das Client Secret nicht im Browser liegt.</p>
      <pre id="token-response">(noch kein Token)</pre>
      <div class="actions">
        <button class="primary" id="introspect" disabled>Weiter: Access Token introspektieren</button>
      </div>
    </section>

    <section class="card">
      <h2 class="step-title">Schritt 3: Introspection</h2>
      <p class="muted">Das Ergebnis zeigt <code>active</code>, <code>sub</code> und die Token-Claims.</p>
      <pre id="introspection">(noch keine Introspection)</pre>
    </section>

    <section class="card">
      <h2 class="step-title">Logout-Rueckmeldung</h2>
      <pre id="logout-result">(noch kein Logout ausgefuehrt)</pre>
    </section>
  </main>

  <script>
    const ISSUER = "__ISSUER__";
    const CLIENT_ID = "__CLIENT_ID__";
    const REDIRECT_URI = `${window.location.origin}/callback`;
    const state = { authorizationCode: null, accessToken: null, idToken: null };

    const byId = (id) => document.getElementById(id);
    const show = (id, value) => {
      byId(id).textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    };

    async function postJson(url, body) {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(JSON.stringify(data, null, 2));
      return data;
    }

    byId("login").addEventListener("click", () => {
      const params = new URLSearchParams({
        response_type: "code",
        client_id: CLIENT_ID,
        redirect_uri: REDIRECT_URI,
        scope: "openid profile email",
        prompt: "login",
      });
      window.location.href = `${ISSUER}/auth?${params.toString()}`;
    });

    byId("exchange").addEventListener("click", async () => {
      const button = byId("exchange");
      button.disabled = true;
      show("token-response", "Code wird gegen Token getauscht ...");
      try {
        const data = await postJson("/api/exchange", {
          code: state.authorizationCode,
          redirect_uri: REDIRECT_URI,
        });
        state.accessToken = data.access_token || null;
        state.idToken = data.id_token || null;
        show("token-response", data);
        byId("introspect").disabled = !state.accessToken;
      } catch (error) {
        show("token-response", error.message);
        button.disabled = false;
      }
    });

    byId("introspect").addEventListener("click", async () => {
      show("introspection", "Token wird introspektiert ...");
      try {
        show("introspection", await postJson("/api/introspect", { token: state.accessToken }));
      } catch (error) {
        show("introspection", error.message);
      }
    });

    byId("logout").addEventListener("click", async () => {
      const params = new URLSearchParams({ post_logout_redirect_uri: window.location.origin });
      if (state.idToken) params.set("id_token_hint", state.idToken);
      let logoutResult = "Kein Access Token vorhanden; nur Logto-Browsersitzung beendet.";
      if (state.accessToken) {
        try {
          logoutResult = await postJson("/api/logout", { token: state.accessToken });
        } catch (error) {
          logoutResult = `Revocation fehlgeschlagen: ${error.message}`;
        }
      }
      show("logout-result", logoutResult);
      sessionStorage.setItem("logoutResult", JSON.stringify(logoutResult));
      window.location.href = `${ISSUER}/session/end?${params.toString()}`;
    });

    const savedLogoutResult = sessionStorage.getItem("logoutResult");
    if (savedLogoutResult) {
      try {
        show("logout-result", JSON.parse(savedLogoutResult));
      } finally {
        sessionStorage.removeItem("logoutResult");
      }
    }

    const query = new URLSearchParams(window.location.search);
    const code = query.get("code");
    if (code) {
      state.authorizationCode = code;
      show("auth-code", code);
      byId("exchange").disabled = false;
      window.history.replaceState({}, document.title, "/");
    } else if (query.get("error")) {
      show("auth-code", {
        error: query.get("error"),
        error_description: query.get("error_description"),
      });
    }
  </script>
</body>
</html>"""


@app.get("/")
def index():
    return HTML.replace("__ISSUER__", LOGTO_ISSUER).replace("__CLIENT_ID__", CLIENT_ID)


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/callback")
def callback():
    if request.args.get("error"):
        query = urllib.parse.urlencode(
            {
                "error": request.args["error"],
                "error_description": request.args.get("error_description", ""),
            }
        )
        return redirect(f"/?{query}")
    code = request.args.get("code")
    if not code:
        return "No authorization code received.", 400
    return redirect(f"/?code={urllib.parse.quote(code)}")


@app.post("/api/exchange")
def exchange_code():
    payload = request.get_json(silent=True) or {}
    code = payload.get("code")
    redirect_uri = payload.get("redirect_uri")
    if not code or not redirect_uri:
        return jsonify(error="Missing authorization code or redirect URI"), 400

    try:
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        return jsonify(error=f"Token exchange request failed: {exc}"), 502

    body = parse_response(response)
    if not response.ok:
        return jsonify(error="Logto token endpoint returned error", response=body), 400

    access_token = body.get("access_token", "")
    body["access_token_shape"] = "jwt-like" if access_token.count(".") == 2 else "opaque-like"
    return jsonify(body)


@app.post("/api/introspect")
def introspect_token():
    token = (request.get_json(silent=True) or {}).get("token")
    if not token:
        return jsonify(error="Missing access token"), 400
    try:
        response, endpoint = post_token_action(
            "introspection_endpoint", "/token/introspection", token
        )
    except requests.RequestException as exc:
        return jsonify(error=f"Introspection request failed: {exc}"), 502

    claims = parse_response(response)
    result = {
        "endpoint": endpoint,
        "status_code": response.status_code,
        "active": claims.get("active"),
        "sub": claims.get("sub"),
        "claims": claims,
    }
    return jsonify(result), (200 if response.ok else 400)


@app.post("/api/logout")
def logout():
    token = (request.get_json(silent=True) or {}).get("token")
    if not token:
        return jsonify(error="Missing access token for revocation"), 400
    try:
        response, endpoint = post_token_action(
            "revocation_endpoint", "/token/revocation", token
        )
    except requests.RequestException as exc:
        return jsonify(error=f"Revocation request failed: {exc}"), 502

    response_text = response.text.strip() or "(empty response - successful revocation)"
    return (
        jsonify(
            endpoint=endpoint,
            status_code=response.status_code,
            response=response_text,
        ),
        200 if response.ok else 400,
    )
