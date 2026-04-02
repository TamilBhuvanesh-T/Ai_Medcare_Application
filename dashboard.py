import streamlit as st
import os
import pandas as pd

# --------------------------
# Access shared backend (from app.py)
# --------------------------
from backend.pipeline import run_full_pipeline
from backend.rag.vector_store import load_vector_store

UPLOAD_DIR = "medical_data/pdfs"

# --------------------------
# Header
# --------------------------
st.markdown("""
<div style="display:flex; align-items:center; gap:10px; margin-top:20px;">
    <div style="font-size:28px;">🩺</div>
    <div style="font-size:26px; font-weight:700;">AI Health Intelligence Dashboard</div>
</div>
<div style="font-size:13px; margin-top:-5px;">
    Smart analysis of your medical reports using AI
</div>
""", unsafe_allow_html=True)

# --------------------------
# Layout
# --------------------------
col1, col2, col3 = st.columns([1.3, 2.5, 1.5])

# --------------------------
# 🟥 COLUMN 1 → Risk + Activities
# --------------------------
with col1:
    st.markdown("### ⚠️ Risk Assessment")

    if st.session_state.analysis:
        r = st.session_state.analysis["risk"]

        st.markdown(f"""
        <div style="background:#fff4f4; padding:15px; border-radius:12px;">
            <b>⚠️ {r['risk_level']}</b><br>
            <h2 style="margin:5px 0;">{r['risk_score']} / 100</h2>
            <span>Immediate follow-up recommended</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:10px;'>", unsafe_allow_html=True)

    # Diabetes Risk
        st.markdown("""
    <div style="margin-top:8px; font-size:13px;">
        <b>📊 Diabetes Risk</b><br>
        <div style="
            height:6px;
            border-radius:4px;
            background: linear-gradient(to right, #facc15, #fb7185);
            width:90%;
        "></div>
        High Risk • 90%
    </div>
    """, unsafe_allow_html=True)

    # Kidney Risk
        st.markdown("""
    <div style="margin-top:8px; font-size:13px;">
        <b>❤️ Kidney Risk</b><br>
        <div style="
            height:6px;
            border-radius:4px;
            background: linear-gradient(to right, #facc15, #fb7185);
            width:80%;
        "></div>
        High Risk • 80%
    </div>
    """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)


        # Suggested Activities (based on risk)
        st.markdown("### 🏃 Suggested Activities")

        if r["risk_score"] > 70:
            activities = [
                "🚶 Daily walking (30 mins)",
                "💧 Drink more water",
                "🥗 Reduce sugar intake",
                "🩺 Consult doctor regularly"
            ]
        else:
            activities = [
                "🏃 Maintain active lifestyle",
                "🥗 Balanced diet",
                "💤 Proper sleep",
                "🧘 Stress management"
            ]

        for act in activities:
            st.markdown(f"• {act}")

    else:
        st.info("Run analysis to see risk & activities")

# --------------------------
# 🟩 COLUMN 2 → Summary
# --------------------------
with col2:
    st.markdown("### 💬 Key Insights")
    st.caption("AI-generated summary of your health report")

    if st.session_state.analysis:
        summary = st.session_state.analysis["summary"]

        for line in summary.split("."):
            if line.strip():
                st.markdown(f"• {line.strip()}")

        # Trend Graph
        trends = st.session_state.analysis["trends"]

        for param, t in trends.items():
            if len(t["dates"]) > 1:
                df = pd.DataFrame({
                    "Date": t["dates"],
                    "Value": t["values"]
                })
                df["Date"] = pd.to_datetime(df["Date"])
                st.line_chart(df.set_index("Date"))
                break

    else:
        st.info("Run analysis to see insights")

# --------------------------
# 🟦 COLUMN 3 → Login + Upload
# --------------------------
with col3:

    # 🔐 Login (UI only)
    

    # 📄 Upload
    st.markdown("### 📄 Upload Medical Reports")

    st.markdown("""
    <div style="
        border:2px dashed #cbd5e1;
        border-radius:10px;
        padding:15px;
        text-align:center;
        color:#6c757d;
        font-size:13px;">
        📄 Drag & drop your medical PDF files here
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(" ", type=["pdf"], label_visibility="collapsed")

    if uploaded:
        path = os.path.join(UPLOAD_DIR, uploaded.name)

        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(uploaded.getbuffer())

            st.success("File uploaded successfully")
        else:
            st.info("Already uploaded")

    # Run Pipeline
    if st.button("🧠 Run Medical AI Analysis", use_container_width=True):
        with st.spinner("Running medical pipeline..."):
            result = run_full_pipeline()
            st.session_state.analysis = result
            st.session_state.vector_store = load_vector_store(384)

        st.success("Analysis completed")