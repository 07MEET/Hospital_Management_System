"""
components.py — FIXED
Fix: metric_row was rendering raw HTML instead of styled cards
Solution: use st.metric() for all metrics — Streamlit handles rendering
"""
import streamlit as st
import pandas as pd


def show_dataframe(data: list, columns: dict = None, height: int = 400):
    """Render a list of dicts as a styled dataframe."""
    if not data:
        empty_state()
        return
    df = pd.DataFrame(data)
    if columns:
        df = df[[c for c in columns.keys() if c in df.columns]]
        df.columns = [columns[c] for c in df.columns]
    st.dataframe(df, use_container_width=True, height=height)


def empty_state(icon: str = "📭", message: str = "No records found."):
    st.markdown(f"""
    <div style="text-align:center;padding:2.5rem;color:#94a3b8;">
        <div style="font-size:2.5rem;margin-bottom:0.5rem;">{icon}</div>
        <div style="font-size:0.9rem;">{message}</div>
    </div>
    """, unsafe_allow_html=True)


def divider():
    st.markdown("---")


def validation_errors(errors: list) -> bool:
    if errors:
        for e in errors:
            st.error(f"❌ {e}")
        return True
    return False


def success_toast(msg: str):  st.success(f"✅ {msg}")
def error_toast(msg: str):    st.error(f"❌ {msg}")
def warning_toast(msg: str):  st.warning(f"⚠️ {msg}")
def info_toast(msg: str):     st.info(f"ℹ️ {msg}")