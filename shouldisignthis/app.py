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
    
    mode = st.radio(
        "Select Mode",
        ["Should I Sign This?", "Which One Should I Sign?"],
        index=0
    )
    
    st.divider()
    
    st.header("Configuration")
    env_api_key = os.environ.get("GOOGLE_API_KEY", "")
    if env_api_key:
        api_key = env_api_key
    else:
        st.header("Configuration")
        api_key = st.text_input("Google API Key", type="password", value="")
        if not api_key:
            st.warning("⚠️ Please enter your Google API Key to proceed.")
    
    st.divider()
    if mode == "Should I Sign This?":
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
if mode == "Should I Sign This?":
    render_single_mode(api_key)
else:
    render_compare_mode(api_key)
