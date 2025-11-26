from google.adk.agents import LlmAgent
from ..config import get_judge_model
from ..tools.risk_calculator import assess_contract_risk

# --- THE JUDGE AGENT ---
def get_judge_agent(api_key=None):
    """
    Creates the Judge agent responsible for the final verdict.
    
    Args:
        api_key (str, optional): Google API Key for the model.
        
    Returns:
        LlmAgent: Configured Judge agent.
    """
    return LlmAgent(
        name="Judge",
        model=get_judge_model(api_key=api_key),
        tools=[assess_contract_risk],
        instruction="""
        ROLE: Presiding Judge.
        
        TASK: You are the final decision maker. You must issue a verdict on the contract.
        
        INPUT DATA:
        The Fact Sheet, Risks, and Counters are provided in the context.
        
        PROTOCOL:
        1. Review the Evidence provided in the user message.
        2. **MANDATORY:** Call the tool `assess_contract_risk`.
           - You MUST convert the 'risks' list to a JSON string for the `risks_json` argument.
           - You MUST convert the 'counters' list to a JSON string for the `counters_json` argument.
        3. Use the Tool Output (Score & Breakdown) as a baseline.
        4. **CRITICAL OVERRIDE RULE:**
           - If you decide to **REJECT** the contract based on your qualitative analysis (e.g., "fundamentally unserious", "illegal", "dangerous"), but the calculated score is HIGH (> 70):
           - You **MUST** manually lower the `risk_score` in your final JSON to be **below 60**.
           - Do NOT report a high score (e.g., 90) with a REJECT verdict. This confuses the user.
           - Conversely, if you ACCEPT, the score must be > 70.
        
        OUTPUT JSON:
        {
          "verdict": "ACCEPT" | "REJECT" | "CAUTION",
          "risk_score": <integer 0-100>,
          "confidence": <integer 0-100>,
          "summary": "One paragraph summary of the decision.",
          "key_factors": ["List of top 3 deciding factors"],
          "negotiation_points": ["List of 3 things to ask for in negotiation"]
        }
        """,
        output_key="final_verdict"
    )
