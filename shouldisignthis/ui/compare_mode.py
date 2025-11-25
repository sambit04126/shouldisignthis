import streamlit as st
import asyncio
import uuid
import os
from shouldisignthis.orchestrator import (
    run_stage_1,
    run_stage_2,
    run_stage_2_5,
    run_stage_3,
    run_stage_5_comparator,
    run_stage_6_comparison_drafter,
    parse_json
)

def render_compare_mode(api_key):
    st.header("🥊 Contract Face-Off")
    st.markdown("**Compare two contracts and let the AI decide the winner.**")

    # Session State
    if "session_id_a" not in st.session_state:
        st.session_state.session_id_a = str(uuid.uuid4())
    if "session_id_b" not in st.session_state:
        st.session_state.session_id_b = str(uuid.uuid4())
    if "pipeline_data_a" not in st.session_state:
        st.session_state.pipeline_data_a = {}
    if "pipeline_data_b" not in st.session_state:
        st.session_state.pipeline_data_b = {}
    if "comparison_result" not in st.session_state:
        st.session_state.comparison_result = None

    # --- HELPER: Run Single Pipeline ---
    async def run_pipeline(file_bytes, mime_type, user_id, session_id, pipeline_key, status_container):
        """Runs Stages 1-3 for a single contract."""
        
        # STAGE 1: Auditor
        with status_container:
            st.write("🔍 Stage 1: Auditing...")
            auditor_out = await run_stage_1(file_bytes, mime_type, user_id, session_id, api_key=api_key)
            if not auditor_out or not auditor_out.get("is_contract"):
                st.error("Invalid Contract")
                return None
            st.session_state[pipeline_key]['auditor'] = auditor_out
            st.write("✅ Stage 1 Complete")

            # STAGE 2: Debate
            st.write("⚔️ Stage 2: Debating...")
            fact_sheet = auditor_out.get('fact_sheet')
            state, _ = await run_stage_2(user_id, session_id, fact_sheet, api_key=api_key)
            st.session_state[pipeline_key]['stage2_state'] = state
            st.write("✅ Stage 2 Complete")

            # STAGE 2.5: Bailiff
            st.write("🕵️ Stage 2.5: Verifying...")
            risks = parse_json(state.get('skeptic_risks', {})).get('risks', [])
            counters = parse_json(state.get('advocate_defense', {})).get('counters', [])
            full_text = auditor_out.get('full_text')
            validated_evidence = await run_stage_2_5(user_id, session_id, risks, counters, full_text, api_key=api_key)
            st.session_state[pipeline_key]['evidence'] = validated_evidence
            st.write("✅ Stage 2.5 Complete")

            # STAGE 3: Judge
            st.write("👨‍⚖️ Stage 3: Judging...")
            verdict = await run_stage_3(user_id, session_id, fact_sheet, validated_evidence, api_key=api_key)
            st.session_state[pipeline_key]['verdict'] = verdict
            st.write("✅ Stage 3 Complete")
            
            return verdict

    # --- UI LAYOUT ---
    col1, col2 = st.columns(2)

    with col1:
        st.header("Contract A")
        file_a = st.file_uploader("Upload Contract A", type=["pdf", "png", "jpg"], key="file_a")

    with col2:
        st.header("Contract B")
        file_b = st.file_uploader("Upload Contract B", type=["pdf", "png", "jpg"], key="file_b")

    # START BUTTON
    if file_a and file_b:
        if st.button("🚀 Start Face-Off", type="primary"):
            # Reset
            st.session_state.pipeline_data_a = {}
            st.session_state.pipeline_data_b = {}
            st.session_state.comparison_result = None
            
            # Run Parallel Pipelines
            async def run_parallel():
                task_a = run_pipeline(file_a.getvalue(), file_a.type, "user_a", st.session_state.session_id_a, "pipeline_data_a", col1)
                task_b = run_pipeline(file_b.getvalue(), file_b.type, "user_b", st.session_state.session_id_b, "pipeline_data_b", col2)
                return await asyncio.gather(task_a, task_b)

            with st.spinner("Running parallel analysis..."):
                verdict_a, verdict_b = asyncio.run(run_parallel())
            
            if verdict_a and verdict_b:
                with st.spinner("🤔 The Comparator is deciding the winner..."):
                    comparison = asyncio.run(run_stage_5_comparator("comparator_user", str(uuid.uuid4()), verdict_a, verdict_b, api_key=api_key))
                    st.session_state.comparison_result = comparison

    # --- RESULTS ---
    if st.session_state.comparison_result:
        res = st.session_state.comparison_result
        
        st.divider()
        st.markdown("<h2 style='text-align: center;'>📊 Comparative Risk Analysis</h2>", unsafe_allow_html=True)
        st.warning("⚠️ **EDUCATIONAL USE ONLY**: This tool provides a side-by-side comparison of risk factors. It does not provide legal advice or recommend which contract to sign.")
        
        # Scoreboard
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            # Need to access verdict_a/b from session state if not in local scope
            # But wait, verdict_a/b are local variables in the button click block.
            # We need to persist them or re-extract them.
            # Actually, we can just get them from pipeline_data_a/b['verdict']
            v_a = st.session_state.pipeline_data_a.get('verdict', {})
            v_b = st.session_state.pipeline_data_b.get('verdict', {})
            
            st.metric("Contract A Risk Score", f"{v_a.get('risk_score')}/100", delta_color="inverse")
        with col_s2:
            st.metric("Contract B Risk Score", f"{v_b.get('risk_score')}/100", delta_color="inverse")

        st.info(f"**Analysis Summary:** {res.get('comparison_summary')}")
        
        st.subheader("Key Differences")
        for point in res.get('key_differences', []):
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                st.markdown(f"**{point.get('category')}**")
                st.caption(point.get('risk_assessment'))
            with c2:
                st.caption("Contract A")
                st.write(point.get('contract_a_observation'))
            with c3:
                st.caption("Contract B")
                st.write(point.get('contract_b_observation'))
            st.divider()

        st.success(f"💡 **Recommendation:** {res.get('comparison_summary')}")
        
        # --- STAGE 6: COMPARISON DRAFTER ---
        st.divider()
        st.header("📧 Decision Brief")
        
        if 'comparison_email' not in st.session_state:
            with st.spinner("Writing decision email..."):
                email_toolkit = asyncio.run(run_stage_6_comparison_drafter("comparator_user", str(uuid.uuid4()), res, api_key=api_key))
                st.session_state.comparison_email = email_toolkit
                
        if 'comparison_email' in st.session_state:
            email_data = st.session_state.comparison_email
            
            st.subheader("Strategy Notes")
            st.info(email_data.get('strategy_notes'))
            
            st.subheader("Draft Email")
            email_subject = email_data.get('email_subject')
            email_body = email_data.get('email_body')
            
            st.text_input("Subject", value=email_subject, key="comp_subject")
            st.text_area("Body", value=email_body, height=300, key="comp_body")
            
            # Mailto Link
            import urllib.parse
            final_subject = st.session_state.get("comp_subject", email_subject)
            final_body = st.session_state.get("comp_body", email_body)
            
            subject_enc = urllib.parse.quote(final_subject)
            body_enc = urllib.parse.quote(final_body)
            mailto_link = f"mailto:?subject={subject_enc}&body={body_enc}"
            
            st.link_button("🚀 Open in Email Client", mailto_link, type="primary")
