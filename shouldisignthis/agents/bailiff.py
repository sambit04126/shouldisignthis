from google.adk.agents import LlmAgent, LoopAgent
from google.adk.tools import FunctionTool
from ..config import get_worker_model

# --- A. THE EXIT TOOL ---
def approve_evidence():
    return "EVIDENCE_APPROVED"

exit_tool = FunctionTool(approve_evidence)

def get_citation_loop(api_key=None):
    """
    Creates the Bailiff Loop agent (Bailiff & Clerk) for fact verification.
    
    Args:
        api_key (str, optional): Google API Key for the models.
        
    Returns:
        LoopAgent: Configured Citation Loop agent.
    """
    # --- B. AGENT 1: THE BAILIFF (Search-Aware) ---
    bailiff_agent = LlmAgent(
        name="Bailiff",
        model=get_worker_model(api_key=api_key),
        instruction="""
        ROLE: Court Bailiff (Fact Checker).
        
        TASK: Verify that the Skeptic's Risks and Advocate's Counters are grounded in the Evidence (Full Text).
        
        INPUT:
        - Evidence: {{full_text}}
        - Current Arguments: {{current_arguments}}
        
        LOGIC:
        1. For each claim, check 'risk_type' (if applicable) and search the Evidence text.
        
        2. IF RISK_TYPE is "MISSING_CLAUSE":
           - VERIFY that the clause is indeed missing from the text.
           - If the text DOES contain this clause -> MARK CONTRADICTED.
           - If the text is indeed missing it -> STATUS: VALID.
           
        3. IF RISK_TYPE is "UNFAVORABLE_TERM" (or Counter):
           - SEARCH for the specific numbers/terms quoted (e.g. "$5,000", "Net 90").
           - If the quote is not found in text -> MARK HALLUCINATION.
           
        4. *** CRITICAL EXCEPTION FOR ADVOCATE ***:
           - IGNORE fields 'industry_context' and 'references'. These come from external research.
           - DO NOT check if URLs or industry stats exist in the contract.
           - ONLY verify the Advocate's claims about *what the contract says* (e.g. "The contract has a $5k cap").
           
        5. If all claims regarding the contract text are accurate -> STATUS: CLEAN.
        
        OUTPUT JSON:
        {
          "status": "CLEAN" or "DIRTY",
          "corrections_needed": [
             {"id": "R1", "issue": "Claims liability is unlimited, but text says capped at $5000."}
          ],
          "verified_arguments": { ...INCLUDE FULL ARGUMENT LIST IF CLEAN... }
        }
        """,
        output_key="bailiff_verdict"
    )

    # --- C. AGENT 2: THE CLERK ---
    clerk_agent = LlmAgent(
        name="Court_Clerk",
        model=get_worker_model(api_key=api_key),
        tools=[exit_tool],
        instruction="""
        ROLE: Court Clerk (Record Corrector).
        
        TASK: Fix the arguments based on the Bailiff's objections OR close the case.
        
        INPUT: {{bailiff_verdict}}
        
        LOGIC:
        1. IF status is "CLEAN": 
           - Call 'approve_evidence' immediately.
           - Do NOT output JSON.
           
        2. IF status is "DIRTY":
           - Rewrite arguments to fix errors.
           - DELETE hallucinations.
           - CORRECT contradictions.
           - Output the CLEANED JSON.
           
        OUTPUT JSON (Only if fixing):
        {
          "risks": [...updated list...],
          "counters": [...updated list...]
        }
        """,
        output_key="current_arguments"
    )

    # --- D. THE LOOP AGENT ---
    return LoopAgent(
        name="Citation_Loop",
        sub_agents=[bailiff_agent, clerk_agent],
        max_iterations=2
    )
