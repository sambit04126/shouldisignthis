import asyncio
import json
import time
import logging
from typing import Any, Dict, Optional, Union

from google.adk.apps.app import App
from google.adk.runners import Runner
from google.adk.plugins.logging_plugin import LoggingPlugin
from google.genai import types

from shouldisignthis.database import get_session_service
from shouldisignthis.agents.drafter import get_drafter_agent, get_comparison_drafter_agent
from shouldisignthis.agents.auditor import get_auditor_agent
from shouldisignthis.agents.debate_team import get_debate_team
from shouldisignthis.agents.bailiff import get_citation_loop
from shouldisignthis.agents.judge import get_judge_agent
from shouldisignthis.agents.arbiter import get_arbiter_agent

# ... (existing imports)

# --- STAGE 5: COMPARATOR (Face-Off) ---
async def run_stage_5_arbiter(user_id: str, session_id: str, verdict_a: dict, verdict_b: dict, api_key: str = None):
    """
    Runs the Arbiter agent to compare two contracts and decide which is safer.

    Args:
        user_id (str): The ID of the user.
        session_id (str): The unique session ID.
        verdict_a (dict): The verdict dictionary for Contract A.
        verdict_b (dict): The verdict dictionary for Contract B.
        api_key (str, optional): Google API Key. Defaults to None.

    Returns:
        dict: The comparison result containing the winner and key differences.
    """
    app_name = "Arbiter_App"
    
    # Construct the input context
    comparison_input = {
        "contract_a": verdict_a,
        "contract_b": verdict_b
    }
    
    message = types.Content(parts=[types.Part(text=f"COMPARE CONTRACTS:\n{json.dumps(comparison_input, indent=2)}")])
    
    session = await _run_agent(
        agent_factory=get_arbiter_agent,
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
    Runs the Drafter agent to generate a decision email based on the comparison result.

    Args:
        user_id (str): The ID of the user.
        session_id (str): The unique session ID.
        comparison_result (dict): The output from the Arbiter agent.
        api_key (str, optional): Google API Key. Defaults to None.

    Returns:
        dict: The drafted email and strategy notes.
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

    Args:
        raw (Union[str, Any]): The raw input, potentially a JSON string or already a dict/list.

    Returns:
        Union[Dict, list, Any]: The parsed JSON object, or an empty dict if parsing fails.
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
            
            logging.error(f"❌ JSON Parse Error: Could not parse JSON from string. Raw (truncated): {raw[:500]!r}")
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
    Generic helper function to initialize and run an ADK agent.

    Args:
        agent_factory (callable): Function that returns an Agent instance.
        app_name (str): Name of the application.
        user_id (str): The ID of the user.
        session_id (str): The unique session ID.
        message (types.Content): The input message for the agent.
        initial_state (Optional[Dict], optional): Initial state for the session. Defaults to None.
        delete_existing_session (bool, optional): Whether to clear previous session data. Defaults to False.
        api_key (Optional[str], optional): Google API Key. Defaults to None.

    Returns:
        Any: The final session object after execution.
    """
    if delete_existing_session:
        await get_session_service().delete_session(app_name=app_name, user_id=user_id, session_id=session_id)

    # Create Session if needed or update state
    if initial_state is not None:
        try:
            await get_session_service().create_session(
                app_name=app_name, user_id=user_id, session_id=session_id, state=initial_state
            )
        except Exception:
            pass

    app = App(name=app_name, root_agent=agent_factory(api_key=api_key), plugins=[LoggingPlugin()])
    runner = Runner(app=app, session_service=get_session_service())
    
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
        pass # Logs handled by plugin
        
    session = await get_session_service().get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    return session

# --- STAGE RUNNERS ---

async def run_stage_1(file_bytes: bytes, mime_type: str, user_id: str, session_id: str, api_key: Optional[str] = None) -> Dict:
    """
    Runs Stage 1: Auditor. Ingests the contract, extracts text, and performs safety checks.

    Args:
        file_bytes (bytes): The raw file content.
        mime_type (str): The MIME type of the file (e.g., 'application/pdf').
        user_id (str): The ID of the user.
        session_id (str): The unique session ID.
        api_key (Optional[str], optional): Google API Key. Defaults to None.

    Returns:
        Dict: The Auditor's output, including fact sheet and safety status.
    """
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
    """
    Runs Stage 2: Debate Team. The Skeptic and Advocate analyze the fact sheet in parallel.

    Args:
        user_id (str): The ID of the user.
        session_id (str): The unique session ID.
        fact_sheet (Dict): The extracted facts from Stage 1.
        api_key (Optional[str], optional): Google API Key. Defaults to None.

    Returns:
        tuple[Dict, float]: A tuple containing the session state (with arguments) and execution duration.
    """
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
    """
    Runs Stage 2.5: Bailiff Loop. Verifies the arguments against the full contract text.

    Args:
        user_id (str): The ID of the user.
        session_id (str): The unique session ID.
        risks (list): List of risks identified by the Skeptic.
        counters (list): List of counters identified by the Advocate.
        full_text (str): The full text of the contract.
        api_key (Optional[str], optional): Google API Key. Defaults to None.

    Returns:
        Dict: The verified arguments (risks and counters).
    """
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
    
    # Only parse clerk output if Bailiff wasn't clean (otherwise Clerk exits with non-JSON)
    clerk_output = {}
    if bailiff_verdict.get("status") != "CLEAN":
        clerk_output = parse_json(session.state.get('current_arguments'))
    
    final_args = None
    if bailiff_verdict and bailiff_verdict.get("status") == "CLEAN":
        verified = bailiff_verdict.get("verified_arguments", {})
        # Check if verified_arguments actually has content (not empty arrays)
        if verified and (verified.get("risks") or verified.get("counters")):
            final_args = verified
    elif isinstance(clerk_output, dict) and "risks" in clerk_output:
        final_args = clerk_output
    
    # Fallback if no valid output or if verified_arguments was empty
    if not final_args or (isinstance(final_args, dict) and 
                          (not final_args.get("risks") and not final_args.get("counters"))):
        final_args = {"risks": risks, "counters": counters} # Fallback
        
    return final_args

async def run_stage_3(user_id: str, session_id: str, fact_sheet: Dict, evidence: Dict, api_key: Optional[str] = None) -> Dict:
    """
    Runs Stage 3: Judge. Reviews the evidence and issues a final verdict and risk score.

    Args:
        user_id (str): The ID of the user.
        session_id (str): The unique session ID.
        fact_sheet (Dict): The extracted facts.
        evidence (Dict): The verified risks and counters.
        api_key (Optional[str], optional): Google API Key. Defaults to None.

    Returns:
        Dict: The final verdict, including risk score and summary.
    """
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
    """
    Runs Stage 4: Drafter. Generates a negotiation toolkit based on the verdict.

    Args:
        user_id (str): The ID of the user.
        session_id (str): The unique session ID.
        verdict_data (Dict): The verdict output from Stage 3.
        tone (str): The desired tone for the negotiation email.
        api_key (Optional[str], optional): Google API Key. Defaults to None.

    Returns:
        Dict: The drafted email and strategy notes.
    """
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
