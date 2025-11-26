import streamlit as st
import os
import sys

# --- PATH FIX ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shouldisignthis.config import configure_logging
from shouldisignthis.ui.single_mode import render_single_mode
from shouldisignthis.ui.compare_mode import render_compare_mode

# --- SETUP ---
st.set_page_config(page_title="ShouldISignThis?", page_icon="⚖️", layout="wide")
configure_logging()

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("⚖️ ShouldISignThis?")
    st.markdown("The AI Consensus Engine for Contract Review")
    
    # --- MODE SWITCH LOGIC ---
    if "nav_mode" not in st.session_state:
        st.session_state.nav_mode = "Should I Sign This?"

    @st.dialog("⚠️ Warning: Progress will be lost")
    def show_mode_warning(new_mode):
        st.write(f"Switching to **{new_mode}** will clear your current analysis and results.")
        st.write("Are you sure you want to switch?")
        
        col1, col2 = st.columns(2)
        if col1.button("Yes, Switch Mode", type="primary"):
            st.session_state.analyzing = False
            st.session_state.nav_mode = new_mode
            st.rerun()
            
        if col2.button("Cancel"):
            st.rerun()

    def handle_mode_change():
        # Check if we have active data that would be lost
        current_mode = st.session_state.nav_mode
        has_data = False
        
        if current_mode == "Should I Sign This?":
            # Check if single mode has data
            if st.session_state.get("pipeline_data"):
                has_data = True
        else:
            # Check if compare mode has data
            if st.session_state.get("pipeline_data_a") or st.session_state.get("pipeline_data_b"):
                has_data = True

        is_running = st.session_state.get("analyzing", False)

        # If analyzing OR has data, revert change and show warning
        if is_running or has_data:
            # The widget value has already changed to the new mode
            new_mode = st.session_state.temp_nav_mode
            # Revert the widget to the old mode for now
            st.session_state.temp_nav_mode = st.session_state.nav_mode
            show_mode_warning(new_mode)
        else:
            # Safe to switch
            st.session_state.nav_mode = st.session_state.temp_nav_mode

    mode = st.radio(
        "Select Mode",
        ["Should I Sign This?", "Which One Should I Sign?"],
        index=0 if st.session_state.nav_mode == "Should I Sign This?" else 1,
        key="temp_nav_mode",
        on_change=handle_mode_change
    )
    
    env_api_key = os.environ.get("GOOGLE_API_KEY", "")
    if env_api_key:
        api_key = env_api_key
    else:
        st.divider()
        st.header("Configuration")
        api_key = st.text_input("Google API Key", type="password", value="")
        if not api_key:
            st.warning("⚠️ Please enter your Google API Key to proceed.")
    
    st.divider()
    if st.session_state.nav_mode == "Should I Sign This?":
        st.info("Architecture: Parallel-Sequential-Loop")
        st.markdown("""
        - **Stage 1**: Auditor (Ingestion)
        - **Stage 2**: Debate Team (Parallel)
        - **Stage 2.5**: Bailiff (Loop)
        - **Stage 3**: Judge (Tool Use)
        - **Stage 4**: Drafter (Action)
        """)
    else:
        st.info("Architecture: Nested Parallelism")
        st.markdown("""
        - **Parallel Pipelines**: Run full analysis on two contracts simultaneously.
        - **Comparator Agent**: Aggregates verdicts and identifies the safer option.
        - **Comparison Drafter**: Generates a decision brief.
        """)

# --- MAIN RENDER ---
if st.session_state.nav_mode == "Should I Sign This?":
    render_single_mode(api_key)
else:
    render_compare_mode(api_key)
