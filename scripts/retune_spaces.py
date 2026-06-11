"""Retune live Genie spaces with rich instructions generated from UC metadata.

Usage (run as workspace admin/catalog owner, profile vm):
  .venv/bin/python scripts/retune_spaces.py list                # spaces + current instruction sizes
  .venv/bin/python scripts/retune_spaces.py preview <space_id>  # print generated instructions (no write)
  .venv/bin/python scripts/retune_spaces.py apply <space_id>    # PATCH one space
  .venv/bin/python scripts/retune_spaces.py apply-all           # PATCH every active space

Instructions only — tables, sample questions, title etc. are never modified.
Original instruction text is backed up to /tmp/retune_backup/<space_id>.txt before PATCH.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import urllib.request

from databricks.sdk import WorkspaceClient

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from genieapp.backend.pipeline.instruction_builder import build_instructions_from_uc  # noqa: E402

APP = "https://genieapp-dev-7474655921234161.aws.databricksapps.com"
WAREHOUSE_ID = "fc62b388f737b2d3"  # app runtime warehouse (db.py)
BACKUP_DIR = pathlib.Path("/tmp/retune_backup")
BACKUP_DIR.mkdir(exist_ok=True)

ws = WorkspaceClient(profile="vm")

_tok = subprocess.run(
    ["databricks", "auth", "token", "--profile", "vm"],
    capture_output=True, text=True, check=True,
).stdout
TOKEN = json.loads(_tok)["access_token"]


def app_get(path: str):
    req = urllib.request.Request(APP + path, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def get_serialized(space_id: str) -> tuple[dict, dict]:
    """Return (space_response, parsed serialized_space)."""
    resp = ws.api_client.do(
        "GET", f"/api/2.0/genie/spaces/{space_id}?include_serialized_space=true"
    )
    return resp, json.loads(resp.get("serialized_space") or "{}")


def current_instruction_text(serialized: dict) -> str:
    ti = serialized.get("instructions", {}).get("text_instructions", [])
    if ti and ti[0].get("content"):
        return ti[0]["content"][0] or ""
    return ""


def space_config(space_id: str) -> dict:
    return app_get(f"/api/spaces/{space_id}/config")


def generate(space_id: str) -> tuple[str, dict, dict]:
    """Generate new instructions for a space. Returns (text, space_resp, serialized)."""
    cfg = space_config(space_id)
    tables = [t["full_name"] for t in cfg.get("tables", [])]
    desc = (cfg.get("branding") or {}).get("description") or cfg.get("display_name", "")
    if not tables:
        raise RuntimeError(f"space {space_id} has no tables in config — skip")
    space_resp, serialized = get_serialized(space_id)
    text = build_instructions_from_uc(ws, WAREHOUSE_ID, tables, desc)
    return text, space_resp, serialized


INSTRUCTION_TITLE = "Data dictionary & query guidance (auto-generated)"


def apply(space_id: str) -> None:
    """Update the space's text instruction via the data-rooms API.

    NOTE: the public `PATCH /genie/spaces/{id}` silently ignores changes to
    `serialized_space.instructions` (verified 2026-06-11). The Genie UI itself
    uses the internal data-rooms API, which does work:
      POST /api/2.0/data-rooms/{space_id}/instructions/{instruction_id}
    Internal API caveat: shape may change without notice — refetch-verify below
    guards against silent breakage.
    """
    text, _, _ = generate(space_id)
    if "## Data Dictionary" not in text or len(text) < 800:
        raise RuntimeError(
            f"generated instructions too thin ({len(text)}ch) — tables unreadable? refusing to downgrade"
        )

    instrs = ws.api_client.do("GET", f"/api/2.0/data-rooms/{space_id}/instructions").get("instructions", [])
    text_instrs = [i for i in instrs if i.get("instruction_type") == "TEXT_INSTRUCTION"]

    if text_instrs:
        ins = text_instrs[0]
        (BACKUP_DIR / f"{space_id}.txt").write_text(ins.get("content", ""))
        old_len = len(ins.get("content", ""))
        body = {
            "title": INSTRUCTION_TITLE,
            "content": text,
            "instruction_type": "TEXT_INSTRUCTION",
        }
        ws.api_client.do(
            "POST",
            f"/api/2.0/data-rooms/{space_id}/instructions/{ins['instruction_id']}",
            body=body,
        )
    else:
        (BACKUP_DIR / f"{space_id}.txt").write_text("")
        old_len = 0
        ws.api_client.do(
            "POST",
            f"/api/2.0/data-rooms/{space_id}/instructions",
            body={"title": INSTRUCTION_TITLE, "content": text, "instruction_type": "TEXT_INSTRUCTION"},
        )

    # Verify by refetch through BOTH surfaces
    after = ws.api_client.do("GET", f"/api/2.0/data-rooms/{space_id}/instructions").get("instructions", [])
    got = next((i.get("content", "") for i in after if i.get("instruction_type") == "TEXT_INSTRUCTION"), "")
    ok = got.strip() == text.strip()
    _, ser = get_serialized(space_id)
    pub = current_instruction_text(ser)
    print(f"  {'VERIFIED' if ok else 'MISMATCH'} — old {old_len}ch → new {len(got)}ch "
          f"(public serialized sees {len(pub)}ch; backup: {BACKUP_DIR}/{space_id}.txt)")
    if not ok:
        raise RuntimeError("refetched instructions do not match what was sent")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"

    if cmd == "list":
        spaces = app_get("/api/admin/spaces")
        for s in spaces:
            sid = s.get("space_id", "")
            try:
                _, ser = get_serialized(sid)
                n = len(current_instruction_text(ser))
            except Exception as e:
                n = f"ERR {str(e)[:40]}"
            print(f"{sid}  {str(n):>6}ch  {s.get('space_type','?'):>9}  {s.get('company_name','')}")

    elif cmd == "preview" and len(sys.argv) > 2:
        text, _, serialized = generate(sys.argv[2])
        print(f"=== current: {len(current_instruction_text(serialized))}ch | generated: {len(text)}ch ===\n")
        print(text)

    elif cmd == "apply" and len(sys.argv) > 2:
        print(f"apply {sys.argv[2]}")
        apply(sys.argv[2])

    elif cmd == "apply-all":
        spaces = app_get("/api/admin/spaces")
        for s in spaces:
            sid = s.get("space_id", "")
            print(f"apply {sid} ({s.get('company_name','')})")
            try:
                apply(sid)
            except Exception as e:
                print(f"  SKIP: {str(e)[:140]}")

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
