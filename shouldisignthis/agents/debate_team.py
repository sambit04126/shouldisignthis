from google.adk.agents import ParallelAgent
from .skeptic import get_skeptic_agent
from .advocate import get_advocate_agent

def get_debate_team(api_key=None):
    """
    Creates the Debate Team parallel agent (Skeptic & Advocate).
    
    Args:
        api_key (str, optional): Google API Key for the models.
        
    Returns:
        ParallelAgent: Configured Debate Team agent.
    """
    return ParallelAgent(
        name="Debate_Team",
        sub_agents=[
            get_skeptic_agent(api_key=api_key),
            get_advocate_agent(api_key=api_key)
        ]
    )
