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
            tags TEXT,
            expected_keywords TEXT,
            expected_tools TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT,
            target_agent TEXT,
            git_commit_or_version_tag TEXT,
            is_baseline BOOLEAN DEFAULT 0
        )
    """)
    
    # Simple migration for existing DB
    try:
        cursor.execute("ALTER TABLE runs ADD COLUMN is_baseline BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists

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
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            score_id TEXT PRIMARY KEY,
            run_id TEXT,
            test_case_id TEXT,
            scorer_type TEXT,
            scorer_version TEXT,
            passed BOOLEAN,
            score REAL,
            reason TEXT,
            raw_judge_response TEXT,
            scored_at TEXT,
            FOREIGN KEY (run_id, test_case_id) REFERENCES run_results(run_id, test_case_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diffs (
            diff_id TEXT PRIMARY KEY,
            baseline_run_id TEXT,
            candidate_run_id TEXT,
            test_case_id TEXT,
            scorer_type TEXT,
            baseline_passed BOOLEAN,
            candidate_passed BOOLEAN,
            baseline_score REAL,
            candidate_score REAL,
            verdict TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()

def upsert_test_cases(test_cases: list[dict], db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for tc in test_cases:
        cursor.execute("""
            INSERT INTO test_cases (id, target_agent, category, input_prompt, expected_criteria, tags, expected_keywords, expected_tools)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                target_agent=excluded.target_agent,
                category=excluded.category,
                input_prompt=excluded.input_prompt,
                expected_criteria=excluded.expected_criteria,
                tags=excluded.tags,
                expected_keywords=excluded.expected_keywords,
                expected_tools=excluded.expected_tools
        """, (
            tc['id'],
            tc['target_agent'],
            tc['category'],
            tc['input_prompt'],
            tc['expected_criteria'],
            json.dumps(tc.get('tags', [])),
            json.dumps(tc.get('expected_keywords', [])),
            json.dumps(tc.get('expected_tools', []))
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

def get_run_results(run_id: str, db_path: str = DB_PATH) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM run_results WHERE run_id = ?", (run_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_test_case(test_case_id: str, db_path: str = DB_PATH) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM test_cases WHERE id = ?", (test_case_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        tc = dict(row)
        tc['tags'] = json.loads(tc['tags']) if tc.get('tags') else []
        tc['expected_keywords'] = json.loads(tc['expected_keywords']) if tc.get('expected_keywords') else []
        tc['expected_tools'] = json.loads(tc['expected_tools']) if tc.get('expected_tools') else []
        return tc
    return None

def delete_scores(run_id: str, db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scores WHERE run_id = ?", (run_id,))
    conn.commit()
    conn.close()

def insert_score(run_id: str, test_case_id: str, scorer_type: str, scorer_version: str, passed: bool | None, score: float | None, reason: str, raw_judge_response: str = None, db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    score_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO scores (score_id, run_id, test_case_id, scorer_type, scorer_version, passed, score, reason, raw_judge_response, scored_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (score_id, run_id, test_case_id, scorer_type, scorer_version, passed, score, reason, raw_judge_response, datetime.datetime.now(datetime.timezone.utc).isoformat()))
    
    conn.commit()
    conn.close()

def set_baseline_run(run_id: str, db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE runs SET is_baseline = 0")
    cursor.execute("UPDATE runs SET is_baseline = 1 WHERE run_id = ?", (run_id,))
    conn.commit()
    conn.close()

def get_baseline_run(db_path: str = DB_PATH) -> str | None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT run_id FROM runs WHERE is_baseline = 1 LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_run_scores(run_id: str, db_path: str = DB_PATH) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scores WHERE run_id = ?", (run_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def insert_diff(diff_id: str, baseline_run_id: str, candidate_run_id: str, test_case_id: str, scorer_type: str, baseline_passed: bool | None, candidate_passed: bool | None, baseline_score: float | None, candidate_score: float | None, verdict: str, db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO diffs (diff_id, baseline_run_id, candidate_run_id, test_case_id, scorer_type, baseline_passed, candidate_passed, baseline_score, candidate_score, verdict, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (diff_id, baseline_run_id, candidate_run_id, test_case_id, scorer_type, baseline_passed, candidate_passed, baseline_score, candidate_score, verdict, datetime.datetime.now(datetime.timezone.utc).isoformat()))
    
    conn.commit()
    conn.close()
