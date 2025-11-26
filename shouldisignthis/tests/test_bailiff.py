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

from shouldisignthis.agents.bailiff import get_citation_loop
from shouldisignthis.database import get_session_service
from shouldisignthis.config import configure_logging

# Setup
configure_logging()
OUTPUT_DIR = "test_output"

@pytest.mark.asyncio
async def test_bailiff():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Mock Data
    full_text = "INDEPENDENT CONTRACTOR AGREEMENT\nThis Agreement is made between Alice (Client) and Bob (Contractor).\n1. Services: Contractor shall provide coding services.\n2. Payment: Client shall pay $100 per hour, Net 30.\n3. Termination: Either party may terminate with 14 days notice.\n4. Liability: Liability is limited to $5,000.\n5. IP: Client owns all work product.\nSigned:"
    
    current_arguments = {
        "risks": [
            {
                "risk": "Liability is unlimited", # <--- CONTRADICTION (Text says $5,000)
                "severity": "HIGH",
                "risk_type": "UNFAVORABLE_TERM",
                "explanation": "Unlimited liability exposes contractor to high risk."
            }
        ],
        "counters": [
            {
                "topic": "Liability Cap",
                "counter": "The contract caps liability at $5,000.", # <--- ACCURATE
                "confidence": "HIGH"
            },
            {
                 "topic": "Payment",
                 "counter": "The contract says payment is Net 90.", # <--- HALLUCINATION (Text says Net 30)
                 "confidence": "MEDIUM"
            }
        ]
    }
    
    print("\n👮 Running Bailiff Loop (Fact Checker)...")
    print(f"📜 Contract Text: {full_text}")
    print(f"📋 Input Arguments: {json.dumps(current_arguments, indent=2)}")
    
    # Create App & Runner
    app = App(name="Bailiff_Test", root_agent=get_citation_loop(), plugins=[LoggingPlugin()])
    runner = Runner(app=app, session_service=get_session_service())
    
    # Create Session
    session_id = str(uuid.uuid4())
    user_id = "test_user"
    await get_session_service().create_session(
        app_name="Bailiff_Test", 
        user_id=user_id, 
        session_id=session_id, 
        state={
            "full_text": full_text,
            "current_arguments": json.dumps(current_arguments, indent=2)
        }
    )
    
    # Input Message
    # The Bailiff expects {{full_text}} and {{current_arguments}} in the input
    # We can pass them as part of the user message or rely on prompt template substitution if configured.
    # Looking at agents/bailiff.py, inputs are {{full_text}} and {{current_arguments}}.
    # The ADK usually handles this via state or message history.
    # We'll pass them in the prompt for simplicity, or set them in state if the agent reads from state.
    # The instruction uses {{variable}}, which implies prompt template substitution from state/input.
    # Let's try putting them in the prompt explicitly to be safe.
    
    prompt = f"""
    Evidence: {full_text}
    
    Current Arguments:
    {json.dumps(current_arguments, indent=2)}
    
    Verify these arguments.
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
    session = await get_session_service().get_session(app_name="Bailiff_Test", user_id=user_id, session_id=session_id)
    
    # Extract Outputs
    # The Clerk updates 'current_arguments' if dirty.
    final_arguments = session.state.get('current_arguments')
    bailiff_verdict = session.state.get('bailiff_verdict')
    
    # Parse if string
    if isinstance(final_arguments, str):
        try:
            final_arguments = json.loads(final_arguments.replace("```json", "").replace("```", "").strip())
        except: pass
        
    if isinstance(bailiff_verdict, str):
        try:
            bailiff_verdict = json.loads(bailiff_verdict.replace("```json", "").replace("```", "").strip())
        except: pass

    print("\n⚖️ Bailiff Verdict:")
    print(json.dumps(bailiff_verdict, indent=2))
    
    print("\n📝 Final Arguments (Clerk Output):")
    print(json.dumps(final_arguments, indent=2))
    
    # Save Output
    output = {
        "bailiff_verdict": bailiff_verdict,
        "final_arguments": final_arguments,
        "duration": duration
    }
    output_path = os.path.join(OUTPUT_DIR, "bailiff_output.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
            
    print(f"💾 Output saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(test_bailiff())
