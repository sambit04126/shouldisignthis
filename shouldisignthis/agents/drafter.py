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
