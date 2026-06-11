"""P0 #1 parity diagnosis probe — capture native-vs-app evidence (no fixes here).

For each fixed question against the Coca-Cola shared space:
  1. app    — full app flow (POST /chat/start ephemeral -> poll -> GET /result)
  2. app_raw — raw GenieMessage (SDK get_message) for the SAME message the app created
  3. native — direct SDK start_conversation_and_wait (native-engine baseline)
Plus a context A/B: same question fresh vs appended to a long-lived conversation.

Artifacts: /tmp/parity/*.json  (analyze, then summarize in docs/worklogs/genie-parity.md)
Run: .venv/bin/python scripts/parity_probe.py
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import time
import urllib.request

from databricks.sdk import WorkspaceClient

APP = "https://genieapp-dev-7474655921234161.aws.databricksapps.com"
SPACE = "01f144169528170cab22ee3e2a5803e4"  # Coca-Cola (shared)
OUT = pathlib.Path("/tmp/parity")
OUT.mkdir(exist_ok=True)

QUESTIONS = [
    "What are total sales by region?",
    "Which products generated the most revenue?",
    "Show me the monthly sales trend",
    "Compare average order value across customer segments",
    "What is our best performing product and why?",
]
AB_QUESTION = "Show me the monthly sales trend"

ws = WorkspaceClient(profile="vm")

_tok = subprocess.run(
    ["databricks", "auth", "token", "--profile", "vm"],
    capture_output=True, text=True, check=True,
).stdout
TOKEN = json.loads(_tok)["access_token"]


def app_call(method: str, path: str, body: dict | None = None):
    """Call the live app API."""
    data = json.dumps(body).encode() if body else None
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(APP + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def app_flow(question: str, conversation_id: str | None = None) -> dict:
    """Run the app's async chat flow; returns the app's parsed result + ids."""
    body = {"question": question, "space_id": SPACE, "ephemeral": True}
    if conversation_id:
        body["conversation_id"] = conversation_id
    start = app_call("POST", "/api/chat/start", body)
    conv, msg = start["conversation_id"], start["message_id"]
    t0 = time.time()
    while time.time() - t0 < 240:
        st = app_call("GET", f"/api/chat/{conv}/{msg}/status?space_id={SPACE}")
        if st["is_complete"]:
            break
        time.sleep(3)
    result = app_call("GET", f"/api/chat/{conv}/{msg}/result?space_id={SPACE}&ephemeral=true")
    result["_elapsed_sec"] = round(time.time() - t0, 1)
    return result


def raw_message(conv: str, msg: str) -> dict:
    """Fetch the raw GenieMessage as the SDK sees it."""
    m = ws.genie.get_message(space_id=SPACE, conversation_id=conv, message_id=msg)
    return m.as_dict()


def save(name: str, obj: dict) -> None:
    (OUT / f"{name}.json").write_text(json.dumps(obj, indent=2, default=str))
    print(f"  saved {name}.json")


def main() -> None:
    # --- Per-question: app flow + raw of same message + native-style ask ---
    for i, q in enumerate(QUESTIONS, 1):
        print(f"[q{i}] {q}")
        app_res = app_flow(q)
        save(f"q{i}_app", app_res)
        if app_res.get("conversation_id") and app_res.get("message_id"):
            save(f"q{i}_app_raw", raw_message(app_res["conversation_id"], app_res["message_id"]))

        t0 = time.time()
        native = ws.genie.start_conversation_and_wait(space_id=SPACE, content=q)
        raw = native.as_dict()
        raw["_elapsed_sec"] = round(time.time() - t0, 1)
        save(f"q{i}_native_raw", raw)

    # --- Context A/B: fresh vs resumed long conversation ---
    print("[ab] fresh conversation")
    save("ab_fresh", app_flow(AB_QUESTION))

    convs = app_call("GET", "/api/conversations")
    long_conv = max(convs, key=lambda c: c.get("message_count", 0))
    print(f"[ab] resumed conversation {long_conv['conversation_id'][:12]}… "
          f"(message_count={long_conv.get('message_count')})")
    resumed = app_flow(AB_QUESTION, conversation_id=long_conv["conversation_id"])
    resumed["_resumed_conversation"] = long_conv["conversation_id"]
    save("ab_resumed", resumed)

    print("PROBE DONE")


if __name__ == "__main__":
    main()
