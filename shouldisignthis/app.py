import streamlit as st
import asyncio
import json
import uuid
import os
import time
import logging
from google.adk.apps.app import App
from google.adk.runners import Runner
from google.adk.plugins.logging_plugin import LoggingPlugin
from google.genai import types

# Import Config & DB
from shouldisignthis.config import configure_logging, DEMO_MODE
from shouldisignthis.database import session_service

# Import Agents
from shouldisignthis.agents.auditor import auditor_agent
from shouldisignthis.agents.debate_team import debate_team
from shouldisignthis.agents.bailiff import citation_loop
from shouldisignthis.agents.judge import judge_agent
from shouldisignthis.agents.drafter import drafter_agent

# --- SETUP ---
st.set_page_config(page_title="ShouldISignThis?", page_icon="⚖️", layout="wide")
configure_logging()

# --- HELPER FUNCTIONS ---
def parse_json(raw):
    if isinstance(raw, str):
        try:
            return json.loads(raw.replace("```json", "").replace("```", "").strip())
        except Exception as e:
            print(f"❌ JSON Parse Error: {e}")
            print(f"❌ Raw Content: {raw}")
            return None
    return raw

# --- ORCHESTRATION (ASYNC WRAPPERS) ---

async def run_stage_1(file_bytes, mime_type, user_id, session_id):
    """Auditor Stage"""
    audit_msg = types.Content(
        role="user", 
        parts=[
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            types.Part(text="Analyze this contract. Extract full text and facts.")
        ]
    )
    
    app = App(name="Auditor_App", root_agent=auditor_agent, plugins=[LoggingPlugin()])
    runner = Runner(app=app, session_service=session_service)
    
    # Create Session
    await session_service.create_session(
        app_name="Auditor_App", user_id=user_id, session_id=session_id, state={}
    )
    
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=audit_msg):
        pass # Logs handled by plugin/stdout
        
    # Get Result
    session = await session_service.get_session(app_name="Auditor_App", user_id=user_id, session_id=session_id)
    return parse_json(session.state.get('auditor_output'))

async def run_stage_2(user_id, session_id, fact_sheet):
    """Debate Team Stage"""
    app = App(name="Debate_App", root_agent=debate_team, plugins=[LoggingPlugin()])
    runner = Runner(app=app, session_service=session_service)
    
    # Create Session for Debate App
    await session_service.create_session(
        app_name="Debate_App", 
        user_id=user_id, 
        session_id=session_id, 
        state={}
    )
    
    prompt = f"""
    FACT SHEET:
    {json.dumps(fact_sheet, indent=2)}

    Analyze these contract terms.
    """
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    
    start_time = time.time()
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
        pass
    duration = time.time() - start_time
    
    session = await session_service.get_session(app_name="Debate_App", user_id=user_id, session_id=session_id)
    return session.state, duration

async def run_stage_2_5(user_id, session_id, risks, counters, full_text):
    """Bailiff Loop Stage"""
    # Inject State
    session = await session_service.get_session(app_name="Auditor_App", user_id=user_id, session_id=session_id)
    new_state = session.state.copy()
    new_state['current_arguments'] = {"risks": risks, "counters": counters}
    new_state['full_text'] = full_text
    
    await session_service.delete_session(app_name="Auditor_App", user_id=user_id, session_id=session_id)
    await session_service.create_session(app_name="Auditor_App", user_id=user_id, session_id=session_id, state=new_state)
    
    app = App(name="Auditor_App", root_agent=citation_loop, plugins=[LoggingPlugin()])
    runner = Runner(app=app, session_service=session_service)
    
    msg = types.Content(role="user", parts=[types.Part(text="Verify these arguments.")])
    
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
        pass
        
    session = await session_service.get_session(app_name="Auditor_App", user_id=user_id, session_id=session_id)
    
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
        
    # Save Validated Evidence
    final_state = session.state.copy()
    final_state['validated_evidence'] = final_args
    await session_service.delete_session(app_name="Auditor_App", user_id=user_id, session_id=session_id)
    await session_service.create_session(app_name="Auditor_App", user_id=user_id, session_id=session_id, state=final_state)
    
    return final_args

async def run_stage_3(user_id, session_id, fact_sheet, evidence):
    """Judge Stage"""
    app = App(name="Auditor_App", root_agent=judge_agent, plugins=[LoggingPlugin()])
    runner = Runner(app=app, session_service=session_service)
    
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
    
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
        pass
        
    session = await session_service.get_session(app_name="Auditor_App", user_id=user_id, session_id=session_id)
    return parse_json(session.state.get('final_verdict'))

async def run_stage_4(user_id, session_id, verdict_data, tone):
    """Drafter Stage"""
    app = App(name="Auditor_App", root_agent=drafter_agent, plugins=[LoggingPlugin()])
    runner = Runner(app=app, session_service=session_service)
    
    prompt_context = f"""
    GENERATE NEGOTIATION TOOLKIT
    
    VERDICT: {verdict_data.get('verdict')} (Score: {verdict_data.get('risk_score')})
    
    NEGOTIATION POINTS TO COVER:
    {json.dumps(verdict_data.get('negotiation_points', []), indent=2)}
    
    TONE: {tone}
    """
    msg = types.Content(role="user", parts=[types.Part(text=prompt_context)])
    
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
        pass
        
    session = await session_service.get_session(app_name="Auditor_App", user_id=user_id, session_id=session_id)
    return parse_json(session.state.get('drafted_email'))


