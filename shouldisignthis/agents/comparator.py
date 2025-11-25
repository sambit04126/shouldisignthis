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
def get_comparator_agent(api_key=None):
    """
    Creates the Comparator agent responsible for comparing two contracts.
    
    Args:
        api_key (str, optional): Google API Key for the model.
        
    Returns:
        LlmAgent: Configured Comparator agent.
    """
    return LlmAgent(
        name="Comparator",
        model=get_judge_model(api_key=api_key), # Use the smart model (Gemini 2.5 Pro)
        output_schema=ComparisonResult,
        instruction="""
        ROLE: Senior Legal Analyst (Educational Role).
        
        TASK: Provide a comparative risk analysis of two contracts (Contract A and Contract B).
        
        INPUT DATA:
        - Contract A: Verdict, Risk Score, Summary.
        - Contract B: Verdict, Risk Score, Summary.
        
        OBJECTIVE:
        1. Compare the Risk Scores objectively.
        2. Identify key differences in terms (Liability, Termination, IP, etc.).
        3. Explain the *implications* of these differences.
        
        CRITICAL GUIDELINES (UPL PREVENTION):
        - Do NOT tell the user which contract to sign.
        - Do NOT use words like "Winner", "Recommended", or "Best Choice".
        - Focus on "Lower Risk" vs "Higher Risk".
        - Frame all output as educational information for the user to make their own decision.
        
        OUTPUT RULES:
        - Identify which contract has the mathematically lower risk score.
        - Provide a clear "Comparison Summary" highlighting the major trade-offs.
        - Break down the comparison into key categories.
        - Respond with ONLY valid JSON.
        """,
        output_key="comparison_result"
    )
