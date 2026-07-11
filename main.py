import argparse
import sys
import subprocess
from harness.runner import run_suite

def get_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except Exception:
        return "unknown"

def main():
    parser = argparse.ArgumentParser(description="LLM Evaluation & Regression Testing Platform")
    parser.add_argument("--agent", type=str, required=True, help="Target agent to run the suite against (e.g., research_agent)")
    parser.add_argument("--commit", type=str, default="", help="Git commit or version tag for this run")
    
    args = parser.parse_args()
    commit_hash = args.commit if args.commit else get_git_commit()
    
    try:
        run_suite(args.agent, commit_hash)
    except Exception as e:
        print(f"Fatal Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
