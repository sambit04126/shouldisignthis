import asyncio
import os
import sys
import json
import pytest
from reportlab.pdfgen import canvas
from google.genai import types
from google.adk.apps.app import App
from google.adk.runners import Runner
from google.adk.plugins.logging_plugin import LoggingPlugin

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shouldisignthis.agents.auditor import get_auditor_agent
from shouldisignthis.database import get_session_service
from shouldisignthis.config import configure_logging

# Setup
configure_logging()
OUTPUT_DIR = "test_output"

def create_sample_contract(filename):
    c = canvas.Canvas(filename)
    c.drawString(100, 800, "INDEPENDENT CONTRACTOR AGREEMENT")
    c.drawString(100, 780, "This Agreement is made between Alice (Client) and Bob (Contractor).")
    c.drawString(100, 760, "1. Services: Contractor shall provide coding services.")
    c.drawString(100, 740, "2. Payment: Client shall pay $100 per hour, Net 30.")
    c.drawString(100, 720, "3. Termination: Either party may terminate with 14 days notice.")
    c.drawString(100, 700, "4. Liability: Liability is limited to $5,000.")
    c.drawString(100, 680, "5. IP: Client owns all work product.")
    c.drawString(100, 660, "Signed: ____________________")
    c.save()
    print(f"📄 Created sample contract: {filename}")

@pytest.mark.asyncio
async def test_auditor():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    pdf_path = os.path.join(OUTPUT_DIR, "sample_contract.pdf")
    create_sample_contract(pdf_path)
    
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()
        
    print("\n🤖 Running Auditor Agent...")
    
    # Create App & Runner
    app = App(name="Auditor_Test", root_agent=get_auditor_agent(), plugins=[LoggingPlugin()])
    runner = Runner(app=app, session_service=get_session_service())
    
    # Create Session
    import uuid
    session_id = str(uuid.uuid4())
    user_id = "test_user"
    await get_session_service().create_session(app_name="Auditor_Test", user_id=user_id, session_id=session_id, state={})
    
    # Input Message
    msg = types.Content(
        role="user", 
        parts=[
            types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"),
            types.Part(text="Analyze this contract.")
        ]
    )
    
    # Run
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
        pass
        
    # Get Result
    session = await get_session_service().get_session(app_name="Auditor_Test", user_id=user_id, session_id=session_id)
    output = session.state.get('auditor_output')
    
    print("\n✅ Auditor Output:")
    print(output)
    
    # Save Output
    output_path = os.path.join(OUTPUT_DIR, "auditor_output.json")
    with open(output_path, "w") as f:
        # Check if output is a Pydantic model or dict
        if hasattr(output, "model_dump"):
            json.dump(output.model_dump(), f, indent=2)
        elif isinstance(output, str):
             f.write(output)
        else:
            json.dump(output, f, indent=2)
            
    print(f"💾 Output saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(test_auditor())
