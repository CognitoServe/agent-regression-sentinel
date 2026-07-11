import sqlite3
import json
from harness.db import DB_PATH
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
run_id = '1479f599-4685-499e-8c4a-8e2f2ab8313a'
cursor.execute('''SELECT test_case_id, scorer_type, passed, score, substr(reason, 1, 150) AS reason_preview
FROM scores WHERE run_id = ? ORDER BY test_case_id, scorer_type''', (run_id,))
rows = cursor.fetchall()
print('--- SQL OUTPUT ---')
for r in rows:
    print(r)

print('\n--- TOOL ROUTING ARRAYS ---')
cursor.execute('SELECT test_case_id, raw_output FROM run_results WHERE run_id=? AND test_case_id LIKE "tc-tool-route-%" ORDER BY test_case_id', (run_id,))
for row in cursor.fetchall():
    data = json.loads(row[1])
    print(f"{row[0]}: {data.get('tool_calls_summary')}")
