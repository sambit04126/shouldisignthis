from typing import Optional, List
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from ..config import get_judge_model

# --- PYDANTIC SCHEMAS ---
class ComparisonPoint(BaseModel):
    category: str = Field(..., description="e.g., Liability, Payment Terms, Termination")
    contract_a_observation: str = Field(..., description="Objective observation of Contract A's term")
    contract_b_observation: str = Field(..., description="Objective observation of Contract B's term")
    risk_assessment: str = Field(..., description="Which one carries higher risk and why (educational)")

class ComparisonResult(BaseModel):
    better_risk_score: str = Field(..., description="'Contract A' or 'Contract B' (based purely on score)")
    comparison_summary: str = Field(..., description="Educational summary of the key risk differences.")
    key_differences: List[ComparisonPoint] = Field(..., description="List of head-to-head comparisons.")

# --- AGENT: THE COMPARATOR (The Analyst) ---
def get_arbiter_agent(api_key=None):
    """
    Creates the Comparator agent responsible for comparing two contracts.
    
    Args:
        api_key (str, optional): Google API Key for the model.
        
    Returns:
        LlmAgent: Configured Comparator agent.
    """
    return LlmAgent(
        name="Arbiter",
        model=get_judge_model(api_key=api_key), # Use the smart model (Gemini 2.5 Pro)
        output_schema=ComparisonResult,
        instruction="""
        ROLE: Chief Legal Arbiter (Strategic Decision Maker).
        
        TASK: Provide a comparative risk analysis of two contracts (Contract A and Contract B).
        
        INPUT DATA:
        - Contract A: Verdict, Risk Score, Summary.
        - Contract B: Verdict, Risk Score, Summary.
        
        OBJECTIVE:
        1. Compare the Risk Scores AND Verdicts.
        2. Identify key differences in terms (Liability, Termination, IP, etc.).
        3. Explain the *implications* of these differences.
        
        CRITICAL LOGIC:
        - **SCORE MEANING**: The Risk Score is a SAFETY SCORE (0-100).
          - **100 = SAFE / LOW RISK**
          - **0 = DANGEROUS / HIGH RISK**
          - Therefore, a HIGHER score is BETTER.
        
        - **Verdict Priority**: If one contract is "REJECT" and the other is "CAUTION" or "ACCEPT", the "REJECT" contract is generally the worse option, regardless of the score.
        - **Consistency Check**: A low score (e.g., 38) SHOULD correspond to a REJECT/CAUTION verdict. If a contract has a Low Score but is ACCEPTED, *that* is a paradox to investigate.
        
        CRITICAL GUIDELINES (UPL PREVENTION):
        - Do NOT tell the user which contract to sign.
        - Do NOT use words like "Winner", "Recommended", or "Best Choice".
        - Focus on "Lower Risk" vs "Higher Risk" but explain the nuance of "Too Good To Be True".
        - Frame all output as educational information for the user to make their own decision.
        
        OUTPUT RULES:
        - Identify which contract has the better *overall risk profile* (considering the Verdict).
        - Provide a clear "Comparison Summary" highlighting the major trade-offs.
        - Break down the comparison into key categories.
        - Respond with ONLY valid JSON.
        """,
        output_key="comparison_result"
    )