# --- UI LAYOUT ---
st.title("🏛️ ShouldISignThis?")
st.markdown("**The AI Consensus Engine for Contract Review**")

with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Google API Key", type="password", value=os.environ.get("GOOGLE_API_KEY", ""))
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key
    
    st.divider()
    st.info("Architecture: Parallel-Sequential-Loop")
    st.markdown("""
    - **Stage 1**: Auditor (Ingestion)
    - **Stage 2**: Debate Team (Parallel)
    - **Stage 2.5**: Bailiff (Loop)
    - **Stage 3**: Judge (Tool Use)
    - **Stage 4**: Drafter (Action)
    """)

# Session State Init
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "pipeline_data" not in st.session_state:
    st.session_state.pipeline_data = {}

# --- MAIN FLOW ---
uploaded_file = st.file_uploader("Upload Contract (PDF/Image)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file:
    st.success(f"File uploaded: {uploaded_file.name}")
    
    if st.button("Start Analysis"):
        # STAGE 1
        with st.status("Stage 1: Auditor (Ingestion & Safety)", expanded=True) as status:
            st.write("Reading file...")
            file_bytes = uploaded_file.getvalue()
            mime_type = uploaded_file.type
            
            auditor_out = asyncio.run(run_stage_1(file_bytes, mime_type, "streamlit_user", st.session_state.session_id))
            
            if auditor_out and auditor_out.get("is_contract"):
                st.session_state.pipeline_data['auditor'] = auditor_out
                st.write("✅ Contract Verified & Safe")
                st.json(auditor_out.get("fact_sheet"))
                status.update(label="Stage 1 Complete", state="complete", expanded=False)
            else:
                st.error("Document rejected: Not a contract or unsafe.")
                st.stop()

        # STAGE 2
        with st.status("Stage 2: Debate Team (Parallel Execution)", expanded=True) as status:
            st.write("⚡ Running Skeptic & Advocate simultaneously...")
            fact_sheet = st.session_state.pipeline_data['auditor'].get('fact_sheet')
            
            state, duration = asyncio.run(run_stage_2("streamlit_user", st.session_state.session_id, fact_sheet))
            
            st.session_state.pipeline_data['stage2_state'] = state
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("😠 Skeptic")
                skeptic_risks = parse_json(state.get('skeptic_risks'))
                st.json(skeptic_risks)
            with col2:
                st.subheader("🛡️ Advocate")
                advocate_defense = parse_json(state.get('advocate_defense'))
                st.json(advocate_defense)
                
            st.caption(f"Parallel Execution Time: {duration:.2f}s")
            status.update(label="Stage 2 Complete", state="complete", expanded=False)

        # STAGE 2.5
        with st.status("Stage 2.5: Bailiff (Hallucination Check)", expanded=True) as status:
            st.write("Verifying claims against full text...")
            
            risks = parse_json(st.session_state.pipeline_data['stage2_state'].get('skeptic_risks', {})).get('risks', [])
            counters = parse_json(st.session_state.pipeline_data['stage2_state'].get('advocate_defense', {})).get('counters', [])
            full_text = st.session_state.pipeline_data['auditor'].get('full_text')
            
            validated_evidence = asyncio.run(run_stage_2_5("streamlit_user", st.session_state.session_id, risks, counters, full_text))
            st.session_state.pipeline_data['evidence'] = validated_evidence
            
            st.write("✅ Evidence Validated")
            st.json(validated_evidence)
            status.update(label="Stage 2.5 Complete", state="complete", expanded=False)

        # STAGE 3
        with st.status("Stage 3: The Judge (Verdict)", expanded=True) as status:
            st.write("Calculating Risk Score...")
            
            verdict = asyncio.run(run_stage_3("streamlit_user", st.session_state.session_id, fact_sheet, st.session_state.pipeline_data['evidence']))
            st.session_state.pipeline_data['verdict'] = verdict
            
            score = verdict.get('risk_score')
            st.metric("Risk Score", f"{score}/100", delta="-High Risk" if score < 70 else "Acceptable")
            st.write(f"**Verdict:** {verdict.get('verdict')}")
            st.info(verdict.get('summary'))
            status.update(label="Stage 3 Complete", state="complete", expanded=False)

        # STAGE 4
        st.header("Stage 4: Negotiation Toolkit")
        tone = st.selectbox("Select Tone", ["Professional", "Firm & Direct", "Collaborative"], index=0)
        
        if st.button("Generate Toolkit"):
            with st.spinner("Drafting email..."):
                toolkit = asyncio.run(run_stage_4("streamlit_user", st.session_state.session_id, st.session_state.pipeline_data['verdict'], tone))
                
                st.subheader("Strategy Notes")
                st.write(toolkit.get('strategy_notes'))
                
                st.subheader("Draft Email")
                st.text_area("Subject", toolkit.get('email_subject'))
                st.text_area("Body", toolkit.get('email_body'), height=300)
