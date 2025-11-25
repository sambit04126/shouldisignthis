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

from shouldisignthis.agents.judge import get_judge_agent
from shouldisignthis.database import session_service
from shouldisignthis.config import configure_logging

# Setup
configure_logging()
OUTPUT_DIR = "test_output"

@pytest.mark.asyncio
async def test_judge():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Mock Data (Simulating output from Bailiff/Clerk)
    final_arguments = {
        "risks": [
            {
                "risk": "Liability is limited to $5,000",
                "severity": "MEDIUM",
                "risk_type": "UNFAVORABLE_TERM",
                "explanation": "Liability is capped at $5,000, which may not cover all potential damages."
            },
            {
                "risk": "No IP ownership transfer specified",
                "severity": "HIGH",
                "risk_type": "MISSING_CLAUSE",
                "explanation": "Client does not own work product by default."
            }
        ],
        "counters": [
            {
                "topic": "Liability Cap",
                "counter": "The contract caps liability at $5,000, which is standard for small projects.",
                "confidence": "HIGH"
            }
        ]
    }
    
    print("\n⚖️ Running Judge Agent...")
    print(f"📋 Input Arguments: {json.dumps(final_arguments, indent=2)}")
    
    # Create App & Runner
    app = App(name="Judge_Test", root_agent=get_judge_agent(), plugins=[LoggingPlugin()])
    runner = Runner(app=app, session_service=session_service)
    
    # Create Session
    session_id = str(uuid.uuid4())
    user_id = "test_user"
    await session_service.create_session(
        app_name="Judge_Test", 
        user_id=user_id, 
        session_id=session_id, 
        state={
            "final_arguments": json.dumps(final_arguments) # Store in state if needed
        }
    )
    
    # Input Message
    # The Judge expects "Fact Sheet, Risks, and Counters" in context.
    # We'll put them in the prompt.
    prompt = f"""
    Please issue a verdict based on these arguments:
    
    Risks:
    {json.dumps(final_arguments['risks'], indent=2)}
    
    Counters:
    {json.dumps(final_arguments['counters'], indent=2)}
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
    session = await session_service.get_session(app_name="Judge_Test", user_id=user_id, session_id=session_id)
    
    # Extract Outputs
    final_verdict = session.state.get('final_verdict')
    
    # Parse if string
    if isinstance(final_verdict, str):
        try:
            final_verdict = json.loads(final_verdict.replace("```json", "").replace("```", "").strip())
        except: pass

    print("\n👨‍⚖️ Final Verdict:")
    print(json.dumps(final_verdict, indent=2))
    
    # Save Output
    output = {
        "final_verdict": final_verdict,
        "duration": duration
    }
    output_path = os.path.join(OUTPUT_DIR, "judge_output.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
            
    print(f"💾 Output saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(test_judge())
