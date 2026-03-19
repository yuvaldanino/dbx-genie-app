"""Direct DB persistence tests — no HTTP, no frontend.

Usage:
    uv run python scripts/test_persistence.py
"""

from __future__ import annotations

import sys
import uuid

from databricks.sdk import WorkspaceClient

# Add src to path so we can import genieapp
sys.path.insert(0, "src")

from genieapp.backend.db import (
    add_message,
    create_conversation,
    get_conversation,
    get_conversation_messages,
    get_starred_messages,
    increment_conversation_message_count,
    list_conversations,
    list_user_spaces,
    parse_sql_rows,
    run_sql,
    toggle_star_message,
    update_message_result,
)

TEST_USER = "test-persistence@test.com"


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def get_space_id(ws: WorkspaceClient) -> str:
    """Get a valid space_id from the DB (spaces table, then sessions fallback)."""
    from genieapp.backend.db import _SESSIONS_TABLE, _SPACES_TABLE

    # Try spaces table first
    try:
        result = run_sql(ws, f"SELECT space_id FROM {_SPACES_TABLE} WHERE is_active = true LIMIT 1")
        rows = parse_sql_rows(result)
        if rows:
            return rows[0]["space_id"]
    except RuntimeError:
        pass

    # Fallback to sessions table
    result = run_sql(ws, f"SELECT space_id FROM {_SESSIONS_TABLE} LIMIT 1")
    rows = parse_sql_rows(result)
    if rows:
        return rows[0]["space_id"]
    raise RuntimeError("No spaces found in DB.")


def test_run_sql_error_visibility(ws: WorkspaceClient) -> None:
    """Test 3: Check that run_sql properly surfaces errors."""
    print("\n=== Test: run_sql error visibility ===")

    # Test with bad SQL
    print("1. Querying nonexistent table...")
    try:
        result = run_sql(ws, "SELECT * FROM nonexistent_catalog.nonexistent_schema.nonexistent_table")
        print(f"   State: {result.get('status', {}).get('state')}")
        print(f"   Error: {result.get('status', {}).get('error', {}).get('message', 'none')}")
        rows = parse_sql_rows(result)
        print(f"   parse_sql_rows returned: {rows}")
        print("   PROBLEM: run_sql did NOT raise on failed query!")
    except RuntimeError as e:
        print(f"   GOOD: run_sql raised RuntimeError: {e}")
    except Exception as e:
        print(f"   run_sql raised {type(e).__name__}: {e}")

    # Test with bad INSERT
    print("\n2. Bad INSERT...")
    try:
        result = run_sql(ws, "INSERT INTO nonexistent_catalog.nonexistent_schema.nonexistent_table VALUES ('x')")
        print(f"   State: {result.get('status', {}).get('state')}")
        print(f"   Error: {result.get('status', {}).get('error', {}).get('message', 'none')}")
        print("   PROBLEM: run_sql did NOT raise on failed INSERT!")
    except RuntimeError as e:
        print(f"   GOOD: run_sql raised RuntimeError: {e}")
    except Exception as e:
        print(f"   run_sql raised {type(e).__name__}: {e}")


def test_conversation_persistence(ws: WorkspaceClient, space_id: str) -> None:
    """Test 1: Full conversation lifecycle."""
    print("\n=== Test: conversation persistence ===")

    conv_id = _unique("test-conv")
    msg_id = _unique("test-msg")

    print(f"1. Creating conversation {conv_id}...")
    create_conversation(ws, conv_id, space_id, TEST_USER, "Test query")
    print("   OK")

    print(f"2. Adding message {msg_id}...")
    add_message(ws, msg_id, conv_id, TEST_USER, "What is revenue?")
    increment_conversation_message_count(ws, conv_id)
    print("   OK")

    print("3. Updating message result...")
    update_message_result(ws, msg_id, conv_id, status="COMPLETED", sql_text="SELECT 1", description="Test result")
    print("   OK")

    print("4. Listing conversations...")
    convs = list_conversations(ws, TEST_USER, space_id)
    found = any(c["conversation_id"] == conv_id for c in convs)
    print(f"   Found test conversation: {found}")
    if not found:
        print(f"   FAIL — conversation {conv_id} not in list")
        print(f"   All conversations: {[c['conversation_id'] for c in convs[:5]]}")
    else:
        print("   PASS")

    print("5. Getting conversation messages...")
    msgs = get_conversation_messages(ws, conv_id)
    if not msgs:
        print("   FAIL — no messages returned")
    else:
        m = msgs[0]
        print(f"   Message ID: {m.get('message_id')}")
        print(f"   Status: {m.get('status')}")
        print(f"   SQL: {m.get('sql_text')}")
        ok = m.get("status") == "COMPLETED" and m.get("sql_text") == "SELECT 1"
        print(f"   PASS" if ok else f"   FAIL — expected COMPLETED/SELECT 1")

    return conv_id, msg_id


def test_star_pin(ws: WorkspaceClient, space_id: str, conv_id: str, msg_id: str) -> None:
    """Test 2: Star/unstar a message."""
    print("\n=== Test: star/pin ===")

    print(f"1. Starring message {msg_id}...")
    toggle_star_message(ws, msg_id, conv_id, TEST_USER, starred=True)
    print("   OK")

    print("2. Getting starred messages...")
    starred = get_starred_messages(ws, TEST_USER, space_id)
    found = any(m.get("message_id") == msg_id for m in starred)
    print(f"   Found starred message: {found}")
    if not found:
        print(f"   FAIL — message {msg_id} not in starred list")
        print(f"   Starred messages: {starred[:3]}")
    else:
        print("   PASS")

    print("3. Unstarring message...")
    toggle_star_message(ws, msg_id, conv_id, TEST_USER, starred=False)
    print("   OK")

    print("4. Verifying unstarred...")
    starred = get_starred_messages(ws, TEST_USER, space_id)
    found = any(m.get("message_id") == msg_id for m in starred)
    print(f"   Still starred: {found}")
    if found:
        print("   FAIL — message still appears as starred after unstar")
    else:
        print("   PASS")


def cleanup(ws: WorkspaceClient, conv_id: str) -> None:
    """Remove test data."""
    from genieapp.backend.db import _CONVERSATIONS_TABLE, _MESSAGES_TABLE

    print("\n=== Cleanup ===")
    try:
        run_sql(ws, f"DELETE FROM {_MESSAGES_TABLE} WHERE conversation_id = '{conv_id}'")
        run_sql(ws, f"DELETE FROM {_CONVERSATIONS_TABLE} WHERE conversation_id = '{conv_id}'")
        print("   Cleaned up test data")
    except Exception as e:
        print(f"   Cleanup failed (non-critical): {e}")


def main() -> None:
    """Run all persistence tests."""
    print("Connecting to Databricks (profile=vm)...")
    ws = WorkspaceClient(profile="vm")
    print(f"   Host: {ws.config.host}")

    # Test error visibility FIRST (before any fixes, to see baseline)
    test_run_sql_error_visibility(ws)

    # Get a valid space_id
    print("\nLooking up a valid space_id...")
    space_id = get_space_id(ws)
    print(f"   Using space_id: {space_id}")

    # Test conversation lifecycle
    conv_id, msg_id = test_conversation_persistence(ws, space_id)

    # Test star/pin
    test_star_pin(ws, space_id, conv_id, msg_id)

    # Cleanup
    cleanup(ws, conv_id)

    print("\n=== All tests complete ===")


if __name__ == "__main__":
    main()
