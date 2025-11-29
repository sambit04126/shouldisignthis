import streamlit as st
import asyncio
import uuid
import os
from shouldisignthis.orchestrator import (
    run_stage_1,
    run_stage_2,
    run_stage_2_5,
    run_stage_3,
    run_stage_4,
    parse_json
)
from shouldisignthis.tools.pdf_generator import create_contract_report

def render_single_mode(api_key):
    """
    Renders the Single Contract Analysis UI mode.
    
    Handles file upload, stage execution (Auditor -> Debate -> Bailiff -> Judge -> Drafter),
    and result display.

    Args:
        api_key (str): The Google API Key to use for the agents.
    """
    st.header("📄 Single Contract Analysis")
    st.markdown("Upload a contract to analyze its risks and generate a negotiation strategy.")

    # Session State Init
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "pipeline_data" not in st.session_state:
        st.session_state.pipeline_data = {}
    if "analyzing" not in st.session_state:
        st.session_state.analyzing = False

    # --- MAIN FLOW ---
    def reset_pipeline():
        st.session_state.pipeline_data = {}
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.analyzing = False

    uploaded_file = st.file_uploader(
        "Upload Contract (PDF/Image)", 
        type=["pdf", "png", "jpg", "jpeg"], 
        on_change=reset_pipeline, 
        key="single_uploader",
        disabled=st.session_state.analyzing
    )

    st.info("🔒 **Privacy Note:** This application is **stateless**. Your document is processed in-memory and deleted immediately after analysis. No data is stored on our servers.")

    if uploaded_file:
        # Security: File Size Limit (5MB)
        if uploaded_file.size > 5 * 1024 * 1024:
            st.error("❌ File too large. Maximum size is 5MB.")
            st.stop()

        st.success(f"File uploaded: {uploaded_file.name}")
        
        # START BUTTON
        if st.button("Start Analysis", type="primary", disabled=st.session_state.analyzing):
            st.session_state.analyzing = True
            st.session_state.pipeline_data = {} # Reset data
            st.rerun()

        # RUN LOGIC
        if st.session_state.analyzing:
            try:
                # STAGE 1
                with st.status("🔍 **Stage 1: The Auditor is scanning the document...**", expanded=True) as status:
                    st.write("Extracting text and identifying key clauses...")
                    file_bytes = uploaded_file.getvalue()
                    mime_type = uploaded_file.type
                    
                    auditor_out = asyncio.run(run_stage_1(file_bytes, mime_type, "streamlit_user", st.session_state.session_id, api_key=api_key))
                    
                    if auditor_out and auditor_out.get("is_contract"):
                        # SAFETY CHECK
                        if auditor_out.get("is_safe") is False:
                            status.update(label="🚫 Document Rejected", state="error", expanded=True)
                            st.error(f"🚫 **Document Rejected: Unsafe Content**")
                            st.warning(f"Reason: {auditor_out.get('safety_reason')}")
                            st.session_state.analyzing = False # Reset state
                            st.stop()
    
                        st.session_state.pipeline_data['auditor'] = auditor_out
                        status.update(label="✅ Stage 1 Complete: Contract Ingested", state="complete", expanded=False)
                    else:
                        st.error("Document rejected: Not a contract.")
                        st.session_state.analyzing = False # Reset state
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
                
                # Done
                st.session_state.analyzing = False
                st.rerun()
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
                st.session_state.analyzing = False
                # st.rerun() # Optional, maybe just show error

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
            score = verdict.get('risk_score', 0)
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
            
            try:
                if 'toolkit' not in st.session_state.pipeline_data:
                     with st.spinner("The Drafter is writing your email..."):
                        toolkit = asyncio.run(run_stage_4("streamlit_user", st.session_state.session_id, verdict, tone, api_key=api_key))
                        st.session_state.pipeline_data['toolkit'] = toolkit
                
                if st.button("🔄 Regenerate Email"):
                     with st.spinner("The Drafter is rewriting..."):
                        toolkit = asyncio.run(run_stage_4("streamlit_user", st.session_state.session_id, verdict, tone, api_key=api_key))
                        st.session_state.pipeline_data['toolkit'] = toolkit
            except Exception as e:
                import logging
                logging.exception("Error in Stage 4 (Drafter)")
                st.error("An error occurred while generating the email. Please check the logs.")
            
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
                
                # --- PDF PREPARATION ---
                if 'pdf_report' not in st.session_state.pipeline_data:
                    with st.spinner("Preparing PDF Report..."):
                        risks_data = parse_json(st.session_state.pipeline_data['stage2_state'].get('skeptic_risks', {})).get('risks', [])
                        pdf_buffer = create_contract_report(
                            filename=uploaded_file.name,
                            verdict=verdict.get('verdict', 'UNKNOWN'),
                            risk_score=verdict.get('risk_score', 0),
                            summary=verdict.get('summary', ''),
                            risks=risks_data
                        )
                        st.session_state.pipeline_data['pdf_report'] = pdf_buffer

                # --- ACTION BUTTONS ---
                col_btn1, col_btn2 = st.columns([1, 1])
                
                with col_btn1:
                    st.link_button("🚀 Open in Email Client", mailto_link, type="primary", use_container_width=True)
                    
                with col_btn2:
                    st.download_button(
                        label="⬇️ Download PDF Report",
                        data=st.session_state.pipeline_data['pdf_report'],
                        file_name=f"ShouldISignThis_Report_{uploaded_file.name}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
