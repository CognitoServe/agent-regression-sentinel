import sqlite3
import json
import uuid
import datetime

DB_PATH = "eval_harness.db"

def init_db(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_cases (
            id TEXT PRIMARY KEY,
            target_agent TEXT,
            category TEXT,
            input_prompt TEXT,
            expected_criteria TEXT,
            tags TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT,
            target_agent TEXT,
            git_commit_or_version_tag TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS run_results (
            run_id TEXT,
            test_case_id TEXT,
            raw_output TEXT,
            latency_ms INTEGER,
            error TEXT,
            timestamp TEXT,
            PRIMARY KEY (run_id, test_case_id)
        )
    """)

    conn.commit()
    conn.close()

def upsert_test_cases(test_cases: list[dict], db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for tc in test_cases:
        cursor.execute("""
            INSERT INTO test_cases (id, target_agent, category, input_prompt, expected_criteria, tags)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                target_agent=excluded.target_agent,
                category=excluded.category,
                input_prompt=excluded.input_prompt,
                expected_criteria=excluded.expected_criteria,
                tags=excluded.tags
        """, (
            tc['id'],
            tc['target_agent'],
            tc['category'],
            tc['input_prompt'],
            tc['expected_criteria'],
            json.dumps(tc['tags'])
        ))
    
    conn.commit()
    conn.close()

def create_run(target_agent: str, git_commit: str = "unknown", db_path: str = DB_PATH) -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    run_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO runs (run_id, started_at, target_agent, git_commit_or_version_tag)
        VALUES (?, ?, ?, ?)
    """, (run_id, datetime.datetime.now(datetime.timezone.utc).isoformat(), target_agent, git_commit))
    
    conn.commit()
    conn.close()
    return run_id

def insert_run_result(run_id: str, test_case_id: str, raw_output: str, latency_ms: int, error: str, db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO run_results (run_id, test_case_id, raw_output, latency_ms, error, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (run_id, test_case_id, raw_output, latency_ms, error, datetime.datetime.now(datetime.timezone.utc).isoformat()))
    
    conn.commit()
    conn.close()
