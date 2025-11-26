import asyncio
import os
import sys
import pytest
import uuid
from shouldisignthis.config import configure_logging
from shouldisignthis.orchestrator import (
    run_stage_1, 
    run_stage_2, 
    run_stage_2_5, 
    run_stage_3,
    run_stage_5_arbiter,
    parse_json
)

# Setup
configure_logging()
SAMPLE_CONTRACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sample_contracts'))
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../test_output/comparator_results'))

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

async def run_single_contract_pipeline(filename, user_id, session_id):
    pdf_path = os.path.join(SAMPLE_CONTRACTS_DIR, filename)
    if not os.path.exists(pdf_path):
        pytest.fail(f"File not found: {pdf_path}")

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    print(f"  Running Pipeline for {filename}...")
    
    # Stage 1
    auditor_out = await run_stage_1(pdf_bytes, "application/pdf", user_id, session_id)
    assert auditor_out and auditor_out.get("is_contract"), f"Auditor rejected {filename}"
    
    # Check for Safety Flag
    if auditor_out.get("is_safe") is False:
        print(f"  ⚠️ {filename} flagged as UNSAFE by Auditor. Returning synthetic REJECT verdict.")
        return {
            "verdict": "REJECT",
            "risk_score": 0, # 0 = Maximum Risk
            "confidence": 100,
            "summary": f"The document was flagged as unsafe or illegal by the Auditor. Reason: {auditor_out.get('safety_reason', 'Unknown')}",
            "key_factors": ["Illegal/Unsafe Content"],
            "negotiation_points": ["Do not sign."]
        }

    fact_sheet = auditor_out.get("fact_sheet")
    full_text = auditor_out.get("full_text")

    # Stage 2
    stage2_state, _ = await run_stage_2(user_id, session_id, fact_sheet)
    skeptic_risks = parse_json(stage2_state.get('skeptic_risks'))
    advocate_defense = parse_json(stage2_state.get('advocate_defense'))

    # Stage 2.5
    risks = skeptic_risks.get('risks', []) if skeptic_risks else []
    counters = advocate_defense.get('counters', []) if advocate_defense else []
    validated_evidence = await run_stage_2_5(user_id, session_id, risks, counters, full_text)

    # Stage 3
    verdict = await run_stage_3(user_id, session_id, fact_sheet, validated_evidence)
    return verdict

@pytest.mark.asyncio
async def test_comparator_perfect_vs_slave():
    print("\n🥊 Starting Face-Off: Perfect vs Slave Contract")
    
    session_id_a = str(uuid.uuid4())
    session_id_b = str(uuid.uuid4())
    
    # Run pipelines in parallel
    task_a = run_single_contract_pipeline("perfect_contract.pdf", "user_perfect", session_id_a)
    task_b = run_single_contract_pipeline("slave_contract.pdf", "user_slave", session_id_b)
    
    verdict_a, verdict_b = await asyncio.gather(task_a, task_b)
    
    print(f"  Contract A (Perfect) Verdict: {verdict_a.get('verdict')} (Score: {verdict_a.get('risk_score')})")
    print(f"  Contract B (Slave) Verdict: {verdict_b.get('verdict')} (Score: {verdict_b.get('risk_score')})")
    
    # Run Comparator
    print("  ⚖️ Running Comparator...")
    comparator_result = await run_stage_5_arbiter(
        "comparator_tester", 
        str(uuid.uuid4()), 
        verdict_a, 
        verdict_b
    )
    
    print("  ✅ Comparator Result Received")
    print(f"  Summary: {comparator_result.get('comparison_summary')}")
    
    # Assertions
    assert comparator_result is not None
    assert "comparison_summary" in comparator_result
    assert len(comparator_result.get("key_differences", [])) > 0
    
    # Check if it correctly identified the nuance (optional, but good for verification)
    # We expect it to discuss the extreme nature of both.
    
    import json
    with open(os.path.join(OUTPUT_DIR, "perfect_vs_slave_comparison.json"), "w") as f:
        json.dump(comparator_result, f, indent=2)

if __name__ == "__main__":
    asyncio.run(test_comparator_perfect_vs_slave())
