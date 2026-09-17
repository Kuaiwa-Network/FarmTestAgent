"""Read-only compatibility fallback for empty desktop read_thread turn items.

Local rollout format is installation-specific, not a public Codex API. Only
hydrate turns already identified by the app; never infer completion or dispatch.
"""
from contextlib import closing
import json
from pathlib import Path
import sqlite3


def hydrate_empty_turns(data, state_db_path):
    turns = {t["id"]: t for t in data.get("turns", []) if t.get("items") == []}
    if not turns or not state_db_path:
        return
    thread_id = data["thread"]["id"]
    state = Path(state_db_path).resolve()
    with closing(sqlite3.connect(state.as_uri()+"?mode=ro", uri=True, timeout=1)) as db:
        row = db.execute("SELECT rollout_path FROM threads WHERE id=?", (thread_id,)).fetchone()
    if not row:
        return
    path = Path(row[0]).resolve()
    root = (state.parent/"sessions").resolve()
    # Windows metadata uses extended-length paths (\\\\?\\C:\\...). samefile
    # compares actual directories rather than mismatched lexical prefixes.
    if not any(parent.samefile(root) for parent in path.parents):
        raise ValueError("Codex rollout is outside the configured sessions directory")
    with path.open("rb") as file:
        raw = file.read(32*1024*1024 + 1)
    if len(raw) > 32*1024*1024:
        raise ValueError("Codex rollout exceeds the compatibility read bound")
    # A writer may be appending the last line. Never consume partial JSON.
    lines = raw.splitlines(keepends=True)
    if lines and not lines[-1].endswith(b"\n"):
        lines.pop()
    records = [json.loads(line) for line in lines]
    if (not records or records[0].get("type") != "session_meta"
            or records[0].get("payload", {}).get("id") != thread_id):
        raise ValueError("Codex rollout identity mismatch")
    items = {key: [] for key in turns}
    started, completed = set(), set()
    seen = set()
    for record in records:
        if record.get("type") != "event_msg":
            continue
        payload = record.get("payload", {})
        turn_id = payload.get("turn_id")
        if turn_id not in turns:
            continue
        kind = payload.get("type")
        if kind == "task_started":
            if turn_id in started:
                raise ValueError("Duplicate Codex turn start")
            started.add(turn_id)
        elif kind == "task_complete":
            completed.add(turn_id)
        elif kind == "item_completed":
            if payload.get("thread_id") != thread_id or turn_id not in started:
                raise ValueError("Codex item identity mismatch")
            item = payload.get("item", {})
            item_type = item.get("type")
            if item_type == "FunctionCallOutput" and item.get("namespace") == "codex_app" \
                    and item.get("name") in ("send_message_to_thread", "create_thread"):
                if not isinstance(item.get("output"), str):
                    raise ValueError("Unknown Codex delegation output format")
                normalized = {"type": "functionCallOutput", "namespace": "codex_app",
                              "name": item["name"], "output": {"text": item["output"]}}
            elif item_type == "AgentMessage" and item.get("phase") in ("final", "final_answer"):
                content = item.get("content")
                if not isinstance(content, list) or not content or any(
                        p.get("type") != "Text" or not isinstance(p.get("text"), str) for p in content):
                    raise ValueError("Unknown Codex final content format")
                normalized = {"type": "agentMessage", "phase": item["phase"],
                              "text": "".join(p["text"] for p in content)}
            else:
                continue
            identity = (turn_id, item.get("id"))
            if not identity[1] or identity in seen or turn_id in completed:
                raise ValueError("Ambiguous Codex rollout item")
            seen.add(identity)
            items[turn_id].append(normalized)
    for turn_id, turn in turns.items():
        if turn_id not in started:
            continue
        if turn.get("status") == "completed" and turn_id not in completed:
            continue
        turn["items"] = items[turn_id]
