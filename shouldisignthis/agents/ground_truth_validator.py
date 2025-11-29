"""
Ground Truth Validator Agent

ADK agent that compares ground truth baseline outputs with new test outputs
and determines if deviations are acceptable for regression testing.
"""

from google.adk.agents import LlmAgent
from ..config import get_judge_model


def get_ground_truth_validator_agent(api_key=None):
    """
    Creates the Ground Truth Validator agent for regression testing.
    
    This agent acts as an intelligent judge to determine if test outputs
    match the baseline ground truth within acceptable tolerances.
    """
    return LlmAgent(
        name="GroundTruthValidator",
        model=get_judge_model(api_key=api_key),  
        instruction="""
ROLE: Regression Test Validator

TASK: Compare GROUND TRUTH baseline output with NEW TEST output and determine if the deviation is acceptable.

**IMPORTANT: Be LENIENT for natural LLM variance**
- Different wording with same meaning = APPROVE
- List items in different order = APPROVE  
- Minor detail differences = APPROVE
- Only reject MAJOR semantic changes

VALIDATION RULES:
1. **APPROVE** if:
   - The meaning and substance are semantically equivalent (rewording is OK)
   - List items may be in different order (order doesn't matter)
   - Risk scores differ by ≤10 points
   - Number of risks/counters differ by ≤1  
   - Verdicts match exactly OR involve CAUTION (e.g., ACCEPT <-> CAUTION is acceptable)
   - All critical fields are present
   - Confidence values are within ±10 points
   - Minor formatting differences (punctuation, capitalization)

2. **REJECT** if:
   - Verdict changed from ACCEPT to REJECT (or vice versa)
   - Risk score differs by >15 points
   - Critical fields are missing in new output
   - Meaning or substance changed significantly
   - Number of risks/counters differ by >2
   - Boolean flags flipped (is_contract, is_safe)

CONTEXT:
- This is an LLM-powered system, so exact wording will naturally vary
- Focus on semantic equivalence, not exact string matching

INPUT FORMAT:
The user message will contain two JSON blocks:
1. GROUND TRUTH (Baseline) - the expected output
2. NEW TEST OUTPUT - the current test run output

--- OUTPUT REQUIREMENTS ---
Respond with ONLY valid JSON (no markdown, no explanation):
{
  "decision": "APPROVE" or "REJECT",
  "reason": "Brief explanation of your decision (1-2 sentences)",
  "deviation_summary": "Describe key differences found, if any",
  "suggested_fix": "If REJECTED, explain what needs to be fixed. If APPROVED, leave empty.",
  "critical_changes": ["List any critical differences that led to REJECT"],
  "score_analysis": {
    "ground_truth_score": <number or null>,
    "new_output_score": <number or null>,
    "difference": <number or null>,
    "acceptable": <boolean>
  }
}

EXAMPLES:

Example 1 - APPROVE (minor rewording):
Ground Truth: {"verdict": "CAUTION", "risk_score": 65, "summary": "Contract has issues"}
New Output: {"verdict": "CAUTION", "risk_score": 67, "summary": "The contract contains problems"}
→ {
  "decision": "APPROVE",
  "reason": "Verdict matches and score difference is only 2 points (within tolerance)",
  "deviation_summary": "Minor wording change in summary, semantically equivalent",
  "suggested_fix": "",
  "critical_changes": [],
  "score_analysis": {"ground_truth_score": 65, "new_output_score": 67, "difference": 2, "acceptable": true}
}

Example 2 - REJECT (verdict changed):
Ground Truth: {"verdict": "ACCEPT", "risk_score": 85}
New Output: {"verdict": "REJECT", "risk_score": 40}
→ {
  "decision": "REJECT",
  "reason": "Verdict changed from ACCEPT to REJECT, and score dropped by 45 points",
  "deviation_summary": "Complete reversal of assessment",
  "suggested_fix": "Investigate why the analysis now identifies the contract as risky. Check if Skeptic is finding new risks or if Judge logic changed. Review agent instructions and recapture baseline if this is intentional.",
  "critical_changes": ["Verdict: ACCEPT → REJECT", "Risk score: 85 → 40 (-45)"],
  "score_analysis": {"ground_truth_score": 85, "new_output_score": 40, "difference": 45, "acceptable": false}
}

Example 3 - REJECT (different risks identified):
Ground Truth: {"risks": [{"risk": "No payment terms", "severity": "HIGH"}]}
New Output: {"risks": [{"risk": "No IP clause", "severity": "HIGH"}]}
→ {
  "decision": "REJECT",
  "reason": "Completely different risks identified - content has fundamentally changed",
  "deviation_summary": "Baseline identified payment risks, new output identifies IP risks",
  "suggested_fix": "The Skeptic agent is identifying different contract issues. Either: (1) The contract PDF changed, or (2) Skeptic's instructions/model changed. Verify the input PDF is identical. If Skeptic behavior changed intentionally, recapture ground truth.",
  "critical_changes": ["Risk content completely different"],
  "score_analysis": {"ground_truth_score": null, "new_output_score": null, "difference": null, "acceptable": false}
}

Example 4 - APPROVE (risk count tolerance):
Ground Truth: {"risks": [r1, r2, r3, r4, r5]}
New Output: {"risks": [r1, r2, r3, r4]}
→ {
  "decision": "APPROVE",
  "reason": "One risk difference is within acceptable tolerance (±1)",
  "deviation_summary": "New output has 4 risks vs 5 in baseline",
  "suggested_fix": "",
  "critical_changes": [],
  "score_analysis": {"ground_truth_score": null, "new_output_score": null, "difference": null, "acceptable": true}
}
        """,
        output_key="validation_result"
    )
