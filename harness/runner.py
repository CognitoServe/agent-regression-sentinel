import json
import yaml
from pathlib import Path
from typing import Dict, Any

from harness.db import init_db, upsert_test_cases, create_run, insert_run_result
from harness.schema import TestCase

def load_config(config_path: str = "config/agents.yaml") -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def load_test_cases(dataset_path: str = "golden_dataset/test_cases.json") -> list[TestCase]:
    with open(dataset_path, "r") as f:
        data = json.load(f)
    return [TestCase(**tc) for tc in data]

def get_adapter(agent_name: str, config: dict) -> Any:
    agent_config = config.get("agents", {}).get(agent_name)
    if not agent_config:
        raise ValueError(f"Agent {agent_name} not found in config")
        
    base_url = agent_config.get("base_url")
    if not base_url:
        raise ValueError(f"Agent {agent_name} missing base_url in config")
        
    if agent_name == "research_agent":
        from harness.adapters.research_agent import ResearchAgentAdapter
        return ResearchAgentAdapter("http://127.0.0.1:8000")
    
    raise NotImplementedError(f"Adapter for {agent_name} not implemented")

def run_suite(target_agent: str, git_commit: str = "unknown"):
    print(f"Initializing DB and loading cases for {target_agent}...")
    init_db()
    config = load_config()
    test_cases = load_test_cases()
    
    # Filter for the target agent
    target_cases = [tc for tc in test_cases if tc.target_agent == target_agent]
    if not target_cases:
        print(f"No test cases found for agent: {target_agent}")
        return
        
    # Upsert test cases to DB
    upsert_test_cases([tc.model_dump() for tc in target_cases])
    
    adapter = get_adapter(target_agent, config)
    run_id = create_run(target_agent, git_commit)
    print(f"Started Run ID: {run_id}")
    print(f"Found {len(target_cases)} test cases.")
    print("-" * 50)
    
    for i, tc in enumerate(target_cases, 1):
        print(f"[{i}/{len(target_cases)}] Executing {tc.id} ({tc.category})")
        print(f"  Prompt: {tc.input_prompt[:60]}...")
        
        raw_output, latency_ms, error = adapter.execute(tc.input_prompt)
        
        if error:
            print(f"  [ERROR] {error}")
        else:
            print(f"  [DONE] {latency_ms}ms")
            
        insert_run_result(
            run_id=run_id,
            test_case_id=tc.id,
            raw_output=raw_output,
            latency_ms=latency_ms,
            error=error
        )
        
    print("-" * 50)
    print(f"Run {run_id} completed. Results saved to DB.")
    return run_id
