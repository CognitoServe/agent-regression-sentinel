import argparse
import sys
import subprocess
from dotenv import load_dotenv
load_dotenv()

from harness.runner import run_suite
from harness.differ import diff_runs
from harness.db import get_run_results, get_test_case, delete_scores, set_baseline_run, get_baseline_run
from harness.scorers.deterministic import run_deterministic
from harness.scorers.llm_judge import run_llm_judge
import sqlite3

def get_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except Exception:
        return "unknown"

def print_diff_report(baseline_id, candidate_id, summary):
    # Fetch run info for printing (simplified timestamps for display)
    conn = sqlite3.connect("eval_harness.db")
    c = conn.cursor()
    c.execute("SELECT started_at FROM runs WHERE run_id=?", (baseline_id,))
    b_time = c.fetchone()[0][:16].replace('T', ' ')
    c.execute("SELECT started_at FROM runs WHERE run_id=?", (candidate_id,))
    c_time = c.fetchone()[0][:16].replace('T', ' ')
    conn.close()

    print("=== REGRESSION REPORT ===")
    print(f"Baseline:  {baseline_id[:8]}... ({b_time})")
    print(f"Candidate: {candidate_id[:8]}... ({c_time})\n")

    print(f"REGRESSIONS ({len(summary['regressions'])}):")
    for r in summary['regressions']:
        print(f"  ❌ {r['test_case_id']:<19} [{r['scorer_type']}]      passed → failed")
    if not summary['regressions']:
        print("  None")
    print()

    print(f"IMPROVEMENTS ({len(summary['improvements'])}):")
    for i in summary['improvements']:
        print(f"  ✅ {i['test_case_id']:<19} [{i['scorer_type']}]      failed → passed")
    if not summary['improvements']:
        print("  None")
    print()

    print(f"SCORE DROPS ({len(summary['score_drops'])}):")
    for d in summary['score_drops']:
        print(f"  ⚠️  {d['test_case_id']:<19} [{d['scorer_type']}]      {d['b_score']} → {d['c_score']}")
    if not summary['score_drops']:
        print("  None")
    print()

    print(f"UNCHANGED: {len(summary['unchanged'])}")
    print(f"UNMEASURABLE: {len(summary['unmeasurable'])}\n")
    print(f"Diff saved as: {summary['diff_id']}")
    
    if summary['regressions']:
        sys.exit(1)
    sys.exit(0)

def score_run(run_id: str, deterministic_only: bool = False, judge_only: bool = False):
    print(f"Scoring Run ID: {run_id}")
    delete_scores(run_id) # Idempotency: clear existing scores for this run
    
    results = get_run_results(run_id)
    if not results:
        print(f"No results found for Run ID: {run_id}")
        return
        
    total_tokens = 0
    total_cost = 0.0
    
    for res in results:
        tc = get_test_case(res['test_case_id'])
        if not tc:
            continue
            
        det_passed = False
        
        if not judge_only:
            print(f"  [Deterministic] Scoring {tc['id']}...")
            run_deterministic(run_id, tc, res['raw_output'])
            
            # To pass to judge, we need to know if deterministic passed
            conn = sqlite3.connect("eval_harness.db")
            cursor = conn.cursor()
            cursor.execute("SELECT passed FROM scores WHERE run_id=? AND test_case_id=? AND scorer_type='deterministic'", (run_id, tc['id']))
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] == 1:
                det_passed = True
        else:
            det_passed = True
            
        if not deterministic_only and det_passed:
            print(f"  [LLM Judge] Scoring {tc['id']}...")
            tokens, cost = run_llm_judge(run_id, tc, res['raw_output'], det_passed)
            total_tokens += tokens
            total_cost += cost
            
    print("-" * 50)
    print(f"Scoring completed for {run_id}.")
    if not deterministic_only:
        print(f"LLM Judge Cost: {total_tokens} tokens / ${total_cost:.6f}")

def main():
    parser = argparse.ArgumentParser(description="LLM Evaluation & Regression Testing Platform")
    parser.add_argument("--agent", type=str, help="Target agent to run the suite against (e.g., research_agent)")
    parser.add_argument("--commit", type=str, default="", help="Git commit or version tag for this run")
    parser.add_argument("--score", type=str, help="Run ID to score")
    parser.add_argument("--deterministic-only", action="store_true", help="Only run deterministic scorer")
    parser.add_argument("--judge-only", action="store_true", help="Only run LLM judge scorer")
    parser.add_argument("--auto-score", action="store_true", help="Automatically score after a run")
    parser.add_argument("--set-baseline", type=str, help="Set the given run ID as the baseline")
    parser.add_argument("--diff", type=str, nargs='*', help="Compare runs: [--diff <candidate>] or [--diff <baseline> <candidate>]")
    
    args = parser.parse_args()
    
    if args.set_baseline:
        set_baseline_run(args.set_baseline)
        print(f"Baseline set to: {args.set_baseline}")
        return

    if args.diff is not None:
        if len(args.diff) == 0:
            print("Error: --diff requires at least 1 candidate run_id.")
            sys.exit(2)
        elif len(args.diff) == 1:
            baseline = get_baseline_run()
            candidate = args.diff[0]
            if not baseline:
                print("Error: No baseline run set. Use --set-baseline or pass two arguments to --diff.")
                sys.exit(2)
        else:
            baseline = args.diff[0]
            candidate = args.diff[1]
            
        try:
            summary = diff_runs(baseline, candidate)
            print_diff_report(baseline, candidate, summary)
        except Exception as e:
            print(f"Error generating diff: {e}")
            sys.exit(2)
        return
        
    if args.score:
        score_run(args.score, args.deterministic_only, args.judge_only)
        return
        
    if not args.agent:
        parser.error("--agent is required if not scoring an existing run")
        
    commit_hash = args.commit if args.commit else get_git_commit()
    
    try:
        run_id = run_suite(args.agent, commit_hash)
        if args.auto_score:
            score_run(run_id)
    except Exception as e:
        print(f"Fatal Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
