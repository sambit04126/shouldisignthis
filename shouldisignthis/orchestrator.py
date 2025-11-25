import asyncio
import json
import time
import logging
from typing import Any, Dict, Optional, Union

from google.adk.apps.app import App
from google.adk.runners import Runner
from google.adk.plugins.logging_plugin import LoggingPlugin
from google.genai import types

from shouldisignthis.database import session_service
from shouldisignthis.agents.drafter import get_drafter_agent, get_comparison_drafter_agent
from shouldisignthis.agents.auditor import get_auditor_agent
from shouldisignthis.agents.debate_team import get_debate_team
from shouldisignthis.agents.bailiff import get_citation_loop
from shouldisignthis.agents.judge import get_judge_agent
from shouldisignthis.agents.comparator import get_comparator_agent

# ... (existing imports)

# --- STAGE 5: COMPARATOR (Face-Off) ---
async def run_stage_5_comparator(user_id: str, session_id: str, verdict_a: dict, verdict_b: dict, api_key: str = None):
    """
    Runs the Comparator agent to judge two contracts.
    """
    app_name = "Comparator_App"
    
    # Construct the input context
    comparison_input = {
        "contract_a": verdict_a,
        "contract_b": verdict_b
    }
    
    message = types.Content(parts=[types.Part(text=f"COMPARE CONTRACTS:\n{json.dumps(comparison_input, indent=2)}")])
    
    session = await _run_agent(
        agent_factory=get_comparator_agent,
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        message=message,
        initial_state={},
        api_key=api_key
    )
    
    # Extract output
    return parse_json(session.state.get('comparison_result'))

# --- STAGE 6: COMPARISON DRAFTER (Action) ---
async def run_stage_6_comparison_drafter(user_id: str, session_id: str, comparison_result: dict, api_key: str = None):
    """
    Runs the Drafter agent to generate a decision email based on the comparison.
    """
    app_name = "ComparisonDrafter_App"
    
    message = types.Content(parts=[types.Part(text=f"GENERATE DECISION BRIEF:\n{json.dumps(comparison_result, indent=2)}")])
    
    session = await _run_agent(
        agent_factory=get_comparison_drafter_agent,
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        message=message,
        initial_state={},
        api_key=api_key
    )
    
    # Extract output
    return parse_json(session.state.get('drafted_email'))


# --- HELPER FUNCTIONS ---
def parse_json(raw: Union[str, Any]) -> Union[Dict, list, Any]:
    """
    Robustly parses JSON from a string, handling markdown code fences and conversational text.
    Returns an empty dict on failure to prevent crashes.
    """
    if isinstance(raw, str):
        try:
            # 1. Try standard clean
            cleaned = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # 2. Try extracting from first { to last }
            try:
                import re
                match = re.search(r'\{.*\}', raw, re.DOTALL)
                if match:
                    return json.loads(match.group())
            except Exception:
                pass
            
            logging.error(f"❌ JSON Parse Error: Could not parse JSON from string.")
            return {} # Return empty dict to prevent AttributeError
    return raw if raw is not None else {}

async def _run_agent(
    agent_factory, 
    app_name: str, 
    user_id: str, 
    session_id: str, 
    message: types.Content, 
    initial_state: Optional[Dict] = None,
    delete_existing_session: bool = False,
    api_key: Optional[str] = None
) -> Any:
    """
    Generic helper to run an ADK agent.
    """
    if delete_existing_session:
        await session_service.delete_session(app_name=app_name, user_id=user_id, session_id=session_id)

    # Create Session if needed or update state
    if initial_state is not None:
        try:
            await session_service.create_session(
                app_name=app_name, user_id=user_id, session_id=session_id, state=initial_state
            )
        except Exception:
            pass

    app = App(name=app_name, root_agent=agent_factory(api_key=api_key), plugins=[LoggingPlugin()])
    runner = Runner(app=app, session_service=session_service)
    
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
        pass # Logs handled by plugin
        
    session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    return session

# --- STAGE RUNNERS ---

