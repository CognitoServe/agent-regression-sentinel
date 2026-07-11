# Eval Harness Architecture

The eval harness is designed as a strict pipeline with clear separations of concern: Execution, Scoring, and Diffing.

## 1. Execution Pipeline
The harness treats the agent as a black box accessed over HTTP.
1. `harness.runner.run_suite` iterates over the `golden_dataset/test_cases.json`.
2. For each test case, it dispatches the `input_prompt` via an Adapter (e.g., `ResearchAgentAdapter`) to the agent's REST API endpoint.
3. The raw JSON output and latency are persisted to the `run_results` table in `eval_harness.db`.

This decoupled execution means we can test any agent that conforms to the expected JSON output schema, provided an adapter exists.

## 2. Scoring Pipeline
Scoring is completely decoupled from execution. A run can be scored (and re-scored) without hitting the agent again.
1. The `harness.scorer` reads raw JSON from `run_results`.
2. **Deterministic Check:** Runs first. Validates structural constraints (e.g., ensuring a `ResearchReport` is valid, specific tools were called, or specific keys exist). If this fails, the test case is marked as a failure immediately.
3. **LLM Judge Check:** If the deterministic check passes, an LLM-as-judge (Claude Haiku) evaluates the semantic quality of the output against the `expected_criteria`. This prevents wasting tokens on malformed outputs.
4. Results are persisted to the `scores` table.

## 3. Diffing Pipeline
The core value of the harness is detecting regressions over time.
1. `harness.differ` compares a `candidate_run_id` against a baseline `run_id`.
2. It compares the scores table to determine if a test case:
   - Regressed (passed in baseline, failed in candidate)
   - Improved (failed in baseline, passed in candidate)
   - Dropped in score (passed both, but score dropped by > 0.1)
3. Results are saved to the `diffs` table and can be visualized in the Streamlit dashboard or parsed in CI via exit codes.
