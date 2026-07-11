import sqlite3
import json
import datetime
from harness.db import DB_PATH, create_run

def setup_manual_test():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if run exists, clear if so
    run_id = "manual-test-run"
    cursor.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
    cursor.execute("DELETE FROM run_results WHERE run_id = ?", (run_id,))
    cursor.execute("DELETE FROM scores WHERE run_id = ?", (run_id,))
    
    cursor.execute("""
        INSERT INTO runs (run_id, started_at, target_agent, git_commit_or_version_tag)
        VALUES (?, ?, ?, ?)
    """, (run_id, datetime.datetime.now(datetime.timezone.utc).isoformat(), "research_agent", "manual"))

    # 1. Induced bad output test for tc-struct-out-1 (forbidden combo)
    bad_struct = {
        "topic": "Capital of France",
        "findings": [
            {
                "claim": "The capital of France is Paris.",
                "confidence": "high",
                "source": "agent_knowledge"
            }
        ],
        "tool_calls_summary": []
    }
    cursor.execute("""
        INSERT INTO run_results (run_id, test_case_id, raw_output, latency_ms, error, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (run_id, "tc-struct-out-1", json.dumps(bad_struct), 100, None, datetime.datetime.now().isoformat()))

    # 2. Judge disagreement test for tc-sem-mem-1 (factually about pancakes)
    bad_mem = {
        "topic": "Pancakes",
        "findings": [
            {
                "claim": "Goal misspecification is when you make pancakes but forget the syrup.",
                "confidence": "high",
                "source": "agent_knowledge"
            }
        ],
        "tool_calls_summary": []
    }
    cursor.execute("""
        INSERT INTO run_results (run_id, test_case_id, raw_output, latency_ms, error, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (run_id, "tc-sem-mem-1", json.dumps(bad_mem), 100, None, datetime.datetime.now().isoformat()))

    conn.commit()
    conn.close()
    print(f"Setup complete. Run ID: {run_id}")

if __name__ == "__main__":
    setup_manual_test()