async def run_stage_1(file_bytes: bytes, mime_type: str, user_id: str, session_id: str, api_key: Optional[str] = None) -> Dict:
    """Auditor Stage: Ingests contract."""
    audit_msg = types.Content(
        role="user", 
        parts=[
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            types.Part(text="Analyze this contract. Extract full text and facts.")
        ]
    )
    
    # Always start fresh for Stage 1
    session = await _run_agent(
        agent_factory=get_auditor_agent,
        app_name="Auditor_App",
        user_id=user_id,
        session_id=session_id,
        message=audit_msg,
        initial_state={},
        delete_existing_session=True,
        api_key=api_key
    )
    return parse_json(session.state.get('auditor_output'))

async def run_stage_2(user_id: str, session_id: str, fact_sheet: Dict, api_key: Optional[str] = None) -> tuple[Dict, float]:
    """Debate Team Stage: Skeptic vs Advocate."""
    prompt = f"""
    FACT SHEET:
    {json.dumps(fact_sheet, indent=2)}

    Analyze these contract terms.
    """
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    
    start_time = time.time()
    session = await _run_agent(
        agent_factory=get_debate_team,
        app_name="Debate_App",
        user_id=user_id,
        session_id=session_id,
        message=msg,
        initial_state={'auditor_output': fact_sheet},
        delete_existing_session=True,
        api_key=api_key
    )
    duration = time.time() - start_time
    
    return session.state, duration

async def run_stage_2_5(user_id: str, session_id: str, risks: list, counters: list, full_text: str, api_key: Optional[str] = None) -> Dict:
    """Bailiff Loop Stage: Verify arguments."""
    new_state = {
        'current_arguments': {"risks": risks, "counters": counters},
        'full_text': full_text
    }
    
    msg = types.Content(role="user", parts=[types.Part(text="Verify these arguments.")])
    
    session = await _run_agent(
        agent_factory=get_citation_loop,
        app_name="Auditor_App", 
        user_id=user_id,
        session_id=session_id,
        message=msg,
        initial_state=new_state,
        delete_existing_session=True,
        api_key=api_key
    )
    
    # Logic to pick best evidence
    bailiff_verdict = parse_json(session.state.get('bailiff_verdict'))
    clerk_output = parse_json(session.state.get('current_arguments'))
    
    final_args = None
    if bailiff_verdict and bailiff_verdict.get("status") == "CLEAN":
        final_args = bailiff_verdict.get("verified_arguments")
    elif isinstance(clerk_output, dict) and "risks" in clerk_output:
        final_args = clerk_output
    
    if not final_args:
        final_args = {"risks": risks, "counters": counters} # Fallback
        
    return final_args

async def run_stage_3(user_id: str, session_id: str, fact_sheet: Dict, evidence: Dict, api_key: Optional[str] = None) -> Dict:
    """Judge Stage: Verdict."""
    context_msg = f"""
    CASE FILE: {session_id}
    
    --- FACT SHEET ---
    {json.dumps(fact_sheet, indent=2)}
    
    --- EVIDENCE FOR REVIEW ---
    RISKS: {json.dumps(evidence.get('risks', []), indent=2)}
    COUNTERS: {json.dumps(evidence.get('counters', []), indent=2)}
    
    Review the evidence and issue your verdict.
    """
    msg = types.Content(role="user", parts=[types.Part(text=context_msg)])
    
    session = await _run_agent(
        agent_factory=get_judge_agent,
        app_name="Auditor_App",
        user_id=user_id,
        session_id=session_id,
        message=msg,
        initial_state={}, 
        delete_existing_session=True,
        api_key=api_key
    )
    return parse_json(session.state.get('final_verdict'))

async def run_stage_4(user_id: str, session_id: str, verdict_data: Dict, tone: str, api_key: Optional[str] = None) -> Dict:
    """Drafter Stage: Negotiation Toolkit."""
    prompt_context = f"""
    GENERATE NEGOTIATION TOOLKIT
    
    VERDICT: {verdict_data.get('verdict')} (Score: {verdict_data.get('risk_score')})
    
    NEGOTIATION POINTS TO COVER:
    {json.dumps(verdict_data.get('negotiation_points', []), indent=2)}
    
    TONE: {tone}
    """
    msg = types.Content(role="user", parts=[types.Part(text=prompt_context)])
    
    session = await _run_agent(
        agent_factory=get_drafter_agent,
        app_name="Auditor_App",
        user_id=user_id,
        session_id=session_id,
        message=msg,
        initial_state={},
        delete_existing_session=True,
        api_key=api_key
    )
    return parse_json(session.state.get('drafted_email'))
