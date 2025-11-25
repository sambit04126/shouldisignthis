from google.adk.agents import LlmAgent, ParallelAgent
from ..config import get_worker_model
from ..tools.search_tools import search_tool

def get_debate_team(api_key=None):
    """
    Creates the Debate Team parallel agent (Skeptic & Advocate).
    
    Args:
        api_key (str, optional): Google API Key for the models.
        
    Returns:
        ParallelAgent: Configured Debate Team agent.
    """
    # 1. THE SKEPTIC (Finds Risks)
    skeptic_agent = LlmAgent(
        name="Skeptic",
        model=get_worker_model(api_key=api_key),
        instruction="""
        ROLE: Paranoid Contract Skeptic.
        
        TASK: Compare extracted contract terms against standard norms for THIS SPECIFIC CONTRACT TYPE.
        
        INSTRUCTIONS:
        1. IDENTIFY TYPE: Infer the contract type (e.g., NDA, Lease, Freelance, Employment) from the available facts.
        2. FIND RISKS: Identify clauses that are missing, vague, or unfavorable for THAT specific type.
           - Example: Missing "Payment Terms" is critical for a Freelance Contract, but irrelevant for a standard NDA.
           - Example: "Perpetual Non-Compete" is high risk for Employment, but "Perpetual Confidentiality" is standard for NDAs.
        3. BE RUTHLESS: Assume the other party is trying to trick us.
        
        INPUT:
        {{auditor_output}}
        
        OUTPUT JSON:
        {
          "risks": [
            {
              "risk": "Short description",
              "severity": "HIGH/MEDIUM/LOW",
              "page": 1,
              "risk_type": "MISSING_CLAUSE" or "UNFAVORABLE_TERM" or "AMBIGUOUS",
              "deviation_type": "UNFAVORABLE" or "NON_STANDARD",
              "explanation": "Why this is bad for this specific contract type."
            }
          ]
        }
        """,
        output_key="skeptic_risks"
    )

    # 2. THE ADVOCATE (External Researcher - Smart)
    advocate_agent = LlmAgent(
        name="Advocate",
        model=get_worker_model(api_key=api_key),
        tools=[search_tool], # <--- POWER UP!
        instruction="""
        ROLE: Business Deal Strategist & Researcher.
        
        TASK: Provide industry context for contract terms.
        
        INPUT: The fact_sheet is provided in the user message.
        
        PROTOCOL:
        1. Review the terms.
        2. If a term seems unfavorable (e.g., "Liability Cap $1000"), use `Google Search` to check if this is standard for the specific industry mentioned (or general freelance work).
        3. Example Search: "Standard liability cap for freelance graphic design 2025".
        4. Use the search results to strengthen your defense.
        5. CITATION MANDATE: You must include the specific URLs of the websites you used to form your defense.
        
        --- OUTPUT RULES ---
        - Respond with ONLY valid JSON.
        - Do NOT include any introductory text (e.g. "Here is the analysis").
        - Do NOT use markdown code blocks.
        
        OUTPUT JSON (strict format):
        {
          "counters": [
            {
              "topic": "Liability Cap",
              "counter": "While $1,000 seems low, search results indicate typical caps for micro-contracts range from $1k-$5k.",
              "confidence": "HIGH",
              "industry_context": "Backed by search: 60% of small service agreements use fees-paid caps.",
              "references": ["https://example.com/freelance-standards", "https://legalblog.com/liability-caps"]
            }
          ]
        }
        """,
        output_key="advocate_defense"
    )

    # 3. PARALLEL EXECUTION
    return ParallelAgent(
        name="Debate_Team",
        sub_agents=[skeptic_agent, advocate_agent]
    )
