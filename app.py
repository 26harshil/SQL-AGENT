import os
import sys
from pathlib import Path
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).parent.resolve()
sys.path.append(str(BASE_DIR))

import pandas as pd
import streamlit as st
import re

from utils.sql_guard import SQLGuard
from utils.python_guard import PythonGuard
from utils.database import DatabaseUtil
from utils.etl_tools import ETLTools
from models.schema import AgentSchema, DataAgentSchema
from langchain_core.messages import HumanMessage, AIMessage

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="SQL & ETL Agent Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# SHARP, ULTRA-MODERN CSS STYLING
# ==============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    
    /* Base typography and smooth rendering */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        box-sizing: border-box;
    }
    
    code, pre, .stCodeBlock {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* App Canvas */
    .stApp {
        background: radial-gradient(circle at 50% 0%, #111827 0%, #080c14 100%);
        color: #e2e8f0;
    }

    /* Remove default Streamlit top header padding */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 1350px;
    }

    /* Top Studio Header */
    .studio-header {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 22px 28px;
        margin-bottom: 24px;
        box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(16px);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
    }
    
    .studio-title {
        font-size: 26px;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .studio-subtitle {
        color: #94a3b8;
        font-size: 13.5px;
        margin-top: 4px;
        font-weight: 400;
    }

    /* Sharp Card Containers */
    .sharp-card {
        background: rgba(15, 23, 42, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 18px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(12px);
        transition: border-color 0.2s ease, transform 0.2s ease;
    }

    .sharp-card:hover {
        border-color: rgba(255, 255, 255, 0.12);
    }

    .card-title {
        font-size: 13px;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Sharp Badges */
    .badge-safe {
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.3);
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    
    .badge-danger {
        background: rgba(244, 63, 94, 0.12);
        color: #fb7185;
        border: 1px solid rgba(251, 113, 133, 0.3);
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    
    .badge-info {
        background: rgba(56, 189, 248, 0.12);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    .badge-warning {
        background: rgba(245, 158, 11, 0.12);
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.3);
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    /* Modern Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 6px;
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 44px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px;
        color: #94a3b8;
        font-size: 14px;
        font-weight: 600;
        padding: 0 20px;
        border: none !important;
        transition: all 0.2s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #f8fafc;
        background-color: rgba(255, 255, 255, 0.04);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
    }

    /* Input & Textarea Enhancements */
    .stTextInput > div > div, .stTextArea > div > div {
        background-color: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        color: #f8fafc !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }

    .stTextInput > div > div:focus-within, .stTextArea > div > div:focus-within {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        padding: 0.5rem 1.25rem;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
        border: 1px solid rgba(255, 255, 255, 0.15);
        color: white;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.35);
    }

    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%);
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5);
        transform: translateY(-1px);
    }

    .stButton > button[kind="secondary"] {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #cbd5e1;
    }

    .stButton > button[kind="secondary"]:hover {
        background: rgba(51, 65, 85, 0.8);
        color: white;
        border-color: rgba(255, 255, 255, 0.2);
    }

    /* Sidebar Clean Styling */
    section[data-testid="stSidebar"] {
        background-color: #0b0f17;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }

    /* Result metric box */
    .metric-pill {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 8px;
    }

    .metric-label {
        color: #94a3b8;
        font-size: 13px;
        font-weight: 500;
    }

    .metric-value {
        color: #f1f5f9;
        font-size: 13px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# SYSTEM HEALTH & ENVIRONMENT PROBES
# ==============================================================================
def check_docker_status():
    try:
        res = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=3)
        return res.returncode == 0
    except Exception:
        return False


def check_db_status():
    db_config = {
        "host": os.environ.get("host", "localhost"),
        "port": int(os.environ.get("port", 5432)),
        "user": os.environ.get("user", "sql_agent_reader"),
        "password": os.environ.get("password", "26102005harshil"),
        "dbname": os.environ.get("database", "postgres"),
    }
    try:
        util = DatabaseUtil(db_config)
        conn = util.get_connection()
        conn.close()
        return True, "Connected (Read-Only Role)"
    except Exception as e:
        return False, str(e)


# ==============================================================================
# CLEAN MINIMAL SIDEBAR (STATUS ONLY, NO UNNECESSARY NAVIGATION)
# ==============================================================================
with st.sidebar:
    st.markdown("### ⚡ Agent Control Hub")
    st.caption("Secure SQL Analytics & Sandboxed ETL Studio")
    st.divider()

    docker_ok = check_docker_status()
    db_ok, db_msg = check_db_status()

    st.markdown("##### System Health")
    c1, c2 = st.columns(2)
    with c1:
        if docker_ok:
            st.markdown('<span class="badge-safe">🐳 Docker OK</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge-danger">🐳 Docker Off</span>', unsafe_allow_html=True)
    with c2:
        if db_ok:
            st.markdown('<span class="badge-safe">🗄️ DB Online</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge-danger">🗄️ DB Offline</span>', unsafe_allow_html=True)

    st.divider()
    st.markdown("##### Environment Context")
    st.markdown(f"""
    <div class="metric-pill">
        <span class="metric-label">DB Host</span>
        <span class="metric-value">{os.environ.get('host', 'localhost')}:{os.environ.get('port', '5432')}</span>
    </div>
    <div class="metric-pill">
        <span class="metric-label">Access Role</span>
        <span class="metric-value">{os.environ.get('user', 'sql_agent_reader')}</span>
    </div>
    <div class="metric-pill">
        <span class="metric-label">Database</span>
        <span class="metric-value">{os.environ.get('database', 'postgres')}</span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    if st.button("🧹 Clear Session Cache", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ==============================================================================
# TOP STUDIO HEADER
# ==============================================================================
st.markdown("""
<div class="studio-header">
    <div>
        <div class="studio-title">
            <span>⚡ Data Intelligence Studio</span>
        </div>
        <div class="studio-subtitle">
            Autonomous SQL Analytical Agent & Isolated Docker ETL Pipeline
        </div>
    </div>
    <div>
        <span class="badge-info">AST Security Guardrails Active</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ==============================================================================
# UNIFIED STUDIO TABS: ONLY SQL AGENT & ETL AGENT
# ==============================================================================
tab_sql, tab_etl = st.tabs([
    "🛡️ SQL Agent Query",
    "🔄 ETL Agent Pipeline"
])


# ==============================================================================
# TAB 1: SQL AGENT QUERY
# ==============================================================================
with tab_sql:
    st.markdown("""
    <div style="margin-bottom: 16px;">
        <span style="font-size: 17px; font-weight: 700; color: #f8fafc;">Natural Language to Read-Only SQL</span>
        <p style="color: #94a3b8; font-size: 13.5px; margin: 3px 0 0 0;">
            Ask business questions in plain English. The agent refines the query, validates via AST parsing, verifies via LLM judge, and executes safely in PostgreSQL.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Preset Quick-Pick Chips
    st.markdown("<div style='font-size: 12px; font-weight: 600; color: #64748b; margin-bottom: 8px;'>QUICK QUERY PRESETS:</div>", unsafe_allow_html=True)
    pcol1, pcol2, pcol3, pcol4 = st.columns(4)
    preset_choice = None
    with pcol1:
        if st.button("💳 Payment Breakdown", use_container_width=True):
            preset_choice = "What are the different types of Payment Methods we have in our database"
    with pcol2:
        if st.button("👥 Top 5 Users", use_container_width=True):
            preset_choice = "Show me top 5 users from users table"
    with pcol3:
        if st.button("📦 Order Summary", use_container_width=True):
            preset_choice = "Count total orders grouped by status"
    with pcol4:
        if st.button("⚠️ Injection Attack Test", use_container_width=True):
            preset_choice = "Delete all records from users table where id > 10"

    # Query Input Area
    sql_input_default = preset_choice if preset_choice else "What are the different types of Payment Methods we have in our database"
    user_query = st.text_area(
        "Enter your analytical question:",
        value=sql_input_default,
        height=95,
        placeholder="e.g. Find top 10 highest value transactions in the last month...",
        help="Type any query about your database schema. Queries are strictly enforced as read-only.",
    )

    run_sql_col1, run_sql_col2 = st.columns([1, 4])
    with run_sql_col1:
        execute_sql_btn = st.button("🚀 Run SQL Agent", type="primary", use_container_width=True)

    if execute_sql_btn and user_query:
        with st.spinner("🤖 Autonomous SQL Agent executing (Curate → Generate → AST Guard → LLM Judge → PostgreSQL)..."):
            from agents.sql_analyst import sql_analyst

            try:
                result = sql_analyst.invoke({"user_question": user_query})

                # Two-column layout for sharp results display
                col_left, col_right = st.columns([1.35, 1.0])

                with col_left:
                    # 1. Curated Question
                    st.markdown("""
                    <div class="sharp-card">
                        <div class="card-title">🔍 1. Clarified Question & Intent</div>
                    """, unsafe_allow_html=True)
                    st.markdown(f"**Intent:** `{result.get('curated_ques', user_query)}`")
                    st.markdown("</div>", unsafe_allow_html=True)

                    # 2. Generated SQL Query
                    gen_sql = result.get("generated_sql_query", "")
                    guard_passed = result.get("sql_guard_passed", False)
                    badge_markup = '<span class="badge-safe">AST Validated</span>' if guard_passed else '<span class="badge-danger">AST Rejected</span>'

                    st.markdown(f"""
                    <div class="sharp-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <span class="card-title" style="margin: 0;">⚡ 2. Generated SQL Query</span>
                            {badge_markup}
                        </div>
                    """, unsafe_allow_html=True)
                    st.code(gen_sql, language="sql")
                    st.markdown("</div>", unsafe_allow_html=True)

                    # 3. Final Analytical Synthesis
                    final_ans = result.get("final_answer", "")
                    st.markdown("""
                    <div class="sharp-card">
                        <div class="card-title">💡 3. Analytical Synthesis</div>
                    """, unsafe_allow_html=True)
                    if final_ans:
                        st.markdown(final_ans)
                    else:
                        st.info("No synthesis generated.")
                    st.markdown("</div>", unsafe_allow_html=True)

                with col_right:
                    # Security Guardrails Card
                    st.markdown("""
                    <div class="sharp-card">
                        <div class="card-title">🛡️ Defense-In-Depth Security Audit</div>
                    """, unsafe_allow_html=True)

                    # Deterministic AST
                    ast_reason = result.get("sql_guard_reason", "No reason provided")
                    norm_sql = result.get("normalized_sql", None)
                    st.markdown("**1. Deterministic AST Guard (`sqlglot`):**")
                    if guard_passed:
                        st.markdown('<span class="badge-safe">PASSED • Read-Only SELECT</span>', unsafe_allow_html=True)
                        st.caption(f"Reason: {ast_reason}")
                        if norm_sql:
                            st.caption("Normalized Query:")
                            st.code(norm_sql, language="sql")
                    else:
                        st.markdown('<span class="badge-danger">REJECTED • Mutation / DDL Blocked</span>', unsafe_allow_html=True)
                        st.caption(f"Reason: {ast_reason}")

                    st.divider()

                    # LLM Safety Reviewer
                    llm_safe = result.get("is_safe", "No")
                    llm_comments = result.get("comments", "N/A")
                    st.markdown("**2. LLM Safety Judge:**")
                    if llm_safe == "Yes":
                        st.markdown('<span class="badge-safe">APPROVED • No Malicious Intent</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="badge-danger">FLAGGED UNSAFE</span>', unsafe_allow_html=True)
                    st.caption(f"Feedback: {llm_comments}")

                    st.divider()

                    # Database Raw Execution Preview
                    st.markdown("**3. PostgreSQL Execution Output:**")
                    raw_res = result.get("sql_query_execution_result", "")
                    if raw_res:
                        # Attempt to parse formatted rows into DataFrame for a sharper look
                        parsed_df = None
                        try:
                            lines = raw_res.strip().split("\n")
                            if len(lines) >= 2 and "|" in lines[0]:
                                headers = [h.strip() for h in lines[0].split("|")]
                                data_rows = []
                                for l in lines[1:]:
                                    if "|" in l and not l.startswith("-"):
                                        data_rows.append([cell.strip() for cell in l.split("|")])
                                if data_rows:
                                    parsed_df = pd.DataFrame(data_rows, columns=headers)
                        except Exception:
                            parsed_df = None

                        if parsed_df is not None and not parsed_df.empty:
                            st.dataframe(parsed_df, use_container_width=True)
                        else:
                            st.text_area("Result Output", value=raw_res, height=140, disabled=True)
                    else:
                        st.info("Query was not dispatched to database due to guardrails or query limits.")

                    st.markdown("</div>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"SQL Agent pipeline execution error: {e}")


# ==============================================================================
# TAB 2: ETL AGENT PIPELINE
# ==============================================================================
with tab_etl:
    st.markdown("""
    <div style="margin-bottom: 16px;">
        <span style="font-size: 17px; font-weight: 700; color: #f8fafc;">Autonomous ETL & Sandboxed Data Transformations</span>
        <p style="color: #94a3b8; font-size: 13.5px; margin: 3px 0 0 0;">
            Ingest data from external REST APIs and run Pandas transformations executed inside a strict AST-guarded, network-isolated Docker sandbox.
        </p>
    </div>
    """, unsafe_allow_html=True)

    etl_step1, etl_step2 = st.tabs([
        "📥 1. Ingest REST API Dataset",
        "⚡ 2. Sandboxed Pandas Transformation"
    ])

    etl_tools = ETLTools()

    # Step 1: Ingest REST API Dataset
    with etl_step1:
        st.markdown("""
        <div class="sharp-card">
            <div class="card-title">🌐 External API Data Ingestion</div>
        """, unsafe_allow_html=True)

        col_url, col_fmt, col_dir = st.columns([2.5, 1, 1.5])
        with col_url:
            api_url = st.text_input(
                "API Endpoint URL",
                value="https://pokeapi.co/api/v2/pokemon",
                help="Enter public REST API endpoint URL returning JSON data."
            )
        with col_fmt:
            out_format = st.selectbox("Target Format", ["csv", "json", "parquet"], index=0)
        with col_dir:
            out_folder = st.text_input("Target Directory", value="data/extract")

        if st.button("⚡ Extract & Ingest Dataset", type="primary"):
            with st.spinner(f"Ingesting dataset from {api_url}..."):
                res_msg = etl_tools.extract_load(api_url, out_folder, out_format)
                st.success(res_msg)

                target_file = Path(out_folder) / f"extracted_data.{out_format}"
                if target_file.is_file():
                    st.markdown("##### Ingested Dataset Preview:")
                    try:
                        if out_format == "csv":
                            df_prev = pd.read_csv(target_file, nrows=10)
                        elif out_format == "json":
                            df_prev = pd.read_json(target_file).head(10)
                        else:
                            df_prev = pd.read_parquet(target_file).head(10)
                        
                        st.dataframe(df_prev, use_container_width=True)
                        st.caption(f"File location: `{target_file}` | Previewing first {len(df_prev)} rows")
                    except Exception as err:
                        st.warning(f"Could not render preview: {err}")

        st.markdown("</div>", unsafe_allow_html=True)

    # Step 2: Sandboxed Transformation
    with etl_step2:
        st.markdown("""
        <div class="sharp-card">
            <div class="card-title">🧪 Isolated Pandas Transformation</div>
        """, unsafe_allow_html=True)

        # Discover available source datasets
        extract_dir = Path("data/extract")
        existing_files = list(extract_dir.glob("*.*")) if extract_dir.exists() else []
        file_options = [str(f) for f in existing_files if f.is_file()]

        if not file_options:
            file_options = ["data/extract/extracted_data.csv"]

        col_src, col_tf_fmt, col_tf_dir = st.columns([2, 1, 1.5])
        with col_src:
            selected_file = st.selectbox("Source Dataset", file_options)
        with col_tf_fmt:
            trans_out_format = st.selectbox("Export Format", ["csv", "parquet", "json"], index=0, key="trans_fmt_box")
        with col_tf_dir:
            trans_out_folder = st.text_input("Export Directory", value="data/transform")

        # Context & Schema Preview Expander
        if Path(selected_file).is_file():
            with st.expander("👁️ Inspect Source Dataset Schema & Sample Rows", expanded=False):
                preview_text = etl_tools.transform_load_context(selected_file)
                st.code(preview_text, language="text")

        # Transformation prompt with quick chips
        st.markdown("<div style='font-size: 12px; font-weight: 600; color: #64748b; margin-top: 10px; margin-bottom: 6px;'>SAMPLE TRANSFORMATION REQUIREMENTS:</div>", unsafe_allow_html=True)
        tchip1, tchip2, tchip3 = st.columns(3)
        tf_preset = None
        with tchip1:
            if st.button("Filter: Bulbasaur Only", key="tc1", use_container_width=True):
                tf_preset = "Filter data to only show bulbasaur pokemon and rename column name to pokemon_name"
        with tchip2:
            if st.button("Add Index & Uppercase Names", key="tc2", use_container_width=True):
                tf_preset = "Convert all text in string columns to uppercase and add a row_number index column"
        with tchip3:
            if st.button("Drop Missing & Sort", key="tc3", use_container_width=True):
                tf_preset = "Drop any empty rows, sort the dataset alphabetically by the primary column"

        trans_instruction = st.text_area(
            "Natural Language Transformation Requirement",
            value=tf_preset or "Filter data to only show bulbasaur pokemon and rename column name to pokemon_name",
            height=85,
            placeholder="Describe how to filter, transform, clean, or aggregate the data...",
        )

        if st.button("🛡️ Execute Sandboxed Transformation", type="primary"):
            with st.spinner("Generating Pandas code → PythonGuard AST validation → Docker execution..."):
                from agents.etl_analyst import transform_load_tool

                try:
                    tool_output = transform_load_tool.invoke({
                        "input_file_path": selected_file,
                        "output_folder": trans_out_folder,
                        "output_format": trans_out_format,
                        "user_question": trans_instruction,
                    })

                    st.markdown("##### Execution Summary:")
                    st.info(tool_output)

                    transformed_file = Path(trans_out_folder) / f"transformed_data.{trans_out_format}"
                    if transformed_file.is_file():
                        st.markdown("##### Transformed Dataset Preview:")
                        if trans_out_format == "csv":
                            df_trans = pd.read_csv(transformed_file)
                        elif trans_out_format == "json":
                            df_trans = pd.read_json(transformed_file)
                        else:
                            df_trans = pd.read_parquet(transformed_file)

                        st.dataframe(df_trans, use_container_width=True)

                        with open(transformed_file, "rb") as f:
                            st.download_button(
                                label=f"⬇️ Download Transformed {trans_out_format.upper()}",
                                data=f.read(),
                                file_name=transformed_file.name,
                                mime="text/csv" if trans_out_format == "csv" else "application/octet-stream",
                                use_container_width=True,
                            )
                except Exception as e:
                    st.error(f"ETL Transformation failed: {e}")

        st.markdown("</div>", unsafe_allow_html=True)
