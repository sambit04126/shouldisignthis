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

from shouldisignthis.agents.drafter import get_drafter_agent
from shouldisignthis.database import session_service
from shouldisignthis.config import configure_logging

# Setup
configure_logging()
OUTPUT_DIR = "test_output"

@pytest.mark.asyncio
async def test_drafter():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Mock Data (Simulating output from Judge)
    final_verdict = {
        "verdict": "ACCEPT WITH CAUTION",
        "risk_score": 82,
        "key_factors": [
            "High risk: Missing IP ownership clause.",
            "Medium risk: $5,000 liability cap."
        ],
        "negotiation_points": [
            "Request explicit IP ownership transfer clause.",
            "Ask to increase liability cap to $10,000 or clarify coverage."
        ]
    }
    
    print("\n✍️ Running Drafter Agent...")
    print(f"📋 Input Verdict: {json.dumps(final_verdict, indent=2)}")
    
    # Create App & Runner
    app = App(name="Drafter_Test", root_agent=get_drafter_agent(), plugins=[LoggingPlugin()])
    runner = Runner(app=app, session_service=session_service)
    
    # Create Session
    session_id = str(uuid.uuid4())
    user_id = "test_user"
    await session_service.create_session(
        app_name="Drafter_Test", 
        user_id=user_id, 
        session_id=session_id, 
        state={
            "final_verdict": json.dumps(final_verdict) # Store in state if needed
        }
    )
    
    # Input Message
    # The Drafter needs the verdict and negotiation points.
    prompt = f"""
    Generate a negotiation toolkit based on this verdict:
    
    Verdict: {final_verdict['verdict']}
    Risk Score: {final_verdict['risk_score']}
    
    Negotiation Points:
    {json.dumps(final_verdict['negotiation_points'], indent=2)}
    """
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    
    # Run
    start_time = time.time()
    try:
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
            # print(f"Event: {event}") 
            pass
    except Exception as e:
        print(f"⚠️ Runner Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
    duration = time.time() - start_time
    print(f"⏱️ Execution Time: {duration:.2f}s")
        
    # Get Result
    session = await session_service.get_session(app_name="Drafter_Test", user_id=user_id, session_id=session_id)
    
    # Extract Outputs
    drafted_email = session.state.get('drafted_email')
    
    # Parse if string
    if isinstance(drafted_email, str):
        try:
            drafted_email = json.loads(drafted_email.replace("```json", "").replace("```", "").strip())
        except: pass

    print("\n📧 Drafted Email:")
    print(json.dumps(drafted_email, indent=2))
    
    # Save Output
    output = {
        "drafted_email": drafted_email,
        "duration": duration
    }
    output_path = os.path.join(OUTPUT_DIR, "drafter_output.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
            
    print(f"💾 Output saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(test_drafter())
