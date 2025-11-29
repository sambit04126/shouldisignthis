from google.adk.agents import LlmAgent
from ..config import get_worker_model
from ..tools.search_tools import search_tool

def get_advocate_agent(api_key=None):
    """
    Creates the Advocate agent responsible for defending the contract with external research.

    Args:
        api_key (str, optional): Google API Key for the model.

    Returns:
        LlmAgent: Configured Advocate agent.
    """
    return LlmAgent(
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
