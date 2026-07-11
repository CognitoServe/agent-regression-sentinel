import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

db_path = Path(__file__).parent.parent / "eval_harness.db"

def get_db_connection():
    return sqlite3.connect(str(db_path))

st.set_page_config(page_title="Eval Harness Dashboard", layout="wide")
st.title("LLM Eval Harness Dashboard")

conn = get_db_connection()

# --- A. Runs Overview ---
st.header("1. Runs Overview")

runs_df = pd.read_sql_query(
    "SELECT run_id, started_at, target_agent, git_commit, is_baseline FROM runs ORDER BY started_at DESC", 
    conn
)

if not runs_df.empty:
    display_df = runs_df.copy()
    display_df['run_id'] = display_df['run_id'].str[:8]
    display_df['git_commit'] = display_df['git_commit'].str[:8]
    
    def highlight_baseline(row):
        return ['background-color: rgba(255, 215, 0, 0.2)' if row['is_baseline'] else '' for _ in row]
    
    st.dataframe(
        display_df.style.apply(highlight_baseline, axis=1),
        use_container_width=True,
        hide_index=True
    )
    
    run_options = display_df['run_id'].tolist()
    default_idx = 0
    baseline_rows = display_df[display_df['is_baseline'] == 1]
    if not baseline_rows.empty:
        default_idx = int(baseline_rows.index[0])
        
    selected_short_id = st.selectbox("Select a Run ID to filter details below:", run_options, index=default_idx)
    selected_full_id = runs_df.iloc[run_options.index(selected_short_id)]['run_id']
else:
    st.warning("No runs found in the database.")
    st.stop()


# --- B. Pass Rate Trend ---
st.header("2. Pass Rate Trend")

trend_query = """
SELECT r.started_at, s.scorer_type, AVG(s.passed) as pass_rate
FROM runs r
JOIN scores s ON r.run_id = s.run_id
WHERE s.passed IS NOT NULL
GROUP BY r.run_id, s.scorer_type
ORDER BY r.started_at ASC
"""
trend_df = pd.read_sql_query(trend_query, conn)

if not trend_df.empty:
    trend_df['pass_rate'] = trend_df['pass_rate'] * 100
    fig_trend = px.line(
        trend_df, 
        x="started_at", 
        y="pass_rate", 
        color="scorer_type",
        markers=True,
        title="Pass Rate over Time",
        labels={"started_at": "Run Timestamp", "pass_rate": "Pass Rate (%)", "scorer_type": "Scorer Type"}
    )
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("No score data available to generate trends.")


# --- C. Per-Category Breakdown ---
st.header(f"3. Per-Category Breakdown ({selected_short_id})")

cat_query = """
SELECT tc.category, s.passed, COUNT(*) as count
FROM scores s
JOIN test_cases tc ON s.test_case_id = tc.id
WHERE s.run_id = ? AND s.passed IS NOT NULL
GROUP BY tc.category, s.passed
"""
cat_df = pd.read_sql_query(cat_query, conn, params=(selected_full_id,))

if not cat_df.empty:
    cat_df['Status'] = cat_df['passed'].map({1: 'Pass', 0: 'Fail'})
    fig_cat = px.bar(
        cat_df,
        x="category",
        y="count",
        color="Status",
        barmode="group",
        color_discrete_map={'Pass': '#2e7d32', 'Fail': '#d32f2f'},
        title="Pass vs Fail by Category",
        labels={"category": "Test Category", "count": "Number of Tests"}
    )
    st.plotly_chart(fig_cat, use_container_width=True)
else:
    st.info("No category data found for the selected run.")


# --- D. Regression Report Viewer ---
st.header("4. Regression Report Viewer")

diffs_query = "SELECT DISTINCT diff_id, created_at FROM diffs ORDER BY created_at DESC"
diffs_df = pd.read_sql_query(diffs_query, conn)

if not diffs_df.empty:
    diff_options = diffs_df['diff_id'].tolist()
    default_diff_idx = 0
    if '180ed156-06f6-41c3-9980-2b06018f600f' in diff_options:
        default_diff_idx = diff_options.index('180ed156-06f6-41c3-9980-2b06018f600f')
        
    selected_diff = st.selectbox("Select a Diff ID to view report:", diff_options, index=default_diff_idx)
    report_query = "SELECT * FROM diffs WHERE diff_id = ?"
    report_df = pd.read_sql_query(report_query, conn, params=(selected_diff,))
    
    if not report_df.empty:
        regressions = report_df[report_df['verdict'] == 'regression']
        improvements = report_df[report_df['verdict'] == 'improvement']
        score_drops = report_df[report_df['verdict'] == 'score_drop']
        unchanged = len(report_df[report_df['verdict'] == 'unchanged'])
        unmeasurable = len(report_df[report_df['verdict'] == 'unmeasurable'])
        
        baseline_id = report_df.iloc[0]['baseline_run_id']
        candidate_id = report_df.iloc[0]['candidate_run_id']
        
        st.markdown(f"**Baseline:** `{baseline_id}` | **Candidate:** `{candidate_id}`")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.error(f"❌ **REGRESSIONS ({len(regressions)})**")
            for _, row in regressions.iterrows():
                st.write(f"- `{row['test_case_id']}` [{row['scorer_type']}]")
        with col2:
            st.success(f"✅ **IMPROVEMENTS ({len(improvements)})**")
            for _, row in improvements.iterrows():
                st.write(f"- `{row['test_case_id']}` [{row['scorer_type']}]")
        with col3:
            st.warning(f"⚠️ **SCORE DROPS ({len(score_drops)})**")
            for _, row in score_drops.iterrows():
                st.write(f"- `{row['test_case_id']}` [{row['scorer_type']}] ({row['baseline_score']} → {row['candidate_score']})")
                
        st.markdown(f"**Unchanged:** {unchanged} | **Unmeasurable:** {unmeasurable}")
else:
    st.info("No diff reports found in the database.")

conn.close()
