import json
import os
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI
from harness.db import insert_score

class JudgeScore(BaseModel):
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    reason: str
    criteria_met: list[str]
    criteria_missed: list[str]

def run_llm_judge(run_id: str, tc: dict, raw_output: str, deterministic_passed: bool) -> tuple[int, float]:
    scorer_type = "llm_judge"
    scorer_version = "judge_claude-haiku_v1"
    
    if not deterministic_passed:
        # Runs only on cases where deterministic scored passed=1.
        return 0, 0.0

    api_key = os.environ.get("OPENAI_API_KEY", "")
    
    # We use OpenRouter to access Claude Haiku
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://github.com/google-deepmind/antigravity",
            "X-Title": "Autonomous Research Agent Eval Harness"
        }
    )
    
    prompt = f"""You are an expert judge evaluating the output of an AI agent.
Evaluate the following output against the expected criteria.

Input Prompt: {tc.get('input_prompt')}
Expected Criteria: {tc.get('expected_criteria')}
Agent Output: {raw_output}

Output your evaluation as a JSON object matching this schema:
{{
    "passed": boolean,
    "score": float between 0.0 and 1.0,
    "reason": "one paragraph justification",
    "criteria_met": ["list of specific criteria satisfied"],
    "criteria_missed": ["list of specific criteria not satisfied"]
}}
"""

    total_tokens = 0
    total_cost = 0.0
    
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model="anthropic/claude-3-haiku",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            raw_response_text = response.choices[0].message.content
            
            usage = getattr(response, "usage", None)
            if usage:
                iter_tokens = getattr(usage, "total_tokens", 0) or 0
                iter_cost = getattr(usage, "cost", None) or 0.0
                total_tokens += iter_tokens
                total_cost += iter_cost
            
            json_text = raw_response_text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()
                
            json_text = json_text.strip()
            if json_text.startswith("{") and not json_text.endswith("}"):
                json_text += "}"
                
            try:
                data = json.loads(json_text)
                judge_score = JudgeScore(**data)
            except (json.JSONDecodeError, ValidationError) as e:
                if attempt == 0:
                    continue
                else:
                    insert_score(run_id, tc['id'], scorer_type, scorer_version, None, None, f"scorer_error: judge_returned_malformed_json ({e})", raw_response_text)
                    return total_tokens, total_cost
            
            insert_score(
                run_id, tc['id'], scorer_type, scorer_version, 
                judge_score.passed, judge_score.score, judge_score.reason, 
                json.dumps(data)
            )
            return total_tokens, total_cost
            
        except Exception as e:
            if attempt == 0:
                continue
            insert_score(run_id, tc['id'], scorer_type, scorer_version, None, None, f"scorer_error: API failure ({e})")
            return total_tokens, total_cost

    return total_tokens, total_cost
