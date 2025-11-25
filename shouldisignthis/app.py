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

# --- PATH FIX ---
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import Config
from shouldisignthis.config import configure_logging, DEMO_MODE

# Import Orchestrator
from shouldisignthis.orchestrator import (
    run_stage_1,
    run_stage_2,
    run_stage_2_5,
    run_stage_3,
    run_stage_4,
    parse_json
)

# --- SETUP ---
st.set_page_config(page_title="ShouldISignThis?", page_icon="⚖️", layout="wide")
configure_logging()


# --- UI LAYOUT ---
st.title("🏛️ ShouldISignThis?")
st.markdown("**The AI Consensus Engine for Contract Review**")

# 1. DISCLAIMER
st.warning("⚠️ **DISCLAIMER**: This tool is for educational and demonstration purposes only. It does not provide legal advice. Do not rely on these results for binding agreements. Always consult a qualified attorney.")

with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Google API Key", type="password", value=os.environ.get("GOOGLE_API_KEY", ""))
    # Security: Do not set os.environ globally in multi-user app
    
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
def reset_pipeline():
    st.session_state.pipeline_data = {}
    st.session_state.session_id = str(uuid.uuid4())

uploaded_file = st.file_uploader("Upload Contract (PDF/Image)", type=["pdf", "png", "jpg", "jpeg"], on_change=reset_pipeline)

