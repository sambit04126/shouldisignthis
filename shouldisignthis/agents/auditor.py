from typing import Optional, Literal
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from ..config import get_auditor_model

# --- PYDANTIC SCHEMAS ---
class FactField(BaseModel):
    value: str
    page: int
    confidence: Literal["HIGH", "MEDIUM", "LOW"]

class FactSheet(BaseModel):
    parties: FactField
    effective_date: Optional[FactField] = None
    termination_clause: Optional[FactField] = None
    payment_terms: Optional[FactField] = None
    liability_cap: Optional[FactField] = None
    intellectual_property: Optional[FactField] = None
    non_compete_clause: Optional[FactField] = None
    dispute_resolution: Optional[FactField] = None
    # Universal Buckets
    key_obligations: Optional[list[FactField]] = Field(default_factory=list, description="List of major obligations found")
    financial_terms: Optional[list[FactField]] = Field(default_factory=list, description="List of other financial terms (rent, royalties, etc)")

class AuditorOutput(BaseModel):
    is_contract: bool
    contract_type: Optional[str] = None
    is_safe: bool
    safety_reason: Optional[str] = None
    full_text: Optional[str] = None  # Only if is_contract & is_safe
    fact_sheet: Optional[FactSheet] = None  # Only if is_contract & is_safe

# --- AGENT: THE AUDITOR (The Analyst) ---
def get_auditor_agent(api_key=None):
    """
    Creates the Auditor agent responsible for initial contract analysis and fact extraction.
    
    Args:
        api_key (str, optional): Google API Key for the model.
        
    Returns:
        LlmAgent: Configured Auditor agent.
    """
    return LlmAgent(
        name="Auditor",
        model=get_auditor_model(api_key=api_key), # Gemini 1.5 Pro (Multimodal)
        output_schema=AuditorOutput, # Enforce Pydantic Schema
        instruction="""
        ROLE: Senior Contract Auditor
        TASK: Analyze the provided document. You are the first line of defense.
        
        INPUT: A document file (PDF/Image) via API context.
        
        --- ANALYSIS STEPS ---
        
        STEP 1: CONTRACT VERIFICATION
        - Determine if this document is actually a legal contract, agreement, or binding document.
        - If it is a menu, resume, news article, blank page, or random image -> is_contract: false.
        - If NOT a contract: Return {"is_contract": false, "contract_type": null, "is_safe": true, "safety_reason": null, "full_text": null, "fact_sheet": null}
        
        STEP 2: SAFETY CHECK
        - Scan for hate speech, dangerous acts, or illegal content (e.g., contracts for illegal services).
        - CRITICAL: Standard legal terms like "termination", "damages", "death", or "penalties" are SAFE.
        - Only flag if the context violates safety policies (violence, hate).
        - If NOT safe: Return {"is_contract": true, "contract_type": "...", "is_safe": false, "safety_reason": "Description of violation", "full_text": null, "fact_sheet": null}
        
        STEP 3: FULL TEXT EXTRACTION (Only if Step 1 & 2 pass)
        - Extract the readable text from the document verbatim.
        - This is required for the downstream citation validator.
        
        STEP 4: FACT EXTRACTION (Only if Step 1 & 2 pass)
        - Extract these fields. Use "NOT FOUND" if missing.
        - Confidence must be: "HIGH", "MEDIUM", "LOW".
        
        --- PAGE NUMBERING RULES ---
        - Page numbers are 1-indexed (first page = 1)
        - For single-page images, use page: 1
        - If a clause spans multiple pages, cite the page where it BEGINS
        
        --- OUTPUT RULES ---
        - Respond with ONLY valid JSON. No markdown code fences.
        - No explanatory text before or after the JSON.
        - All string values must be properly escaped.
        """,
        output_key="auditor_output"
    )
