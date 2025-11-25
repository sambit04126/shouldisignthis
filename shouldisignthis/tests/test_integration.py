import asyncio
import os
import sys
import json
import uuid
import time
from io import BytesIO
from reportlab.pdfgen import canvas
from shouldisignthis.config import configure_logging

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import App Stages
from shouldisignthis.app import (
    run_stage_1, 
    run_stage_2, 
    run_stage_2_5, 
    run_stage_3, 
    run_stage_4,
    parse_json
)

# Setup
configure_logging()
OUTPUT_DIR = "test_output"

def generate_mock_contract():
    """Generates a simple PDF contract for testing."""
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "FREELANCE SERVICES AGREEMENT")
    p.drawString(100, 780, "This Agreement is made between Client Inc. and Freelancer Joe.")
    p.drawString(100, 760, "1. Services: Python Development.")
    p.drawString(100, 740, "2. Payment: $100/hr, Net 60 terms.") # Unfavorable
    p.drawString(100, 720, "3. Termination: 30 days notice.")
    p.drawString(100, 700, "4. Liability: Capped at $1,000.") # Low cap
    p.drawString(100, 680, "5. IP: Client owns all work product immediately.")
    p.drawString(100, 660, "Signed: ____________________")
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer.getvalue()

async def test_integration():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print("\n🚀 Starting Integration Test (End-to-End Pipeline)...")
    
    # 0. Generate Contract
    pdf_bytes = generate_mock_contract()
    user_id = "integration_test_user"
    session_id = str(uuid.uuid4())
    print(f"📄 Generated Mock Contract ({len(pdf_bytes)} bytes)")
    
    # 1. STAGE 1: Auditor
    print("\n--- STAGE 1: AUDITOR ---")
    start = time.time()
    auditor_out = await run_stage_1(pdf_bytes, "application/pdf", user_id, session_id)
    print(f"⏱️ Stage 1 Time: {time.time() - start:.2f}s")
    
    if not auditor_out or not auditor_out.get("is_contract"):
        print("❌ Stage 1 Failed: Document rejected or parsing error.")
        return
        
    fact_sheet = auditor_out.get("fact_sheet")
    full_text = auditor_out.get("full_text")
    print(f"✅ Fact Sheet Extracted: {json.dumps(fact_sheet, indent=2)}")
    
    # 2. STAGE 2: Debate Team
    print("\n--- STAGE 2: DEBATE TEAM ---")
    start = time.time()
    stage2_state, duration = await run_stage_2(user_id, session_id, fact_sheet)
    print(f"⏱️ Stage 2 Time: {duration:.2f}s")
    
    skeptic_risks = parse_json(stage2_state.get('skeptic_risks'))
    advocate_defense = parse_json(stage2_state.get('advocate_defense'))
    
    print(f"😠 Skeptic Risks: {len(skeptic_risks.get('risks', [])) if skeptic_risks else 0}")
    print(f"🛡️ Advocate Counters: {len(advocate_defense.get('counters', [])) if advocate_defense else 0}")
    
    # 3. STAGE 2.5: Bailiff
    print("\n--- STAGE 2.5: BAILIFF LOOP ---")
    start = time.time()
    risks = skeptic_risks.get('risks', []) if skeptic_risks else []
    counters = advocate_defense.get('counters', []) if advocate_defense else []
    
    validated_evidence = await run_stage_2_5(user_id, session_id, risks, counters, full_text)
    print(f"⏱️ Stage 2.5 Time: {time.time() - start:.2f}s")
    print(f"✅ Validated Evidence: {json.dumps(validated_evidence, indent=2)}")
    
    # 4. STAGE 3: Judge
    print("\n--- STAGE 3: JUDGE ---")
    start = time.time()
    verdict = await run_stage_3(user_id, session_id, fact_sheet, validated_evidence)
    print(f"⏱️ Stage 3 Time: {time.time() - start:.2f}s")
    print(f"👨‍⚖️ Verdict: {verdict.get('verdict')} (Score: {verdict.get('risk_score')})")
    
    # 5. STAGE 4: Drafter
    print("\n--- STAGE 4: DRAFTER ---")
    start = time.time()
    tone = "Professional"
    toolkit = await run_stage_4(user_id, session_id, verdict, tone)
    print(f"⏱️ Stage 4 Time: {time.time() - start:.2f}s")
    print(f"📧 Drafted Email Subject: {toolkit.get('email_subject')}")
    
    # Save Final Output
    final_output = {
        "fact_sheet": fact_sheet,
        "skeptic": skeptic_risks,
        "advocate": advocate_defense,
        "evidence": validated_evidence,
        "verdict": verdict,
        "toolkit": toolkit
    }
    output_path = os.path.join(OUTPUT_DIR, "integration_output.json")
    with open(output_path, "w") as f:
        json.dump(final_output, f, indent=2)
    print(f"\n💾 Full Integration Output saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(test_integration())
