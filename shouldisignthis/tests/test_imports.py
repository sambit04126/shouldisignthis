import sys
import os

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from shouldisignthis.config import get_auditor_model
    print("✅ Config imported")
    
    from shouldisignthis.database import get_session_service
    print("✅ Database imported")
    
    from shouldisignthis.agents.auditor import get_auditor_agent
    print("✅ Auditor Agent imported")
    
    from shouldisignthis.agents.debate_team import get_debate_team
    print("✅ Debate Team Agent imported")
    
    from shouldisignthis.agents.bailiff import get_citation_loop
    print("✅ Bailiff Agent imported")
    
    from shouldisignthis.agents.judge import get_judge_agent
    print("✅ Judge Agent imported")
    
    from shouldisignthis.agents.drafter import get_drafter_agent
    print("✅ Drafter Agent imported")
    
    print("🎉 All imports successful!")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)
