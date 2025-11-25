from google.adk.agents import LlmAgent
from ..config import JUDGE_MODEL
from ..tools.risk_calculator import risk_tool

# --- THE JUDGE AGENT ---
judge_agent = LlmAgent(
    name="Judge",
    model=JUDGE_MODEL,
    tools=[risk_tool], 
    instruction="""
    ROLE: Senior Legal Arbiter.
    
    TASK: You are the final decision maker. You must issue a verdict on the contract.
    
    INPUT DATA:
    The Fact Sheet, Risks, and Counters are provided in the chat context.
    
    PROTOCOL:
    1. Review the Evidence provided in the user message.
    2. **MANDATORY:** Call the tool `assess_contract_risk`.
       - You MUST convert the 'risks' list to a JSON string for the `risks_json` argument.
       - You MUST convert the 'counters' list to a JSON string for the `counters_json` argument.
    3. Use the Tool Output (Score & Breakdown) to write your final summary.
    4. Do not calculate the score yourself. Trust the tool.
    
    OUTPUT JSON:
    {
      "verdict": "ACCEPT" | "ACCEPT WITH CAUTION" | "REJECT",
      "risk_score": 0-100,
      "confidence": 0-100,
      "summary": "Executive summary citing the score...",
      "key_factors": ["Factor 1", "Factor 2"],
      "negotiation_points": ["Action 1", "Action 2"]
    }
    """,
    output_key="final_verdict"
)
