import asyncio
import os
import sys
import json
import uuid
import pytest
from shouldisignthis.config import configure_logging

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import App Stages
from shouldisignthis.orchestrator import (
    run_stage_1, 
    run_stage_2, 
    run_stage_2_5, 
    run_stage_3,
    parse_json
)

# Setup
configure_logging()
# PDFs are in sample_contracts/ relative to this test file
SAMPLE_CONTRACTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sample_contracts'))
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../test_output/edge_case_results'))

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

async def run_pipeline_on_file(filename):
    pdf_path = os.path.join(SAMPLE_CONTRACTS_DIR, filename)
    print(f"\n🧪 Testing: {filename}")
    
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return None

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    user_id = "edge_tester"
    session_id = str(uuid.uuid4())
    
    # 1. Auditor
    print("  Running Auditor...")
    auditor_out = await run_stage_1(pdf_bytes, "application/pdf", user_id, session_id)
    if not auditor_out or not auditor_out.get("is_contract"):
        print(f"  ❌ Auditor Rejected: {auditor_out}")
        return { "filename": filename, "status": "REJECTED_BY_AUDITOR", "details": auditor_out }

    fact_sheet = auditor_out.get("fact_sheet")
    full_text = auditor_out.get("full_text")
    
    # 2. Debate
    print("  Running Debate...")
    stage2_state, _ = await run_stage_2(user_id, session_id, fact_sheet)
    skeptic_risks = parse_json(stage2_state.get('skeptic_risks'))
    advocate_defense = parse_json(stage2_state.get('advocate_defense'))
    
    # 2.5 Bailiff
    print("  Running Bailiff...")
    risks = skeptic_risks.get('risks', []) if skeptic_risks else []
    counters = advocate_defense.get('counters', []) if advocate_defense else []
    validated_evidence = await run_stage_2_5(user_id, session_id, risks, counters, full_text)
    
    # 3. Judge
    print("  Running Judge...")
    verdict = await run_stage_3(user_id, session_id, fact_sheet, validated_evidence)
    
    print(f"  👨‍⚖️ Verdict: {verdict.get('verdict')} (Score: {verdict.get('risk_score')})")
    
    result = {
        "filename": filename,
        "auditor": auditor_out,
        "skeptic": skeptic_risks,
        "verdict": verdict
    }
    
    # Save individual result
    with open(os.path.join(OUTPUT_DIR, f"result_{filename}.json"), "w") as f:
        json.dump(result, f, indent=2)
        
    return result

@pytest.mark.asyncio
async def test_edge_cases():
    # List of all edge cases to verify
    files = [
        "poison_ignore_instructions.pdf",
        "perfect_contract.pdf",
        "slave_contract.pdf",
        "ambiguous_contract.pdf",
        "balanced_contract.pdf",
        "complex_contract.pdf"
    ]
    
    results = {}
    for f in files:
        results[f] = await run_pipeline_on_file(f)
        
    # Summary
    print("\n--- EDGE CASE SUMMARY ---")
    for fname, res in results.items():
        if not res:
            print(f"❌ {fname}: Failed to run")
            continue
            
        verdict = res.get("verdict", {}).get("verdict", "UNKNOWN")
        score = res.get("verdict", {}).get("risk_score", "N/A")
        print(f"📄 {fname}: {verdict} (Risk: {score})")

if __name__ == "__main__":
    asyncio.run(test_edge_cases())
