import json
import os
from datetime import datetime, timezone
from config import LOG_FILE

SUMMARY_FILE = "logs/session_summary.jsonl"
SUMMARY_INTERVAL = 5


def _write_session_summary() -> None:
    """Read audit.jsonl, compute aggregate metrics, append to session_summary.jsonl."""
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]

    total = len(entries)
    tier_counts = {"safe": 0, "caution": 0, "refuse": 0}
    for entry in entries:
        t = entry.get("tier", "")
        if t in tier_counts:
            tier_counts[t] += 1

    recent_questions = [e["question"] for e in entries[-3:]]

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_interactions": total,
        "tier_distribution": tier_counts,
        "recent_questions": recent_questions,
    }

    with open(SUMMARY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(summary) + "\n")

    print(
        f"[SUMMARY] {total} total | "
        f"safe={tier_counts['safe']} caution={tier_counts['caution']} refuse={tier_counts['refuse']}"
    )


def log_interaction(question: str, tier: str, response: str) -> None:
    """
    Append a structured record of this interaction to the audit log.
    Creates logs/ directory if it doesn't exist.
    Every 5 interactions, writes an aggregate summary to session_summary.jsonl.
    """
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    q_truncated = question[:300]
    r_preview = response[:200]

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tier": tier,
        "question": q_truncated,
        "response_preview": r_preview,
        "question_length": len(question),
        "response_length": len(response),
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    print(f'[LOGGED] tier={tier} | "{q_truncated[:60]}..." → {len(response)} chars')

    # Count lines without reading the whole file into memory
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        total = sum(1 for line in f if line.strip())

    if total % SUMMARY_INTERVAL == 0:
        _write_session_summary()
