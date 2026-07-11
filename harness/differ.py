import uuid
from harness.db import get_run_scores, insert_diff

def diff_runs(baseline_run_id: str, candidate_run_id: str) -> dict:
    baseline_scores = get_run_scores(baseline_run_id)
    candidate_scores = get_run_scores(candidate_run_id)
    
    # Map (test_case_id, scorer_type) to score dict
    b_map = {(s['test_case_id'], s['scorer_type']): s for s in baseline_scores}
    c_map = {(s['test_case_id'], s['scorer_type']): s for s in candidate_scores}
    
    all_keys = set(b_map.keys()).union(set(c_map.keys()))
    
    diff_id = str(uuid.uuid4())
    
    summary = {
        'diff_id': diff_id,
        'regressions': [],
        'improvements': [],
        'score_drops': [],
        'unchanged': [],
        'unmeasurable': [],
        'new_or_removed': []
    }
    
    for key in all_keys:
        tc_id, scorer_type = key
        b = b_map.get(key)
        c = c_map.get(key)
        
        if not b or not c:
            summary['new_or_removed'].append({
                'test_case_id': tc_id,
                'scorer_type': scorer_type,
                'status': 'removed' if b else 'new'
            })
            continue
            
        b_pass = b['passed']
        c_pass = c['passed']
        b_score = b['score']
        c_score = c['score']
        
        verdict = "unchanged"
        
        if b_pass is None or c_pass is None:
            verdict = "unmeasurable"
        elif b_pass == 1 and c_pass == 0:
            verdict = "regression"
        elif b_pass == 0 and c_pass == 1:
            verdict = "improvement"
        elif b_score is not None and c_score is not None and (b_score - c_score > 0.1):
            verdict = "score_drop"
            
        insert_diff(
            diff_id=diff_id,
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            test_case_id=tc_id,
            scorer_type=scorer_type,
            baseline_passed=b_pass,
            candidate_passed=c_pass,
            baseline_score=b_score,
            candidate_score=c_score,
            verdict=verdict
        )
        
        record = {
            'test_case_id': tc_id,
            'scorer_type': scorer_type,
            'b_pass': b_pass,
            'c_pass': c_pass,
            'b_score': b_score,
            'c_score': c_score
        }
        
        if verdict == 'regression':
            summary['regressions'].append(record)
        elif verdict == 'improvement':
            summary['improvements'].append(record)
        elif verdict == 'score_drop':
            summary['score_drops'].append(record)
        elif verdict == 'unmeasurable':
            summary['unmeasurable'].append(record)
        elif verdict == 'unchanged':
            summary['unchanged'].append(record)
            
    return summary
