import asyncio
import os
import sys
import json
import uuid
import argparse
from pathlib import Path

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shouldisignthis.config import configure_logging
from shouldisignthis.orchestrator import (
    run_stage_1, 
    run_stage_2, 
    run_stage_2_5, 
    run_stage_3,
    parse_json
)

configure_logging()

SAMPLE_CONTRACTS_DIR = Path(__file__).parent / "sample_contracts"
GROUND_TRUTH_DIR = Path(__file__).parent / "ground_truth"

async def capture_ground_truth(contract_name):
    print(f"\n📸 Capturing ground truth for: {contract_name}")
    
    pdf_path = SAMPLE_CONTRACTS_DIR / f"{contract_name}.pdf"
    if not pdf_path.exists():
        print(f"❌ Contract PDF not found: {pdf_path}")
        return

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    user_id = f"gt_capture_{uuid.uuid4()}"
    session_id = str(uuid.uuid4())
    
    # Output directory
    output_dir = GROUND_TRUTH_DIR / contract_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Stage 1: Auditor ---
    print("  Running Auditor...")
    auditor_out = await run_stage_1(pdf_bytes, "application/pdf", user_id, session_id)
    with open(output_dir / "auditor_output.json", "w") as f:
        json.dump(auditor_out, f, indent=2)

    if not auditor_out.get("is_contract"):
        print("  ⚠️ Document rejected by Auditor. Stopping.")
        return

    fact_sheet = auditor_out.get("fact_sheet")
    full_text = auditor_out.get("full_text")

    # --- Stage 2: Debate ---
    print("  Running Debate Team...")
    stage2_state, _ = await run_stage_2(user_id, session_id, fact_sheet)
    
    skeptic_risks = parse_json(stage2_state.get('skeptic_risks'))
    advocate_defense = parse_json(stage2_state.get('advocate_defense'))
    
    with open(output_dir / "skeptic_risks.json", "w") as f:
        json.dump(skeptic_risks, f, indent=2)
    with open(output_dir / "advocate_defense.json", "w") as f:
        json.dump(advocate_defense, f, indent=2)

    # --- Stage 2.5: Bailiff ---
    print("  Running Bailiff...")
    risks = skeptic_risks.get('risks', [])
    counters = advocate_defense.get('counters', [])
    validated_evidence = await run_stage_2_5(user_id, session_id, risks, counters, full_text)
    
    with open(output_dir / "validated_evidence.json", "w") as f:
        json.dump(validated_evidence, f, indent=2)

    # --- Stage 3: Judge ---
    print("  Running Judge...")
    verdict = await run_stage_3(user_id, session_id, fact_sheet, validated_evidence)
    
    with open(output_dir / "final_verdict.json", "w") as f:
        json.dump(verdict, f, indent=2)
        
    # Metadata
    metadata = {
        "contract_name": contract_name,
        "capture_timestamp": str(uuid.uuid4()), # Placeholder or actual time
        "model_version": "gemini-2.5-pro" # Or read from config
    }
    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Ground truth captured in: {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture ground truth baselines.")
    parser.add_argument("--contract", type=str, help="Name of the contract (without .pdf)")
    parser.add_argument("--all", action="store_true", help="Capture for all sample contracts")
    
    args = parser.parse_args()
    
    if args.contract:
        asyncio.run(capture_ground_truth(args.contract))
    elif args.all:
        for pdf_file in SAMPLE_CONTRACTS_DIR.glob("*.pdf"):
            asyncio.run(capture_ground_truth(pdf_file.stem))
    else:
        parser.print_help()
