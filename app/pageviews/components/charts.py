"""
components/charts.py — All dashboard charts for HMS using Plotly
Clean, medical-themed, consistent styling
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from db import run_query


# ── Chart theme ────────────────────────────────────────────────
COLORS = {
    "primary":   "#1a3c64",
    "accent":    "#2563eb",
    "green":     "#10b981",
    "amber":     "#f59e0b",
    "red":       "#ef4444",
    "cyan":      "#06b6d4",
    "purple":    "#8b5cf6",
    "pink":      "#ec4899",
    "bg":        "#ffffff",
    "grid":      "#f0f4f8",
    "text":      "#475569",
}

CHART_LAYOUT = dict(
    paper_bgcolor = "rgba(0,0,0,0)",
    plot_bgcolor  = "rgba(0,0,0,0)",
    font          = dict(family="DM Sans, sans-serif", color=COLORS["text"], size=12),
    margin        = dict(l=10, r=10, t=40, b=10),
    xaxis         = dict(showgrid=True, gridcolor=COLORS["grid"], zeroline=False),
    yaxis         = dict(showgrid=True, gridcolor=COLORS["grid"], zeroline=False),
    legend        = dict(bgcolor="rgba(0,0,0,0)"),
)


def _apply_layout(fig, title: str = ""):
    fig.update_layout(**CHART_LAYOUT, title=dict(
        text=title, font=dict(size=14, color=COLORS["primary"]), x=0
    ))
    return fig


# ── 1. Appointments Bar Chart (last 7 days) ───────────────────
def appointments_bar_chart():
    """Bar chart: number of appointments per day for the last 7 days."""
    data = run_query("""
        SELECT appt_date::TEXT AS day,
               COUNT(*) AS total,
               SUM(CASE WHEN status='Completed'  THEN 1 ELSE 0 END) AS completed,
               SUM(CASE WHEN status='Cancelled'  THEN 1 ELSE 0 END) AS cancelled,
               SUM(CASE WHEN status IN ('Pending','Confirmed') THEN 1 ELSE 0 END) AS pending
        FROM appointments
        WHERE appt_date >= CURRENT_DATE - INTERVAL '6 days'
        GROUP BY appt_date
        ORDER BY appt_date
    """)

    if not data:
        st.info("No appointment data for the last 7 days.")
        return

    df = pd.DataFrame(data)
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Completed", x=df["day"], y=df["completed"],
                         marker_color=COLORS["green"], opacity=0.85))
    fig.add_trace(go.Bar(name="Pending",   x=df["day"], y=df["pending"],
                         marker_color=COLORS["amber"], opacity=0.85))
    fig.add_trace(go.Bar(name="Cancelled", x=df["day"], y=df["cancelled"],
                         marker_color=COLORS["red"],   opacity=0.85))
    fig.update_layout(barmode="stack")
    _apply_layout(fig, "📅 Appointments — Last 7 Days")
    st.plotly_chart(fig, use_container_width=True)


# ── 2. Revenue Line Chart (last 30 days) ─────────────────────
def revenue_line_chart():
    """Line chart: daily revenue collected over the last 30 days."""
    data = run_query("""
        SELECT DATE(payment_date)::TEXT AS day,
               SUM(amount_paid) AS revenue
        FROM payments
        WHERE payment_date >= CURRENT_DATE - INTERVAL '29 days'
        GROUP BY DATE(payment_date)
        ORDER BY DATE(payment_date)
    """)

    if not data:
        st.info("No payment data yet.")
        return

    df = pd.DataFrame(data)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["day"], y=df["revenue"],
        mode="lines+markers",
        name="Revenue",
        line=dict(color=COLORS["accent"], width=2.5),
        marker=dict(size=6, color=COLORS["accent"]),
        fill="tozeroy",
        fillcolor="rgba(37,99,235,0.08)"
    ))
    _apply_layout(fig, "💰 Daily Revenue (₹) — Last 30 Days")
    fig.update_yaxes(tickprefix="₹")
    st.plotly_chart(fig, use_container_width=True)


# ── 3. Fraud Alerts Pie Chart ─────────────────────────────────
def fraud_pie_chart():
    """Donut chart: fraud alerts by severity."""
    data = run_query("""
        SELECT severity, COUNT(*) AS count
        FROM fraud_alerts
        WHERE status = 'Open'
        GROUP BY severity
    """)

    if not data:
        st.success("✅ No open fraud alerts.")
        return

    df      = pd.DataFrame(data)
    colors  = [
        {"High": COLORS["red"], "Medium": COLORS["amber"], "Low": COLORS["green"]}.get(s, "#94a3b8")
        for s in df["severity"]
    ]
    fig = go.Figure(go.Pie(
        labels=df["severity"], values=df["count"],
        hole=0.55,
        marker=dict(colors=colors),
        textinfo="label+percent",
        hovertemplate="%{label}: %{value} alerts<extra></extra>"
    ))
    fig.update_layout(
        **{k: v for k, v in CHART_LAYOUT.items() if k not in ("xaxis","yaxis")},
        title=dict(text="🚨 Open Fraud Alerts by Severity",
                   font=dict(size=14, color=COLORS["primary"]), x=0),
        showlegend=True,
        annotations=[dict(text=f"{df['count'].sum()}<br>Alerts",
                          x=0.5, y=0.5, font_size=14,
                          font_color=COLORS["primary"], showarrow=False)]
    )
    st.plotly_chart(fig, use_container_width=True)


# ── 4. Medicine Stock Bar Chart ───────────────────────────────
def stock_bar_chart(top_n: int = 10):
    """Horizontal bar: medicine stock levels vs reorder level."""
    data = run_query(f"""
        SELECT brand_name, stock_quantity, reorder_level
        FROM medicines
        ORDER BY stock_quantity ASC
        LIMIT {top_n}
    """)

    if not data:
        st.info("No medicine data.")
        return

    df = pd.DataFrame(data)
    colors = [
        COLORS["red"]   if row["stock_quantity"] == 0 else
        COLORS["amber"] if row["stock_quantity"] <= row["reorder_level"] else
        COLORS["green"]
        for _, row in df.iterrows()
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["brand_name"], x=df["stock_quantity"],
        orientation="h",
        name="Current Stock",
        marker_color=colors,
        text=df["stock_quantity"],
        textposition="inside"
    ))
    fig.add_trace(go.Scatter(
        y=df["brand_name"], x=df["reorder_level"],
        mode="markers",
        name="Reorder Level",
        marker=dict(symbol="line-ns", size=12, color="#374151",
                    line=dict(width=2, color="#374151"))
    ))
    _apply_layout(fig, "📦 Medicine Stock Levels (Low → High)")
    fig.update_layout(height=max(300, len(df) * 35))
    st.plotly_chart(fig, use_container_width=True)


# ── 5. Daily Patient Metrics ──────────────────────────────────
def daily_metrics_chart():
    """Multi-line: daily new patients and appointments over 14 days."""
    patients_data = run_query("""
        SELECT DATE(registration_date)::TEXT AS day, COUNT(*) AS new_patients
        FROM patients
        WHERE registration_date >= CURRENT_DATE - INTERVAL '13 days'
        GROUP BY DATE(registration_date)
        ORDER BY DATE(registration_date)
    """)
    appts_data = run_query("""
        SELECT appt_date::TEXT AS day, COUNT(*) AS appointments
        FROM appointments
        WHERE appt_date >= CURRENT_DATE - INTERVAL '13 days'
        GROUP BY appt_date
        ORDER BY appt_date
    """)

    if not patients_data and not appts_data:
        st.info("No data available for the last 14 days.")
        return

    df_p = pd.DataFrame(patients_data) if patients_data else pd.DataFrame(columns=["day","new_patients"])
    df_a = pd.DataFrame(appts_data)    if appts_data    else pd.DataFrame(columns=["day","appointments"])
    df   = pd.merge(df_p, df_a, on="day", how="outer").fillna(0).sort_values("day")

    fig = go.Figure()
    if "new_patients" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["day"], y=df["new_patients"],
            mode="lines+markers", name="New Patients",
            line=dict(color=COLORS["accent"], width=2),
            marker=dict(size=5)
        ))
    if "appointments" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["day"], y=df["appointments"],
            mode="lines+markers", name="Appointments",
            line=dict(color=COLORS["green"], width=2),
            marker=dict(size=5)
        ))
    _apply_layout(fig, "📊 Daily Activity — Last 14 Days")
    st.plotly_chart(fig, use_container_width=True)


# ── 6. Department-wise Appointment Chart ──────────────────────
def department_chart():
    """Bar chart: appointments per department this month."""
    data = run_query("""
        SELECT dept.dept_name, COUNT(*) AS count
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        JOIN departments dept ON d.dept_id = dept.dept_id
        WHERE DATE_TRUNC('month', a.appt_date) = DATE_TRUNC('month', CURRENT_DATE)
        GROUP BY dept.dept_name
        ORDER BY count DESC
    """)

    if not data:
        st.info("No department data this month.")
        return

    df  = pd.DataFrame(data)
    fig = px.bar(df, x="dept_name", y="count",
                 color="count", color_continuous_scale=["#dbeafe","#1a3c64"],
                 labels={"dept_name": "Department", "count": "Appointments"})
    _apply_layout(fig, "🏥 Appointments by Department (This Month)")
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(fig, use_container_width=True)


# ── 7. Bill Status Donut Chart ────────────────────────────────
def billing_status_chart():
    """Donut: bills by payment status."""
    data = run_query("""
        SELECT status, COUNT(*) AS count, SUM(net_payable) AS total_value
        FROM bills
        GROUP BY status
    """)

    if not data:
        st.info("No billing data yet.")
        return

    df     = pd.DataFrame(data)
    colors = {
        "Paid":    COLORS["green"],
        "Partial": COLORS["amber"],
        "Unpaid":  COLORS["red"],
    }
    clrs = [colors.get(s, "#94a3b8") for s in df["status"]]

    fig = go.Figure(go.Pie(
        labels=df["status"], values=df["count"],
        hole=0.55,
        marker=dict(colors=clrs),
        textinfo="label+percent",
        customdata=df["total_value"],
        hovertemplate="%{label}: %{value} bills (₹%{customdata:,.0f})<extra></extra>"
    ))
    fig.update_layout(
        **{k: v for k, v in CHART_LAYOUT.items() if k not in ("xaxis","yaxis")},
        title=dict(text="💳 Bills by Payment Status",
                   font=dict(size=14, color=COLORS["primary"]), x=0),
    )
    st.plotly_chart(fig, use_container_width=True)
