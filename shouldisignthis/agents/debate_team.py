from google.adk.agents import LlmAgent, ParallelAgent
from ..config import WORKER_MODEL
from ..tools.search_tools import search_tool

# --- A. THE SKEPTIC (Internal Logic Only - Fast) ---
skeptic_agent = LlmAgent(
    name="Skeptic",
    model=WORKER_MODEL,
    instruction="""
    ROLE: Contract Deviation Analyzer.
    
    TASK: Compare extracted contract terms against standard norms for THIS SPECIFIC CONTRACT TYPE.
    
    INPUT: The fact_sheet is provided in the user message.
    
    ANALYSIS RULES:
    1. IDENTIFY TYPE: Infer the contract type (e.g., NDA, Lease, Freelance, Employment) from the available facts.
    2. SCAN FOR MISSING: Check for clauses that are CRITICAL for *this specific type*.
       - Example: An NDA *must* have a "Confidentiality Period".
       - Example: A Lease *must* have "Rent Amount".
       - Do NOT flag missing "Payment Terms" if it's an NDA.
    3. SCAN FOR DEVIATIONS: Compare found values against industry norms for *this type*.
    4. RISK TYPES: 
       - "MISSING_CLAUSE" (e.g. No rent in a lease) -> page: null
       - "UNFAVORABLE_TERM" (e.g. 100 year NDA) -> page: [number]
    
    OUTPUT JSON (Strict Schema Example):
    {
      "risks": [
        {
          "risk": "Confidentiality period not specified",
          "severity": "HIGH",
          "page": null,
          "risk_type": "MISSING_CLAUSE", 
          "deviation_type": "UNFAVORABLE",
          "explanation": "Standard NDAs specify a duration (e.g. 2-5 years). Indefinite is risky."
        }
      ]
    }
    """,
    output_key="skeptic_risks"
)

# --- B. THE ADVOCATE (External Researcher - Smart) ---
advocate_agent = LlmAgent(
    name="Advocate",
    model=WORKER_MODEL,
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

# --- C. THE DEBATE TEAM ---
debate_team = ParallelAgent(
    name="Debate_Team",
    sub_agents=[skeptic_agent, advocate_agent]
)
