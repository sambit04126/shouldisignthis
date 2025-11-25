import asyncio
import os
import sys
import json
import uuid
import time
from shouldisignthis.config import configure_logging

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import App Stages
from shouldisignthis.orchestrator import (
    run_stage_1, 
    run_stage_2, 
    run_stage_2_5, 
    run_stage_3, 
    run_stage_5_comparator,
    parse_json
)

# Setup
configure_logging()
OUTPUT_DIR = "test_output"
SAMPLE_CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "sample_contracts")

async def run_pipeline(file_bytes, mime_type, user_id, session_id, label):
    """Runs Stages 1-3 for a single contract."""
    print(f"\n🚀 Starting Pipeline for: {label}")
    
    # STAGE 1: Auditor
    print(f"[{label}] 🔍 Stage 1: Auditing...")
    auditor_out = await run_stage_1(file_bytes, mime_type, user_id, session_id)
    if not auditor_out or not auditor_out.get("is_contract"):
        print(f"[{label}] ❌ Invalid Contract")
        return None
    
    fact_sheet = auditor_out.get('fact_sheet')
    full_text = auditor_out.get('full_text')

    # STAGE 2: Debate
    print(f"[{label}] ⚔️ Stage 2: Debating...")
    state, _ = await run_stage_2(user_id, session_id, fact_sheet)
    
    # STAGE 2.5: Bailiff
    print(f"[{label}] 🕵️ Stage 2.5: Verifying...")
    risks = parse_json(state.get('skeptic_risks', {})).get('risks', [])
    counters = parse_json(state.get('advocate_defense', {})).get('counters', [])
    validated_evidence = await run_stage_2_5(user_id, session_id, risks, counters, full_text)

    # STAGE 3: Judge
    print(f"[{label}] 👨‍⚖️ Stage 3: Judging...")
    verdict = await run_stage_3(user_id, session_id, fact_sheet, validated_evidence)
    print(f"[{label}] ✅ Verdict: {verdict.get('verdict')} (Score: {verdict.get('risk_score')})")
    
    return verdict

async def run_comparator_test():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print("\n🥊 Starting Comparator Integration Test...")
    
    # 1. Load Contracts
    complex_path = os.path.join(SAMPLE_CONTRACTS_DIR, "complex_contract.pdf")
    simple_path = os.path.join(SAMPLE_CONTRACTS_DIR, "sample_contract.pdf")

    if not os.path.exists(complex_path) or not os.path.exists(simple_path):
        print(f"❌ Sample contracts not found in {SAMPLE_CONTRACTS_DIR}")
        return

    with open(complex_path, "rb") as f:
        complex_bytes = f.read()
    
    with open(simple_path, "rb") as f:
        simple_bytes = f.read()

    # 2. Run Parallel Pipelines
    print("\n--- RUNNING PARALLEL PIPELINES ---")
    task_complex = run_pipeline(complex_bytes, "application/pdf", "user_complex", str(uuid.uuid4()), "COMPLEX (BAD)")
    task_simple = run_pipeline(simple_bytes, "application/pdf", "user_simple", str(uuid.uuid4()), "SIMPLE (GOOD)")
    
    verdict_complex, verdict_simple = await asyncio.gather(task_complex, task_simple)
    
    if not verdict_complex or not verdict_simple:
        print("❌ One or both pipelines failed.")
        return

    # 3. Run Comparator
    print("\n--- STAGE 5: COMPARATOR ---")
    comparison = await run_stage_5_comparator("comparator_test_user", str(uuid.uuid4()), verdict_complex, verdict_simple)
    
    print(f"\n🏆 Comparison Result:\n{json.dumps(comparison, indent=2)}")
    
    # Assertions
    if comparison:
        score_winner = comparison.get('better_risk_score')
        print(f"\n✅ Better Risk Score: {score_winner}")
        
        # We expect the Simple contract (Contract B in this call order? No, we passed complex then simple)
        # run_stage_5_comparator(..., verdict_a, verdict_b)
        # So A = Complex, B = Simple.
        # Simple should have lower risk.
        if "Contract B" in score_winner:
             print("✅ CORRECT: Contract B (Simple) identified as lower risk.")
        else:
             print("⚠️ UNEXPECTED: Contract A (Complex) identified as lower risk?")
             
    # Save Output
    output_path = os.path.join(OUTPUT_DIR, "comparator_integration_output.json")
    with open(output_path, "w") as f:
        json.dump(comparison, f, indent=2)
    print(f"\n💾 Output saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(run_comparator_test())
