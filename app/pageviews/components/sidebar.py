"""
components/sidebar.py — Role-based sidebar navigation for HMS
"""
import streamlit as st
from auth import logout


# ── Nav items per role ─────────────────────────────────────────
NAV_ITEMS = {
    "Admin": [
        ("📊", "Dashboard",        "dashboard"),
        ("👥", "All Patients",     "patients"),
        ("📅", "Appointments",     "appointments"),
        ("👨‍⚕️", "Doctors",         "doctors"),
        ("🔬", "Lab Overview",     "lab"),
        ("💰", "Billing Overview", "billing"),
        ("📋", "Audit Log",        "audit"),
        ("⚙️", "Settings",         "settings"),
    ],
    "Doctor": [
        ("📊", "My Dashboard",     "dashboard"),
        ("📅", "My Appointments",  "appointments"),
        ("🩺", "Diagnose & Prescribe", "diagnose"),
        ("🔬", "Lab Orders",       "lab"),
    ],
    "Receptionist": [
        ("📊", "Dashboard",        "dashboard"),
        ("🧑‍⚕️", "Register Patient", "register"),
        ("📅", "Book Appointment", "book"),
        ("📋", "Today's Queue",    "queue"),
    ],
    "Lab_Tech": [
        ("📊", "Dashboard",        "dashboard"),
        ("⏳", "Pending Orders",   "pending"),
        ("✅", "Enter Results",    "results"),
    ],
    "Pharmacist": [
        ("📊", "Dashboard",        "dashboard"),
        ("💊", "Dispense Medicine","dispense"),
        ("📦", "Inventory",        "inventory"),
        ("⚠️", "Low Stock Alerts", "lowstock"),
    ],
    "Billing_Staff": [
        ("📊", "Dashboard",        "dashboard"),
        ("🧾", "Generate Bill",    "generate"),
        ("💳", "Record Payment",   "payment"),
    ],
}

# Role display labels
ROLE_LABELS = {
    "Admin":         "System Administrator",
    "Doctor":        "Physician",
    "Receptionist":  "Front Desk",
    "Lab_Tech":      "Lab Technician",
    "Pharmacist":    "Pharmacist",
    "Billing_Staff": "Billing Staff",
}

# Role accent colors (for visual differentiation)
ROLE_COLORS = {
    "Admin":         "#f59e0b",
    "Doctor":        "#3b82f6",
    "Receptionist":  "#10b981",
    "Lab_Tech":      "#06b6d4",
    "Pharmacist":    "#8b5cf6",
    "Billing_Staff": "#ec4899",
}


def render_sidebar(user: dict) -> str:
    """
    Render the sidebar and return the currently selected page key.
    """
    role  = user["role"]
    items = NAV_ITEMS.get(role, [])

    with st.sidebar:
        # ── Logo & App Name ──────────────────────────────
        st.markdown("""
        <div style="padding:1.5rem 1rem 1rem;
                    border-bottom:1px solid rgba(255,255,255,0.1);
                    margin-bottom:0.75rem;">
            <div style="font-size:2rem;text-align:center;">🏥</div>
            <div style="font-family:'DM Serif Display',serif;
                        font-size:1.3rem;color:#ffffff;
                        font-weight:600;text-align:center;
                        margin-top:6px;letter-spacing:-0.5px;">
                MediCare HMS
            </div>
            <div style="font-size:0.65rem;color:#93c5fd;
                        text-align:center;letter-spacing:2px;
                        text-transform:uppercase;margin-top:2px;">
                Hospital Management
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── User Info Card ───────────────────────────────
        role_color = ROLE_COLORS.get(role, "#64748b")
        role_label = ROLE_LABELS.get(role, role)

        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.07);
                    border-radius:12px;padding:0.85rem 1rem;
                    margin:0 0 1rem;
                    border-left:3px solid {role_color};">
            <div style="font-size:0.95rem;font-weight:700;
                        color:#ffffff;margin-bottom:2px;">
                👤 {user['username']}
            </div>
            <div style="font-size:0.72rem;color:{role_color};
                        text-transform:uppercase;letter-spacing:1px;
                        font-weight:600;">
                {role_label}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Navigation ───────────────────────────────────
        st.markdown("""
        <div style="font-size:0.65rem;color:#64748b;
                    text-transform:uppercase;letter-spacing:2px;
                    padding:0 0.25rem;margin-bottom:0.4rem;">
            Navigation
        </div>
        """, unsafe_allow_html=True)

        # Track selected page in session state
        if "current_page" not in st.session_state:
            st.session_state["current_page"] = items[0][2] if items else "dashboard"

        selected_key = st.session_state["current_page"]

        for icon, label, key in items:
            is_active = (key == selected_key)
            bg        = "rgba(255,255,255,0.12)" if is_active else "transparent"
            border    = f"border-left:3px solid {role_color};" if is_active else "border-left:3px solid transparent;"
            weight    = "700" if is_active else "400"
            color     = "#ffffff" if is_active else "#94a3b8"

            if st.button(
                f"{icon}  {label}",
                key=f"nav_{key}",
                use_container_width=True,
            ):
                st.session_state["current_page"] = key
                st.rerun()

        # ── Divider ──────────────────────────────────────
        st.markdown("""
        <div style="height:1px;background:rgba(255,255,255,0.08);
                    margin:1rem 0;"></div>
        """, unsafe_allow_html=True)

        # ── System Status ────────────────────────────────
        from db import test_connection
        db_ok, db_msg = test_connection()
        db_status = "🟢 Online" if db_ok else "🔴 Offline"

        st.markdown(f"""
        <div style="font-size:0.72rem;color:#64748b;
                    padding:0 0.25rem;line-height:1.8;">
            <div style="color:#94a3b8;margin-bottom:4px;">System Status</div>
            <div>Database: <span style="color:{'#10b981' if db_ok else '#ef4444'}">
                {db_status}</span></div>
            <div style="color:#475569;margin-top:6px;font-size:0.65rem;">
                Secure connection ✓
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Logout ───────────────────────────────────────
        if st.button("🚪  Logout", use_container_width=True, key="sidebar_logout"):
            logout()

    return st.session_state.get("current_page", "dashboard")