if uploaded_file:
    # Security: File Size Limit (5MB)
    if uploaded_file.size > 5 * 1024 * 1024:
        st.error("❌ File too large. Maximum size is 5MB.")
        st.stop()

    st.success(f"File uploaded: {uploaded_file.name}")
    
    # START BUTTON (Triggers Stages 1-3)
    if st.button("Start Analysis", type="primary"):
        # Reset Pipeline Data on new run
        st.session_state.pipeline_data = {}
        
        # STAGE 1
        with st.status("🔍 **Stage 1: The Auditor is scanning the document...**", expanded=True) as status:
            st.write("Extracting text and identifying key clauses...")
            file_bytes = uploaded_file.getvalue()
            mime_type = uploaded_file.type
            
            auditor_out = asyncio.run(run_stage_1(file_bytes, mime_type, "streamlit_user", st.session_state.session_id, api_key=api_key))
            
            if auditor_out and auditor_out.get("is_contract"):
                st.session_state.pipeline_data['auditor'] = auditor_out
                status.update(label="✅ Stage 1 Complete: Contract Ingested", state="complete", expanded=False)
            else:
                st.error("Document rejected: Not a contract or unsafe.")
                st.stop()

        # STAGE 2
        with st.status("⚔️ **Stage 2: The Debate Team is arguing...**", expanded=True) as status:
            st.write("The **Skeptic** is hunting for risks while the **Advocate** searches for industry norms...")
            fact_sheet = st.session_state.pipeline_data['auditor'].get('fact_sheet')
            
            state, duration = asyncio.run(run_stage_2("streamlit_user", st.session_state.session_id, fact_sheet, api_key=api_key))
            st.session_state.pipeline_data['stage2_state'] = state
            status.update(label="✅ Stage 2 Complete: Arguments Filed", state="complete", expanded=False)

        # STAGE 2.5
        with st.status("🕵️ **Stage 2.5: The Bailiff is verifying facts...**", expanded=True) as status:
            st.write("Checking for hallucinations and verifying citations against the contract text...")
            
            risks = parse_json(st.session_state.pipeline_data['stage2_state'].get('skeptic_risks', {})).get('risks', [])
            counters = parse_json(st.session_state.pipeline_data['stage2_state'].get('advocate_defense', {})).get('counters', [])
            full_text = st.session_state.pipeline_data['auditor'].get('full_text')
            
            validated_evidence = asyncio.run(run_stage_2_5("streamlit_user", st.session_state.session_id, risks, counters, full_text, api_key=api_key))
            st.session_state.pipeline_data['evidence'] = validated_evidence
            status.update(label="✅ Stage 2.5 Complete: Evidence Secured", state="complete", expanded=False)

        # STAGE 3
        with st.status("👨‍⚖️ **Stage 3: The Judge is deliberating...**", expanded=True) as status:
            st.write("Weighing the arguments and calculating the final Risk Score...")
            
            verdict = asyncio.run(run_stage_3("streamlit_user", st.session_state.session_id, fact_sheet, st.session_state.pipeline_data['evidence'], api_key=api_key))
            st.session_state.pipeline_data['verdict'] = verdict
            status.update(label="✅ Stage 3 Complete: Verdict Issued", state="complete", expanded=False)

    # --- DISPLAY RESULTS (Persistent) ---
    if 'auditor' in st.session_state.pipeline_data:
        with st.expander("✅ Stage 1: Fact Sheet", expanded=False):
            st.json(st.session_state.pipeline_data['auditor'].get("fact_sheet"))

    if 'stage2_state' in st.session_state.pipeline_data:
        with st.expander("✅ Stage 2: Debate Arguments", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("😠 Skeptic")
                st.json(parse_json(st.session_state.pipeline_data['stage2_state'].get('skeptic_risks')))
            with col2:
                st.subheader("🛡️ Advocate")
                st.json(parse_json(st.session_state.pipeline_data['stage2_state'].get('advocate_defense')))

    if 'evidence' in st.session_state.pipeline_data:
        with st.expander("✅ Stage 2.5: Validated Evidence", expanded=False):
            st.json(st.session_state.pipeline_data['evidence'])

    if 'verdict' in st.session_state.pipeline_data:
        verdict = st.session_state.pipeline_data['verdict']
        score = verdict.get('risk_score')
        v_str = verdict.get('verdict', 'UNKNOWN').upper()
        
        st.divider()
        st.header("👨‍⚖️ Final Verdict")
        
        col_v1, col_v2 = st.columns([1, 3])
        with col_v1:
            st.metric("Risk Score", f"{score}/100", delta="-High Risk" if score < 70 else "Acceptable")
        with col_v2:
            if "REJECT" in v_str:
                st.error(f"🚫 **VERDICT: {v_str}**")
                st.markdown(f"**Reason:** {verdict.get('summary')}")
            elif "CAUTION" in v_str:
                st.warning(f"⚠️ **VERDICT: {v_str}**")
                st.markdown(f"**Reason:** {verdict.get('summary')}")
            else:
                st.success(f"✅ **VERDICT: {v_str}**")
                st.info(verdict.get('summary'))

        # --- STAGE 4: AUTO DRAFTER ---
        st.divider()
        st.header("✍️ Negotiation Toolkit")
        
        tone = st.selectbox("Select Tone", ["Professional", "Firm & Direct", "Collaborative"], index=0)
        
        # Auto-Run Logic: If verdict exists but toolkit doesn't OR tone changed (simple check: just run if missing)
        # For simplicity in this demo, we run if missing. If user changes tone, we need a button or auto-rerun.
        # Let's add a "Regenerate" button, but auto-run first time.
        
        if 'toolkit' not in st.session_state.pipeline_data:
             with st.spinner("The Drafter is writing your email..."):
                toolkit = asyncio.run(run_stage_4("streamlit_user", st.session_state.session_id, verdict, tone, api_key=api_key))
                st.session_state.pipeline_data['toolkit'] = toolkit
        
        if st.button("🔄 Regenerate Email"):
             with st.spinner("The Drafter is rewriting..."):
                toolkit = asyncio.run(run_stage_4("streamlit_user", st.session_state.session_id, verdict, tone, api_key=api_key))
                st.session_state.pipeline_data['toolkit'] = toolkit
        
        if 'toolkit' in st.session_state.pipeline_data:
            toolkit = st.session_state.pipeline_data['toolkit']
            
            st.subheader("Strategy Notes")
            st.info(toolkit.get('strategy_notes'))
            
            st.subheader("Draft Email")
            email_subject = toolkit.get('email_subject')
            email_body = toolkit.get('email_body')
            
            st.text_input("Subject", value=email_subject, key="final_subject")
            st.text_area("Body (Editable)", value=email_body, height=300, key="final_body")
            
            # Prepare Mailto Link
            import urllib.parse
            
            # Get latest values from state if edited, else use defaults
            final_subject = st.session_state.get("final_subject", email_subject)
            final_body = st.session_state.get("final_body", email_body)
            
            subject_enc = urllib.parse.quote(final_subject)
            body_enc = urllib.parse.quote(final_body)
            mailto_link = f"mailto:?subject={subject_enc}&body={body_enc}"
            
            st.link_button("🚀 Open in Email Client", mailto_link, type="primary")
