import asyncio
import os
import sys
import json
import uuid
import time
import pytest
from google.genai import types
from google.adk.apps.app import App
from google.adk.runners import Runner
from google.adk.plugins.logging_plugin import LoggingPlugin

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shouldisignthis.agents.debate_team import get_debate_team
from shouldisignthis.database import session_service
from shouldisignthis.config import configure_logging

# Setup
configure_logging()
OUTPUT_DIR = "test_output"

@pytest.mark.asyncio
async def test_debate():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Mock Fact Sheet (from Stage 1)
    fact_sheet = {
        "parties": { "value": "Alice (Client) and Bob (Contractor)", "page": 1, "confidence": "HIGH" },
        "payment_terms": { "value": "Client shall pay $100 per hour, Net 30.", "page": 1, "confidence": "HIGH" },
        "liability_cap": { "value": "Liability is limited to $5,000.", "page": 1, "confidence": "HIGH" },
        "termination_clause": { "value": "Either party may terminate with 14 days notice.", "page": 1, "confidence": "HIGH" },
        "intellectual_property": { "value": "Client owns all work product.", "page": 1, "confidence": "HIGH" },
        "non_compete_clause": { "value": "NOT FOUND", "page": 1, "confidence": "LOW" }
    }
    
    print("\n🤖 Running Debate Team (Skeptic & Advocate)...")
    print(f"📋 Input Fact Sheet: {json.dumps(fact_sheet, indent=2)}")
    
    # Create App & Runner
    app = App(name="Debate_Test", root_agent=get_debate_team(), plugins=[LoggingPlugin()])
    runner = Runner(app=app, session_service=session_service)
    
    # Create Session
    session_id = str(uuid.uuid4())
    user_id = "test_user"
    await session_service.create_session(app_name="Debate_Test", user_id=user_id, session_id=session_id, state={})
    
    # Input Message
    prompt = f"""
    FACT SHEET:
    {json.dumps(fact_sheet, indent=2)}

    Analyze these contract terms.
    """
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    
    # Run
    start_time = time.time()
    try:
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
            # print(f"Event: {event}") # Debug print
            pass
    except Exception as e:
        print(f"⚠️ Runner Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    duration = time.time() - start_time
    print(f"⏱️ Execution Time: {duration:.2f}s")
        
    # Get Result
    session = await session_service.get_session(app_name="Debate_Test", user_id=user_id, session_id=session_id)
    
    # Extract Outputs
    skeptic_risks = session.state.get('skeptic_risks')
    advocate_defense = session.state.get('advocate_defense')
    
    # Parse if string
    if isinstance(skeptic_risks, str):
        try:
            skeptic_risks = json.loads(skeptic_risks.replace("```json", "").replace("```", "").strip())
        except: pass
        
    if isinstance(advocate_defense, str):
        try:
            advocate_defense = json.loads(advocate_defense.replace("```json", "").replace("```", "").strip())
        except: pass

    print("\n😠 Skeptic Output:")
    print(json.dumps(skeptic_risks, indent=2))
    
    print("\n🛡️ Advocate Output:")
    print(json.dumps(advocate_defense, indent=2))
    
    # Speedup Metric (Keeping this as it is useful)
    sequential_estimate = 8 + 6 # Estimated sequential time
    speedup_pct = ((sequential_estimate - duration) / sequential_estimate) * 100
    print(f"\n📊 Speedup vs sequential (est): {speedup_pct:.0f}% faster")
    
    # Save Output
    output = {
        "skeptic": skeptic_risks,
        "advocate": advocate_defense,
        "duration": duration,
        "speedup_pct": speedup_pct
    }
    output_path = os.path.join(OUTPUT_DIR, "debate_output.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
            
    print(f"💾 Output saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(test_debate())
