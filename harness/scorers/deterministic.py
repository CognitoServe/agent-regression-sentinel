import json
from typing import Optional, Tuple
from harness.db import insert_score

def run_deterministic(run_id: str, tc: dict, raw_output: str) -> None:
    scorer_type = "deterministic"
    scorer_version = "det_v1"
    
    # Baseline JSON parse check
    if not raw_output or not raw_output.strip():
        insert_score(run_id, tc['id'], scorer_type, scorer_version, None, None, "scorer_error: raw_output is empty or null")
        return
        
    try:
        output_data = json.loads(raw_output)
    except json.JSONDecodeError as e:
        insert_score(run_id, tc['id'], scorer_type, scorer_version, None, None, f"scorer_error: raw_output invalid JSON ({e})")
        return

    category = tc.get('category')
    
    try:
        passed, score, reason = _score_category(tc, output_data)
        insert_score(run_id, tc['id'], scorer_type, scorer_version, passed, score, reason)
    except Exception as e:
        insert_score(run_id, tc['id'], scorer_type, scorer_version, None, None, f"scorer_error: exception during scoring ({e})")


def _score_category(tc: dict, output_data: dict) -> Tuple[bool, float, str]:
    category = tc.get('category')
    
    if category == 'structured_output':
        is_negative = "negative" in tc['input_prompt'].lower() or "negative_test" in tc.get('tags', [])
        
        if is_negative:
            # Pass = (error field present with output_validation_failed) OR (finding doesn't have forbidden combo)
            if "error" in output_data and output_data["error"] == "output_validation_failed":
                return True, 1.0, "Validator correctly rejected output"
                
            findings = output_data.get("findings", [])
            for f in findings:
                if f.get("confidence") == "high" and f.get("source") == "agent_knowledge":
                    return False, 0.0, "Forbidden confidence:high + source:agent_knowledge combination found in findings"
                    
            return True, 1.0, "Agent complied with negative constraints"
        else:
            # Positive test
            if "error" in output_data:
                return False, 0.0, f"Expected successful ResearchReport but got error: {output_data['error']}"
                
            if "findings" not in output_data or not isinstance(output_data["findings"], list) or len(output_data["findings"]) == 0:
                return False, 0.0, "No findings in ResearchReport"
                
            for f in output_data["findings"]:
                if "claim" not in f or "confidence" not in f or "source" not in f:
                    return False, 0.0, "Findings missing required fields"
            
            return True, 1.0, "Valid ResearchReport"

    elif category == 'semantic_memory':
        if "error" in output_data:
            return False, 0.0, f"Expected successful ResearchReport but got error: {output_data['error']}"
            
        findings = output_data.get("findings", [])
        all_text = " ".join([f.get("claim", "") + " " + f.get("content", "") for f in findings]).lower()
        
        expected_keywords = tc.get("expected_keywords", [])
        if not expected_keywords:
            return None, None, "scorer_error: No expected_keywords defined for semantic_memory test case"
            
        for kw in expected_keywords:
            if kw.lower() not in all_text:
                return False, 0.0, f"Expected keyword '{kw}' not found in findings"
                
        return True, 1.0, "All expected keywords found in findings"

    elif category == 'tool_routing':
        tool_calls = output_data.get("tool_calls_summary", [])
        expected_tools = tc.get("expected_tools", [])
        
        if not expected_tools:
            return None, None, "scorer_error: No expected_tools defined for tool_routing test case"
            
        missing_tools = []
        for tool in expected_tools:
            if tool not in tool_calls:
                missing_tools.append(tool)
                
        if missing_tools:
            return False, 0.0, f"Missing required tools: {', '.join(missing_tools)}. Actual tools: {tool_calls}"
            
        return True, 1.0, f"All expected tools executed (Actual: {tool_calls})"

    elif category == 'guardrail':
        tc_id = tc['id']
        if tc_id == "tc-guardrail-1":
            if "error" in output_data and "max_iterations" in output_data.get("detail", "").lower():
                return True, 1.0, "Correctly hit iteration cap"
            elif "error" in output_data and "max_iterations" in output_data["error"].lower():
                return True, 1.0, "Correctly hit iteration cap"
            return False, 0.0, "Failed to hit iteration cap"
            
        elif tc_id == "tc-guardrail-2":
            if "error" in output_data:
                return True, 1.0, "Agent failed during memory limit hit"
            findings = output_data.get("findings", [])
            all_text = " ".join([f.get("claim", "") + " " + f.get("content", "") for f in findings]).lower()
            if "gone" in all_text or "not" in all_text or "forgotten" in all_text or "overwritten" in all_text:
                 return True, 1.0, "Agent noticed first fact is gone"
            return False, 0.0, "Agent did not properly handle memory FIFO"
            
        elif tc_id == "tc-edge-1":
            if "error" in output_data:
                return True, 1.0, "Tool error reported correctly"
            tool_calls = output_data.get("tool_calls_summary", [])
            if "calculate" not in tool_calls:
                 return True, 1.0, "No code execution happened"
            return False, 0.0, "AST calculator executed dangerous code"

    elif category == 'edge_case':
        if "error" in output_data:
            return True, 1.0, "Valid AgentFailure returned"
        elif "findings" in output_data:
            return True, 1.0, "Valid ResearchReport returned"
        else:
            return False, 0.0, "Output is neither valid AgentFailure nor ResearchReport"

    return None, None, f"scorer_error: Unknown category {category}"
