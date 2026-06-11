"""Post-deploy verification against the live app (see docs/OPERATIONS.md).

Usage:
    python3 scripts/verify_live.py          # smoke + history data check
    python3 scripts/verify_live.py --chat   # also run a full ephemeral chat flow

Requires: `databricks auth token --profile vm` to work.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request

APP = "https://genieapp-dev-7474655921234161.aws.databricksapps.com"
COCA_COLA_SPACE = "01f144169528170cab22ee3e2a5803e4"  # shared test space


def get_token() -> str:
    """Fetch an OAuth token via the Databricks CLI (profile vm)."""
    out = subprocess.run(
        ["databricks", "auth", "token", "--profile", "vm"],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)["access_token"]


TOKEN = get_token()


def call(method: str, path: str, body: dict | None = None, timeout: int = 300):
    """Call the live app; returns (status_code, parsed_json, elapsed_sec)."""
    data = json.dumps(body).encode() if body else None
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(APP + path, data=data, method=method, headers=headers)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return r.status, json.loads(raw) if raw else None, time.time() - t0


def smoke() -> None:
    """All endpoints 200; spaces must be >1 (n=1 = Acme fallback = GRANT missing)."""
    for p in ["/api/health", "/api/users/me", "/api/version"]:
        code, _, dt = call("GET", p)
        print(f"{p}: {code} ({dt:.2f}s)")
        assert code == 200, f"SMOKE FAIL {p}"
    code, spaces, dt = call("GET", "/api/spaces")
    print(f"/api/spaces: {code} n={len(spaces)} ({dt:.2f}s)")
    assert len(spaces) > 1, "GRANT MISSING — only fallback space visible"


def history_data() -> None:
    """Old conversations must return real data arrays, not metadata-only."""
    _, convs, _ = call("GET", "/api/conversations")
    print(f"/api/conversations: n={len(convs)}")
    checked = with_data = 0
    for conv in convs[:5]:
        cid = conv["conversation_id"]
        code, msgs, dt = call("GET", f"/api/conversations/{cid}")
        print(f"  conv {cid[:8]}…: {code} msgs={len(msgs)} ({dt:.1f}s)")
        for m in msgs:
            r = m.get("response") or {}
            if r.get("status") == "COMPLETED" and r.get("sql"):
                checked += 1
                if r.get("row_count", 0) > 0:
                    with_data += 1
    print(f"history: {with_data}/{checked} completed-with-SQL messages have data")
    assert checked == 0 or with_data / checked >= 0.5, "HISTORY DATA REGRESSION"


def chat_flow() -> None:
    """Full ephemeral chat flow against the shared Coca-Cola space."""
    _, start, _ = call("POST", "/api/chat/start", {
        "question": "What are total sales by region?",
        "space_id": COCA_COLA_SPACE,
        "ephemeral": True,
    })
    conv, msg = start["conversation_id"], start["message_id"]
    print(f"chat started: conv={conv[:8]}…")
    t0 = time.time()
    while time.time() - t0 < 180:
        _, st, _ = call("GET", f"/api/chat/{conv}/{msg}/status?space_id={COCA_COLA_SPACE}")
        print(f"  {st['status']} ({time.time()-t0:.0f}s)")
        if st["is_complete"]:
            break
        time.sleep(3)
    _, res, _ = call("GET", f"/api/chat/{conv}/{msg}/result?space_id={COCA_COLA_SPACE}&ephemeral=true")
    print(f"chat result: status={res['status']} rows={res['row_count']} err={res.get('error')}")
    assert res["status"] == "COMPLETED" and res["row_count"] > 0, "CHAT FLOW FAIL"


if __name__ == "__main__":
    smoke()
    history_data()
    if "--chat" in sys.argv:
        chat_flow()
    print("VERIFY OK")
