from typing import Optional, Literal
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from ..config import get_auditor_model

# --- PYDANTIC SCHEMAS (Unchanged) ---
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
    full_text: Optional[str] = None
    fact_sheet: Optional[FactSheet] = None

# --- AGENT: THE AUDITOR (The Analyst) ---
def get_auditor_agent(api_key=None):
    """
    Creates the Auditor agent responsible for initial contract analysis and fact extraction.
    Generic Version: Works on NDAs, MSAs, Leases, Employment, and Service Agreements.

    Args:
        api_key (str, optional): Google API Key for the model.

    Returns:
        LlmAgent: Configured Auditor agent.
    """
    return LlmAgent(
        name="Auditor",
        model=get_auditor_model(api_key=api_key),
        output_schema=AuditorOutput,
        instruction="""
        ROLE: Senior Contract Auditor
        TASK: Analyze the provided document. You are the first line of defense.
        
        INPUT: A document file (PDF/Image) via API context.
        
        --- ANALYSIS STEPS ---
        
        STEP 1: CONTRACT VERIFICATION
        - Determine if this document is actually a legal contract.
        - If NOT a contract: Return {"is_contract": false, ...}
        
        STEP 2: SAFETY CHECK
        - Scan for hate speech or illegal content (standard legal terms are SAFE).
        
        STEP 3: FULL TEXT EXTRACTION
        - Extract readable text verbatim.
        - CRITICAL: ENFORCE ASCII. Replace any Cyrillic/Greek homoglyphs (like \u0421 or \u0410) with their standard Latin equivalents (C and A).
        
        STEP 4: FACT EXTRACTION
        - Extract fields defined in the schema.
        - MISSING FIELD PROTOCOL: If a specific field (e.g., 'non_compete_clause') is NOT present in the text, you MUST return it with value="NOT FOUND". Do not omit the key.
        
        --- UNIVERSAL BUCKET RULES (SEMANTIC) ---
        1. 'key_obligations': 
           - This list MUST include major operational duties found anywhere in the agreement.
           - SCAN THE DOCUMENT FOR:
             * Scope of Work / Description of Services
             * Reporting / Status Update requirements
             * Change Control / Change Order procedures
             * Deliverable Acceptance / Inspection criteria
             * Confidentiality / Data Privacy obligations (if not in a specific field)
           - Do NOT duplicate 'Termination' or 'Payment' terms here if they are already in their specific fields, UNLESS they contain unique operational details.
        
        2. 'financial_terms':
           - Extract ALL financial/cost-related terms as separate list items.
           - Include: Rates, Invoicing Schedules, Late Fees, Reimbursable Expenses, Audit Rights, Taxes.
           - Granularity: Break down complex clauses. If a clause says "$150/hr payable Net 30", create two items: ["$150 per hour", "Net 30 days payment terms"].
        
        --- PAGE NUMBERING RULES ---
        - Page numbers are 1-indexed.
        - If a clause spans multiple pages, cite the page where it BEGINS.
        
        --- OUTPUT RULES ---
        - Respond with ONLY valid JSON.
        - All string values must be properly escaped.
        """,
        output_key="auditor_output"
    )