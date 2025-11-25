import json
from google.adk.tools import FunctionTool

def assess_contract_risk(risks_json: str, counters_json: str):
    """
    Calculates the quantitative risk score based on risks and counters.
    
    Args:
        risks_json: A JSON string representing the list of Risk objects.
        counters_json: A JSON string representing the list of Counter objects.
    """
    # Parse the JSON strings back into lists
    try:
        risks = json.loads(risks_json)
        counters = json.loads(counters_json)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON string provided to tool."}

    print(f"   🧮 TOOL CALL: Calculating score for {len(risks)} risks...")
    
    base_score = 100
    risk_weights = {
        'HIGH': {'uncountered': -15, 'weak_counter': -10, 'strong_counter': -5},
        'MEDIUM': {'uncountered': -8, 'weak_counter': -4, 'strong_counter': -2},
        'LOW': {'uncountered': -3, 'weak_counter': -1, 'strong_counter': 0}
    }
    
    breakdown = []
    
    # Helper to find strength
    def get_strength(risk_topic):
        if not counters: return 'uncountered'
        for c in counters:
            # Fuzzy match topic
            if c.get('topic', '').lower() in risk_topic.lower():
                return 'strong_counter' if c.get('confidence') == 'HIGH' else 'weak_counter'
        return 'uncountered'

    for risk in risks:
        # Check for Missing Clause Penalty (-10 flat)
        if risk.get('risk_type') == 'MISSING_CLAUSE':
            penalty = -10
            reason = "Missing Clause"
        else:
            severity = risk.get('severity', 'MEDIUM')
            strength = get_strength(risk.get('risk', ''))
            penalty = risk_weights.get(severity, risk_weights['MEDIUM']).get(strength, -5)
            reason = f"{severity} ({strength})"
            
        base_score += penalty
        breakdown.append(f"{risk.get('risk')}: {penalty} pts [{reason}]")
        
    final_score = max(0, min(100, base_score))
    
    # Confidence Calc
    evidence_count = len(risks) + len(counters)
    confidence = min(100, 80 + min(20, evidence_count * 2))
    
    # Heuristic Verdict
    if final_score >= 85: verdict = "ACCEPT"
    elif final_score >= 70: verdict = "ACCEPT WITH CAUTION"
    else: verdict = "REJECT"
    
    return {
        "calculated_score": final_score,
        "calculated_confidence": confidence,
        "recommended_verdict": verdict,
        "breakdown": breakdown
    }

# Wrap as ADK Tool
risk_tool = FunctionTool(assess_contract_risk)
