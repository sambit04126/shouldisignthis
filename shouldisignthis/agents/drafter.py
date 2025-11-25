from google.adk.agents import LlmAgent
from ..config import get_worker_model

def get_drafter_agent(api_key=None):
    """
    Creates the Drafter agent responsible for generating the negotiation toolkit.
    
    Args:
        api_key (str, optional): Google API Key for the model.
        
    Returns:
        LlmAgent: Configured Drafter agent.
    """
    return LlmAgent(
        name="Drafter",
        model=get_worker_model(api_key=api_key),
        instruction="""
        ROLE: Professional Legal Correspondent & Strategy Coach.
        
        TASK: Generate a "Negotiation Toolkit" for the User based on the Verdict and Negotiation Points provided in the input.
        
        1. STRATEGY: Internal advice on how to handle this negotiation.
        2. SCRIPT: The actual email to send to the other party.
        
        GUIDELINES:
        1. STRATEGY NOTES (Internal Context):
           - Explain *why* we are asking for these changes based on the risks found.
           - Identify which points are likely "Deal Breakers" vs. "Nice to Haves".
           - Example: "The IP clause is critical, but you can probably compromise on the payment terms if they push back."
           
        2. EMAIL DRAFT (External Script):
           - Subject Line: Professional and clear.
           - Body: Ready to Copy/Paste.
           - Use the negotiation points provided to write specific, actionable requests.
           - Sign off as "[Your Name]" (User will replace).
        
        OUTPUT JSON:
        {
          "strategy_notes": "Brief bullet points on how to approach the negotiation.",
          "email_subject": "Subject line for the email.",
          "email_body": "Full text of the email to the other party. Use placeholders like [Your Name] where appropriate."
        }
        """,
        output_key="drafted_email"
    )

def get_comparison_drafter_agent(api_key=None):
    """
    Creates the Drafter agent responsible for generating a comparison summary email.
    
    Args:
        api_key (str, optional): Google API Key for the model.
        
    Returns:
        LlmAgent: Configured Drafter agent for comparisons.
    """
    return LlmAgent(
        name="ComparisonDrafter",
        model=get_worker_model(api_key=api_key),
        instruction="""
        ROLE: Strategic Legal Advisor.
        
        TASK: Generate a "Decision Brief" email for the User to send to their stakeholders (e.g., Boss, Client, Partner) based on the Comparative Risk Analysis.
        
        INPUT: Comparison Result JSON (Better Risk Score, Comparison Summary, Key Differences).
        
        OBJECTIVE:
        1. Summarize the findings clearly.
        2. Explain WHY one contract is safer than the other.
        3. Highlight the critical trade-offs.
        
        OUTPUT FORMAT:
        1. STRATEGY NOTES: Internal advice on how to present this decision.
        2. EMAIL DRAFT: A professional email to a stakeholder recommending the safer option (or explaining the risks of both).
        
        OUTPUT JSON:
        {
          "strategy_notes": "Brief bullet points on how to present this comparison.",
          "email_subject": "Subject line for the email (e.g., Contract Review: Option A vs Option B).",
          "email_body": "Full text of the email. Professional tone. Summarize the key risks and the recommended path forward."
        }
        """,
        output_key="drafted_email"
    )
